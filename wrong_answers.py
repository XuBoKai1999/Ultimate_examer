"""Persistent wrong-answer identifiers."""

import json
from pathlib import Path


class WrongAnswerStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.items = self._load()

    def _load(self) -> dict[str, set[str]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(f"Invalid wrong-answer file {self.path}: {error}") from error
        if not isinstance(data, dict) or not all(
            isinstance(bank_id, str)
            and isinstance(question_ids, list)
            and all(isinstance(question_id, str) for question_id in question_ids)
            for bank_id, question_ids in data.items()
        ):
            raise ValueError(f"Invalid wrong-answer file {self.path}: expected bank IDs mapped to question ID arrays")
        return {bank_id: set(question_ids) for bank_id, question_ids in data.items()}

    def contains(self, bank_id: str, question_id: str) -> bool:
        return question_id in self.items.get(bank_id, set())

    def add(self, bank_id: str, question_id: str) -> None:
        questions = self.items.setdefault(bank_id, set())
        if question_id in questions:
            return
        questions.add(question_id)
        self._save()

    def remove(self, bank_id: str, question_id: str) -> None:
        questions = self.items.get(bank_id)
        if not questions or question_id not in questions:
            return
        questions.remove(question_id)
        if not questions:
            del self.items[bank_id]
        self._save()

    def prune(self, bank_id: str, valid_question_ids: set[str]) -> None:
        questions = self.items.get(bank_id)
        if questions is None or questions <= valid_question_ids:
            return
        questions.intersection_update(valid_question_ids)
        if not questions:
            del self.items[bank_id]
        self._save()

    def clear_banks(self, bank_ids: set[str]) -> None:
        if not self.items.keys() & bank_ids:
            return
        for bank_id in bank_ids:
            self.items.pop(bank_id, None)
        self._save()

    def _save(self) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({key: sorted(value) for key, value in sorted(self.items.items())}, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
