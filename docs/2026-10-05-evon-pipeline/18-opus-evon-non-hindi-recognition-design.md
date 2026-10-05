# 18: Evon non-Hindi recognition: surface the evidence, let Evon decide

Answers `17-evon-non-hindi-recognition-prompt.md`, including its later rule that spelling and phonetic variants are
not recognition evidence. A parallel answer to the same prompt is `18-evon-non-hindi-recognition-design.md`;
section 8 compares the two. Design only: no Evon or Prisma calls were made. Every number
below was measured in this session on the committed 25k-clip corpus, on the same group-disjoint split doc 09 uses.
The split reproduces exactly: the combined detector scores 0.4706 test accuracy here, doc 09 reports 0.470.

## 0. Short answer

- **(a) "This is not standard Hindi": yes, with one strict filter.** Surface only forms a Hindi reader can *see*
  are not Hindi, and only when at least two different ones appear in the conversation. On held-out data this rule
  never fired on near-Hindi speech (0 of 162 single turns, 0 of 51 three-turn windows, 0 of 29 five-turn windows
  from Khariboli, Haryanvi and Jaipuri). It fired on 21% of single regional turns, 48% of three-turn windows and
  63% of five-turn windows.
- **The marker lists cannot be surfaced as they are.** 116 of the 324 strongest markers (z ≥ 5) are ordinary Hindi
  words (लोग, के, रही, नजर, रंग). The raw top-5 per dialect "finds evidence" in 78% of near-Hindi turns and
  points at the wrong language family about a third of the time. The property that matters is "can a reader see
  it", not the z-score.
- **(b) Naming the variety: reliable at family level, exact only for a few.** When the gate fires, the forms point
  to the right family 85% of the time by simple majority (92% if weighed by corpus frequency). Exact variety is
  supported for Bhojpuri, Chhattisgarhi and Garhwali (forms point home 85 to 93% of the time). For Maithili,
  Magahi, Bajjika and Angika the visible forms are shared Bihari forms: family right 97 to 100%, exact variety
  mostly not. This reproduces doc 09's tiers without being told them.
- **Where Prisma erased the evidence, nothing in the transcript can recover it.** Marwari (6% of three-turn
  windows pass), Magahi (25%), Haryanvi and Jaipuri (0%). The design stays silent there and Evon treats the turn as
  Hindi, which is doc 09's Level 4 default. Handing over a label instead would not help: in the real Magahi example
  below, the detector's label is Bajjika.
- **The owner's constraint is right for (a) and mostly right for (b).** Its one real risk is how much Evon itself
  knows about regional grammar, which nobody has measured. Section 6 names the fallback and the test that decides
  whether it is needed.

## 1. How this was measured

- **Markers.** The audit's own `log_odds_discriminative_words()` on the doc 09 train split, without the top-15 cut:
  1,366 forms at z ≥ 3, 324 at z ≥ 5. The committed `audit_results.json` predates the last 10 Khortha rows, so its
  split differs and its top-15 lists overlap with these by 9.2 of 15 per dialect on average. The strong markers are
  stable across the two splits (बा, हई, छे, हे, दिखत). The weak tails are not: Magahi keeps 1 of its 15, Bundeli 0.
  That instability is part of the answer to "how many markers".
- **Reader-visibility labels.** I labelled each of the 324 z ≥ 5 forms as one of three kinds. **N**: a Hindi reader
  can see it is not standard Hindi (बा, एगो, हई, छै, दिखेण, लग्युं). **H**: ordinary Hindi or a common loanword
  (लोग, रही, नजर, व्हाइट). **A**: a real regional form that is also a Hindi word, a Hindi fragment or an English
  word (हो, मन, मा, आ, हे, गो, लागत, करेला). Result: 141 N, 116 H, 67 A. The H and A lists are in Appendix A.
  These labels are Claude's reading from general knowledge and **have not been reviewed by a native speaker.**
- **Test data.** The doc 09 test split (4,399 clips). A "conversation" is simulated as consecutive clips from one
  collection group (state|district|gender). That is a recording-group proxy, not a real speaker or call.
- **Near-Hindi control.** Khariboli, Haryanvi and Jaipuri test clips. **The repo has no standard-Hindi Prisma
  transcripts at all**, so the false-alarm rate on real Hindi speakers is unmeasured. Khariboli, the base of
  standard Hindi, is the closest proxy available.
- **"Points the right way"** means the majority home variety of the surfaced forms matches the clip's label. It is a
  corpus-statistics stand-in for what an ideal reader could infer. It is not a measurement of Evon.

## 2. Findings that decide the design

### 2.1 Raw marker lists cannot show "not Hindi"

Single turns, held-out:

