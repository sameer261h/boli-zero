"""Stage 5: rebuilt Prisma behavioural-similarity evidence, cautiously.

Fixes vs. the earlier ad-hoc clustering pass:
  1. Normalize substitution rate by total_human_words (real word-opportunity
     count), not clip_count (clips vary wildly in length).
  2. Do NOT hard-delete "universal" substitutions. Downweight them with an
     IDF-style weight (log(19 / n_dialects_with_this_pair)) so a pair that's
     universal contributes ~0 but a pair that's common-but-at-very-different-
     RATES across dialects still carries signal.
  3. Compare three independently-reasoned similarity methods per pair:
       - cosine on IDF-weighted, word-opportunity-normalized rate vectors
       - Jaccard overlap of substitution-pair TYPES (ignores rate entirely)
       - Spearman rank-correlation of rates, restricted to substitution types
         both dialects actually share (tests whether the RELATIVE ordering
         of shared patterns agrees, independent of absolute scale)
  4. For each of the 8 explicitly-named candidate pairs, and the proposed
     4-way Sadri+Surgujia+Awadhi+Haryanvi bucket, report all three methods
     and whether they agree (stability) -> STRONG/MODERATE/WEAK/UNSUPPORTED.

No Evon/Prisma calls -- pure recomputation from already-saved
per_dialect_results.json.
"""

import json
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint"
ANALYSIS_DIR = DATA_DIR / "analysis"
OUT_DIR = DATA_DIR / "regional_fingerprint_audit"

NAMED_PAIRS = [
    ("Magahi", "Bajjika"), ("Marwari", "Rajasthani"), ("Surgujia", "Chhattisgarhi"),
    ("Khortha", "Surjapuri"), ("Maithili", "Angika"), ("Kumaoni", "Garhwali"),
    ("Kumaoni", "Khariboli"), ("Bundeli", "Khariboli"),
]
CHALLENGE_BUCKET = ["Sadri", "Surgujia", "Awadhi", "Haryanvi"]


