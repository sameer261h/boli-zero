"""Analyze human-vs-Prisma transcript pairs for dialect-specific transformation
patterns ("the Prisma fingerprint" hypothesis).

Cleans annotation artifacts (<tags>, [brackets], {glosses}, punctuation) from
the human transcript so the comparison isolates actual ASR behavior rather
than our own annotation conventions, then does a word-level alignment
(difflib) per clip and aggregates substitution/deletion/insertion patterns
per dialect.

Usage:
  python analyze_prisma_fingerprint.py
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint"
OUT_DIR = DATA_DIR / "analysis"

DIALECTS = [
    "Bhojpuri", "Chhattisgarhi", "Maithili", "Rajasthani", "Garhwali",
    "Marwari", "Magahi", "Bajjika", "Khortha", "Angika", "Kumaoni",
    "Sadri", "Khariboli", "Surgujia", "Bundeli", "Surjapuri", "Awadhi",
    "Haryanvi", "Jaipuri",
]

TAG_RE = re.compile(r"</?[A-Za-z_]+>")  # <noise>, </noise>, <PAUSE>, etc.
BRACKET_RE = re.compile(r"\[[^\]]*\]")  # [inaudible], [breathing]
BRACE_RE = re.compile(r"\{[^}]*\}")  # {atm}, {color}
TRAILING_DASH_RE = re.compile(r"-{1,}\s*$")
PUNCT_RE = re.compile(r"[।,.?!;:\"'()\-]")
WS_RE = re.compile(r"\s+")


def clean(text):
    text = unicodedata.normalize("NFC", text)  # canonicalize nukta/matra codepoint sequences
    text = TAG_RE.sub(" ", text)
    text = BRACKET_RE.sub(" ", text)
    text = BRACE_RE.sub(" ", text)
    text = TRAILING_DASH_RE.sub(" ", text)
    text = PUNCT_RE.sub(" ", text)
    text = WS_RE.sub(" ", text).strip()
    return text


def tokenize(text):
    return clean(text).split()


def load_dialect(dialect):
    path = DATA_DIR / f"{dialect}.jsonl"
    rows = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r.get("error"):
                continue
            if not r.get("human_transcript") or not r.get("prisma_transcript"):
                continue
            rows.append(r)
    return rows


def align(human_tokens, prisma_tokens):
    """Return list of (op, human_span, prisma_span) from difflib opcodes."""
    sm = SequenceMatcher(None, human_tokens, prisma_tokens, autojunk=False)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        ops.append((tag, tuple(human_tokens[i1:i2]), tuple(prisma_tokens[j1:j2])))
    return ops


def analyze_dialect(dialect, marker_words):
    rows = load_dialect(dialect)
    sub_counter = Counter()  # (human_word, prisma_word) for 1:1 substitutions
    delete_counter = Counter()  # human word dropped entirely
    insert_counter = Counter()  # prisma word added (hallucination)
    marker_fates = Counter()  # what happens to known dialect marker words specifically

    total_human_words = 0
    total_edit_ops = 0  # rough word-level edit distance proxy
    clip_count = 0
    identical_count = 0

    for r in rows:
        h_tokens = tokenize(r["human_transcript"])
        p_tokens = tokenize(r["prisma_transcript"])
        if not h_tokens:
            continue
        clip_count += 1
        total_human_words += len(h_tokens)

        if h_tokens == p_tokens:
            identical_count += 1
            continue

        ops = align(h_tokens, p_tokens)
        for tag, h_span, p_span in ops:
            if tag == "replace" and len(h_span) == 1 and len(p_span) == 1:
                if h_span[0] != p_span[0]:  # guard against alignment artifacts on repeated words
                    sub_counter[(h_span[0], p_span[0])] += 1
                    total_edit_ops += 1
            elif tag == "replace":
                h_joined, p_joined = " ".join(h_span), " ".join(p_span)
                if h_joined != p_joined:
                    sub_counter[(h_joined, p_joined)] += 1
                total_edit_ops += max(len(h_span), len(p_span))
            elif tag == "delete":
                for w in h_span:
                    delete_counter[w] += 1
                total_edit_ops += len(h_span)
            elif tag == "insert":
                for w in p_span:
                    insert_counter[w] += 1
                total_edit_ops += len(p_span)

            for w in h_span:
                if w in marker_words:
                    if tag == "delete":
                        marker_fates[(w, "DELETED")] += 1
                    elif tag == "replace":
                        repl = " ".join(p_span) if p_span else "DELETED"
                        marker_fates[(w, repl)] += 1

    wer_proxy = total_edit_ops / total_human_words if total_human_words else 0

    return {
        "dialect": dialect,
        "clip_count": clip_count,
        "identical_count": identical_count,
        "identical_rate": round(identical_count / clip_count, 4) if clip_count else 0,
        "total_human_words": total_human_words,
        "word_edit_rate_proxy": round(wer_proxy, 4),
        "top_substitutions": sub_counter.most_common(40),
        "top_deletions": delete_counter.most_common(30),
        "top_insertions": insert_counter.most_common(30),
        "marker_word_fates": marker_fates.most_common(40),
    }


def load_known_markers():
    """Pull known dialect marker words from the earlier markers_v2.json run, if present."""
    markers_path = DATA_DIR.parent / "markers_v2.json"
    all_markers = defaultdict(set)
    if markers_path.exists():
        data = json.loads(markers_path.read_text())
        for dialect, markers in data.get("markers", {}).items():
            for word in markers:
                all_markers[dialect].add(word)
    return all_markers


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    known_markers = load_known_markers()

    all_results = {}
    cross_dialect_subs = Counter()  # substitution patterns appearing across many dialects
    dialect_subs_sets = {}

    for dialect in DIALECTS:
        marker_words = known_markers.get(dialect, set())
        print(f"=== {dialect} (marker words known: {len(marker_words)}) ===")
        result = analyze_dialect(dialect, marker_words)
        all_results[dialect] = result
        dialect_subs_sets[dialect] = set(w for w, _ in result["top_substitutions"])
        print(f"  clips={result['clip_count']} identical_rate={result['identical_rate']} "
              f"word_edit_rate_proxy={result['word_edit_rate_proxy']}")
        for (h, p), c in result["top_substitutions"][:8]:
            cross_dialect_subs[(h, p)] += 1
            print(f"    {h!r} -> {p!r}  (x{c})")
        print()

    with open(OUT_DIR / "per_dialect_results.json", "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Cross-dialect: which exact (human,prisma) substitution pairs recur across many dialects?
    universal = [(pair, n) for pair, n in cross_dialect_subs.items() if n >= 3]
    universal.sort(key=lambda x: -x[1])
    with open(OUT_DIR / "cross_dialect_universal_substitutions.json", "w") as f:
        json.dump([{"human": h, "prisma": p, "dialect_count": n} for (h, p), n in universal],
                   f, ensure_ascii=False, indent=2)

    print("\n=== Summary across all dialects ===")
    for dialect, result in sorted(all_results.items(), key=lambda x: -x[1]["word_edit_rate_proxy"]):
        print(f"{dialect}: clips={result['clip_count']} "
              f"identical_rate={result['identical_rate']} "
              f"word_edit_rate_proxy={result['word_edit_rate_proxy']}")

    print(f"\nSubstitution patterns recurring in >=3 dialects: {len(universal)}")
    print(f"Results written to {OUT_DIR}")


if __name__ == "__main__":
    main()