| Evidence set (per variety) | Regional turns with ≥2 forms | Near-Hindi turns with ≥1 form | Near-Hindi with ≥2 | When ≥2 fire, majority points to wrong family |
|---|---|---|---|---|
| Raw top-5 by z (87 forms) | 48.9% | 78.4% | 51.2% | 30.3% |
| Raw top-15 (230) | 66.0% | 90.1% | 67.9% | 33.3% |
| Raw, all z ≥ 3 (1,366) | 94.4% | 99.4% | 95.7% | 31.5% |
| N + A (208) | 33.5% | 22.2% | 3.1% | 18.3% |
| N, top-5 per variety (45) | 12.1% | 0.6% | 0% | 15.2% |
| N, top-10 per variety (70) | 15.2% | 0.6% | 0% | 16.5% |
| **N, all (141)** | **21.3%** | **0.6%** | **0%** | **15.4%** |

Raw lists are dominated by Hindi words that some regions merely use more, often because the corpus is image
descriptions (रंग, दीवार, आसमान). They "find" regional evidence in nearly every near-Hindi turn, so they cannot
support claim (a) at all. Inside the N set, a short strong list and the full list behave almost the same
(precision moves 1 to 2 points) while the full list adds coverage. **Decision: keep every reviewed N form, drop
every H form, never let an A form count.** Strength rank stops mattering once visibility is enforced.

### 2.2 Homographs break the silence on near-Hindi speech

Adding the 67 A forms raises near-Hindi turns with any hit from 0.6% to 22.2%, and to 55% over three turns.
Sentence position rescues only the copula-like homographs: हो is utterance-final 33% of the time in Khortha against
6% in near-Hindi speech; हय is final 32% of the time and never occurs in near-Hindi speech. मन, मा, आ, गो, जग, इ and ई are under 10% final everywhere, so
position tells nothing. A slot rule would add a parser for a small gain, so A forms are simply never surfaced.

### 2.3 Two different forms, pooled over the conversation

| Pooled turns | Regional windows that pass | Near-Hindi windows that pass |
|---|---|---|
| 1 | 21.3% | 0 of 162 |
| 3 | 48.2% | 0 of 51 |
| 5 | 62.6% | 0 of 29 |

Per variety, three-turn windows. "Points home" is the share of passing windows whose majority form belongs to the
same doc 09 profile:

| Variety | Pass | Points home (profile) | Points to right family | Doc 09 class |
|---|---|---|---|---|
| Bajjika | 89% | 37% | 98% | B |
| Angika | 85% | 23% | 100% | D |
| Bhojpuri | 75% | 92% | | A |
| Maithili | 66% | 34% | 100% | C |
| Chhattisgarhi | 65% | 85% | | A |
| Surgujia | 63% | 82% | | D |
| Garhwali | 60% | 93% | | A |
| Awadhi (n=10) | 50% | 20% | | D (see 2.8) |
| Rajasthani | 45% | 64% | 62% | B |
| Sadri | 43% | 58% | | D |
| Kumaoni | 32% | 0% (all to Garhwali) | 96% | C (see 2.7) |
| Khortha | 32% | 31% | 12% | B |
| Magahi | 25% | 8% | 97% | D |
| Bundeli (n=14) | 21% | 0% | | C |
| Surjapuri (n=12) | 17% | 50% | | D |
| Marwari | 6% | 4 of 6 | | D |
| Khariboli | 0% | | | C |
| Haryanvi | 0% | | | E |
| Jaipuri | 0% | | | E |

The gate lines up with doc 09 without being given its tiers. The A-class varieties are the ones whose visible
forms point home. The Bihari C and D varieties get family-level evidence. The near-Hindi C and E varieties get
nothing. Doc 09's detector agrees from the other side: 78% of Level 1 windows pass the gate (of 104), 60% of
Level 2 (of 806), 21% of Level 3 (of 515), and 0 of 17 at Level 4.

### 2.4 Shared and ambiguous forms (brief point 3)

**Shared forms.** 68 of the 141 N forms are used, at 25% or more of their home rate, by a variety outside the
home's doc 09 profile. The big groups:

- Bhojpuri's -ल past forms (रहल, लागल, बैठल, रखल, बनल) and एगो run across the whole Bihari belt. This is why
  Maithili, Magahi, Bajjika and Angika evidence "points to Bhojpuri" while staying 97 to 100% family-correct.
- छे and छै are shared by Maithili, Angika, Surjapuri and Rajasthani. In Rajasthani windows that pass the gate,
  the majority form points to Maithili 26 times out of 73.
- Almost every Garhwali form (यख, दिखेण, लग्युं, छन) is shared with Kumaoni, which may be a labelling artifact
  (2.7).

The prompt marks these "also heard from speakers of other regions", without naming the regions. That gives Evon a
reason to stop at family level without handing it a verdict.

