"""Routing and labelling checks. The Devanagari strings below are marker-test inputs, not claims about any recording."""
import httpx
import pytest

from boli_zero import routing as r
from boli_zero.clients import PrismaClient
from boli_zero.config import GnaniConfig


def labels(raw, assessment=None, supplied=None):
    return [p.label for p in r.propose(raw, assessment, supplied)]


def part(raw, label, **kw):
    return next(p for p in r.propose(raw, **kw) if p.label == label)


# --- routing: unsupported varieties go to Hindi mode, but keep their own label ---------------------------------------
def test_unsupported_candidate_is_shown_with_the_required_wording():
    route = r.route(r.BHOJPURI)
    assert route.display == "Likely Bhojpuri; recognized using Hindi mode."
    assert (route.proposed_label, route.recognition_language_code, route.workaround) == (r.BHOJPURI, "hi-IN", True)
    assert r.route(r.BUNDELI).display == "Likely Bundeli; recognized using Hindi mode."


def test_hindi_is_not_a_workaround_and_other_gets_no_mode():
    assert (r.route(r.HINDI).display, r.route(r.HINDI).workaround) == ("Hindi", False)
    other = r.route(r.OTHER)
    assert other.recognition_language_code is None and "no recognition mode" in other.display


def test_named_candidate_without_a_configured_mode_is_not_silently_sent_as_hindi():
    route = r.route("tulu_candidate")
    assert route.recognition_language_code is None and route.display == "Likely Tulu; no recognition mode configured"


def test_every_configured_mode_is_an_offered_prisma_language():
    assert set(r.RECOGNITION_MODE.values()) <= r.PRISMA_LANGUAGE_CODES
    assert not {"bho", "bho-IN", "bundeli"} & r.PRISMA_LANGUAGE_CODES


# --- label rules ------------------------------------------------------------------------------------------------------
def test_two_distinct_markers_give_a_candidate():
    assert labels("रउआ कहाँ जात बानी") == [r.BHOJPURI]
    assert part("रउआ कहाँ जात बानी", r.BHOJPURI).rule == "two_or_more_distinct_markers"


def test_one_marker_needs_the_speaker_to_name_bhojpuri():
    named = "इसको भोजपुरी में बोलेंगे तू कहाँ रहेला"
    assert part(named, r.BHOJPURI).rule == "one_marker_and_speaker_names_bhojpuri"
    unnamed = "तू कहाँ रहता है तुम बताओ रहेला"
    assert labels(unnamed) == [r.UNCERTAIN]
    assert part(unnamed, r.UNCERTAIN).rule == "one_marker_without_speaker_naming_bhojpuri"


def test_a_hedging_saved_assessment_downgrades_a_single_marker_candidate_and_keeps_competitors():
    raw = "इसको भोजपुरी में बोलेंगे तू कहाँ रहेला"
    hedged = {"language_assessment": "The target language may be Bhojpuri or a related dialect."}
    p = part(raw, r.UNCERTAIN, assessment=hedged)
    assert p.rule.endswith("saved_assessment_hedges") and r.BHOJPURI in p.competing and "awadhi" in p.competing


def test_shared_forms_and_devanagari_alone_never_make_a_candidate():
    assert labels("तू कहाँ बा ह तू कहाँ बा") == [r.UNCERTAIN]  # shared forms only
    plain = "यह एक बहुत सुंदर जगह है यहाँ सब लोग आते हैं"
    assert labels(plain) == [r.UNCERTAIN]
    assert part(plain, r.UNCERTAIN).rule == "devanagari_text_without_variety_specific_evidence"


def test_naming_bhojpuri_without_any_bhojpuri_form_is_uncertain():
    p = part("यह वाक्य भोजपुरी में कैसे बोलेंगे कृपया बताइए", r.UNCERTAIN)
    assert p.rule == "speaker_names_bhojpuri_but_no_variety_specific_form_recognized"


def test_mixed_lesson_keeps_both_languages():
    raw = "हिंदी सेंटेंस है आप कहाँ जा रहे हैं इसको कैसे बोलेंगे रउआ कहाँ जात बानी"
    assert labels(raw) == [r.HINDI, r.BHOJPURI]
    clip = r.label_clip(raw_output=raw, submitted_language_code="hi-IN")
    assert clip.identification["mixed"] is True
    assert clip.identification["summary"] == "Mixed: Hindi | Likely Bhojpuri; recognized using Hindi mode."
    assert clip.recognition_matches_route


def test_short_or_non_devanagari_output_is_insufficient():
    assert labels("रउआ बानी") == [r.OTHER]
    assert labels("this is english text with many words in it") == [r.OTHER]
    assert r.propose("", None)[0].evidence == []


