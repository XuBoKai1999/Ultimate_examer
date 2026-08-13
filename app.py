"""Ultimate_examer GUI: Practice and Exam modes."""

from pathlib import Path
import random
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk

from question_bank import Question, QuestionBank, load_question_banks
from wrong_answers import WrongAnswerStore


MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 28

TEXT = {
    "zh-Hant": {
        "choose_banks": "選擇題庫", "json_banks": "JSON 題庫", "no_banks_selected": "尚未選擇題庫", "selected_banks": "已選擇 {count} 個：{names}",
        "mode": "模式：", "practice": "練習", "exam": "考試", "wrong_answer": "錯題練習",
        "order": "出題方式：", "all": "全部依序", "random": "隨機抽題", "range": "指定範圍", "count": "題數：", "range_start": "起點：", "range_end": "終點：", "start": "開始",
        "clear_selected": "清除所選題庫錯題", "font_size": "字體大小", "language": "語言：",
        "welcome": "選擇一個或多個題庫後開始練習。", "question": "題目", "status": "狀態",
        "question_position": "題目 {current} / {total}", "previous": "上一題", "next": "下一題", "submit": "交卷",
        "unanswered": "未作答", "answered": "已作答", "correct": "正確", "incorrect": "錯誤",
        "result": "{status}；正確答案：{answer}. {text}", "no_bank_title": "無題庫",
        "choose_bank_first": "請先選擇至少一個題庫。", "bank_error": "題庫錯誤", "wrong_error": "錯題紀錄錯誤",
        "wrong_unavailable": "錯題紀錄無法載入。", "count_error": "題數錯誤", "no_wrong_title": "無錯題",
        "invalid_count": "題數必須介於 1 和 {maximum} 之間。",
        "invalid_range": "範圍必須符合 1 ≤ 起點 ≤ 終點 ≤ {maximum}。",
        "no_wrong": "選取的題庫目前沒有錯題紀錄。", "submit_confirm": "確定要交卷並批改嗎？",
        "exam_result": "考試結果", "score": "得分：{score} / {total}", "clear_title": "清除錯題",
        "clear_confirm": "確定清除目前所選題庫的所有錯題紀錄嗎？", "clear_done": "已清除目前所選題庫的錯題紀錄。",
    },
    "en": {
        "choose_banks": "Choose Banks", "json_banks": "JSON Question Banks", "no_banks_selected": "No question bank selected", "selected_banks": "Selected {count}: {names}",
        "mode": "Mode:", "practice": "Practice", "exam": "Exam", "wrong_answer": "Wrong Answers",
        "order": "Question set:", "all": "All Sequential", "random": "Random Sample", "range": "Range", "count": "Questions:", "range_start": "From:", "range_end": "To:", "start": "Start",
        "clear_selected": "Clear Selected Banks", "font_size": "Font size", "language": "Language:",
        "welcome": "Choose one or more question banks to begin.", "question": "Question", "status": "Status",
        "question_position": "Question {current} / {total}", "previous": "Previous", "next": "Next", "submit": "Submit",
        "unanswered": "Unanswered", "answered": "Answered", "correct": "Correct", "incorrect": "Incorrect",
        "result": "{status}; correct answer: {answer}. {text}", "no_bank_title": "No Bank",
        "choose_bank_first": "Choose at least one question bank first.", "bank_error": "Question Bank Error", "wrong_error": "Wrong Answer Error",
        "wrong_unavailable": "The wrong-answer record could not be loaded.", "count_error": "Question Count Error", "no_wrong_title": "No Wrong Answers",
        "invalid_count": "Question count must be between 1 and {maximum}.",
        "invalid_range": "Range must satisfy 1 ≤ start ≤ end ≤ {maximum}.",
        "no_wrong": "The selected banks have no recorded wrong answers.", "submit_confirm": "Submit and grade this exam?",
        "exam_result": "Exam Result", "score": "Score: {score} / {total}", "clear_title": "Clear Wrong Answers",
        "clear_confirm": "Clear all wrong answers for the selected banks?", "clear_done": "Wrong answers for the selected banks were cleared.",
    },
}
LANGUAGE_NAMES = ("繁體中文", "English")
ZOOM_BINDINGS = {"<Control-plus>": 1, "<Control-equal>": 1, "<Control-minus>": -1}