**Meaning-ambiguous forms.** In `needs_fixing_wrong_substitutions.csv` (5,948 pairs, 7,327 meaning-changing
instances), only 340 instances have an admissible form as Prisma's output, and nearly all come from another
regional form (अउ → आऊ 19, आउ → अऊ 10, घनी → गणी 7). A Hindi word turning into an admissible form happens a
handful of times (और → एगो 2, है → हवे 2, से → छो 2). The words earlier reports flagged as genuinely ambiguous are
all handled by the labels: इ, ई, हे and खातिर are A, so never surfaced. वो (the एगो confusion in doc 16 §2.5) and
रही (doc 06's flattened progressive) are H. लौकत stays in, because every source of it is the same Bhojpuri verb
(लोकत, लउकत).

**Universal substitutions.** Of the patterns in `cross_dialect_universal_substitutions.json`, only छै and छे
are admissible forms at all, and both already carry the shared note. They still count toward "not Hindi" (no
standard Hindi sentence uses them) but, as doc 17 asks, they do not argue for any one variety. Every other
universal pattern (है/हैं, मे/में, यहाँ/यहां, बहोत/बहुत, के/का) involves an H form and is never surfaced.

### 2.5 The fingerprint proper: forms Prisma invents

For 24 of the 141 forms, the speaker rarely said the form Prisma wrote (the same word appears in the human
transcript under 25% of the time, with 20+ occurrences). Examples across all clips:

| Prisma wrote | Speaker said the same | What speakers actually said |
|---|---|---|
| दिखीरु | 0% (n=94) | दिखेरो, दिखे रियो |
| देरो | 9% (n=35) | दे रो, दे रहियो |
| लौकत | 17% (n=151) | लोकत, लउकत |
| अटे | 21% (n=81) | अठे |
| गैल | 2% (n=138) | गइल |
| दोगो | 2% (n=83) | दुगो |

This is where doc 06's fingerprint survives as text: the form is still visibly non-Hindi, but it is Prisma's
spelling, not the speaker's. An earlier draft of this design added "the recognizer writes this when speakers say X"
for these forms. Checked against doc 14's IGNORE rule (at most one character apart once spaces and nukta are
removed), most of those sources are spelling variants of the very same word: गैल from गइल, दोगो from दुगो, लौकत
from लोकत, अटे from अठे. Under doc 17's rule they carry no recognition evidence, so the note is dropped. The only
substantive sources left are the Rajasthani progressive family (दिखीरु and रु from दिखेरो or दिखे रियो, आरो from
आ रियो, देरो from दे रहियो), about six forms. That is too few to justify a mechanism in v1. The forms themselves
stay in the lexicon, because दिखीरु is visibly non-Hindi whatever its source.

What the fingerprint cannot do: doc 06's strongest patterns end in a Hindi word or in nothing. यख is deleted or
becomes एक, रियो becomes रही. Doc 16 §2.3 measured that a Hindi-looking word cannot be flagged as mistranscribed
from the word alone (precision 15% at best). So hints like "this रही may have been रियो" are not surfaced.

### 2.6 Tested and left out

- **Absence of Hindi copulas** (from the ideation pass). Over three turns, near-Hindi speech almost always contains
  है, हैं or था (no copula in 0 to 4% of windows), while Garhwali (73%), Khortha (62%), Surjapuri (62%) and
  Bhojpuri (48%) often have none. Letting "one visible form plus no Hindi copula in 15+ words" also pass the gate
  lifts three-turn coverage from 48.2% to 52.8%, still with 0% near-Hindi. Left out of v1 because image
  descriptions ("यह एक ... है") are unusually copula-heavy, so this is the rule most likely to break on real calls.
  Revisit with conversational data.
- **Colour and noun forms.** The image task inflates forms like पीलो, करिया, हरियर, पाणी. Removing 18 such forms
  drops three-turn coverage only from 48.2% to 45.4%. Coverage rests on function forms (copulas, classifiers,
  tense and aspect endings, deictics), which should transfer to calls far better than the colour words.

### 2.7 Kumaoni evidence looks Garhwali because Kumaoni was recorded in Garhwal

All 1,141 Kumaoni clips come from Tehri Garhwal (595) and Uttarkashi (546). Those are Garhwal districts, and the
same two that hold all the Garhwali clips. Kumaoni windows that pass the gate point to Garhwali 23 times out of 24.
Either these speakers really use Garhwali forms or the label is loose. Doc 09's finding that Kumaoni's best
partner is Khariboli, not Garhwali, should be re-read with this in mind. For this design it means Garhwali forms
carry a "shared" flag that may come only from mislabelled rows. That makes Evon more cautious than necessary,
which is the safe direction.

### 2.8 The dataset label is sometimes wrong, and visible evidence catches it

13 of 187 "Awadhi" clips (11 from Budaun) are plainly Marathi (आहे, दिसत, इथे, बाजूला). The detector, trained
on those labels, still ranks Awadhi first for the held-out ones (0.25 to 0.32). The visible forms say Marathi. A label-based design passes the
dataset's mistake straight to Evon; an evidence-based one exposes it. Separately, 130 of the 187 Awadhi clips were
recorded in Balrampur, Chhattisgarh, which may explain part of doc 09's Awadhi to Chhattisgarhi tie.

## 3. The design

### 3.1 Offline: one small lexicon file

Built once from the train split, reviewed by a native speaker, versioned:

```
for each form with z >= 5 for some variety (train split, the audit's log-odds):
    keep only if the reviewer marks it N (visibly not standard Hindi)      # drops H and A
    shared  = a variety outside the home's doc-09 profile uses it at >= 25% of the home rate
    home    = variety with the highest z        # kept for auditing only, never sent to Evon
```

