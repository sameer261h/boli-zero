"""Deterministic Bhojpuri-marker detector: flags whether a Devanagari transcript
is likely Bhojpuri vs plain Hindi, based on presence of distinctive dialect
markers. No LLM call — fast, free, explainable, and avoids the language-ID
unreliability we saw from Evon itself (it once misread a Bhojpuri word as Nepali).
"""

import re

# Distinctive Bhojpuri markers. Two sources, merged:
# (1) hand-picked from Boli cards / transcripts used across early experiments.
# (2) corpus-derived: word-frequency comparison of 5,903 real Bhojpuri transcripts
#     vs 6,840 real Hindi transcripts from Vaani-transcription-part — every word
#     below appeared 0 times in the Hindi set and 35+ times in the Bhojpuri set.
HAND_PICKED_MARKERS = [
    "बा", "बानी", "बाड़ी",  # copula forms (है/हूं/हो equivalents)
    "नइखे", "नइखीं",  # negation (नहीं है)
    "देब", "देई", "देइब",  # future "will give" forms
    "रउआ", "रउरा",  # you (आप)
    "काल्हे",  # tomorrow/yesterday (कल)
    "सोमारे", "सोमार",  # Monday (सोमवार)
    "अउरी",  # and/more (और)
    "दीं",  # please give (दीजिए)
    "आवे वाला बा",  # is coming
    "देले बानी",  # have given/paid
    "काहे",  # why (क्यों)
    "अगिला",  # next (अगला)
    "पाइब",  # will be able (पाऊंगा)
    "मोहलत",  # grace period (used distinctly in Bhojpuri collections speech)
    "तनखा",  # salary (used more in Bhojpuri/Bihari registers than standard Hindi)
    "कइले",  # did/having done (किया)
    "होखे", "होई",  # will happen (होगा)
    "जाइब", "जाईब",  # will go (जाऊंगा)
    "कटवा",  # get cut/disconnected
    "रहल", "रहल बा",  # is happening/ongoing
    "कहब",  # will say (कहूंगा)
]

CORPUS_DERIVED_MARKERS = [
    "रहल", "गइल", "लागता", "एकरा", "बाड़े", "लइका", "कोनो", "सन", "गईल",
    "लगावल", "केतना", "आपन", "रंगल", "दिखता", "जइसन", "जौन", "लोकत", "करिया",
    "बैठल", "पियर", "लउकत", "हमनी", "ठे", "जेमे", "एमें", "मिलेला", "जउन",
    "एइजा", "बावे", "बिया", "ओकरे", "उज्जर", "इहां", "पहनले", "आवेला", "हउवे",
    "जेकरा", "दिखात", "आवता", "लोगन", "आवत", "लईका", "हमके", "केहू", "जॉन",
    "कौनो", "बानी", "गेल", "बईठल", "जोवन", "कइल", "जेकर", "करल", "जवन",
    "हअ", "लौकत", "रहेला", "भईल", "होला", "लगाता",
]

MARKERS = sorted(set(HAND_PICKED_MARKERS) | set(CORPUS_DERIVED_MARKERS))

# Plain substring matching — Python's \b doesn't handle Devanagari combining
# vowel marks (मात्रा) reliably, so word-boundary regex broke real matches.
# Instead, short markers prone to collision (like "बा") are filtered below.
MARKER_PATTERN = re.compile("|".join(re.escape(m) for m in MARKERS))
SHORT_MARKERS_NEEDING_ISOLATION = {"बा", "दू"}
# Devanagari letters/vowel-signs that, if touching a short marker, mean it's
# actually inside a longer word (e.g. "बा" inside "बाइके").
# Devanagari block minus punctuation (danda ।॥ at U+0964-0965) so sentence-
# ending markers aren't wrongly treated as mid-word.
DEVANAGARI_WORD_CHAR = re.compile(r"[ऀ-ॣ०-ॿ]")


