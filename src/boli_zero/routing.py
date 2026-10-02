"""Provisional language-variety labelling and recognition-mode routing, as a layer AROUND Gnani Prisma.

What this is: a way to attach a proposed variety label, with its evidence, to a recording, and to say which of
Prisma's offered language modes the recording is sent in. What it is not: language identification that has been
validated, a change to Prisma's supported languages, or any form of training.

Gnani documents no audio language identification (STT REST and realtime both require an explicit language code;
there is no 'auto'; TTS 'auto' detects the language of TEXT). So labels here come from two kinds of evidence:
  1. The raw Prisma output of the clip, checked against a short, author-compiled marker table (see MARKER_SOURCE).
  2. Saved audio-model assessments, used as labelled context only. They are unverified model hearing, not Gnani
     output and not human review.
Filenames are never used. No numerical confidence is produced; every label carries the rule that produced it.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Language codes Prisma's REST docs list (docs.gnani.ai/api/STT/speech-to-text.md). Bhojpuri and Bundeli are absent.
PRISMA_LANGUAGE_CODES = frozenset({"bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN", "ta-IN", "te-IN"})
MODE_NAMES = {"hi-IN": "Hindi"}

HINDI, BHOJPURI, BUNDELI = "hindi", "bhojpuri_candidate", "bundeli_candidate"
UNCERTAIN, OTHER = "related_variety_uncertain", "other_or_insufficient"
DISPLAY = {HINDI: "Hindi", BHOJPURI: "Likely Bhojpuri", BUNDELI: "Likely Bundeli",
           UNCERTAIN: "Related variety, uncertain", OTHER: "Other language or insufficient speech"}
# Nearest Prisma mode per variety. A variety missing here has no configured recognition mode.
RECOGNITION_MODE = {HINDI: "hi-IN", BHOJPURI: "hi-IN", BUNDELI: "hi-IN", UNCERTAIN: "hi-IN"}

ORIGIN_RAW = "saved Prisma raw output, checked against the provisional marker table"
ORIGIN_ASSESSMENT = "saved gpt-audio-1.5 assessment (unverified model hearing; not Gnani, not a human)"
MARKER_SOURCE = ("Compiled by Claude on 2026-10-02 from general knowledge of Hindi and Bhojpuri grammar. NOT validated by a "
                 "Bhojpuri speaker. Deliberately short: precision over recall, so no hit is not evidence of absence. "
                 "Marks the eastern Hindi-belt family; neighbouring varieties (Awadhi, Magahi, Maithili) are not ruled out.")


def display(label: str) -> str:
    if label in DISPLAY:
        return DISPLAY[label]
    if label.endswith("_candidate"):
        return "Likely " + label.removesuffix("_candidate").replace("_", " ").title()
    raise ValueError(f"unknown label {label!r}")


# --- marker tables (Devanagari, compared after normalisation) -------------------------------------------------------
# role -> (kind, note). A form here is counted as distinctive evidence for the eastern family.
_EASTERN = {
    "pronoun": ("vocabulary", "honorific or plural pronoun", ["रउआ", "रउरा", "हमनी"]),
    "vocabulary": ("vocabulary", "word form", ["एगो", "कबो"]),
    "present auxiliary": ("grammar", "present-tense 'to be' auxiliary", ["बानी", "बाड़ू", "बाड़ी", "बाड़े", "बाड़न", "बाटे", "बाटी", "बाटू"]),
    "habitual verb": ("grammar", "habitual verb ending -ला", ["रहेला", "जाला", "करेला", "खाला", "आवेला"]),
    "future 2nd person": ("grammar", "2nd person future -बा/-बू", ["अइबा", "जइबा", "चलबू", "जइबू"]),
}
# Seen in Bhojpuri but also elsewhere (or homographs of other words): reported, never counted.
_SHARED = ["बा", "ह", "तू"]
_HINDI_WORDS = ["मैं", "हूँ", "कभी"]
_HINDI_PHRASES = [("रहे", "हैं"), ("रहा", "है"), ("रही", "है")]
_HINDI_FUTURE = re.compile(r"ेंगे$")  # करेंगे, बोलेंगे, देखेंगे: the standard Hindi plural future
HEDGE_PHRASES = ("related dialect", "closely related", "or a related")
MIN_WORDS = 4
_TOKEN = re.compile(r"[^\s।॥,.?!;:\"'()\[\]\-]+")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("‌", "").replace("‍", "")
    return text.replace("ँ", "ं")  # chandrabindu and anusvara are written interchangeably in recognizer output


_EASTERN_FORMS = {_norm(form): (role, kind, note) for role, (kind, note, forms) in _EASTERN.items() for form in forms}
_SHARED_FORMS = {_norm(f) for f in _SHARED}
_HINDI_FORMS = {_norm(f) for f in _HINDI_WORDS}
_HINDI_PHRASE_FORMS = [(_norm(a), _norm(b)) for a, b in _HINDI_PHRASES]
_NAMES_BHOJPURI, _NAMES_HINDI = _norm("भोजपुरी"), _norm("हिंदी")


# --- data shapes ----------------------------------------------------------------------------------------------------
class Evidence(BaseModel):
    kind: Literal["eastern_marker", "standard_hindi_marker", "speaker_names_language", "shared_form_noted",
                  "saved_model_assessment", "supplied"]
    supports: str | None = None  # variety name or label id this item points toward; None = context only
    text: str = Field(min_length=1)  # the form or statement, quoted exactly
    span: tuple[int, int] | None = None  # character offsets into raw_output
    context: str | None = None
    origin: str = Field(min_length=1)
    note: str = ""


class Part(BaseModel):
    """One proposed language/variety present in the clip. A clip can have several (mixed lessons)."""
    label: str
    display: str
    rule: str  # the named rule that produced the label
    evidence: list[Evidence]
    competing: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


class Route(BaseModel):
    proposed_label: str
    recognition_language_code: str | None  # what the router would send; None = no mode chosen
    workaround: bool  # True when the proposed variety is not itself a Prisma language
    display: str


class BoostBlock(BaseModel):
    """Boosted output is kept apart from the baseline and only exists after a validated experiment."""
    applied: bool = False
    reason: str = "no validated boost experiment exists"
    settings: dict | None = None
    baseline_output: str
    boosted_output: str | None = None
    experiment_ref: str | None = None

    @model_validator(mode="after")
    def _boost_needs_provenance(self):
        if self.boosted_output is not None and not (self.applied and self.settings and self.experiment_ref):
            raise ValueError("boosted_output requires applied=True, settings and an experiment_ref")
        return self


class RoutedClip(BaseModel):
    clip: dict
    recognition: dict  # submitted_language_code, raw_output (exact), request_id, source
    identification: dict  # method, gnani_language_identification, mixed, parts, assessment_context, summary
    routes: list[Route]
    recognition_matches_route: bool
    boost: BoostBlock


# --- routing --------------------------------------------------------------------------------------------------------
def route(label: str) -> Route:
    """Which Prisma mode a proposed label is sent in, and how to say so. The label itself is never changed."""
    if label == OTHER:
        return Route(proposed_label=label, recognition_language_code=None, workaround=False,
                     display=f"{display(label)}; no recognition mode chosen")
    name = label.removesuffix("_candidate") if label.endswith("_candidate") else label
    code = RECOGNITION_MODE.get(label) or RECOGNITION_MODE.get(name)
    if code is None:
        return Route(proposed_label=label, recognition_language_code=None, workaround=True,
                     display=f"{display(label)}; no recognition mode configured")
    if label == HINDI:
        return Route(proposed_label=label, recognition_language_code=code, workaround=False, display=display(label))
    return Route(proposed_label=label, recognition_language_code=code, workaround=True,
                 display=f"{display(label)}; recognized using {MODE_NAMES[code]} mode.")


# --- evidence and proposals -----------------------------------------------------------------------------------------
def _tokens(raw: str) -> list[tuple[str, int, int]]:
    return [(_norm(m.group()), m.start(), m.end()) for m in _TOKEN.finditer(raw)]


def find_evidence(raw_output: str, extra_markers: dict[str, str] | None = None) -> list[Evidence]:
    """Every marker hit in the raw output, with its position and a few words of context. Pure text; no model call.

    extra_markers: additional eastern-family forms (form -> provenance note), for example development-derived and
    unverified. They are counted like table markers but carry their note, so they can be told apart.
    """
    extra = {_norm(form): note for form, note in (extra_markers or {}).items()}
    toks = _tokens(raw_output)
    found: list[Evidence] = []

    def add(kind, supports, i, note="", length=1):
        text = " ".join(t[0] for t in toks[i:i + length])
        context = " ".join(t[0] for t in toks[max(0, i - 3): i + length + 3])
        found.append(Evidence(kind=kind, supports=supports, text=text, span=(toks[i][1], toks[i + length - 1][2]),
                              context=context, origin=ORIGIN_RAW, note=note))

    for i, (tok, _, _) in enumerate(toks):
        if tok in _EASTERN_FORMS:
            role, _, note = _EASTERN_FORMS[tok]
            add("eastern_marker", "bhojpuri", i, f"{role}: {note}")
        elif tok in extra and tok not in _SHARED_FORMS:
            add("eastern_marker", "bhojpuri", i, f"development-derived, unverified: {extra[tok]}")
        elif tok in _SHARED_FORMS:
            add("shared_form_noted", None, i, "also occurs outside Bhojpuri or is a homograph; not counted")
        if tok in _HINDI_FORMS:
            add("standard_hindi_marker", "hindi", i, "standard Hindi form")
        elif _HINDI_FUTURE.search(tok):
            add("standard_hindi_marker", "hindi", i, "standard Hindi plural future -ेंगे")
        if i + 1 < len(toks) and (tok, toks[i + 1][0]) in _HINDI_PHRASE_FORMS:
            add("standard_hindi_marker", "hindi", i, "standard Hindi progressive", length=2)
        if tok == _NAMES_BHOJPURI:
            add("speaker_names_language", "bhojpuri", i, "the speaker says the word 'Bhojpuri'")
        elif tok == _NAMES_HINDI:
            add("speaker_names_language", "hindi", i, "the speaker says the word 'Hindi'")
    return found


def assessment_evidence(assessment: dict | None) -> list[Evidence]:
    """Quote the saved model assessment verbatim, as context. Nothing here is parsed into labels."""
    fields = ("language_evidence", "bhojpuri_evidence", "language_assessment", "uncertainties")
    return [Evidence(kind="saved_model_assessment", text=str(assessment[f]), origin=ORIGIN_ASSESSMENT,
                     note=f"assessment field: {f}") for f in fields if assessment and assessment.get(f)]


def assessment_hedges(assessment: dict | None) -> bool:
    """True when the saved assessment itself says the language may be a related dialect. Keyword check on its language fields."""
    text = " ".join(str(assessment.get(f, "")) for f in ("language_evidence", "bhojpuri_evidence", "language_assessment")) if assessment else ""
    return any(phrase in text.lower() for phrase in HEDGE_PHRASES)


_NOT_EXCLUSIVE = "table markers are not validated as exclusive to Bhojpuri"
_NEIGHBOURS = ["awadhi", "magahi", "maithili"]


def propose(raw_output: str, assessment: dict | None = None, supplied: list[Evidence] | None = None,
            extra_markers: dict[str, str] | None = None) -> list[Part]:
    """Proposed variety labels for one clip, one Part per language present. Rules are listed in the README."""
    toks = _tokens(raw_output)
    devanagari = sum(1 for t, _, _ in toks if any("ऀ" <= ch <= "ॿ" for ch in t))
    if len(toks) < MIN_WORDS or devanagari * 2 < len(toks):
        return [Part(label=OTHER, display=display(OTHER), rule="too_few_words_or_not_devanagari", evidence=[],
                     uncertainty=[f"fewer than {MIN_WORDS} recognized words, or mostly non-Devanagari output"])]

    ev = find_evidence(raw_output, extra_markers)
    eastern = [e for e in ev if e.kind == "eastern_marker"]
    distinct_eastern = {e.text for e in eastern}
    names_bhojpuri = [e for e in ev if e.kind == "speaker_names_language" and e.supports == "bhojpuri"]
    hindi = [e for e in ev if e.kind == "standard_hindi_marker"]
    names_hindi = [e for e in ev if e.kind == "speaker_names_language" and e.supports == "hindi"]
    shared = [e for e in ev if e.kind == "shared_form_noted"]
    hedged = assessment_hedges(assessment)
    parts: list[Part] = []

    # Eastern (Bhojpuri-side) evidence
    if len(distinct_eastern) >= 2:
        label, rule = BHOJPURI, "two_or_more_distinct_markers"
    elif len(distinct_eastern) == 1 and names_bhojpuri and not hedged:
        label, rule = BHOJPURI, "one_marker_and_speaker_names_bhojpuri"
    elif len(distinct_eastern) == 1 and names_bhojpuri and hedged:
        label, rule = UNCERTAIN, "one_marker_and_speaker_names_bhojpuri_but_saved_assessment_hedges"
    elif distinct_eastern:
        label, rule = UNCERTAIN, "one_marker_without_speaker_naming_bhojpuri"
    elif names_bhojpuri:
        label, rule = UNCERTAIN, "speaker_names_bhojpuri_but_no_variety_specific_form_recognized"
    else:
        label = rule = None
    if label:
        evidence = eastern + names_bhojpuri + shared
        uncertainty = [_NOT_EXCLUSIVE, "marker table not reviewed by a native speaker",
                       "raw recognition may have rewritten or dropped Bhojpuri forms"]
        if len(distinct_eastern) == 1:
            uncertainty.append("rests on a single distinct marker")
        if hedged:
            uncertainty.append("the saved audio-model assessment itself allows a related dialect")
        parts.append(Part(label=label, display=display(label), rule=rule, evidence=evidence, uncertainty=uncertainty,
                          competing=[UNCERTAIN if label == BHOJPURI else BHOJPURI] + _NEIGHBOURS))

    # Standard Hindi evidence (the explanation in a lesson, or Hindi sentences before a Bhojpuri rendering)
    distinct_hindi = {e.text for e in hindi}
    if len(distinct_hindi) >= 2 or (len(distinct_hindi) == 1 and names_hindi):
        parts.append(Part(label=HINDI, display=display(HINDI),
                          rule="two_or_more_distinct_hindi_markers" if len(distinct_hindi) >= 2 else "one_hindi_marker_and_speaker_names_hindi",
                          evidence=hindi + names_hindi,
                          uncertainty=["Hindi forms also appear in Hindi-influenced Bhojpuri speech; spans are evidence, not full segments"]))

    # Evidence supplied from outside the table (a person, or a cited source): the only way a named candidate such as Bundeli appears
    for name in sorted({e.supports for e in (supplied or []) if e.supports and e.supports not in ("bhojpuri", "hindi")}):
        items = [e for e in supplied if e.supports == name]
        parts.append(Part(label=f"{name}_candidate", display=display(f"{name}_candidate"), rule="externally_supplied_evidence",
                          evidence=items, competing=[UNCERTAIN],
                          uncertainty=[f"{name} handling is unverified: no marker table and no validated sample exist for it"]))

    parts.sort(key=lambda part: part.label != HINDI)  # Hindi first: in a lesson it is usually the explanation
    if not parts:
        parts.append(Part(label=UNCERTAIN, display=display(UNCERTAIN), rule="devanagari_text_without_variety_specific_evidence",
                          evidence=shared, uncertainty=["script and word overlap with Hindi are not evidence of a variety"],
                          competing=[HINDI, BHOJPURI] + _NEIGHBOURS))
    return parts


def label_clip(*, raw_output: str, submitted_language_code: str, request_id: str | None = None, assessment: dict | None = None,
               clip: dict | None = None, source: str = "", supplied: list[Evidence] | None = None,
               extra_markers: dict[str, str] | None = None) -> RoutedClip:
    """Combine one clip's saved recognition result with a proposed labelling. Makes no API call.

    The submitted language code is kept as a separate fact from the proposed labels: a clip proposed as Bhojpuri and
    recognized in Hindi mode stays labelled Bhojpuri.
    """
    if submitted_language_code not in PRISMA_LANGUAGE_CODES:
        raise ValueError(f"{submitted_language_code!r} is not a Prisma language code")
    parts = propose(raw_output, assessment, supplied, extra_markers)
    routes = [route(p.label) for p in parts]
    codes = {r.recognition_language_code for r in routes if r.recognition_language_code}
    parts_summary = " | ".join(r.display for r in routes)
    return RoutedClip(
        clip=clip or {},
        recognition={"submitted_language_code": submitted_language_code, "raw_output": raw_output, "request_id": request_id, "source": source},
        identification={
            "method": "evidence rules over saved raw Prisma output; saved model assessment used only as context and a hedge flag",
            "gnani_language_identification": "none documented for audio input; not used",
            "mixed": len(parts) > 1, "parts": [p.model_dump() for p in parts],
            "assessment_context": [e.model_dump() for e in assessment_evidence(assessment)],
            "summary": ("Mixed: " if len(parts) > 1 else "") + parts_summary,
        },
        routes=routes,
        recognition_matches_route=codes == {submitted_language_code},
        boost=BoostBlock(baseline_output=raw_output),
    )


def attach_boost(record: RoutedClip, *, settings: dict, output: str, experiment: dict) -> RoutedClip:
    """Record a boosted transcript next to, never over, the baseline. Refuses unless a validated experiment is cited."""
    needed = ("id", "references_human_corrected", "improved_over_baseline")
    if not all(experiment.get(k) for k in needed):
        raise ValueError(f"boost not justified: the experiment must have {needed} all set (no such experiment exists yet)")
    record.boost = BoostBlock(applied=True, reason="validated experiment cited", settings=settings,
                              baseline_output=record.recognition["raw_output"], boosted_output=output, experiment_ref=str(experiment["id"]))
    return record


def recognize_and_label(client, audio, *, language_code: str = "hi-IN", assessment: dict | None = None, clip: dict | None = None) -> RoutedClip:
    """Send audio to Prisma in the chosen mode (one billable request unless cached), then label the raw result."""
    before = client.calls
    result = client.transcribe_detailed(audio, language_code)
    return label_clip(raw_output=result["text"], submitted_language_code=language_code, request_id=result.get("request_id"),
                      assessment=assessment, clip=clip, source="live Prisma request" if client.calls > before else "local cache")