Today that gives 141 forms, 68 of them shared. No variety name leaves this file.

### 3.2 Runtime: evidence from the turns Evon already sees

```
def build_evidence(user_turns):          # the user turns Evon receives: history (up to 6) + this turn
    found = {}                            # form -> turns seen in, last turn index, first fragment
    for n, text in enumerate(user_turns):
        words = text.split()
        for i, w in enumerate(words):
            if w in LEXICON:
                f = found.setdefault(w, {"turns": set(), "fragment": words[i-2 : i+3]})
                f["turns"].add(n); f["last"] = n
    if len(found) < 2:
        return None                       # abstain: the template stays exactly as today
    order = sorted(found, key=(shared last, most recent first))[:6]
    return one line per form: the form and its fragment, plus only these notes when true:
        "in K of the user's turns"
        "also heard from speakers of other regions"
```

The six-line cap rarely binds (2% of three-turn windows have eight or more distinct forms). No scores, no
z-values, no variety names, no detector output.

### 3.3 What Evon receives

Still a single user turn with no system prompt (the `EvonReply` docstring explains why). When `build_evidence`
returns nothing, the prompt is byte-for-byte today's. When it returns a block:

```
{history}User said:

{user_text}

About the user's words: the speech recognizer can only write standard Hindi, so it spells regional
speech as if it were Hindi. Even so, it wrote these forms, which are not standard Hindi:
{evidence}
Use your own knowledge of Hindi and its regional varieties to decide how this person speaks. If these
forms are not enough to tell, say so.

Reply in one short, natural sentence suitable for being spoken aloud on a phone call. Do not explain
your reasoning, do not give alternatives. Return exactly:

SPEECH: <standard Hindi | regional, cannot tell which | the region or variety you recognise>
WORDS: <the user's words that decided it, or none>
REPLY: <your one-sentence reply>
```

The existing parser keeps working. It takes the first line after `REPLY:` in the text after the last `</think>`,
so the SPEECH and WORDS lines above it never reach the spoken reply; they are read separately for logging. The
three SPEECH choices are doc 09's levels in plain words.

### 3.4 Confidence and abstention: doc 09's four levels, used twice

1. **Before Evon: abstention.** No block unless two different reviewed forms appear. On this data, every Level 4
   window and every near-Hindi window stays on today's prompt.
2. **After Evon: what Boli accepts.** Evon's answer is checked against its own quotes and against the detector run
   on the whole window (doc 16 F8), and the less specific reading wins:

```
def accepted_level(speech, words, window_text, detector):    # detector = doc 09 Stage 7 on the window
    if any(w not in window_text for w in words):   return 4, "quoted words are not in the transcript"
    if speech in (None, "standard Hindi"):          return 4
    if speech == "regional, cannot tell which":     return 3
    named = alias(speech)                           # "Bhojpuri"/"भोजपुरी" -> Bhojpuri, "Bihar" -> Bihari family
    if named == detector.top1 and detector.level == 1:            return 1, named
    if same_group(named, detector.top1):                          return 2, group(named)
        # same doc-09 profile; or the same family when Evon named only a region
    return 3, "Evon and detector disagree"                         # logged for review
```

In v1 the accepted level is only logged in `turn.dev`. It does not change the reply language: doc 09 separates the
detection map from the response map, and that decision needs its own evidence.

### 3.5 Deliberately not sent to Evon

- Variety names, per form or per speaker. That is the rejected label, including in disguise ("बा: Bhojpuri").
- H forms (invisible to a reader, 2.1) and A forms (they break near-Hindi silence, 2.2).
- "This Hindi word may have been X" hints (doc 16 §2.3, 15% precision at best).
- Detector confidence (doc 07 §7 and doc 09 Stage 2: calibration is poor and isotonic scaling barely moved it).
- Spelling-variant notes such as "Prisma writes गैल for गइल" (doc 17's rule, doc 14's IGNORE class; see 2.5).

### 3.6 Where it plugs in

`ConversationEngine.reply()` already builds `context` from `conv.history`. Build the evidence from those same user
turns plus `turn.recognized_text`, pass it to `EvonReply.reply_with_usage` as one optional argument, and store the
block, the SPEECH and WORDS lines and the accepted level in `turn.dev`. The detector needs the export step doc 16
F7 describes (scikit-learn is not a dependency today). The lexicon is one JSON file. The Claude path is untouched;
its system prompt already says "reply in Bhojpuri" unconditionally (doc 16 F6), which is a separate problem.

## 4. Walkthrough on real transcripts

All windows are from the doc 09 test split. **P** is what Prisma wrote, which is all Evon sees. **H** is the human
reference with annotation tags removed, never available at runtime. Detector is doc 09 Stage 7 run on the whole
window. Evidence blocks are the literal output of the 3.2 rule, built from train-split data only.

### 4.1 Clear case: Bhojpuri (Bihar, East Champaran, male)

