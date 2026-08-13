import json
from pathlib import Path
import tempfile
import unittest

from wrong_answers import WrongAnswerStore


class WrongAnswerStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "wrong.json"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_add_persists_across_instances_without_duplicates(self):
        store = WrongAnswerStore(self.path)
        store.add("bank-one", "q2")
        store.add("bank-one", "q1")
        store.add("bank-one", "q1")
        store.add("bank-two", "q1")

        loaded = WrongAnswerStore(self.path)
        self.assertTrue(loaded.contains("bank-one", "q1"))
        self.assertTrue(loaded.contains("bank-one", "q2"))
        self.assertTrue(loaded.contains("bank-two", "q1"))
        self.assertFalse(loaded.contains("bank-one", "q3"))
        self.assertEqual({"bank-one": ["q1", "q2"], "bank-two": ["q1"]}, json.loads(self.path.read_text()))

    def test_missing_file_is_empty(self):
        self.assertFalse(WrongAnswerStore(self.path).contains("bank", "q1"))

    def test_remove_only_affects_matching_bank_and_question(self):
        store = WrongAnswerStore(self.path)
        store.add("bank-one", "q1")
        store.add("bank-one", "q2")
        store.add("bank-two", "q1")
        store.remove("bank-one", "q1")
        loaded = WrongAnswerStore(self.path)
        self.assertFalse(loaded.contains("bank-one", "q1"))
        self.assertTrue(loaded.contains("bank-one", "q2"))
        self.assertTrue(loaded.contains("bank-two", "q1"))

    def test_prune_only_affects_the_loaded_bank(self):
        store = WrongAnswerStore(self.path)
        store.add("loaded", "current")
        store.add("loaded", "stale")
        store.add("not-loaded", "stale")
        store.prune("loaded", {"current"})
        loaded = WrongAnswerStore(self.path)
        self.assertTrue(loaded.contains("loaded", "current"))
        self.assertFalse(loaded.contains("loaded", "stale"))
        self.assertTrue(loaded.contains("not-loaded", "stale"))

    def test_clear_banks_does_not_affect_other_banks(self):
        store = WrongAnswerStore(self.path)
        store.add("selected-one", "q1")
        store.add("selected-two", "q2")
        store.add("other", "q3")
        store.clear_banks({"selected-one", "selected-two"})
        loaded = WrongAnswerStore(self.path)
        self.assertFalse(loaded.contains("selected-one", "q1"))
        self.assertFalse(loaded.contains("selected-two", "q2"))
        self.assertTrue(loaded.contains("other", "q3"))

    def test_invalid_file_is_rejected(self):
        self.path.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid wrong-answer file"):
            WrongAnswerStore(self.path)


if __name__ == "__main__":
    unittest.main()