def _is_isolated(transcript: str, start: int, end: int) -> bool:
    before_ok = start == 0 or not DEVANAGARI_WORD_CHAR.match(transcript[start - 1])
    after_ok = end == len(transcript) or not DEVANAGARI_WORD_CHAR.match(transcript[end])
    return before_ok and after_ok

# A single marker can still be a coincidental match (short markers especially).
# Confidence saturates at 3+ distinct markers; below the threshold, default to Hindi.
CONFIDENCE_SATURATION = 3
CONFIDENCE_THRESHOLD = 0.67  # requires ~2 markers to clear


def detect(transcript: str, threshold: float = CONFIDENCE_THRESHOLD) -> dict:
    valid_matches = []
    for m in MARKER_PATTERN.finditer(transcript):
        token = m.group()
        if token in SHORT_MARKERS_NEEDING_ISOLATION and not _is_isolated(
            transcript, m.start(), m.end()
        ):
            continue
        valid_matches.append(token)
    matches = valid_matches
    unique_matches = sorted(set(matches))
    confidence = min(1.0, len(unique_matches) / CONFIDENCE_SATURATION)
    is_bhojpuri = confidence >= threshold
    return {
        "transcript": transcript,
        "is_bhojpuri": is_bhojpuri,
        "confidence": round(confidence, 2),
        "marker_count": len(matches),
        "unique_marker_count": len(unique_matches),
        "markers_found": unique_matches,
        "language": "bhojpuri" if is_bhojpuri else "hindi",
    }


if __name__ == "__main__":
    # Validation set: genuinely Bhojpuri statements from the EMI experiments,
    # vs the 5 Vaani scene-description clips (should read as plain Hindi).
    bhojpuri_cases = [
        "हम सोमवार के पैसा जमा कर देब।",
        "अभी पइसा नइखे, काल्हे जमा कर देब।",
        "आज पइसा ना बा, सोमारे दे देब।",
        "दू दिन अउरी मोहलत दे दीं, तनखा आवे वाला बा।",
        "हम त काल्हे पइसा जमा कर देले बानी, फेर काहे फोन आ रहल बा?",
        "पूरा पइसा अभी ना दे पाइब, आधा आज देब बाकी अगिला हफ्ता।",
        "हम पैसा नइखीं देब, जे करे के होखे करी।",
        "इहाँ एह नाम के कवनो आदमी नइखे रहत।",
    ]
    hindi_cases = [
        "ये ट्रैफिक सिग्नल से रिलेटेड है जिसमें प्रदूषण की वजह से दिखाया जा रहा है",
        "आगे एक पेड़ है और चार बाइके दिख रही हैं इसमें एक ट्रक दिख",
        "यह एक तालाब है गंदा सा तालाब है जिसमें चिड़िया है कुछ बच्चे हैं",
        "ये कोई फंक्शन है जिसमें ढेर सारी बच्चियां हैं और इनका पहनावा का जो रंग है वो सफ़ेद और लाल में है",
        "भारत की राजधानी क्या है?",
    ]

    print("=== Should detect as Bhojpuri ===")
    correct = 0
    for t in bhojpuri_cases:
        r = detect(t)
        status = "✓" if r["is_bhojpuri"] else "✗ MISSED"
        correct += r["is_bhojpuri"]
        print(f"{status} [{r['marker_count']} markers: {r['markers_found']}] {t}")
    print(f"\n{correct}/{len(bhojpuri_cases)} correctly flagged as Bhojpuri")

    print("\n=== Should detect as plain Hindi ===")
    correct = 0
    for t in hindi_cases:
        r = detect(t)
        status = "✓" if not r["is_bhojpuri"] else "✗ FALSE POSITIVE"
        correct += not r["is_bhojpuri"]
        print(f"{status} [{r['marker_count']} markers: {r['markers_found']}] {t}")
    print(f"\n{correct}/{len(hindi_cases)} correctly flagged as plain Hindi")