Detector: Level 1 (Bhojpuri 0.77, Maithili 0.15).

```
P1  एगो मारुती खड़ा बा कुछ गाड़ी बाटे तो साइड में खड़ा बा मारुती सजुकी के जो बोर्ड भी लागल बा
H1  एगो मारुती खड़ा बा अ कुछ गाड़ी बाटे तोन साइड मे खड़ा बा मारुती सुज़की के ए जनवा बोर्ड भी लागल बा।
P2  मारुती सुज़ुकी के शोरूम बा या बहुत गाड़ी बाहर लागल बा बहुत गाड़ी अंदर से कसाई करके निकल रहा बा
H2  ई मारुती सुज़की के शो-रूम बा। यहाँ बहुत गाड़ी बाहर लागल बा अ बहुत गाड़ी अन्दर से कसाई करके निकल रहल बा।
P3  सर कुर्सी पे बैठ के पढ़ा रहल बाणे कुछ लैका खड़ा बाणा सोगनी के बैठावे का प्रयास कर लेता है
H3  सर कुर्सी पे बैठ के पढ़ा रहल बाड़े कुछ लईका खड़ा बाड़ां सं ओकनी के बैठावे के प्रयास कईल जातरा
```

Evidence block:

```
- बा: "…मारुती खड़ा बा कुछ गाड़ी…" (in 2 of the user's turns)
- बाटे: "…कुछ गाड़ी बाटे तो साइड…"
- रहल: "…के पढ़ा रहल बाणे कुछ…" (also heard from speakers of other regions)
- लागल: "…बोर्ड भी लागल बा…" (in 2 of the user's turns; also heard from speakers of other regions)
- एगो: "…एगो मारुती खड़ा…" (also heard from speakers of other regions)
```

Even in a clear case the fingerprint is visible: P2 flattened रहल to रहा, and P3 rewrote "प्रयास कईल जातरा" as
the Hindi "प्रयास कर लेता है". The block puts the two unshared copula forms first. Hoped-for answer:
`SPEECH: Bhojpuri`, `WORDS: बा, बाटे`. Accepted at Level 1 (Evon and the detector agree on the variety, detector at
Level 1). If Evon only says "Bihar", the result is Level 2 and nothing breaks.

### 4.2 Marginal case: Maithili (Bihar, Saharsa, female)

Detector: Level 2 (Maithili 0.72, Angika 0.13). Maithili is not an A-class variety, so the detector itself stops at
the Bihari-central profile.

```
P1  मिट्टी नजर आए ब्रहल छे और बगल में बहुत सारा कचरा जना फैला नजर आएल छे गाड़ी पर
H1  मिट्टी नजर आब रहल छै और बगल मे बहुत सारा कचड़ा जना फैलल नजर आब रहल छै गाड़ी पर
P2  कार पर उजला रंग के कुछ लगे रहोल छे नीचा में इत्ता सब नजर आय रहल छे
H2  कार पर ऊजरा रंग के किछ लगा रहल छै नीचा में ईटा सब नजर आव रहल छै।
P3  इ फोटो में हमरा महात्मा बुद्ध के मूर्ति नजर आय रहल छे जैकर जे एकटा हाथ उठेला छे एकटा हाथ नीचा छे
H3  ई फोटो मे हमरा महात्मा बुद्ध के मूर्ति नजर आव रहल छै जकर जे एकटा हाथ उठेएले छै एकटा हाथ नीचा छै।
```

Evidence block:

```
- छे: "…आए ब्रहल छे और बगल…" (in 3 of the user's turns; also heard from speakers of other regions)
- रहल: "…नजर आय रहल छे…" (in 2 of the user's turns; also heard from speakers of other regions)
```

Both forms are shared, and छे also reads as the Rajasthani or Gujarati copula, so the shared note matters. The raw
transcript gives Evon more than the block: हमरा, एकटा and जैकर are visible Maithili forms that fall under the
z ≥ 5 cut. Hoped-for answer: "Maithili", or "Bihar, cannot tell which". Both are accepted at Level 2. The answer to
watch for in testing is "Rajasthani" or "Gujarati" from छे alone; the audit turns that into Level 3 because it
disagrees with the detector's profile, and logs it.

### 4.3 Weak detector confidence: Haryanvi and Magahi

**Haryanvi (Haryana, Rohtak, female).** Detector: Level 4 (Haryanvi 0.46, Marwari 0.17). Doc 09 maps Haryanvi to
Level 4 at any confidence.

```
P1  और इसमें बहुत सारे हरे हरे रंग की बेल भी है जो कि पहाड़ियों के ऊपर से जा रही है आदि झरने में भी बह रही है और पानी में
H1  और इसम्ह बहुत सारे हरे हरे रंग की बेल भी हजो कि पहाड़ियों के ऊपर से जा रही ही हं आंधी झरने म भी बह रही हं और पानी म
P2  भूरे रंग का मार्बल का फर्श भी है दोहरे रंग की इसमें खड़ी कुर्सी गाल रखी है
H2  धोले रंग का मार्बल का फर्श भी हं धोले रंग की इसम्ह घणी ए कुर्सी घाल राखी हं।
P3  रेलिंग लगा रखी है दो तीन इसमें गोल सर्कल
H3  ऊपर त इसकह लोह की चोगरदे न रेलिंग लगा राखी ह दो तीन इसम्ह गोल सर्कल
```

