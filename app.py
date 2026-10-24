import json
import os
import re
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent
KB_PATH = BASE_DIR / "knowledge_base.json"

st.set_page_config(page_title="SupportMate AI", page_icon="🛠️", layout="wide")

STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "for", "of", "and",
    "or", "in", "on", "at", "my", "our", "i", "we", "it", "this", "that",
    "what", "how", "can", "you", "please", "with", "from", "be", "as", "by",
    "has", "have", "had", "not", "when", "issue", "problem", "error"
}

# Small synonym map helps simple search match common ways users describe issues.
SYNONYMS = {
    "500": {"internal", "server", "payment", "api"},
    "slow": {"latency", "timeout", "performance"},
    "signin": {"login", "authentication"},
    "log": {"logs", "logging"},
    "db": {"database", "connection"},
    "unauthorized": {"401", "token", "authentication"},
    "forbidden": {"403", "permission", "authorization"},
    "upload": {"file", "storage"},
}

def tokenize(text):
    """Convert text into lowercase words and expand a few known synonyms."""
    words = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    words = {w for w in words if w not in STOP_WORDS}
    expanded = set(words)
    for word in words:
        expanded.update(SYNONYMS.get(word, set()))
    return expanded

@st.cache_data
def load_knowledge_base():
    with open(KB_PATH, "r", encoding="utf-8") as file:
        return json.load(file)

def entry_text(entry):
    """Combine fields used for retrieval; the source fields are still displayed separately."""
    parts = [
        entry["title"], entry["category"], entry["escalation_team"],
        " ".join(entry["symptoms"]),
        " ".join(entry["diagnostic_checks"]),
        " ".join(entry["known_resolution"]),
        entry.get("notes", "")
    ]
    return " ".join(parts)

def retrieve(query, entries, top_k=3):
    """Transparent keyword-overlap retrieval; returns scores and matching entries."""
    query_terms = tokenize(query)
    if not query_terms:
        return []
    scored = []
    for entry in entries:
        entry_terms = tokenize(entry_text(entry))
        overlap = query_terms & entry_terms
        # Jaccard-like score avoids simply favoring longer entries.
        score = len(overlap) / max(1, len(query_terms | entry_terms))
        # Boost direct title/symptom matches so specific issues rank higher.
        title_terms = tokenize(entry["title"])
        symptom_terms = tokenize(" ".join(entry["symptoms"]))
        score += 0.18 * len(query_terms & title_terms)
        score += 0.12 * len(query_terms & symptom_terms)
        scored.append((score, entry, sorted(overlap)))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item for item in scored[:top_k] if item[0] > 0]

def generate_answer(query, results):
    """
    If OPENAI_API_KEY is configured, ask an LLM to summarize only retrieved facts.
    Otherwise use a deterministic, source-grounded response so the prototype still runs.
    """
    if not results:
        return (
            "I couldn't find a sufficiently relevant entry in the current knowledge base. "
            "Please share the exact error message or code, the affected service, when it began, "
            "and whether the issue affects one user or many. Do not include passwords, tokens, or secrets."
        ), "No matching source"

    top_score, top_entry, _ = results[0]
    # Conservative threshold: ask for clarification rather than forcing a weak match.
    if top_score < 0.08:
        return (
            "I found no strong match in the available knowledge base. Please provide the exact "
            "error code/message, affected service, when it started, and the scope of impact. "
            "I won't guess a resolution without supporting documentation."
        ), "No sufficiently strong match"

    # Optional AI generation. The model is instructed to use retrieved entries only.
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            context = []
            for score, entry, _ in results:
                context.append({
                    "id": entry["id"],
                    "title": entry["title"],
                    "symptoms": entry["symptoms"],
                    "diagnostic_checks": entry["diagnostic_checks"],
                    "known_resolution": entry["known_resolution"],
                    "escalation_team": entry["escalation_team"],
                    "notes": entry.get("notes", "")
                })
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a technical support assistant. Use only the supplied knowledge-base "
                            "entries. Do not invent commands, causes, or resolutions. Clearly separate "
                            "documented facts from suggested checks. If the entries do not answer the issue, "
                            "say the knowledge base is insufficient and ask concise clarifying questions. "
                            "Never request secrets. Give numbered troubleshooting steps and identify the "
                            "escalation team when supported. Mention the KB ID(s) used."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"User issue: {query}\nRetrieved knowledge-base entries:\n{json.dumps(context, indent=2)}"
                    }
                ]
            )
            return response.choices[0].message.content, "OpenAI API"
        except Exception as exc:
            # Fall back safely if API setup fails; don't expose internal exception details to end users.
            fallback = build_grounded_answer(top_entry)
            return fallback + "\n\n_AI generation was unavailable, so a source-grounded template was used._", "Local fallback"

    return build_grounded_answer(top_entry), "Local knowledge-base template"

