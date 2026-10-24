import json
import re
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent
ENTRIES = json.loads((BASE_DIR / "knowledge_base.json").read_text(encoding="utf-8"))
STOP = {"the", "a", "an", "is", "are", "to", "for", "of", "and", "my", "i", "it", "issue", "error", "problem"}
def tokens(text):
    return {w for w in re.findall(r"[a-zA-Z0-9]+", text.lower()) if w not in STOP}
def retrieve(query):
    q = tokens(query)
    ranked = []
    for entry in ENTRIES:
        corpus = " ".join([entry["title"], *entry["symptoms"], *entry["diagnostic_checks"]])
        t = tokens(corpus)
        score = len(q & t) / max(1, len(q | t))
        ranked.append((score, entry["id"]))
    return sorted(ranked, reverse=True)

class RetrievalSmokeTests(unittest.TestCase):
    def test_payment_api(self):
        self.assertEqual(retrieve("payment API returns 500 error")[0][1], "KB-001")
    def test_database_connection(self):
        self.assertEqual(retrieve("cannot connect to database")[0][1], "KB-002")
    def test_login(self):
        self.assertEqual(retrieve("users cannot log in")[0][1], "KB-003")
    def test_upload(self):
        self.assertEqual(retrieve("file upload fails")[0][1], "KB-006")

if __name__ == "__main__":
    unittest.main()