Evidence block: none. Prisma turned every Haryanvi form into Hindi (इसम्ह → इसमें, राखी → रखी, हं → है) and
mangled some into different meanings (धोले "white" → भूरे "brown", घणी → खड़ी). Today's prompt goes out unchanged
and Evon treats the turn as Hindi. That is the correct outcome: nothing left in the text is non-Hindi, and a Hindi
reply is what doc 09 prescribes at Level 4. "Not Hindi" is not a claim this transcript can support.

**Magahi (Bihar, Gaya, female).** Detector: Level 3 (Bajjika 0.39, Maithili 0.31).

```
P1  इधर उधर कपड़ा पहन गए थे सब एक रंग के देखने में काफी सुन्दर लगे फूल से भी सजावट है नारंगी रंग से
H1  कुछ हथीन उजर उजर कपडा पहिनले हथीन सब एके रंग के देखे में काफी सुन्दर लगित हई फूल से भी सजावल हई नारंगी रंग से
P2  ये फील्ड है
H2  यहाँ बड़ी गो के फिल्ड हई
P3  ये जो मॉल है मॉल है सरफ साबुन तेल कोलगेट
H3  ये जो मॉल है। ये मॉल है ओकरा में सर्फ साबुन तेल कोलगेट
```

Evidence block: none. The speaker said हई, हथीन, लगित, सजावल; Prisma wrote है, थे, लगे, सजावट. A label here
would have been "Bajjika", the wrong variety. This is the hard ceiling of any transcript-only method, and silence
beats a wrong label.

### 4.4 Evidence outranks a weak detector: Marwari (Rajasthan, Nagaur, male)

Detector: Level 3 (Marwari 0.38, Rajasthani 0.31).

```
P1  आसमान नीलो है और पीछे बहुत सारा घर भी है
H1  आसमान निलो है और पीछे बहुत सारा घर भी है।
P2  अटे एक छोरो खड़े हुए है भी हाथ में और पीला कलर की चुन्नी है और ब्लैक कलर की ड्रेस पहन रखी है पीछे गेट है
H2  अठे एक छोराे खड़यो है बीके हाथ में बिंटिया पहरेड़ी है और पीला कलर की चुन्नी है और ब्लैक कलर की ड्रेस पहर रखी है बीके पीछे गेट है।
P3  नीला कलर थोड़ा कलर का भी लाग रहे हो मंजिला लाग रखी अनुपम से लग रही
H3  एक नीला कलर का बोर्ड टांग रखा हे ओर धोला कलर का लाल कलर का मंजिला टांग रखा हे। यह काफी अनुपम द्रशय
```

Evidence block:

```
- अटे: "…अटे एक छोरो…"
- नीलो: "…आसमान नीलो है और…" (also heard from speakers of other regions)
```

अटे is Prisma's one-letter respelling of अठे ("here"), the deictic doc 06 found deleted or mangled; नीलो has the
Rajasthani -ओ adjective ending, and the raw text also shows छोरो. A reader who knows Rajasthani should place अटे
without help; whether Evon does is exactly what section 6 has to measure. Hoped-for answer: "Rajasthani" or
"Marwari". Either matches the detector's top profile, so it is accepted at Level 2 (Rajasthani-Marwari) although
the detector alone only reached Level 3.

### 4.5 The label is wrong: an "Awadhi" clip that is Marathi (Uttar Pradesh, Budaun, female)

Single turn. Detector: Level 3 (Awadhi 0.32, Garhwali 0.21).

```
P   या दृश्यमे आपलाला असे बगैरमिते की इथे एका सपाट जागेवरती एक ट्रेक्टर दिसत आहे तो ट्रेक्टर निड्या व पांढरा रंगाचा आहे
H   ह्या दृष्यामध्ये आपल्याला असे बघायला मिळते कि इथे एका सपाट जागेवरती एक ट्रॅक्टर दिसत आहे तो ट्रॅक्टर निळ्या व पांढऱ्या रंगाचा आहे.
```

Evidence block:

```
- दिसत: "…एक ट्रेक्टर दिसत आहे तो…"
- आहे: "…ट्रेक्टर दिसत आहे तो ट्रेक्टर…"
```

Expected answer: Marathi. The raw text is Marathi throughout (इथे, आपलाला, जागेवरती, रंगाचा). Accepted at Level 3
with a logged disagreement, and the disagreement is the useful signal: the detector and the dataset label are the
ones that are wrong. Telling Evon "the speaker uses Awadhi" would have been telling it something false.

### 4.6 A cautious answer: Garhwali (Uttarakhand, Uttarkashi, female)

Detector: Level 2 (Garhwali 0.56, Kumaoni 0.28).

