# Safe vs. ambiguous Prisma transformation classification — concrete design

Status: core algorithm **ready to implement**; semantic-equivalence clustering is a
**documented but not-yet-validated extension** (needs a linguist pass before it gates
any production behavior). See the verdict section at the end.

This builds directly on `docs/2026-10-05-evon-pipeline/10-chatgpt-safe-vs-ambiguous-review-prompt.md`
(the "6 examples" write-up) and reuses the data/tooling in
`experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/` and
`experiments/2026-10-05-evon-pipeline/scripts/analyze_prisma_fingerprint.py`. All numbers
below were computed from the real 25k-clip corpus in this session; the scripts used are
reproduced inline as pseudocode and also exist as working Python at
`/tmp/claude-0/-home-user-boli-zero/11b7a7bf-af9a-5ac9-8b43-2932d2e1b2ba/scratchpad/dealign.py`
(not committed — portable pseudocode is given below so this doc stands alone).

---

## 0. The single biggest finding, stated up front

**Before any scoring formula matters, the "6 examples" numbers in doc 10 are not
reproducible from the repo's own `analyze_prisma_fingerprint.py`, and the discrepancy is
large enough to flip several verdicts from "scattered" to "clearly dominant."**

Look at `align()` in `analyze_prisma_fingerprint.py`:

```python
def align(human_tokens, prisma_tokens):
    sm = SequenceMatcher(None, human_tokens, prisma_tokens, autojunk=False)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue          # <-- equal-tag spans are dropped before the caller ever sees them
        ops.append((tag, tuple(human_tokens[i1:i2]), tuple(prisma_tokens[j1:j2])))
    return ops
```

`marker_fates` in `analyze_dialect()` only iterates over `ops` (never-equal). That means
the repo's own pipeline **cannot structurally produce an "UNCHANGED" outcome** for a
marker word at all — every occurrence of a word that survives untouched inside a clip
that has *some* other edit elsewhere is invisible to `marker_fates`, and every occurrence
inside a fully-identical clip (`h_tokens == p_tokens`) is skipped even earlier. So
whatever produced doc 10's "UNCHANGED (24.5%)" line for Bhojpuri "है" was **not**
`analyze_dialect()` as committed — it was some other, undocumented one-off computation,
and its exact denominator (which clips counted, how UNCHANGED was detected) can't be
verified from the repo.

I recomputed all 6 example words with an explicit, auditable denominator: every
occurrence of the target word in the human transcript, across every clip (including
fully-identical clips, where the word trivially counts as UNCHANGED), using the *same*
whole-sentence `difflib` alignment the repo already uses. Results (`N` = total tracked
occurrences):

| Dialect | Word | N | Top outcome (whole-block difflib) | % |
|---|---|---|---|---|
| Rajasthani | री | 374 | `रही` | 44.7% |
| Rajasthani | है | 3054 | `UNCHANGED` | 71.4% |
| Garhwali | यख | 374 | `UNCHANGED` | 33.2% |
| Garhwali | भौत | 122 | `बहुत` | 34.4% |
| Bhojpuri | है | 1695 | `UNCHANGED` | 81.5% |
| Bhojpuri | बा | 4741 | `UNCHANGED` | 82.6% |

Two of the six ("है" in both Rajasthani and Bhojpuri, plus "बा") look **dominantly
UNCHANGED** once UNCHANGED is counted correctly — the opposite of "scattered, no
dominant outcome" as doc 10 characterized them. This is a denominator bug/ambiguity in
the *prior* analysis, not a property of the data. **Recommendation: any production
scoring pipeline must explicitly define and log its denominator (identical clips
included, equal-span occurrences included) and that definition must be reviewed before
anyone trusts a "scattered" verdict again.**

