"""Canonical data shapes: dataset rows, learned rules, and manual ratings."""
from __future__ import annotations

import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Split = Literal["train", "validation", "test"]


class DatasetRecord(BaseModel):
    """One aligned pair. Every ingested source is converted to this shape."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    anchor_language: str = Field(min_length=1)  # standard language, e.g. "hi"
    target_language: str = Field(min_length=1)  # unsupported variety, e.g. "bho"
    anchor_text: str = Field(min_length=1)
    target_text: str = Field(min_length=1)
    audio_path: str | None = None  # relative to data/raw unless absolute
    speaker_id: str | None = None
    source: str = Field(min_length=1)
    license: str = Field(min_length=1)
    split: Split | None = None

    @field_validator("anchor_text", "target_text")
    @classmethod
    def _nfc(cls, value: str) -> str:
        return unicodedata.normalize("NFC", value)

    @field_validator("audio_path", "speaker_id")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        return value or None


class LexicalMapping(BaseModel):
    anchor: str = Field(min_length=1)
    target: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)  # model self-reported, not calibrated
    supporting_example_ids: list[str] = Field(min_length=1)


class GrammaticalPattern(BaseModel):
    category: str = Field(min_length=1)  # e.g. "verb ending", "negation", "pronoun"
    description: str = Field(min_length=1)
    anchor_form: str | None = None
    target_form: str | None = None
    confidence: float = Field(ge=0, le=1)
    supporting_example_ids: list[str] = Field(min_length=1)


class UnresolvedPattern(BaseModel):
    """A difference the model saw but could not turn into a rule."""

    description: str = Field(min_length=1)
    example_ids: list[str] = Field(default_factory=list)


class LearnedRules(BaseModel):
    anchor_language: str
    target_language: str
    shots: int
    lexical_mappings: list[LexicalMapping] = Field(default_factory=list)
    grammatical_patterns: list[GrammaticalPattern] = Field(default_factory=list)
    unresolved_patterns: list[UnresolvedPattern] = Field(default_factory=list)
    validation_problems: list[str] = Field(default_factory=list)  # items dropped while parsing


class RatingRecord(BaseModel):
    """One native-speaker judgement of two anonymous outputs for one item."""

    item_id: str = Field(min_length=1)
    rater_id: str = Field(min_length=1)
    choice: Literal["1", "2", "tie", "both_bad"]
    notes: str = ""