```
P1  यख वायर भी दिखेण लग्यां एक टावर खड़ू होयूं बहुत सारा डोखरा त खाग
P2  वर यख छुट्टू छी एक पौधा दिखाण लग्युं एच तार दिखाणा लग्यां
P3  पुराने जमाने में बनाई जा
H3  पत्थरों की दीवार च उन थे पुराण जमाणु मा बणाई जांद।
```

Evidence block:

```
- यख: "…यख वायर भी…" (in 2 of the user's turns; also heard from speakers of other regions)
- लग्यां: "…भी दिखेण लग्यां एक टावर…" (in 2 of the user's turns; also heard from speakers of other regions)
- लग्युं: "…पौधा दिखाण लग्युं एच तार…" (also heard from speakers of other regions)
- दिखेण: "…वायर भी दिखेण लग्यां एक…" (also heard from speakers of other regions)
```

Every form carries the shared note because of the Kumaoni rows recorded in Garhwal (2.7). Hoped-for answer:
"Garhwali" or "Uttarakhand Pahari", accepted at Level 2 either way (Level 1 needs the detector at 0.70). This is
the cost of the Kumaoni labelling problem: a clear Garhwali speaker gets a cautious reading. P3 also shows the
other failure: a fully Garhwali sentence came out as a Hindi fragment with nothing to surface.

## 5. Is the owner's constraint right?

**For (a), yes, and the label alternative is worse, not just less elegant.** The detector's signal leans on Hindi
words a reader cannot check (2.1). Its exact label is right 47% of the time. In two of the seven windows above
(Magahi, Marathi) the label it would hand Evon is wrong, and in a third (Garhwali) the label data itself is
suspect.

