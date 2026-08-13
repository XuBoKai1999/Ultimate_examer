import unittest
from unittest.mock import patch

from app import (
    App, ExamSession, MAX_FONT_SIZE, MIN_FONT_SIZE, PracticeSession, RADIO_TRISTATE_VALUE, TEXT, ZOOM_BINDINGS,
    adjusted_font_size, questions_from_banks, select_questions, update_wrong_record, wheel_zoom_change,
    wrong_questions_from_banks, tree_layout,
)
from question_bank import Option, Question, QuestionBank, Section, load_question_bank
from wrong_answers import WrongAnswerStore
from pathlib import Path
import tempfile


def question(question_id="q1", answer="b"):
    return Question(
        id=question_id,
        text=f"Question {question_id}?",
        options=(Option("a", "A"), Option("b", "B")),
        answer=answer,
    )


def bank(bank_id, *question_ids):
    return QuestionBank(
        schema_version="1.0",
        id=bank_id,
        title=bank_id,
        language="en",
        sections=(Section("section", "Section", tuple(question(item) for item in question_ids)),),
    )


class PracticeSessionTests(unittest.TestCase):
    def test_all_selection_preserves_pool_order(self):
        items = [question("q1"), question("q2"), question("q3")]
        self.assertEqual(["q1", "q2", "q3"], [item.id for item in select_questions(items, "all")])

    def test_random_selection_uses_requested_count_without_duplicates(self):
        items = [question("q1"), question("q2"), question("q3")]
        with patch("app.random.sample", return_value=[items[2], items[0]]) as sample:
            selected = select_questions(items, "random", count=2)
        sample.assert_called_once_with(items, 2)
        self.assertEqual(["q3", "q1"], [item.id for item in selected])

    def test_range_selection_is_one_based_inclusive_and_ignores_number(self):
        items = [question("q1"), question("q2"), question("q3"), question("q4")]
        self.assertEqual(["q2", "q3"], [item.id for item in select_questions(items, "range", start=2, end=3)])

    def test_invalid_selection_parameters(self):
        items = [question("q1"), question("q2"), question("q3")]
        for kwargs in ({"count": 0}, {"count": 4}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "invalid count"):
                select_questions(items, "random", **kwargs)
        for start, end in ((0, 2), (1, 4), (3, 2)):
            with self.subTest(start=start, end=end), self.assertRaisesRegex(ValueError, "invalid range"):
                select_questions(items, "range", start=start, end=end)

    def test_sequential_preserves_original_order(self):
        session = PracticeSession([question("q1"), question("q2"), question("q3")])
        self.assertEqual(["q1", "q2", "q3"], [item.id for item in session.questions])

    def test_random_reorders_without_duplicates(self):
        questions = [question("q1"), question("q2"), question("q3")]
        with patch("app.random.shuffle", side_effect=lambda items: items.reverse()) as shuffle:
            session = PracticeSession(questions, random_order=True)
        shuffle.assert_called_once()
        self.assertEqual(["q3", "q2", "q1"], [item.id for item in session.questions])
        self.assertEqual(3, len({id(item) for item in session.questions}))

    def test_unanswered_navigation_previous_and_jump(self):
        session = PracticeSession([question("q1"), question("q2"), question("q3")])
        self.assertTrue(session.next())
        self.assertEqual("q2", session.current.id)
        self.assertTrue(session.previous())
        self.assertEqual("q1", session.current.id)
        self.assertTrue(session.jump(2))
        self.assertEqual("q3", session.current.id)
        self.assertEqual("unanswered", session.status(2))

    def test_answer_and_result_survive_navigation(self):
        session = PracticeSession([question("q1"), question("q2")])
        self.assertFalse(session.answer("a"))
        self.assertEqual("incorrect", session.status(0))
        session.next()
        self.assertTrue(session.answer("b"))
        self.assertEqual("correct", session.status(1))
        session.previous()
        self.assertEqual("a", session.answers[0])
        self.assertEqual("incorrect", session.status(0))
        with self.assertRaisesRegex(ValueError, "already answered"):
            session.answer("b")

    def test_radio_selection_tracks_each_question_answer(self):
        session = PracticeSession([question("q1"), question("q2")])
        self.assertEqual("", session.answers.get(session.index, ""))
        session.answer("a")
        self.assertEqual("a", session.answers.get(session.index, ""))
        session.next()
        self.assertEqual("", session.answers.get(session.index, ""))
        session.previous()
        self.assertEqual("a", session.answers.get(session.index, ""))
        self.assertNotEqual("", RADIO_TRISTATE_VALUE)

    def test_navigation_boundaries(self):
        session = PracticeSession([question("q1"), question("q2")])
        self.assertFalse(session.can_previous)
        self.assertFalse(session.previous())
        self.assertEqual(0, session.index)
        session.jump(1)
        self.assertFalse(session.can_next)
        self.assertFalse(session.next())
        self.assertEqual(1, session.index)
        self.assertFalse(session.jump(2))

    def test_multiple_banks_form_one_pool_for_both_orders(self):
        pool = questions_from_banks([bank("first", "q1", "q2"), bank("second", "q3")])
        self.assertEqual(["q1", "q2", "q3"], [item.id for item in PracticeSession(pool).questions])
        with patch("app.random.shuffle", side_effect=lambda items: items.reverse()):
            randomized = PracticeSession(pool, random_order=True)
        self.assertEqual(["q3", "q2", "q1"], [item.id for item in randomized.questions])

    def test_rejects_empty_session_and_unknown_option(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            PracticeSession([])
        session = PracticeSession([question()])
        with self.assertRaisesRegex(ValueError, "Unknown option"):
            session.answer("z")

    def test_font_size_is_clamped(self):
        self.assertEqual(MIN_FONT_SIZE, adjusted_font_size(MIN_FONT_SIZE, -1))
        self.assertEqual(MAX_FONT_SIZE, adjusted_font_size(MAX_FONT_SIZE, 1))
        self.assertEqual(15, adjusted_font_size(14, 1))

    def test_zoom_shortcuts_and_mouse_wheel(self):
        self.assertEqual(1, ZOOM_BINDINGS["<Control-plus>"])
        self.assertEqual(1, ZOOM_BINDINGS["<Control-equal>"])
        self.assertEqual(-1, ZOOM_BINDINGS["<Control-minus>"])
        self.assertEqual((1, -1, 0), (wheel_zoom_change(120), wheel_zoom_change(-120), wheel_zoom_change(0)))

    def test_tree_layout_tracks_font_metrics_and_shrinks_back(self):
        small = tree_layout(linespace=16, question_width=250, status_width=70)
        large = tree_layout(linespace=34, question_width=440, status_width=140)
        self.assertEqual((24, 260, 98), small)
        self.assertEqual((42, 440, 168), large)
        self.assertGreater(large[0], small[0])


class ExamSessionTests(unittest.TestCase):
    def test_question_count_and_sequential_order(self):
        session = ExamSession([question("q1"), question("q2"), question("q3")], 2)
        self.assertEqual(["q1", "q2"], [item.id for item in session.questions])

    def test_random_order_then_question_count(self):
        items = [question("q1"), question("q2"), question("q3")]
        with patch("app.random.shuffle", side_effect=lambda values: values.reverse()):
            session = ExamSession(items, 2, random_order=True)
        self.assertEqual(["q3", "q2"], [item.id for item in session.questions])

    def test_count_must_fit_pool(self):
        for count in (0, 2):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, "between 1 and 1"):
                ExamSession([question()], count)

    def test_pre_submit_status_hides_correctness_and_answers_can_change(self):
        session = ExamSession([question()], 1)
        session.answer("a")
        self.assertEqual("answered", session.status(0))
        session.answer("b")
        self.assertEqual("answered", session.status(0))
        self.assertEqual("b", session.answers[0])

    def test_unanswered_navigation_and_jump(self):
        session = ExamSession([question("q1"), question("q2"), question("q3")], 3)
        self.assertTrue(session.next())
        self.assertTrue(session.jump(2))
        self.assertTrue(session.previous())
        self.assertEqual("q2", session.current.id)

    def test_selection_survives_exam_navigation(self):
        session = ExamSession([question("q1"), question("q2")], 2)
        session.answer("a")
        session.next()
        self.assertEqual("", session.answers.get(session.index, ""))
        session.previous()
        self.assertEqual("a", session.answers.get(session.index, ""))

    def test_submit_scores_and_exposes_results(self):
        session = ExamSession([question("q1"), question("q2"), question("q3")], 3)
        session.answer("b")
        session.next()
        session.answer("a")
        self.assertEqual((1, 3), session.submit())
        self.assertEqual(["correct", "incorrect", "unanswered"], [session.status(i) for i in range(3)])
        self.assertEqual(["q2"], [item.id for item in session.wrong_questions])
        with self.assertRaisesRegex(ValueError, "already submitted"):
            session.answer("b")