def build_grounded_answer(entry):
    """Construct a useful answer directly from documented fields."""
    lines = [
        f"### Likely area: {entry['category']}",
        f"**Recommended checks**"
    ]
    lines.extend([f"{i}. {step}" for i, step in enumerate(entry["diagnostic_checks"], start=1)])
    lines.append("**Documented resolution guidance**")
    lines.extend([f"- {step}" for step in entry["known_resolution"]])
    lines.append(f"**Escalate to:** {entry['escalation_team']}")
    if entry.get("notes"):
        lines.append(f"**Important note:** {entry['notes']}")
    lines.append(f"**Source:** {entry['id']} — {entry['title']}")
    return "\n\n".join(lines)

entries = load_knowledge_base()

st.title("🛠️ SupportMate AI")
st.caption("A sample AI assistant for investigating common technical support issues.")
with st.sidebar:
    st.header("About this prototype")
    st.write("Searches a small simulated knowledge base and shows the supporting source.")
    st.write("AI generation is optional. Without an API key, it uses a source-grounded response template.")
    st.divider()
    st.subheader("Try an example")
    examples = [
        "The payment API is returning a 500 error",
        "My application cannot connect to the database",
        "Users are unable to log in",
        "The application is very slow",
        "Our API returns 401 unauthorized",
        "File upload keeps failing",
        "The printer is making a strange noise"
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state["issue_input"] = example

st.markdown("Describe the issue in plain language. Avoid including passwords, tokens, or other secrets.")
default_value = st.session_state.get("issue_input", "")
issue = st.text_area(
    "Technical issue",
    value=default_value,
    placeholder="Example: The payment API is returning a 500 error...",
    height=100,
    key="issue_text"
)

if st.button("Investigate issue", type="primary"):
    if not issue.strip():
        st.warning("Please describe the technical issue first.")
    else:
        results = retrieve(issue, entries)
        answer, mode = generate_answer(issue, results)
        st.session_state["last_query"] = issue
        st.session_state["last_answer"] = answer
        st.session_state["last_mode"] = mode
        st.session_state["last_results"] = [
            {"score": score, "entry": entry, "overlap": overlap}
            for score, entry, overlap in results
        ]

if "last_answer" in st.session_state:
    st.subheader("Troubleshooting guidance")
    st.markdown(st.session_state["last_answer"])
    st.caption(f"Response method: {st.session_state.get('last_mode', 'Unknown')}")

    st.subheader("Knowledge-base sources")
    results = st.session_state.get("last_results", [])
    if not results:
        st.info("No source was strong enough to support a recommendation.")
    else:
        for item in results:
            entry = item["entry"]
            with st.expander(f"{entry['id']} — {entry['title']} (retrieval score: {item['score']:.3f})"):
                st.write(f"**Category:** {entry['category']}")
                st.write("**Symptoms:** " + "; ".join(entry["symptoms"]))
                st.write("**Diagnostic checks:**")
                for check in entry["diagnostic_checks"]:
                    st.write(f"- {check}")
                st.write("**Known resolution:**")
                for resolution in entry["known_resolution"]:
                    st.write(f"- {resolution}")
                st.write(f"**Escalation team:** {entry['escalation_team']}")
                if entry.get("notes"):
                    st.warning(entry["notes"])

st.divider()
st.caption("Demo only: sample data, keyword-based retrieval, and optional LLM generation. Verify all steps against official runbooks before using them in real systems.")
