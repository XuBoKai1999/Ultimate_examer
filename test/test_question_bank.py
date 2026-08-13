import copy
import json
from pathlib import Path
import tempfile
import unittest

from question_bank import load_question_bank, load_question_banks


ISO17025_BANK = Path(__file__).parents[1] / "Bank" / "ISO17025_question_bank.json"


def valid_bank(bank_id="sample-bank"):
    return {
        "schema_version": "1.0",
        "id": bank_id,
        "title": "Sample Bank",
        "language": "en",
        "sections": [{
            "id": "general",
            "title": "General",
            "questions": [{
                "id": "q1",
                "text": "Question?",
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "answer": "a",
            }],
        }],
    }


class QuestionBankTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write(self, data, name="bank.json"):
        path = self.directory / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def assert_invalid(self, data, message):
        with self.assertRaisesRegex(ValueError, message):
            load_question_bank(self.write(data))

    def test_readme_minimal_bank_loads(self):
        bank = load_question_bank(self.write(valid_bank()))
        self.assertEqual("sample-bank", bank.id)
        self.assertEqual("general", bank.sections[0].id)
        self.assertEqual("q1", bank.sections[0].questions[0].id)
        self.assertEqual("a", bank.sections[0].questions[0].options[0].id)

    def test_iso17025_bank_is_canonical(self):
        bank = load_question_bank(ISO17025_BANK)
        self.assertEqual("iso17025-training-2017-zh-hant", bank.id)
        self.assertEqual([23, 25, 32, 20, 13], [len(section.questions) for section in bank.sections])
        self.assertEqual(113, sum(len(section.questions) for section in bank.sections))

    def test_malformed_json(self):
        path = self.directory / "bad.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, r"bad\.json at line 1, column 2"):
            load_question_bank(path)

    def test_unsupported_schema_version(self):
        data = valid_bank()
        data["schema_version"] = "2.0"
        self.assert_invalid(data, "unsupported schema_version '2.0'")

    def test_missing_required_field(self):
        data = valid_bank()
        del data["language"]
        self.assert_invalid(data, "missing required field.*language")

    def test_unknown_fields_at_every_level(self):
        mutations = (
            lambda data: data.update(extra=True),
            lambda data: data["sections"][0].update(extra=True),
            lambda data: data["sections"][0]["questions"][0].update(extra=True),
            lambda data: data["sections"][0]["questions"][0]["options"][0].update(extra=True),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                data = valid_bank()
                mutate(data)
                self.assert_invalid(data, "unknown field.*extra")

    def test_invalid_id_at_every_level(self):
        targets = (
            lambda data: data.update(id="Bad ID"),
            lambda data: data["sections"][0].update(id="Bad ID"),
            lambda data: data["sections"][0]["questions"][0].update(id="Bad ID"),
            lambda data: data["sections"][0]["questions"][0]["options"][0].update(id="Bad ID"),
        )
        for mutate in targets:
            with self.subTest(mutate=mutate):
                data = valid_bank()
                mutate(data)
                self.assert_invalid(data, "invalid id")

    def test_duplicate_section_id(self):
        data = valid_bank()
        data["sections"].append(copy.deepcopy(data["sections"][0]))
        self.assert_invalid(data, "duplicate section id")

    def test_duplicate_question_id_across_sections(self):
        data = valid_bank()
        second = copy.deepcopy(data["sections"][0])
        second["id"] = "other"
        data["sections"].append(second)
        self.assert_invalid(data, "duplicate question id")

    def test_duplicate_option_id(self):
        data = valid_bank()
        data["sections"][0]["questions"][0]["options"][1]["id"] = "a"
        self.assert_invalid(data, "duplicate option id")

    def test_empty_required_string(self):
        data = valid_bank()
        data["sections"][0]["questions"][0]["text"] = "  "
        self.assert_invalid(data, "text must be a non-empty string")

    def test_empty_sections(self):
        data = valid_bank()
        data["sections"] = []
        self.assert_invalid(data, "sections must contain at least 1")

    def test_empty_questions(self):
        data = valid_bank()
        data["sections"][0]["questions"] = []
        self.assert_invalid(data, "questions must contain at least 1")

    def test_fewer_than_two_options(self):
        data = valid_bank()
        data["sections"][0]["questions"][0]["options"] = [{"id": "a", "text": "A"}]
        self.assert_invalid(data, "options must contain at least 2")

    def test_answer_must_reference_option(self):
        data = valid_bank()
        data["sections"][0]["questions"][0]["answer"] = "c"
        self.assert_invalid(data, "answer 'c' does not reference an option id")

    def test_invalid_tags(self):
        for tags, message in ((["ok", ""], "non-empty strings"), (["same", "same"], "duplicates")):
            with self.subTest(tags=tags):
                data = valid_bank()
                data["sections"][0]["questions"][0]["tags"] = tags
                self.assert_invalid(data, message)

    def test_optional_fields_load(self):
        data = valid_bank()
        data.update(description="Description", source="book.pdf")
        question = data["sections"][0]["questions"][0]
        question.update(number="12A", source="p. 3", tags=["topic", "review"], note="Checked")
        bank = load_question_bank(self.write(data))
        loaded = bank.sections[0].questions[0]
        self.assertEqual(("Description", "book.pdf"), (bank.description, bank.source))
        self.assertEqual(("12A", "p. 3", ("topic", "review"), "Checked"),
                         (loaded.number, loaded.source, loaded.tags, loaded.note))

    def test_array_order_is_preserved(self):
        data = valid_bank()
        first_question = data["sections"][0]["questions"][0]
        first_question["options"] = [
            {"id": "z", "text": "Last letter first"},
            {"id": "a", "text": "First letter second"},
        ]
        first_question["answer"] = "z"
        second_section = copy.deepcopy(data["sections"][0])
        second_section["id"] = "first-by-name"
        second_section["questions"][0]["id"] = "q2"
        data["sections"].insert(0, second_section)
        bank = load_question_bank(self.write(data))
        self.assertEqual(["first-by-name", "general"], [section.id for section in bank.sections])
        self.assertEqual(["z", "a"], [option.id for option in bank.sections[1].questions[0].options])

    def test_multiple_bank_loading(self):
        paths = [self.write(valid_bank("first"), "first.json"), self.write(valid_bank("second"), "second.json")]
        self.assertEqual(["first", "second"], [bank.id for bank in load_question_banks(paths)])

    def test_duplicate_bank_id(self):
        paths = [self.write(valid_bank(), "first.json"), self.write(valid_bank(), "second.json")]
        with self.assertRaisesRegex(ValueError, r"second\.json: duplicate bank id 'sample-bank'.*first\.json"):
            load_question_banks(paths)

    def test_number_must_be_a_string(self):
        data = valid_bank()
        data["sections"][0]["questions"][0]["number"] = 1
        self.assert_invalid(data, "number must be a non-empty string")


if __name__ == "__main__":
    unittest.main()