class WrongAnswerModeTests(unittest.TestCase):
    def test_mode_lifecycle_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WrongAnswerStore(Path(directory) / "wrong.json")
            update_wrong_record(store, "bank", "q1", "incorrect")
            update_wrong_record(store, "bank", "q1", "incorrect")
            self.assertEqual({"q1"}, store.items["bank"])
            update_wrong_record(store, "bank", "q1", "correct")
            self.assertTrue(store.contains("bank", "q1"))
            update_wrong_record(store, "bank", "q1", "correct", remove_if_correct=True)
            self.assertFalse(store.contains("bank", "q1"))

    def test_pool_uses_bank_and_question_ids_in_bank_order(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WrongAnswerStore(Path(directory) / "wrong.json")
            store.add("first", "q2")
            store.add("second", "q1")
            banks = [bank("first", "q1", "q2"), bank("second", "q1")]
            self.assertEqual(["q2", "q1"], [item.id for item in wrong_questions_from_banks(banks, store)])

    def test_wrong_pool_supports_random_order(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WrongAnswerStore(Path(directory) / "wrong.json")
            store.add("first", "q1")
            store.add("first", "q2")
            pool = wrong_questions_from_banks([bank("first", "q1", "q2")], store)
            with patch("app.random.shuffle", side_effect=lambda values: values.reverse()):
                session = PracticeSession(pool, random_order=True)
            self.assertEqual(["q2", "q1"], [item.id for item in session.questions])


class TranslationTests(unittest.TestCase):
    def test_languages_define_the_same_keys(self):
        self.assertEqual(set(TEXT["zh-Hant"]), set(TEXT["en"]))

    def test_translation_and_formatting(self):
        app = App.__new__(App)
        app.language = "zh-Hant"
        self.assertEqual("題目 2 / 10", app.t("question_position", current=2, total=10))
        app.language = "en"
        self.assertEqual("Question 2 / 10", app.t("question_position", current=2, total=10))

    def test_session_status_codes_remain_language_independent(self):
        session = PracticeSession([question()])
        session.answer("b")
        self.assertEqual("correct", session.status(0))


class RealBankFlowTests(unittest.TestCase):
    def test_all_modes_with_iso17025_bank(self):
        loaded = load_question_bank(Path(__file__).parents[1] / "Bank" / "ISO17025_question_bank.json")
        pool = questions_from_banks([loaded])
        self.assertEqual(113, len(pool))

        practice = PracticeSession(pool)
        practice.answer(practice.current.answer)
        self.assertEqual("correct", practice.status(0))

        exam = ExamSession(pool, 10)
        exam.answer(next(option.id for option in exam.current.options if option.id != exam.current.answer))
        self.assertEqual((0, 10), exam.submit())

        with tempfile.TemporaryDirectory() as directory:
            store = WrongAnswerStore(Path(directory) / "wrong.json")
            store.add(loaded.id, exam.wrong_questions[0].id)
            wrong_pool = wrong_questions_from_banks([loaded], store)
            self.assertEqual([exam.wrong_questions[0].id], [item.id for item in wrong_pool])


if __name__ == "__main__":
    unittest.main()