This doesn't make doc 10 vacuous — "री", "यख", and "भौत" are not UNCHANGED-dominated
words (they're real substitution/content words), so the denominator bug doesn't explain
their apparent scatter. That's what section 1 investigates.

---

## 1. Testing the alignment-artifact hypothesis (does multi-word block merging hide consistency?)

### Method

`difflib.SequenceMatcher.get_opcodes()` returns **contiguous runs** of non-equal tokens
as a single `replace` opcode, even when the run actually contains two independent,
spatially-adjacent edits (e.g. the target word substitutes *and* its neighbor
substitutes, with no untouched token between them to break the block). This is exactly
the confound flagged in doc 10: "रही छै", "यखमा जी", "रहा हलवा" etc. are plausibly two
edits glued into one block by `difflib`'s block-matching heuristic, not one coherent
multi-word transformation.

To test this, I implemented a **second, independent alignment method** — a global
word-level DP alignment (Needleman-Wunsch style) where the substitution cost between
human word `h` and Prisma word `p` is a *character-similarity* cost, not an exact-match
cost:

```python
def char_sim(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()   # 0..1, 1 = identical

def align_fuzzy(human_tokens, prisma_tokens, gap_cost=0.92):
    n, m = len(human_tokens), len(prisma_tokens)
    dp = [[0.0]*(m+1) for _ in range(n+1)]
    for i in range(1, n+1): dp[i][0] = i * gap_cost
    for j in range(1, m+1): dp[0][j] = j * gap_cost
    for i in range(1, n+1):
        for j in range(1, m+1):
            sub_cost = 0.0 if human_tokens[i-1] == prisma_tokens[j-1] \
                       else 1.0 - char_sim(human_tokens[i-1], prisma_tokens[j-1])
            dp[i][j] = min(
                dp[i-1][j-1] + sub_cost,   # align h[i-1] <-> p[j-1] (substitute or match)
                dp[i-1][j]   + gap_cost,   # h[i-1] deleted
                dp[i][j-1]   + gap_cost,   # p[j-1] inserted
            )
    # standard traceback -> list of (h_idx_or_None, p_idx_or_None, cost)
```

Because this is a **1:1 (+gap) alignment by construction**, every human word gets
*exactly one* outcome: aligned to one specific Prisma word (cost 0 = identical =
`UNCHANGED`; cost > 0 = `-> <that word>`), or a gap (`DELETED`). **Multi-word blocks are
structurally impossible** — this directly removes the confound doc 10 flagged, rather
than just theorizing about it. `gap_cost = 0.92` was chosen so that gap+gap (0.92+0.92 =
1.84) is cheaper than aligning two genuinely unrelated words (cost close to 1.0 each, but
real substitutions like री↔रही have `char_sim ≈ 0.57`, cost `≈ 0.43`, far below the gap
alternative) — i.e., it prefers substituting visually/phonetically similar words over
treating them as independent insert+delete. I checked robustness: **re-running with
`gap_cost` in {0.80, 0.85, 0.92, 0.97, 1.05} produced bit-for-bit identical top-outcome
percentages for both "री" and "भौत"** — the result is not a tuning artifact.

### Results: exact (whole-block difflib) vs. fuzzy (de-merged 1:1) outcome distributions

| Dialect/Word | N | Top-1 % (exact, whole-block) | Top-1 % (fuzzy, de-merged) | Verdict on artifact hypothesis |
|---|---|---|---|---|
| Rajasthani "री" | 374 | 44.7% (→रही) | **63.1%** (→रही) | **Partially confirmed** — merging was hiding real consistency; a big chunk of the "multi-word" outcomes (रही छै, दिखीरी, दिखेरी, …) really were री→रही plus an unrelated neighboring edit |
| Rajasthani "है" | 3054 | 71.4% (UNCHANGED) | 70.9% (UNCHANGED) | **Not a factor** — but DELETED jumps 6.9%→15.4% once de-merged: deletions of "है" were being absorbed into blocks like "रहे हैं" and mislabeled as substitutions |
| Garhwali "यख" | 374 | 33.2% (UNCHANGED) | 32.6% (UNCHANGED) | **Not a factor at all** — यख is genuinely scattered under both methods; this deictic really is context-dependent |
| Garhwali "भौत" | 122 | 34.4% (→बहुत) | **87.7%** (→बहुत) | **Strongly confirmed** — the single biggest result in this analysis. Once de-merged, भौत→बहुत is overwhelmingly the dominant pattern (entropy drops from 4.99 to 0.81 bits, distinct outcomes drop from 76 to 8) |
| Bhojpuri "है" | 1695 | 81.5% (UNCHANGED) | 81.2% (UNCHANGED) | Not a factor — already dominant either way |
| Bhojpuri "बा" | 4741 | 82.6% (UNCHANGED) | 82.6% (UNCHANGED) | Not a factor for the top outcome, but DELETED is undercounted 1.7%→6.2% when merged (same hidden-deletion pattern as "है") |

**Conclusion: the alignment-artifact hypothesis is real but selective.** It matters a
lot for words whose *non-dominant* correct transformation sits inside longer phrases
(भौत "very" shows up next to adjectives it's modifying — "बहुत सारे", "बहुत सुंदर" — so
it's disproportionately caught in multi-word blocks; री similarly sits next to verb
stems that often change too). It does **not** rescue words whose scatter is genuine
content-level ambiguity (यख — a deictic whose Hindi rendering depends on real context,
not an artifact) or change the picture for words already dominated by UNCHANGED/DELETED
as single tokens. It also reveals a **second artifact in the same direction**: deletions
of a target word get mislabeled as multi-word substitutions when a neighboring word also
changes, so the exact/whole-block method systematically *undercounts* deletions for
is/copula words — this cuts against safety, not for it, and needs to be in the
deletion-risk accounting (section 3).

**This means: the outcome-extraction step for the production algorithm must use the
fuzzy 1:1 DP alignment, not the existing whole-sentence `difflib` opcodes.** The
existing `align()`/`analyze_dialect()` pipeline is fine for aggregate dialect
fingerprinting (its original purpose) but is the wrong tool for per-word consistency
scoring.

---

## 2. The scoring algorithm

### 2.1 Outcome extraction (per word, per dialect)

For dialect `D` and target word `X`:

1. Load all clips for `D` (`load_dialect()`, unchanged from the existing script).
2. For each clip, tokenize both transcripts with the existing `clean()`/`tokenize()`.
3. Run `align_fuzzy(human_tokens, prisma_tokens)` (section 1) to get a 1:1(+gap) word
   alignment for the whole sentence.
4. For every human-token index `i` where `human_tokens[i] == X`, record one outcome:
   - aligned to nothing → `"DELETED"`
   - aligned to `prisma_tokens[j]` with `cost == 0` → `"UNCHANGED"`
   - aligned to `prisma_tokens[j]` with `cost > 0` → `f"-> {prisma_tokens[j]}"`
5. Accumulate a `Counter` over all these outcomes across all clips in `D`. `N` = total
   occurrences (`sum(counter.values())`).

This gives one flat distribution per `(dialect, word)` pair with no multi-word blocks,
by construction.

### 2.2 The statistical gate

Given the outcome counter and `N`:

```
top_label, top_count = counter.most_common(1)[0]
p1 = top_count / N                                   # point estimate of consistency

# Wilson score lower bound, 95% one-sided confidence (z = 1.96)
def wilson_lower_bound(n1, N, z=1.96):
    p = n1 / N
    denom = 1 + z**2 / N
    center = p + z**2 / (2*N)
    margin  = z * sqrt((p*(1-p) + z**2/(4*N)) / N)
    return (center - margin) / denom

lb = wilson_lower_bound(top_count, N)
```

**Why Wilson lower bound and not raw `p1`:** words in this corpus range from `N=122`
(भौत) to `N=4741` (बा). A raw percentage treats a word seen 50 times the same as one
seen 5,000 times, which is exactly backwards for a production "silently auto-correct"
gate — a lucky 8/10 for a rare word is not the same evidence as 3500/5000 for a common
one. The Wilson interval (not the simpler normal-approximation interval, which behaves
badly near `p=0` or `p=1`) shrinks the usable bound for small `N` and converges to `p1`
for large `N`. I use the **lower bound only** — it answers "what's the worst-case
consistency I can still defend at 95% confidence," which is the right question for a
behavior that silently rewrites transcripts.

**Why not raw percentage alone:** per the original doc 10 framing ("safe if top outcome
≥ 70%, ≥10 occurrences") — `N=10` is far too small; at `N=10` even `p1=0.80` has a
Wilson LB of only `0.49`, i.e. statistically indistinguishable from a coin flip at that
sample size. The minimum-N requirement below is a direct consequence of plugging real
numbers into this formula, not an arbitrary round number.

**Why not entropy as the primary gate:** I computed Shannon entropy (`H = -Σ p_i log2
p_i`) for every word above and it's informative as a *diagnostic* (reported in every
table) but a poor *primary gate*: words with large `N` accumulate long tails of
one-off/transcription-noise outcomes (Bhojpuri "बा" has 196 distinct outcomes at
`N=4741`, most of them singletons), which inflates entropy even when the top outcome is
overwhelmingly dominant (बा: `H=1.56` bits despite `p1=0.826`). Entropy conflates "the
top answer isn't dominant" with "there's a long thin tail of noise below a dominant
answer" — exactly the two situations we need to tell apart. Wilson LB on the top-1 share
doesn't have this problem. **Recommendation: log entropy and distinct-outcome-count
per word for human review/monitoring dashboards, but gate production behavior on Wilson
LB of top-1 (or top-cluster, see 2.4) share.**

### 2.3 Minimum sample size and decision tiers

```
MIN_N_FLOOR        = 50     # below this, don't even attempt a verdict
MIN_N_AUTOCORRECT  = 100    # required (in addition to the LB bar) for silent auto-apply
SAFE_LB_SHADOW     = 0.70   # LB threshold for "safe candidate" (shadow-mode / log-only)
SAFE_LB_AUTOCORRECT= 0.75   # stricter LB threshold required to silently auto-apply in prod

def classify(outcomes: Counter, N: int, top_is_deletion: bool, in_delete_allowlist: bool):
    if N < MIN_N_FLOOR:
        return "INSUFFICIENT_DATA"

    top_label, top_count = outcomes.most_common(1)[0]
    lb = wilson_lower_bound(top_count, N)

    if top_label == "DELETED" and not in_delete_allowlist:
        return "AMBIGUOUS"          # deletions never pass by default -- see section 3

    if lb >= SAFE_LB_AUTOCORRECT and N >= MIN_N_AUTOCORRECT:
        return "SAFE_AUTOCORRECT"   # apply silently via lookup table
    if lb >= SAFE_LB_SHADOW:
        return "SAFE_CANDIDATE"     # log/shadow-mode: apply but flag for audit, don't trust blindly yet
    return "AMBIGUOUS"              # surface top 2-3 outcomes to Evon as a hint, don't auto-apply
```

Two tiers of "safe" (`SAFE_AUTOCORRECT` vs `SAFE_CANDIDATE`) rather than one, because the
cost of a wrong silent correction in a production voice pipeline is asymmetric and the
task explicitly calls this out: a word just barely clearing `LB ≥ 0.70` at `N=60` is
real signal, but it's not the same confidence level as `LB ≥ 0.80` at `N=3000`. Shipping
`SAFE_CANDIDATE` entries as silent auto-corrects on day one is how this becomes "wrong
often enough to matter"; shipping them as logged-but-applied-with-audit-trail lets you
promote them to `SAFE_AUTOCORRECT` once the corpus (or a follow-up audit) confirms them.

`MIN_N_FLOOR = 50` is not arbitrary: at `N=50`, even `p1=1.00` (literally never observed
any other outcome) only reaches `LB=0.929`, and `p1=0.80` at `N=50` gives `LB=0.674` —
already failing `SAFE_LB_SHADOW`. In other words, the floor is where the *gate itself*
starts being informative; below it, the Wilson bound auto-rejects almost everything
anyway, so `MIN_N_FLOOR` mainly exists to short-circuit to a distinct `INSUFFICIENT_DATA`
label (so it's obvious in reporting *why* a word wasn't classified, rather than it
silently reading as "ambiguous" and getting lumped in with words that have abundant data
and genuine scatter).

### 2.4 Semantic-equivalence clustering — proposed, but gated behind manual curation

Doc 10 asked specifically whether है/हैं/UNCHANGED should be pooled as one "safe cluster"
since they're just copula agreement/tense variants. I think the idea is sound **in
principle** but must not be automated by the same character-similarity metric already
used for alignment (section 1) — that would be circular (it would just re-derive "these
strings look similar" rather than "these strings are functionally interchangeable to a
downstream Hindi-reading LLM"), and it risks silently merging real semantic contrasts
dialect speakers intend (e.g. a dialect speaker's choice between present/past copula
forms is sometimes meaningful).

**Design**: a per-dialect, human-curated `semantic_clusters` lookup
(`{(dialect, word): [outcome_label, ...]}`), reviewed by someone who actually reads the
dialect, listing which non-deletion outcome labels are considered interchangeable for
Evon's purposes. The scoring function then computes the LB on the **summed count of the
cluster's members** instead of just the single top label — but with one hard rule:
**`DELETED` can never be a member of a semantic-equivalence cluster** (it isn't an
"equivalent" rendering, it's information loss — see section 3), and a word's
`DELETED` share must additionally be checked against a cap even after clustering.

Illustration with real data (not yet linguist-reviewed — this is a worked example of the
mechanism, not a shipped cluster list):

- **Maithili "छै"** (copula): fuzzy outcomes are `→छे` 65.7%, `UNCHANGED` 13.6%,
  `DELETED` 10.0%, `→है` 1.7%, `→छ` 0.9%, `→छई` 0.8%. Treating {छे, UNCHANGED, है, छ, छई}
  as one "copula orthographic/agreement variant" cluster (excluding DELETED) sums to
  **82.7%**, `LB95 ≈ 0.81` — this would flip "छै" from `AMBIGUOUS` to `SAFE_CANDIDATE`
  under clustering, *if* a Maithili-literate reviewer confirms छे/है/छ/छई really are
  interchangeable here. **But its DELETED share (10.0%) is a real, separate 1-in-10
  failure mode that clustering does nothing about** — I'd recommend a rule like "cluster
  LB ≥ 0.70 AND DELETED share ≤ 10%" before calling a clustered word safe, and छै sits
  exactly on that deletion-share boundary, which is a good reason to leave it
  `AMBIGUOUS` until a human looks at it, not a good reason to auto-pass it.
- **Rajasthani "है"**: clustering {UNCHANGED, हैं, रहे} (copula-agreement variants,
  excluding DELETED) sums to 79.7%, `LB ≈ 0.78` — again flips to "safe" by the cluster
  rule alone, but DELETED is 15.4% here, well past a 10% cap, so the deletion-share
  check correctly keeps it `AMBIGUOUS` despite the clustered consistency looking good.

**This is the main reason clustering is not part of the core algorithm I'd recommend
shipping now**: in both real test cases above, clustering alone would have produced a
verdict (`SAFE`) that a secondary, un-automatable check (deletion share) immediately
overturns. Clustering adds real recall but also real risk of papering over a double-digit
deletion rate, and the equivalence judgment itself needs a linguist, not code. Treat it
as a v2 enhancement with the deletion-share guard built in from day one, not a v1
feature.

---

## 3. Deletions and insertions

The working assumption in doc 10 — deletions should almost never be "safe" because
there's no candidate replacement to look up — holds up against the data, with the
nuance from section 1 that deletions were being **undercounted**, not overcounted, by
the original whole-block method.

I specifically went looking for a counterexample: a word whose *dominant* fuzzy-aligned
outcome is `DELETED`, across a sample deliberately biased toward the best candidates for
"purely grammatical particle that's safe to drop" (deictics, conjunctions, copulas):

| Dialect/Word | Role | N | Top-1 outcome | Top-1 % | Wilson LB95 |
|---|---|---|---|---|---|
| Rajasthani "अठे" | deictic "here" | 197 | DELETED | 29.9% | 0.240 |
| Garhwali "यु" | deictic "this" | 202 | DELETED | 26.2% | 0.207 |
| Chhattisgarhi "अउ" | conjunction "and" | 701 | DELETED | 30.4% | 0.271 |

**None of these come remotely close to the 0.70 bar even as a point estimate, let alone
the Wilson lower bound.** Every one of them has a second outcome (a specific
substitution, e.g. "अउ" → "और" at 28.5%, almost tied with its own deletion rate) that's
nearly as common as the deletion itself. This is a real, if small, empirical test of the
"principled exception for purely grammatical particles" question doc 10 raised, and the
answer in this corpus is **no** — I could not find a single word, including ones
deliberately chosen to be the best possible candidates for a grammatical-particle
exception, whose dominant fate is deletion with anything close to safe-level
consistency. Whatever a particle's "true" grammatical lightness is linguistically, in
practice Prisma does not drop it consistently enough to license an unattended
auto-delete rule.

**Recommendation**: `DELETED` is excluded from `SAFE_AUTOCORRECT`/`SAFE_CANDIDATE` by
default, full stop, with a `delete_allowlist` parameter in the classifier (section 2.3)
kept **empty** until/unless a specific word is manually reviewed by a linguist AND
clears a stricter bar than substitutions (I'd suggest requiring `LB ≥ 0.85` at
`N ≥ 200` for a deletion specifically, given the asymmetric cost of silently dropping
content vs. silently normalizing spelling). No word in this analysis qualifies today.
Insertions (Prisma hallucinating a word with no human-side counterpart) were not
separately re-scored here — they're structurally different (there's no "X" to key a
lookup table on; an insertion is Prisma adding words, not transforming one) and belong
to a different mechanism (hallucination filtering), not this classifier.

---

## 4. Full validation table

Validated the complete algorithm (fuzzy DP alignment → outcome counter → Wilson LB gate,
`MIN_N_FLOOR=50`, `SAFE_LB_SHADOW=0.70`, deletions excluded by default) against the 6
original example words plus 9 more pulled from real top-substitution/top-deletion lists
across 6 dialects (15 words total, chosen to include deictics, copulas, conjunctions,
classifiers, and numerals — a deliberately adversarial mix, not cherry-picked toward
"safe"):

| Dialect | Word | Role | N | Top-1 outcome | p1 | LB95 | Entropy (bits) | #distinct | **Verdict** |
|---|---|---|---|---|---|---|---|---|---|
| Rajasthani | री | dialectal verb-ending ("is doing") | 374 | → रही | 0.631 | 0.581 | 1.65 | 17 | **AMBIGUOUS** |
| Rajasthani | है | copula | 3054 | UNCHANGED | 0.709 | 0.692 | 1.63 | 92 | **AMBIGUOUS** (just under bar) |
| Rajasthani | अठे | deictic "here" | 197 | DELETED | 0.299 | 0.240 | 3.52 | 40 | **AMBIGUOUS** |
| Rajasthani | एक | numeral/article "one/a" | 1429 | UNCHANGED | 0.852 | 0.832 | 0.90 | 36 | **SAFE_AUTOCORRECT** (no-op) |
| Garhwali | यख | deictic "here" | 374 | UNCHANGED | 0.326 | 0.281 | 3.66 | 71 | **AMBIGUOUS** |
| Garhwali | भौत | dialectal "very" | 122 | → बहुत | 0.877 | 0.807 | 0.81 | 8 | **SAFE_CANDIDATE** (N<100) |
| Garhwali | यु | deictic "this" | 202 | DELETED | 0.262 | 0.207 | 3.92 | 48 | **AMBIGUOUS** |
| Bhojpuri | है | copula | 1695 | UNCHANGED | 0.812 | 0.792 | 1.25 | 46 | **SAFE_AUTOCORRECT** (no-op) |
| Bhojpuri | बा | existential copula marker | 4741 | UNCHANGED | 0.826 | 0.814 | 1.56 | 196 | **SAFE_AUTOCORRECT** (no-op) |
| Bhojpuri | एगो | classifier "a/one" | 1173 | UNCHANGED | 0.729 | 0.703 | 2.00 | 67 | **SAFE_CANDIDATE** (barely clears) |
| Maithili | छै | copula | 2900 | → छे | 0.657 | 0.639 | 2.06 | 113 | **AMBIGUOUS** (see clustering note, 2.4) |
| Maithili | के | genitive/dative particle | 2366 | UNCHANGED | 0.676 | 0.657 | 2.10 | 106 | **AMBIGUOUS** (just under bar) |
| Chhattisgarhi | हे | copula | 3591 | → है | 0.416 | 0.400 | 2.29 | 96 | **AMBIGUOUS** |
| Chhattisgarhi | अउ | conjunction "and" | 701 | DELETED | 0.304 | 0.271 | 3.15 | 46 | **AMBIGUOUS** |
| Marwari | है | copula | 3510 | UNCHANGED | 0.752 | 0.737 | 1.54 | 103 | **SAFE_AUTOCORRECT** (no-op) |

### Sanity-checking the verdicts

- **"SAFE" mostly means "leave it alone," not "rewrite it."** 5 of the 6 `SAFE_*`
  verdicts have `UNCHANGED` as the top outcome — i.e. the lookup-table action is "this
  word is already fine as transcribed, don't let Evon second-guess it," not "substitute
  Y for X." Only भौत→बहुत is a genuine substitution rule. This is a useful and correct
  distinction for the actual pipeline (a `NOOP` entry still has value: it tells the
  downstream stage "don't spend reasoning budget flagging this one," separate from an
  active `REPLACE` entry), and the classifier's output should carry this distinction
  through, not just a bare safe/ambiguous bit.
- **Copulas are the hardest category and the algorithm correctly refuses most of them.**
  है/हे/छै/के all land `AMBIGUOUS` or borderline — matching the intuition (these are
  short, high-frequency, grammatically loaded words where Prisma's behavior genuinely
  depends on surrounding tense/number context) except where the dialect's copula happens
  to usually survive untouched (Bhojpuri, Marwari), in which case it correctly flips to
  safe-as-noop. This variation *between* dialects for the "same" grammatical slot is
  itself an interesting, plausible finding, not a red flag — different dialects'
  phonetic distance from standard Hindi copula forms plausibly explains it.
  (Flagged as unconfirmed linguistics in the caveats below.)
- **Deictics (यख, अठे, यु) and the "and"-conjunction (अउ) all correctly land
  `AMBIGUOUS`** with no close calls — consistent with section 3's finding that
  grammatical-particle deletions never got close to the safety bar.
- **भौत's reversal (ambiguous in doc 10 → SAFE_CANDIDATE here) is the clearest
  demonstration that the artifact hypothesis mattered for at least one real,
  practically-useful pattern.** This is a genuinely different conclusion from the
  original write-up, not a restatement of it.
- **Two words (है-Rajasthani at 0.692, के-Maithili at 0.657, एगो-Bhojpuri at 0.703) sit
  within ~2 points of the 0.70 line.** This is exactly where a single hyperparameter
  choice (0.70 vs 0.68) changes a label, and is worth flagging explicitly rather than
  pretending the threshold is more precise than the underlying estimate — see caveats.

---

## 5. What I am NOT confident about

- **The 0.70 / 0.75 LB thresholds are principled (derived from what the gate needs to
  reject coin-flip-level evidence) but not empirically tuned against any downstream
  cost model.** I don't have a number for "how bad is a wrong silent correction
  vs. how bad is an unnecessary hint to Evon," and that tradeoff should set the exact
  threshold, not a round number. Treat 0.70/0.75 as a reasonable starting point to
  implement and monitor, not a validated optimum.
- **`gap_cost = 0.92` in the fuzzy aligner is validated for robustness (stable across
  0.80–1.05) but not validated for correctness against hand-labeled ground truth.** I
  spot-checked outcome labels by eye (the भौत and री top outcomes look linguistically
  right) but did not build a labeled eval set of "what should this word's outcome have
  been, per a human annotator" to measure the aligner's precision/recall directly. This
  is the single most important validation gap before trusting the algorithm's per-word
  outcomes at scale — I'd want at least ~50 hand-checked (clip, word, outcome) triples
  per dialect before shipping `SAFE_AUTOCORRECT` behavior into production, separate from
  the sample-size requirement on `N`.
- **Whether UNCHANGED-dominant words should even be called "safe" is a framing choice,
  not a data finding.** Calling है in Bhojpuri "safe" means "tell the downstream stage
  not to touch it, with high confidence" — that's a different and lower-risk kind of
  "safe" than an active substitution rule, and conflating the two tiers (as the current
  table partly does, for simplicity) could be read as more validated than it is. I'd
  recommend the production schema store `action: NOOP | REPLACE(word) | FLAG` explicitly
  rather than a single `is_safe` boolean, so this distinction survives into
  implementation.
- **Semantic clustering (2.4) is a worked mechanism, not a validated feature.** Both
  real examples I ran it against (छै, है-Rajasthani) show it can be overturned by the
  deletion-share guard, which is reassuring (the guard works), but I have zero
  linguist-reviewed cluster definitions — every example in this doc is illustrative, not
  shippable.
- **I only tested 15 (dialect, word) pairs out of a large, mostly-unexplored space**
  (19 dialects × many marker/high-frequency words each). The pattern held up
  consistently across this sample, but it's not a full corpus sweep. The algorithm in
  section 2 is cheap enough (`O(clips × avg_sentence_len²)` per word, offline) to run
  across every word in every dialect's `top_substitutions`/`top_deletions` list — that
  full sweep has not been done, only this validation sample.
- **I did not re-test insertions at all** (see section 3) — that's a real gap, not an
  oversight I'm dismissing; it just needs a different framing (there's no "X" to key a
  lookup table on for a hallucinated insertion) and wasn't in scope for "does X have a
  safe fate."

## 6. Verdict

**Ready to implement now:**
- The fuzzy DP word alignment as the outcome-extraction method (section 2.1), replacing
  whole-sentence `difflib` opcodes for this specific per-word-consistency sub-task (it
  can and should coexist with the existing `analyze_dialect()` aggregate fingerprinting,
  which is a different use case and doesn't need this change).
- The Wilson-lower-bound gate with the tiered `INSUFFICIENT_DATA` /
  `AMBIGUOUS` / `SAFE_CANDIDATE` / `SAFE_AUTOCORRECT` output (section 2.2–2.3), including
  logging `p1`, `LB`, `N`, entropy, and distinct-outcome-count per word so verdicts are
  auditable, not just a boolean.
- The deletion/insertion policy in section 3: `DELETED` excluded from any safe tier by
  default, with an empty allowlist today.
- Running this across the full set of `top_substitutions`/`top_deletions`/
  `top_insertions` candidates in `per_dialect_results.json` for all 19 dialects, to
  produce the actual candidate lookup table (this doc validated the *method*, not the
  full table).

**Needs more validation before it gates production silent-correction behavior:**
- A hand-labeled eval set (~50 triples/dialect) to measure the fuzzy aligner's outcome
  labels against human judgment, before trusting `SAFE_AUTOCORRECT` entries at face
  value.
- A real cost model (false-silent-correction cost vs. missed-hint cost) to pick final
  threshold values instead of the principled-but-round 0.70/0.75 used here.
- Linguist review before shipping any semantic-equivalence cluster (section 2.4) — don't
  let clustering silently expand the safe set without that review, and keep the
  deletion-share guard mandatory whenever clustering is used.
- A full 19-dialect sweep (not just the 15-word sample here) before concluding how much
  of the corpus is actually `SAFE_*` vs `AMBIGUOUS` in aggregate — this doc establishes
  that the split is real and gives a reproducible method, not the final size of either
  bucket.