def adjusted_font_size(current: int, change: int) -> int:
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, current + change))


def wheel_zoom_change(delta: int) -> int:
    return 1 if delta > 0 else -1 if delta < 0 else 0


def questions_from_banks(banks: list[QuestionBank]) -> list[Question]:
    return [question for bank in banks for section in bank.sections for question in section.questions]


def select_questions(
    questions: list[Question], method: str, *, count: int | None = None,
    start: int | None = None, end: int | None = None,
) -> list[Question]:
    if method == "all":
        return list(questions)
    if method == "random":
        if count is None or not 1 <= count <= len(questions):
            raise ValueError("invalid count")
        return random.sample(questions, count)
    if method == "range":
        if start is None or end is None or not 1 <= start <= end <= len(questions):
            raise ValueError("invalid range")
        return list(questions[start - 1:end])
    raise ValueError("unknown selection method")


def wrong_questions_from_banks(banks: list[QuestionBank], store: WrongAnswerStore) -> list[Question]:
    return [
        question for bank in banks for section in bank.sections for question in section.questions
        if store.contains(bank.id, question.id)
    ]


def update_wrong_record(
    store: WrongAnswerStore, bank_id: str, question_id: str, status: str, remove_if_correct: bool = False
) -> None:
    if status == "incorrect":
        store.add(bank_id, question_id)
    elif status == "correct" and remove_if_correct:
        store.remove(bank_id, question_id)


class PracticeSession:
    def __init__(self, questions: list[Question], random_order: bool = False):
        if not questions:
            raise ValueError("Practice session requires at least one question")
        self.questions = list(questions)
        if random_order:
            random.shuffle(self.questions)
        self.index = 0
        self.answers: dict[int, str] = {}

    @property
    def current(self) -> Question:
        return self.questions[self.index]

    @property
    def can_previous(self) -> bool:
        return self.index > 0

    @property
    def can_next(self) -> bool:
        return self.index + 1 < len(self.questions)

    def answer(self, option_id: str) -> bool:
        if self.index in self.answers:
            raise ValueError("Question already answered")
        if option_id not in {option.id for option in self.current.options}:
            raise ValueError("Unknown option")
        self.answers[self.index] = option_id
        return option_id == self.current.answer

    def status(self, index: int) -> str:
        if index not in self.answers:
            return "unanswered"
        return "correct" if self.answers[index] == self.questions[index].answer else "incorrect"

    def jump(self, index: int) -> bool:
        if not 0 <= index < len(self.questions):
            return False
        self.index = index
        return True

    def previous(self) -> bool:
        return self.jump(self.index - 1) if self.can_previous else False

    def next(self) -> bool:
        return self.jump(self.index + 1) if self.can_next else False