# --- Bundeli: a possible candidate, never produced by the table --------------------------------------------------------
def test_bundeli_appears_only_with_supplied_evidence_and_is_marked_unverified():
    raw = "यह बुंदेली में कहा गया वाक्य है जो हम सब सुन रहे हैं"
    assert r.BUNDELI not in labels(raw)
    supplied = [r.Evidence(kind="supplied", supports="bundeli", text="example cited form", origin="reviewer note, 2026-10-02")]
    p = part(raw, r.BUNDELI, supplied=supplied)
    assert p.display == "Likely Bundeli" and p.rule == "externally_supplied_evidence"
    assert any("unverified" in u for u in p.uncertainty)
    with pytest.raises(ValueError):
        r.Evidence(kind="supplied", supports="bundeli", text="x", origin="")  # evidence must say where it came from


# --- separation of facts ----------------------------------------------------------------------------------------------
def test_raw_output_is_preserved_exactly_and_submission_is_independent_of_the_label():
    raw = "  रउआ   कहाँ जात बानी \n"
    clip = r.label_clip(raw_output=raw, submitted_language_code="hi-IN", clip={"video_id": "x"})
    assert clip.recognition["raw_output"] == raw
    assert clip.recognition["submitted_language_code"] == "hi-IN"
    assert clip.identification["parts"][0]["label"] == r.BHOJPURI  # not relabelled as Hindi
    assert clip.boost.baseline_output == raw and clip.boost.boosted_output is None and not clip.boost.applied
    with pytest.raises(ValueError):
        r.label_clip(raw_output=raw, submitted_language_code="bho-IN")


def test_labels_do_not_depend_on_clip_metadata_such_as_filenames():
    raw = "रउआ कहाँ जात बानी"
    a = r.label_clip(raw_output=raw, submitted_language_code="hi-IN", clip={"filename": "Bhojpuri lesson.mp3"})
    b = r.label_clip(raw_output=raw, submitted_language_code="hi-IN", clip={"filename": "something else.mp3"})
    assert a.identification == b.identification


def test_assessment_text_is_quoted_as_labelled_context_only():
    raw = "यह एक बहुत सुंदर जगह है यहाँ सब लोग आते हैं"
    assessment = {"bhojpuri_evidence": "model says Bhojpuri", "uncertainties": "unverified"}
    clip = r.label_clip(raw_output=raw, submitted_language_code="hi-IN", assessment=assessment)
    assert clip.identification["parts"][0]["label"] == r.UNCERTAIN  # the model's claim alone does not create a label
    assert all("unverified model hearing" in c["origin"] for c in clip.identification["assessment_context"])


def test_boost_is_refused_without_a_validated_experiment_and_never_overwrites_the_baseline():
    clip = r.label_clip(raw_output="रउआ कहाँ जात बानी", submitted_language_code="hi-IN")
    with pytest.raises(ValueError, match="not justified"):
        r.attach_boost(clip, settings={"bias_list": ["रउआ"]}, output="x", experiment={"id": "e1"})
    ok = {"id": "e1", "references_human_corrected": True, "improved_over_baseline": True}
    r.attach_boost(clip, settings={"bias_list": ["रउआ"]}, output="boosted text", experiment=ok)
    assert clip.boost.boosted_output == "boosted text" and clip.boost.baseline_output == "रउआ कहाँ जात बानी"
    assert clip.recognition["raw_output"] == "रउआ कहाँ जात बानी"
    with pytest.raises(ValueError):
        r.BoostBlock(baseline_output="a", boosted_output="b")  # boosted text without provenance


# --- the thin wrapper around the real client (mock server, no credits) --------------------------------------------------
def test_recognize_and_label_sends_one_hindi_mode_request_and_keeps_the_proposed_label(tmp_path):
    seen = []

    def handler(request):
        seen.append(request.content)
        return httpx.Response(200, json={"success": True, "request_id": "req_1", "timestamp": "t", "transcript": "रउआ कहाँ जात बानी"})

    config = GnaniConfig("k", "https://api.example.invalid", "X-API-Key-ID", tmp_path / "cache")
    client = PrismaClient(config)
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    clip = r.recognize_and_label(client, b"audio bytes")
    assert len(seen) == 1 and b"hi-IN" in seen[0]
    assert clip.identification["parts"][0]["label"] == r.BHOJPURI and clip.recognition["request_id"] == "req_1"
    again = r.recognize_and_label(client, b"audio bytes")
    assert again.recognition["source"] == "local cache" and len(seen) == 1