def main():
    d = json.load(open(ANALYSIS_DIR / "per_dialect_results.json"))
    dialects = list(d.keys())
    n_dialects = len(dialects)

    # 1. collect all substitution-pair types and which dialects have them, with raw counts
    pair_dialect_count = {}
    pair_rate = {}  # (dialect, pair) -> count / total_human_words
    pair_types_by_dialect = {}
    for dialect in dialects:
        info = d[dialect]
        thw = info["total_human_words"]
        types = set()
        for pair, count in info["top_substitutions"]:
            p = tuple(pair)
            types.add(p)
            pair_rate[(dialect, p)] = count / thw if thw else 0.0
            pair_dialect_count[p] = pair_dialect_count.get(p, 0) + 1
        pair_types_by_dialect[dialect] = types

    all_pairs = sorted(pair_dialect_count.keys())
    pair_idx = {p: i for i, p in enumerate(all_pairs)}

    # 2. IDF weight per substitution-pair type (downweight, don't delete)
    idf = {p: np.log(n_dialects / pair_dialect_count[p]) for p in all_pairs}
    print(f"{len(all_pairs)} distinct substitution-pair types across {n_dialects} dialects")
    print("IDF range:", round(min(idf.values()), 3), "to", round(max(idf.values()), 3))
    most_universal = sorted(pair_dialect_count.items(), key=lambda x: -x[1])[:5]
    print("Most universal pairs (highest dialect_count, lowest idf, downweighted not deleted):")
    for p, c in most_universal:
        print(f"   {p} appears in {c}/{n_dialects} dialects, idf={idf[p]:.3f}")

    # 3. build IDF-weighted, word-opportunity-normalized vectors
    vecs = np.zeros((n_dialects, len(all_pairs)))
    for i, dialect in enumerate(dialects):
        for p in pair_types_by_dialect[dialect]:
            vecs[i, pair_idx[p]] = pair_rate[(dialect, p)] * idf[p]
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vecs_n = vecs / norms
    cosine_sim = vecs_n @ vecs_n.T

    def jaccard(d1, d2):
        s1, s2 = pair_types_by_dialect[d1], pair_types_by_dialect[d2]
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / len(s1 | s2)

    def spearman_shared(d1, d2):
        shared = pair_types_by_dialect[d1] & pair_types_by_dialect[d2]
        if len(shared) < 4:
            return None, len(shared)
        r1 = [pair_rate[(d1, p)] for p in shared]
        r2 = [pair_rate[(d2, p)] for p in shared]
        rho, _ = spearmanr(r1, r2)
        return (round(float(rho), 3) if rho == rho else None), len(shared)

    d_idx = {d: i for i, d in enumerate(dialects)}

    def classify(cos, jac, rho, n_shared):
        # STRONG: all three signals clearly positive and in agreement
        # MODERATE: cosine positive, at least one other signal supports it
        # WEAK: signals present but small / disagree
        # UNSUPPORTED: no real shared basis (too few shared types, near-zero everywhere)
        if n_shared < 3:
            return "UNSUPPORTED (too few shared substitution types to judge)"
        signals_positive = sum([
            cos is not None and cos > 0.35,
            jac is not None and jac > 0.12,
            rho is not None and rho > 0.3,
        ])
        if signals_positive >= 3:
            return "STRONG"
        if signals_positive == 2:
            return "MODERATE"
        if signals_positive == 1:
            return "WEAK"
        return "UNSUPPORTED"

    print("\n=== Named pair stability test (3 independent methods) ===")
    pair_results = {}
    for a, b in NAMED_PAIRS:
        if a not in d_idx or b not in d_idx:
            print(f"  {a} <-> {b}: MISSING DATA")
            continue
        cos = float(cosine_sim[d_idx[a], d_idx[b]])
        jac = jaccard(a, b)
        rho, n_shared = spearman_shared(a, b)
        verdict = classify(cos, jac, rho, n_shared)
        pair_results[f"{a}<->{b}"] = {"cosine": round(cos, 3), "jaccard": round(jac, 3),
                                        "spearman_on_shared": rho, "n_shared_types": n_shared, "verdict": verdict}
        print(f"  {a:15}<->{b:15} cosine={cos:.3f}  jaccard={jac:.3f}  spearman(shared={n_shared})={rho}  => {verdict}")

    print("\n=== Full pairwise matrix for the 4-way challenge bucket: Sadri+Surgujia+Awadhi+Haryanvi ===")
    bucket_results = {}
    for a, b in combinations(CHALLENGE_BUCKET, 2):
        if a not in d_idx or b not in d_idx:
            continue
        cos = float(cosine_sim[d_idx[a], d_idx[b]])
        jac = jaccard(a, b)
        rho, n_shared = spearman_shared(a, b)
        verdict = classify(cos, jac, rho, n_shared)
        bucket_results[f"{a}<->{b}"] = {"cosine": round(cos, 3), "jaccard": round(jac, 3),
                                          "spearman_on_shared": rho, "n_shared_types": n_shared, "verdict": verdict}
        print(f"  {a:12}<->{b:12} cosine={cos:.3f}  jaccard={jac:.3f}  spearman(shared={n_shared})={rho}  => {verdict}")

    # also show each of these 4 dialects' single strongest partner among ALL 19,
    # to see if their "best friend" is actually inside or outside the proposed bucket
    print("\n=== Each challenge-bucket member's single strongest partner among all 19 (by cosine) ===")
    strongest_partner = {}
    for dname in CHALLENGE_BUCKET:
        i = d_idx[dname]
        sims = [(dialects[j], float(cosine_sim[i, j])) for j in range(n_dialects) if j != i]
        sims.sort(key=lambda x: -x[1])
        strongest_partner[dname] = sims[:4]
        print(f"  {dname}: " + ", ".join(f"{nm}={s:.3f}" for nm, s in sims[:4]))

    out = {
        "n_substitution_pair_types": len(all_pairs),
        "named_pair_results": pair_results,
        "challenge_bucket_pairwise": bucket_results,
        "challenge_bucket_strongest_partners": strongest_partner,
        "full_cosine_matrix": cosine_sim.tolist(),
        "dialect_order": dialects,
    }
    with open(OUT_DIR / "prisma_similarity_v2_results.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'prisma_similarity_v2_results.json'}")


if __name__ == "__main__":
    main()