**For (b), mostly yes, with one risk that is specific to Evon and unmeasured.** Evidence only helps if Evon knows
that बाटे is Bhojpuri or that लग्युं is Garhwali. A 30B Indic model probably knows the large varieties (Bhojpuri,
Maithili, Rajasthani, Marathi) and may not know Garhwali, Khortha or Surgujia morphology. If testing shows that, the
next step should still be evidence rather than a verdict: add per-form geography from the corpus ("recorded mostly
in Uttarakhand"), which is what "some regional exposure" gives a human reader. That sits closer to a label, so it
should be added only for the varieties where the forms-only version fails.

**Where the constraint has no answer is erased evidence (4.3).** No transcript-only design can recover it. The
choices are silence (recommended) or a label that, on this data, is often wrong.

## 6. What has to be measured before this ships

No Evon calls were made for this document. The decision needs one offline run:

- **Arms.** A: today's template plus the SPEECH and WORDS lines (can Evon tell from the raw transcript alone?).
  B: the block from 3.3. C: B plus per-form geography. D: the rejected label, as a control only.
- **Data.** Held-out windows from the doc 09 test split, stratified by variety, plus a standard-Hindi control that
  does not exist yet (Vaani's metadata has a `language` field, so Hindi rows may be pullable; unverified). Also some
  real conversational turns, because every number here comes from image descriptions (doc 16 F10).
- **Scores.** Rate of "not Hindi" on near-Hindi and Hindi input (must stay near zero), accepted-level accuracy per
  variety against doc 09's tiers, rate of WORDS that are not in the transcript, reply length (the reason the template
  has no system prompt), and whether the block shifts the reply language (it should not, yet).
- **Reviews before trusting any of it.** A native-speaker pass over the 324 N/H/A labels, and a check of the
  Kumaoni and Awadhi labels (2.7, 2.8).

## 7. The same thing in plain English

The speech recognizer only knows Hindi. When someone speaks Bhojpuri or Garhwali, it writes their words down as if
they were Hindi, a bit like autocorrect "fixing" a word it doesn't know. Most of the regional flavour gets lost on
the way. But some words survive, because the recognizer has no Hindi word to swap in. The Bhojpuri "बा" ("is")
usually comes through as बा. Those survivors are clues.

We have 25,000 recordings where we know both what people really said and what the recognizer wrote, so we could
work out which clues survive for each region. The obvious plan was to give Evon a list of clue words for the region
we think the person is from, or simply tell it the region. We checked both against the real recordings and both go
wrong. Many "clue words" are ordinary Hindi words that some regions just use more often, like "people" or
"colour". Count those as clues and you find "regional speech" in almost every plain Hindi sentence. And the region
guess is wrong about half the time.

So the system does something smaller. It looks only for words that anyone who knows Hindi can see are not Hindi,
and it only speaks up when it finds two different ones in the conversation. It then shows Evon those words, inside
the bit of sentence where they appeared, and lets Evon work out the region itself, the way someone who has
travelled a little hears "बा" and thinks "that's Bhojpuri". When a word is used in more than one region, it says so.
It never tells Evon the answer.

Why we expect it to work: on recordings of near-Hindi speech, the two-word rule never went off, not once. On
regional speech it went off for about half of three-turn conversations, and when it did, the words pointed to the
right part of the country about nine times in ten. For some languages (Bhojpuri, Chhattisgarhi, Garhwali) they point
to the exact language. For the Bihar languages they only point to the area, and the system is built to say so.

What it can't do: when the recognizer has already turned every regional word into Hindi, there is nothing left to
show. The system then stays quiet and Evon treats the person as a Hindi speaker, which is the safe choice. Telling
Evon a guessed region wouldn't help there either. In one of our examples the guess was the wrong language, and in
another the recordings themselves were mislabelled (Marathi filed as Awadhi). The clue words caught that; the label
didn't.

What's still unknown: whether Evon knows enough about these regional languages to read the clues. That needs the
one test run in section 6 before any of this goes live.

## 8. Relation to the other doc 18

`18-evon-non-hindi-recognition-design.md` answers the same prompt and agrees on the core: raw forms in context, no
dialect names or scores in the prompt, an empty-evidence path, doc 09's four levels as the ceiling, and an offline
test with a label arm as control only. The measurable differences:

- **Inventory.** It proposes z ≥ 8 and 25+ occurrences, then hand-removal of common words. On this split that rule
  starts from 113 forms, 46 of them ordinary Hindi (के, लोग, रही, नजर, रंग, दीवार); before the hand-removal it
  passes 49% of near-Hindi single turns and 84% of near-Hindi three-turn windows. Once the Hindi and homograph forms
  are removed, both inventories are silent on near-Hindi speech, but the z ≥ 8 cut covers less: 13.5% of regional
  single turns and 33.3% of three-turn windows, against 21.3% and 48.2% here. The stronger cut buys no precision.
- **Gate.** It allows a single marker type at Level 3; here a single form never passes. One visible form already shows up in near-Hindi
  speech (0.6% of single turns, 3.4% of five-turn windows) while two never did, and pooling over turns recovers
  most of the coverage (2.3).
- **Output.** It asks Evon for a confidence word as well; this design skips that because doc 09 found the detector
  itself poorly calibrated, and an uncalibrated self-report adds a field nobody can use yet.
- **Validation.** Its walkthrough rows (Bhojpuri row 28, Khariboli row 7, Jaipuri row 1) point the same way as
  4.1 and 4.3 here; row 28 (बा, एगो) also passes this design's two-form gate.

## Appendix A: labels used (Claude's reading, needs native-speaker review)

**H, ordinary Hindi or loanword, never surfaced (116):** अच्छा अच्छे अति आओ आप आपको आसपास आसमान उधर उनकी एंड कई
करता करना करो कलर काका कितना कूड़ा के को खड़ा खड़ी खड़े खूब खूबसूरत चलता चीजें छठ छोटू छोटे जमीन जहाँ जाता जाते
जाली जिनका जी डाला ढेर तक तस्वीर तीर तुम थे दिख दिखता दिखते दिखने दिखाई दिखी दिखे दीवार दे देख देखता देखने
देखिए देखे देता नजर नज़र नीचा पड़ी पड़े पहना पोता बड़े बने भारी भीतर मस्त मिट्टी मिलते मिलो में यह यहां या येलो
रंग रखीं रही रहे रहो रेड लगता लगते लगीं लगे लागू लिए लिख लिया लो लोग वाला वास्ते व्हाइट शॉप सकते सके सड़क सफ़ेद
सब सबके सुन्दर से हम हमने हाँ हुआ हुई हुए हैं होता

**A, regional form that is also Hindi, a fragment or English, never surfaced (67):** अगाड़ी आ इ ई ईटा औ करन करेला
कु कुल खातिर गो छ छा छी जग जन जला जाके जू जोन टा ठा तल्ला ते तें नीलू पहनले पिछाड़ी बटे बर बाई बाना बानी बेस
भले मन मने मा माँ माइन माजी मायने य यक यू ल लग लाग लागत लागे लागो लेले सन सो ह हटे हय हरे हा हाई हाय हे हो
होके होल होला

**N:** every other z ≥ 5 form (141). Of these, 18 colour and noun forms (पियर उजर हरियर करिया पथरा हरो कालो पीलो भूरो
नीलो पाणी उज्जर गाछी हरयां हरयूं लाइटा इटा एटा) were used only for the 2.6 robustness check.

## Appendix B: reproducing the numbers

The analysis ran from a scratch directory and is not committed. It imports the repo's own `load_rows`,
`make_split`, `log_odds_discriminative_words` (`regional_fingerprint_audit.py`), `fit_and_eval`
(`v1_detector.py`) and `tokenize` (`analyze_prisma_fingerprint.py`), so the split, marker formula, detector and
alignment are the committed ones. Steps: (1) log-odds on the train split with no top-n cut; (2) the N/H/A labels in
Appendix A; (3) on the test split, non-overlapping windows of 1, 3 and 5 consecutive clips per collection group,
counting distinct N forms; (4) the doc 09 detector, isotonic-calibrated on validation, mapped to levels with Stage
7's 0.70 / 0.45 / 0.20 cut points and Stage 8's class assignments; (5) word alignment with `SequenceMatcher` for the
"speaker said the same" rates in 2.5 (all clips).