class ExamSession(PracticeSession):
    def __init__(self, questions: list[Question], count: int, random_order: bool = False):
        if not 1 <= count <= len(questions):
            raise ValueError(f"Question count must be between 1 and {len(questions)}")
        super().__init__(questions, random_order)
        self.questions = self.questions[:count]
        self.submitted = False

    def answer(self, option_id: str) -> None:
        if self.submitted:
            raise ValueError("Exam already submitted")
        if option_id not in {option.id for option in self.current.options}:
            raise ValueError("Unknown option")
        self.answers[self.index] = option_id

    def status(self, index: int) -> str:
        if index not in self.answers:
            return "unanswered"
        if not self.submitted:
            return "answered"
        return "correct" if self.answers[index] == self.questions[index].answer else "incorrect"

    def submit(self) -> tuple[int, int]:
        self.submitted = True
        return sum(self.status(index) == "correct" for index in range(len(self.questions))), len(self.questions)

    @property
    def wrong_questions(self) -> list[Question]:
        if not self.submitted:
            return []
        return [question for index, question in enumerate(self.questions) if self.status(index) == "incorrect"]


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.language = "zh-Hant"
        self.mode_code = "practice"
        self.order_code = "all"
        root.title("Ultimate Examer")
        root.geometry("1050x700")
        self.paths: tuple[str, ...] = ()
        self.session: PracticeSession | ExamSession | None = None
        self.loaded_banks: list[QuestionBank] = []
        self.question_keys: dict[int, tuple[str, str]] = {}
        try:
            self.wrong_answers = WrongAnswerStore(Path(__file__).with_name("wrong_answers.json"))
        except ValueError as error:
            self.wrong_answers = None
            messagebox.showerror(self.t("wrong_error"), str(error))
        self.answer_var = tk.StringVar()
        self.font_size = 14
        self.app_font = font.Font(family="TkDefaultFont", size=self.font_size)
        self.style = ttk.Style()
        self._apply_font()

        self.main = ttk.Frame(root, padding=16)
        self.main.pack(fill="both", expand=True)
        self.controls = ttk.Frame(self.main)
        self.controls.pack(fill="x")
        self.build_controls()

        ttk.Separator(self.main).pack(fill="x", pady=12)
        self.content = ttk.Frame(self.main)
        self.content.pack(fill="both", expand=True)
        self.show_welcome()

        for sequence, change in ZOOM_BINDINGS.items():
            root.bind(sequence, lambda event, amount=change: self.zoom(amount))
        root.bind("<Control-MouseWheel>", self._wheel_zoom)

    def t(self, key: str, **values) -> str:
        return TEXT[self.language][key].format(**values)

    def build_controls(self):
        previous_count = self.question_count.get() if hasattr(self, "question_count") and self.question_count.winfo_exists() else "10"
        previous_start = self.range_start.get() if hasattr(self, "range_start") and self.range_start.winfo_exists() else "1"
        previous_end = self.range_end.get() if hasattr(self, "range_end") and self.range_end.winfo_exists() else "20"
        for child in self.controls.winfo_children():
            child.destroy()
        setup = ttk.Frame(self.controls)
        setup.pack(fill="x")
        ttk.Button(setup, text=self.t("choose_banks"), command=self.choose_banks).pack(side="left")
        bank_text = self.t("selected_banks", count=len(self.paths), names=", ".join(Path(path).name for path in self.paths)) if self.paths else self.t("no_banks_selected")
        self.bank_label = ttk.Label(setup, text=bank_text)
        self.bank_label.pack(side="left", padx=10, fill="x", expand=True)
        ttk.Label(setup, text=self.t("mode")).pack(side="left")
        mode_codes = ("practice", "exam", "wrong_answer")
        self.mode = ttk.Combobox(setup, values=tuple(self.t(code) for code in mode_codes), state="readonly", width=13)
        self.mode.current(mode_codes.index(self.mode_code))
        self.mode.pack(side="left")
        self.mode.bind("<<ComboboxSelected>>", self.mode_changed)
        ttk.Label(setup, text=self.t("order")).pack(side="left", padx=(10, 0))
        order_codes = ("all", "random", "range")
        self.order = ttk.Combobox(setup, values=tuple(self.t(code) for code in order_codes), state="readonly", width=11)
        self.order.current(order_codes.index(self.order_code))
        self.order.pack(side="left")
        self.order.bind("<<ComboboxSelected>>", self.order_changed)
        ttk.Label(setup, text=self.t("count")).pack(side="left", padx=(10, 0))
        self.question_count = ttk.Spinbox(setup, from_=1, to=9999, width=5)
        self.question_count.set(previous_count)
        self.question_count.pack(side="left")
        ttk.Label(setup, text=self.t("range_start")).pack(side="left", padx=(10, 0))
        self.range_start = ttk.Spinbox(setup, from_=1, to=9999, width=5)
        self.range_start.set(previous_start)
        self.range_start.pack(side="left")
        ttk.Label(setup, text=self.t("range_end")).pack(side="left", padx=(6, 0))
        self.range_end = ttk.Spinbox(setup, from_=1, to=9999, width=5)
        self.range_end.set(previous_end)
        self.range_end.pack(side="left")
        self.update_selection_state()
        ttk.Button(setup, text=self.t("start"), command=self.start).pack(side="left", padx=(10, 0))
        ttk.Button(setup, text=self.t("clear_selected"), command=self.clear_selected_wrong_answers).pack(side="left", padx=(10, 0))
        zoom = ttk.Frame(self.controls)
        zoom.pack(fill="x", pady=(12, 0))
        ttk.Label(zoom, text=self.t("font_size")).pack(side="left")
        ttk.Button(zoom, text="−", width=3, command=lambda: self.zoom(-1)).pack(side="left", padx=4)
        ttk.Button(zoom, text="+", width=3, command=lambda: self.zoom(1)).pack(side="left")
        self.size_label = ttk.Label(zoom, text=str(self.font_size))
        self.size_label.pack(side="left", padx=6)
        ttk.Label(zoom, text=self.t("language")).pack(side="left", padx=(12, 4))
        self.language_box = ttk.Combobox(zoom, values=LANGUAGE_NAMES, state="readonly", width=12)
        self.language_box.current(0 if self.language == "zh-Hant" else 1)
        self.language_box.pack(side="left")
        self.language_box.bind("<<ComboboxSelected>>", self.language_changed)

    def mode_changed(self, _event=None):
        self.mode_code = ("practice", "exam", "wrong_answer")[self.mode.current()]

    def order_changed(self, _event=None):
        self.order_code = ("all", "random", "range")[self.order.current()]
        self.update_selection_state()

    def update_selection_state(self):
        self.question_count.configure(state="normal" if self.order_code == "random" else "disabled")
        range_state = "normal" if self.order_code == "range" else "disabled"
        self.range_start.configure(state=range_state)
        self.range_end.configure(state=range_state)

    def language_changed(self, _event=None):
        self.language = ("zh-Hant", "en")[self.language_box.current()]
        self.build_controls()
        if self.session:
            self.build_session_ui()
            self.show_question()
        else:
            self.show_welcome()

    def show_welcome(self):
        for child in self.content.winfo_children():
            child.destroy()
        ttk.Label(self.content, text=self.t("welcome")).pack(pady=80)

    def _apply_font(self):
        self.root.option_add("*Font", self.app_font)
        for widget in ("TLabel", "TButton", "TRadiobutton", "TCombobox", "Treeview"):
            self.style.configure(widget, font=self.app_font)

    def zoom(self, change: int):
        size = adjusted_font_size(self.font_size, change)
        if size != self.font_size:
            self.font_size = size
            self.app_font.configure(size=size)
            self._apply_font()
            self.size_label.configure(text=str(size))

    def _wheel_zoom(self, event):
        change = wheel_zoom_change(event.delta)
        if change:
            self.zoom(change)
        return "break"

    def choose_banks(self):
        paths = filedialog.askopenfilenames(
            title=self.t("choose_banks"),
            initialdir=Path(__file__).parent / "Bank",
            filetypes=((self.t("json_banks"), "*.json"),),
        )
        if paths:
            self.paths = paths
            self.bank_label.configure(text=self.t("selected_banks", count=len(paths), names=", ".join(Path(path).name for path in paths)))

    def start(self):
        if not self.paths:
            messagebox.showwarning(self.t("no_bank_title"), self.t("choose_bank_first"))
            return
        try:
            banks = load_question_banks(self.paths)
            questions = questions_from_banks(banks)
        except (OSError, ValueError) as error:
            messagebox.showerror(self.t("bank_error"), str(error))
            return
        self.loaded_banks = banks
        self.question_keys = {
            id(question): (bank.id, question.id)
            for bank in banks for section in bank.sections for question in section.questions
        }
        if self.wrong_answers is not None:
            try:
                for bank in banks:
                    self.wrong_answers.prune(
                        bank.id,
                        {question.id for section in bank.sections for question in section.questions},
                    )
            except OSError as error:
                messagebox.showerror(self.t("wrong_error"), str(error))
        if self.mode_code == "wrong_answer":
            if self.wrong_answers is None:
                messagebox.showerror(self.t("wrong_error"), self.t("wrong_unavailable"))
                return
            questions = wrong_questions_from_banks(banks, self.wrong_answers)
            if not questions:
                messagebox.showinfo(self.t("no_wrong_title"), self.t("no_wrong"))
                return
        try:
            if self.order_code == "random":
                questions = select_questions(questions, "random", count=int(self.question_count.get()))
            elif self.order_code == "range":
                questions = select_questions(
                    questions, "range", start=int(self.range_start.get()), end=int(self.range_end.get())
                )
            else:
                questions = select_questions(questions, "all")
        except ValueError as error:
            key = "invalid_range" if self.order_code == "range" else "invalid_count"
            messagebox.showerror(self.t("count_error"), self.t(key, maximum=len(questions)))
            return
        if self.mode_code == "exam":
            self.session = ExamSession(questions, len(questions))
        else:
            self.session = PracticeSession(questions)
        self.build_session_ui()
        self.show_question()

    def build_session_ui(self):
        for child in self.content.winfo_children():
            child.destroy()
        list_frame = ttk.Frame(self.content)
        list_frame.pack(side="left", fill="y", padx=(0, 16))
        self.question_list = ttk.Treeview(list_frame, columns=("status",), show="tree headings", selectmode="browse")
        self.question_list.heading("#0", text=self.t("question"))
        self.question_list.heading("status", text=self.t("status"))
        self.question_list.column("#0", width=330)
        self.question_list.column("status", width=90, anchor="center")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.question_list.yview)
        self.question_list.configure(yscrollcommand=scrollbar.set)
        self.question_list.pack(side="left", fill="y")
        scrollbar.pack(side="right", fill="y")
        self.question_list.bind("<<TreeviewSelect>>", self.jump_to_selected)
        for index, question in enumerate(self.session.questions):
            snippet = question.text.replace("\n", " ")[:38]
            self.question_list.insert("", "end", iid=str(index), text=f"{index + 1}. {snippet}", values=(self.t(self.session.status(index)),))
        self.question_area = ttk.Frame(self.content)
        self.question_area.pack(side="left", fill="both", expand=True)

    def show_question(self):
        for child in self.question_area.winfo_children():
            child.destroy()
        question = self.session.current
        selected = self.session.answers.get(self.session.index, "")
        self.answer_var.set(selected)
        self.question_list.selection_set(str(self.session.index))
        self.question_list.see(str(self.session.index))

        ttk.Label(self.question_area, text=self.t("question_position", current=self.session.index + 1, total=len(self.session.questions))).pack(anchor="w")
        ttk.Label(self.question_area, text=question.text, wraplength=640, justify="left").pack(
            anchor="w", fill="x", pady=(12, 16)
        )
        exam = isinstance(self.session, ExamSession)
        answered = self.session.index in self.session.answers
        locked = answered and not exam or exam and self.session.submitted
        self.option_buttons = []
        for option in question.options:
            button = ttk.Radiobutton(
                self.question_area,
                text=f"{option.id}. {option.text}",
                value=option.id,
                variable=self.answer_var,
                command=self.select_answer,
                state="disabled" if locked else "normal",
            )
            button.pack(anchor="w", fill="x", pady=4)
            self.option_buttons.append(button)
        self.result = tk.Label(self.question_area, text="", anchor="w", justify="left", font=self.app_font)
        self.result.pack(anchor="w", fill="x", pady=(18, 8))
        if answered and not exam or exam and self.session.submitted:
            self.show_result()

        navigation = ttk.Frame(self.question_area)
        navigation.pack(fill="x", side="bottom")
        ttk.Button(
            navigation, text=self.t("previous"), command=self.go_previous,
            state="normal" if self.session.can_previous else "disabled",
        ).pack(side="left")
        ttk.Button(
            navigation, text=self.t("next"), command=self.go_next,
            state="normal" if self.session.can_next else "disabled",
        ).pack(side="right")

        if exam and not self.session.submitted:
            ttk.Button(navigation, text=self.t("submit"), command=self.submit_exam).pack(side="right", padx=10)

    def select_answer(self):
        selected = self.answer_var.get()
        if not selected:
            return
        if isinstance(self.session, ExamSession):
            self.session.answer(selected)
            self.question_list.set(str(self.session.index), "status", self.t("answered"))
            return
        if self.session.index in self.session.answers:
            return
        self.session.answer(selected)
        for button in self.option_buttons:
            button.configure(state="disabled")
        self.question_list.set(str(self.session.index), "status", self.t(self.session.status(self.session.index)))
        status = self.session.status(self.session.index)
        self.update_wrong(self.session.current, status, self.mode_code == "wrong_answer")
        self.show_result()

    def submit_exam(self):
        if not messagebox.askyesno(self.t("submit"), self.t("submit_confirm")):
            return
        score, total = self.session.submit()
        for question in self.session.wrong_questions:
            self.update_wrong(question, "incorrect")
        for index in range(total):
            self.question_list.set(str(index), "status", self.t(self.session.status(index)))
        self.show_question()
        messagebox.showinfo(self.t("exam_result"), self.t("score", score=score, total=total))

    def update_wrong(self, question: Question, status: str, remove_if_correct: bool = False):
        if self.wrong_answers is None:
            return
        try:
            update_wrong_record(self.wrong_answers, *self.question_keys[id(question)], status, remove_if_correct)
        except OSError as error:
            messagebox.showerror(self.t("wrong_error"), str(error))

    def clear_selected_wrong_answers(self):
        if not self.paths:
            messagebox.showwarning(self.t("no_bank_title"), self.t("choose_bank_first"))
            return
        if self.wrong_answers is None:
            messagebox.showerror(self.t("wrong_error"), self.t("wrong_unavailable"))
            return
        try:
            banks = load_question_banks(self.paths)
        except (OSError, ValueError) as error:
            messagebox.showerror(self.t("bank_error"), str(error))
            return
        if not messagebox.askyesno(self.t("clear_title"), self.t("clear_confirm")):
            return
        try:
            self.wrong_answers.clear_banks({bank.id for bank in banks})
        except OSError as error:
            messagebox.showerror(self.t("wrong_error"), str(error))
            return
        messagebox.showinfo(self.t("clear_title"), self.t("clear_done"))

    def show_result(self):
        question = self.session.current
        status = self.session.status(self.session.index)
        correct = status == "correct"
        answer = next(option.text for option in question.options if option.id == question.answer)
        self.result.configure(
            text=self.t("result", status=self.t(status), answer=question.answer, text=answer),
            fg="#167a3e" if correct else "#b42318",
        )

    def go_previous(self):
        if self.session.previous():
            self.show_question()

    def go_next(self):
        if self.session.next():
            self.show_question()

    def jump_to_selected(self, _event=None):
        selected = self.question_list.selection()
        target = int(selected[0]) if selected else self.session.index
        if target != self.session.index and self.session.jump(target):
            self.show_question()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
