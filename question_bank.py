"""Canonical question-bank schema 1.0 loading, independent from any GUI."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Iterable


ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class Option:
    id: str
    text: str


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    options: tuple[Option, ...]
    answer: str
    number: str | None = None
    source: str | None = None
    tags: tuple[str, ...] = ()
    note: str | None = None


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    questions: tuple[Question, ...]


@dataclass(frozen=True)
class QuestionBank:
    schema_version: str
    id: str
    title: str
    language: str
    sections: tuple[Section, ...]
    description: str | None = None
    source: str | None = None


def _object(value: object, allowed: set[str], required: set[str], context: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{context}: must be an object")
    unknown = value.keys() - allowed
    if unknown:
        raise ValueError(f"{context}: unknown field(s): {', '.join(sorted(unknown))}")
    missing = required - value.keys()
    if missing:
        raise ValueError(f"{context}: missing required field(s): {', '.join(sorted(missing))}")
    return value


def _string(data: dict, field: str, context: str, *, optional: bool = False) -> str | None:
    if optional and field not in data:
        return None
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: {field} must be a non-empty string")
    return value


def _id(data: dict, context: str) -> str:
    value = _string(data, "id", context)
    if not ID_PATTERN.fullmatch(value):
        raise ValueError(f"{context}: invalid id {value!r}")
    return value


def _array(data: dict, field: str, context: str, minimum: int) -> list:
    value = data[field]
    if not isinstance(value, list):
        raise ValueError(f"{context}: {field} must be an array")
    if len(value) < minimum:
        raise ValueError(f"{context}: {field} must contain at least {minimum} item(s)")
    return value


def load_question_bank(path: str | Path) -> QuestionBank:
    """Load and validate one canonical schema 1.0 question bank."""
    source_path = Path(path)
    try:
        raw = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {source_path} at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    except UnicodeDecodeError as error:
        raise ValueError(f"Invalid UTF-8 in {source_path}: {error}") from error

    bank_context = f"Invalid question bank {source_path}"
    data = _object(
        raw,
        {"schema_version", "id", "title", "description", "language", "source", "sections"},
        {"schema_version", "id", "title", "language", "sections"},
        bank_context,
    )
    schema_version = _string(data, "schema_version", bank_context)
    if schema_version != "1.0":
        raise ValueError(f"{bank_context}: unsupported schema_version {schema_version!r}")
    bank_id = _id(data, bank_context)
    title = _string(data, "title", bank_context)
    language = _string(data, "language", bank_context)
    raw_sections = _array(data, "sections", bank_context, 1)

    sections: list[Section] = []
    section_ids: set[str] = set()
    question_ids: set[str] = set()
    for section_index, raw_section in enumerate(raw_sections, 1):
        section_context = f"{bank_context}, section {section_index}"
        section_data = _object(
            raw_section,
            {"id", "title", "questions"},
            {"id", "title", "questions"},
            section_context,
        )
        section_id = _id(section_data, section_context)
        section_context = f"{bank_context}, section {section_id!r}"
        if section_id in section_ids:
            raise ValueError(f"{section_context}: duplicate section id")
        section_ids.add(section_id)
        section_title = _string(section_data, "title", section_context)
        raw_questions = _array(section_data, "questions", section_context, 1)

        questions: list[Question] = []
        for question_index, raw_question in enumerate(raw_questions, 1):
            question_context = f"{section_context}, question {question_index}"
            question_data = _object(
                raw_question,
                {"id", "number", "text", "options", "answer", "source", "tags", "note"},
                {"id", "text", "options", "answer"},
                question_context,
            )
            question_id = _id(question_data, question_context)
            question_context = f"{section_context}, question {question_id!r}"
            if question_id in question_ids:
                raise ValueError(f"{question_context}: duplicate question id in bank {bank_id!r}")
            question_ids.add(question_id)
            text = _string(question_data, "text", question_context)
            answer = _string(question_data, "answer", question_context)
            raw_options = _array(question_data, "options", question_context, 2)

            options: list[Option] = []
            option_ids: set[str] = set()
            for option_index, raw_option in enumerate(raw_options, 1):
                option_context = f"{question_context}, option {option_index}"
                option_data = _object(raw_option, {"id", "text"}, {"id", "text"}, option_context)
                option_id = _id(option_data, option_context)
                option_context = f"{question_context}, option {option_id!r}"
                if option_id in option_ids:
                    raise ValueError(f"{option_context}: duplicate option id")
                option_ids.add(option_id)
                options.append(Option(option_id, _string(option_data, "text", option_context)))

            if answer not in option_ids:
                raise ValueError(f"{question_context}: answer {answer!r} does not reference an option id")

            tags: tuple[str, ...] = ()
            if "tags" in question_data:
                raw_tags = question_data["tags"]
                if not isinstance(raw_tags, list):
                    raise ValueError(f"{question_context}: tags must be an array")
                if any(not isinstance(tag, str) or not tag.strip() for tag in raw_tags):
                    raise ValueError(f"{question_context}: tags must contain only non-empty strings")
                if len(raw_tags) != len(set(raw_tags)):
                    raise ValueError(f"{question_context}: tags must not contain duplicates")
                tags = tuple(raw_tags)

            questions.append(
                Question(
                    id=question_id,
                    text=text,
                    options=tuple(options),
                    answer=answer,
                    number=_string(question_data, "number", question_context, optional=True),
                    source=_string(question_data, "source", question_context, optional=True),
                    tags=tags,
                    note=_string(question_data, "note", question_context, optional=True),
                )
            )
        sections.append(Section(section_id, section_title, tuple(questions)))

    return QuestionBank(
        schema_version=schema_version,
        id=bank_id,
        title=title,
        language=language,
        sections=tuple(sections),
        description=_string(data, "description", bank_context, optional=True),
        source=_string(data, "source", bank_context, optional=True),
    )


def load_question_banks(paths: Iterable[str | Path]) -> list[QuestionBank]:
    """Load banks in input order, rejecting duplicate bank IDs."""
    banks: list[QuestionBank] = []
    seen: dict[str, Path] = {}
    for path in paths:
        source_path = Path(path)
        bank = load_question_bank(source_path)
        if bank.id in seen:
            raise ValueError(
                f"Invalid question bank {source_path}: duplicate bank id {bank.id!r}; first loaded from {seen[bank.id]}"
            )
        seen[bank.id] = source_path
        banks.append(bank)
    return banks
