# Phase 4: marker library for 19 regional varieties + ordinary Hindi

Cleaning: shared `clean()`; no spelling/sound-variant work was done (see VARIANT FLAG note). Markers come from Prisma text, validated on group-disjoint held-out data and against the other 19 groups, then filtered for picture-topic words using Hindi clips on the same prompt images.

## Ratings

| group | clips | stable | after topic filter | marker recall (strict split) | SVM ceiling (strict) | rating | confidence |
|---|---|---|---|---|---|---|---|
| Angika | 557 | 2 | 2 | 0.00 | 0.07 | **not separable from text** | ok |
| Awadhi | 187 | 1 | 1 | 0.03 | 0.09 | **not separable from text** | LOW |
| Bajjika | 861 | 0 | 0 | 0.00 | 0.50 | **not separable from text** | ok |
| Bhojpuri | 4847 | 42 | 42 | 0.60 | 0.67 | **clear markers** | ok |
| Bundeli | 447 | 6 | 6 | 0.01 | 0.14 | **not separable from text** | ok |
| Chhattisgarhi | 3687 | 41 | 41 | 0.49 | 0.60 | **clear markers** | ok |
| Garhwali | 1893 | 47 | 47 | 0.53 | 0.63 | **clear markers** | ok |
| Haryanvi | 164 | 1 | 1 | 0.28 | 0.21 | **not separable from text** | LOW |
| Jaipuri | 86 | 28 | 24 | 0.06 | 0.00 | **not separable from text** | LOW |
| Khariboli | 717 | 32 | 15 | 0.15 | 0.13 | **not separable from text** | ok |
| Khortha | 809 | 2 | 2 | 0.27 | 0.33 | **not separable from text** | ok |
| Kumaoni | 1141 | 33 | 24 | 0.20 | 0.15 | **shared with neighbours** | ok |
| Magahi | 930 | 1 | 1 | 0.06 | 0.10 | **not separable from text** | ok |
| Maithili | 3348 | 37 | 31 | 0.21 | 0.52 | **not separable from text** | ok |
| Marwari | 1450 | 40 | 38 | n/a | 0.00 | **not separable from text** | ok |
| Rajasthani | 2440 | 48 | 48 | 0.03 | 0.35 | **not separable from text** | ok |
| Sadri | 678 | 0 | 0 | 0.03 | 0.22 | **not separable from text** | ok |
| Surgujia | 526 | 19 | 17 | n/a | 0.00 | **not separable from text** | LOW |
| Surjapuri | 194 | 14 | 14 | 0.58 | 0.32 | **clear markers** | LOW |
| Hindi | 3997 | 33 | 33 | 0.16 | 0.45 | **not separable from text** | ok |

Clusters of varieties the text cannot reliably tell apart (SVM confusion >= 15%): {Angika, Magahi, Maithili, Surjapuri}; {Awadhi, Bhojpuri, Chhattisgarhi, Sadri, Surgujia}; {Bundeli, Garhwali, Jaipuri, Khariboli, Kumaoni, Hindi}; {Haryanvi, Marwari, Rajasthani}

## Confusion (marker model, pooled over 5 seeds, rows=true, share of that group's test clips)

| true | top confusions (>=5%) | no marker fired |
|---|---|---|
| Angika | Surjapuri 24%, Maithili 14%, Kumaoni 13%, Bhojpuri 10% | 3% |
| Awadhi | Bhojpuri 25%, Chhattisgarhi 18%, Jaipuri 13%, Maithili 8% | 8% |
| Bajjika | Bhojpuri 33%, Kumaoni 10%, Maithili 10%, Surjapuri 7% | 7% |
| Bhojpuri | Kumaoni 6% | 2% |
| Bundeli | Jaipuri 23%, Kumaoni 17%, Khariboli 13%, Marwari 11% | 2% |
| Chhattisgarhi | Jaipuri 7%, Bhojpuri 6%, Kumaoni 5% | 5% |
| Garhwali | Kumaoni 11% | 5% |
| Haryanvi | Marwari 21%, Kumaoni 14%, Rajasthani 12%, Jaipuri 10% | 2% |
| Jaipuri | Kumaoni 15%, Marwari 10%, Rajasthani 8%, Surjapuri 8% | 2% |
| Khariboli | Kumaoni 25%, Jaipuri 19%, Marwari 7%, Hindi 7% | 3% |
| Khortha | Bhojpuri 21%, Maithili 14%, Garhwali 6%, Surjapuri 5% | 14% |
| Kumaoni | Garhwali 35%, Jaipuri 10%, Khariboli 7% | 0% |
| Magahi | Kumaoni 16%, Bhojpuri 16%, Maithili 15%, Jaipuri 12% | 7% |
| Maithili | Surjapuri 17%, Bhojpuri 13%, Kumaoni 7%, Jaipuri 6% | 3% |
| Marwari | Kumaoni 14%, Rajasthani 12%, Garhwali 7%, Jaipuri 6% | 4% |
| Rajasthani | Marwari 23%, Kumaoni 9%, Garhwali 6%, Jaipuri 5% | 6% |
| Sadri | Chhattisgarhi 25%, Bhojpuri 19%, Jaipuri 7%, Surgujia 7% | 7% |
| Surgujia | Chhattisgarhi 33%, Bhojpuri 11% | 7% |
| Surjapuri | Maithili 8%, Jaipuri 6%, Kumaoni 5% | 3% |
| Hindi | Kumaoni 24%, Jaipuri 20%, Khariboli 11%, Rajasthani 8% | 2% |

## Marker sets (top 15 per group after the topic filter; kind: w=word, e2/e3=ending, b/t=2-/3-word pair)

### Angika - not separable from text (2 markers; topic-flagged 0)
- `w:छै` df=25 lift=6x stable=7/10 topic=ok ~Maithili/Rajasthani
- `b:के फोटो` df=9 lift=6x stable=6/10 topic=ok ~Bajjika/Bhojpuri/Chhattisgarhi/Khortha

### Awadhi - not separable from text (1 markers; topic-flagged 0)
- `e2:ती` df=10 lift=4x stable=6/10 topic=ok ~Angika/Bundeli/Khariboli/Magahi/Maithili/Sadri/Surgujia

### Bajjika - not separable from text (0 markers; topic-flagged 0)

### Bhojpuri - clear markers (42 markers; topic-flagged 0)
- `w:बाटे` df=347 lift=94x stable=10/10 topic=ok
- `w:बा` df=1239 lift=44x stable=10/10 topic=ok
- `e3:ाटे` df=364 lift=41x stable=10/10 topic=ok
- `w:जाला` df=49 lift=31x stable=10/10 topic=ok
- `w:लौकता` df=55 lift=25x stable=10/10 topic=ok
- `w:देता` df=44 lift=19x stable=10/10 topic=ok
- `w:लागता` df=77 lift=14x stable=10/10 topic=ok ~Awadhi
- `w:ह` df=177 lift=12x stable=10/10 topic=ok ~Chhattisgarhi
- `w:गैल` df=52 lift=13x stable=10/10 topic=ok ~Khariboli
- `w:जौन` df=25 lift=14x stable=10/10 topic=ok
- `e3:वता` df=41 lift=13x stable=10/10 topic=ok
- `w:एमे` df=68 lift=8x stable=10/10 topic=ok ~Bajjika/Surgujia
- `e3:गता` df=138 lift=7x stable=10/10 topic=ok ~Awadhi/Maithili
- `e2:टे` df=396 lift=6x stable=10/10 topic=ok ~Bundeli/Jaipuri
- `e3:ावल` df=136 lift=7x stable=10/10 topic=ok ~Bajjika/Magahi

### Bundeli - not separable from text (6 markers; topic-flagged 0)
- `b:जहा मे` df=8 lift=22x stable=9/10 topic=ok ~Khariboli
- `e2:खो` df=12 lift=4x stable=9/10 topic=ok ~Angika/Haryanvi/Magahi/Marwari/Rajasthani/Surjapuri
- `e2:छी` df=9 lift=5x stable=7/10 topic=ok ~Angika/Garhwali/Khariboli/Kumaoni/Maithili/Hindi
- `w:पीले` df=10 lift=8x stable=6/10 topic=ok ~Jaipuri/Khariboli
- `e2:गी` df=14 lift=5x stable=6/10 topic=ok ~Angika/Garhwali/Jaipuri/Khariboli/Kumaoni/Surjapuri
- `w:लगी` df=30 lift=3x stable=6/10 topic=ok ~Garhwali/Jaipuri/Khariboli/Kumaoni/Hindi

### Chhattisgarhi - clear markers (41 markers; topic-flagged 0)
- `w:हावे` df=35 lift=32x stable=10/10 topic=ok
- `b:दिखत हे` df=261 lift=18x stable=10/10 topic=ok ~Surgujia
- `w:हमन` df=28 lift=18x stable=10/10 topic=ok
- `w:अउ` df=36 lift=17x stable=10/10 topic=ok ~Surgujia
- `w:अऊ` df=89 lift=15x stable=10/10 topic=ok ~Sadri/Surgujia
- `w:हवे` df=264 lift=11x stable=10/10 topic=ok ~Surgujia
- `w:ठन` df=38 lift=12x stable=10/10 topic=ok ~Sadri
- `w:औ` df=35 lift=11x stable=10/10 topic=ok ~Surgujia
- `w:हे` df=501 lift=9x stable=10/10 topic=ok ~Awadhi/Sadri/Surgujia
- `w:जन` df=50 lift=10x stable=10/10 topic=ok ~Garhwali/Kumaoni/Sadri
- `w:दिखत` df=417 lift=9x stable=10/10 topic=ok ~Awadhi/Sadri/Surgujia
- `e3:िखत` df=417 lift=9x stable=10/10 topic=ok ~Awadhi/Sadri/Surgujia
- `e2:खत` df=448 lift=8x stable=10/10 topic=ok ~Awadhi/Sadri/Surgujia
- `w:आऊ` df=29 lift=8x stable=10/10 topic=ok ~Khortha/Surgujia
- `w:मन` df=306 lift=6x stable=10/10 topic=ok ~Sadri/Surgujia

### Garhwali - clear markers (47 markers; topic-flagged 0)
- `e2:ेण` df=130 lift=35x stable=10/10 topic=ok ~Kumaoni
- `e3:खेण` df=130 lift=35x stable=10/10 topic=ok ~Kumaoni
- `w:दिखेण` df=129 lift=35x stable=10/10 topic=ok ~Kumaoni
- `e3:गणा` df=18 lift=32x stable=10/10 topic=ok
- `w:लग्यु` df=119 lift=23x stable=10/10 topic=ok ~Kumaoni
- `w:यु` df=39 lift=25x stable=10/10 topic=ok ~Kumaoni
- `w:दिखेणा` df=56 lift=23x stable=10/10 topic=ok ~Kumaoni
- `e3:ेणा` df=59 lift=23x stable=10/10 topic=ok ~Kumaoni
- `w:लग्या` df=114 lift=21x stable=10/10 topic=ok ~Kumaoni
- `e2:यु` df=175 lift=19x stable=10/10 topic=ok ~Kumaoni
- `e3:्यु` df=138 lift=19x stable=10/10 topic=ok ~Kumaoni
- `w:यख` df=79 lift=20x stable=10/10 topic=ok ~Kumaoni
- `w:लगण` df=30 lift=21x stable=10/10 topic=ok ~Kumaoni
- `w:बिटिन` df=33 lift=18x stable=10/10 topic=ok ~Kumaoni
- `w:जू` df=29 lift=18x stable=10/10 topic=ok ~Kumaoni

### Haryanvi - not separable from text (1 markers; topic-flagged 0)
- `b:रखी है` df=11 lift=14x stable=6/10 topic=ok ~Marwari

### Jaipuri - not separable from text (24 markers; topic-flagged 4)
- `w:बगल` df=18 lift=12x stable=10/10 topic=ok
- `b:हुए है` df=17 lift=9x stable=10/10 topic=ok ~Khariboli/Kumaoni/Hindi
- `b:हुई है` df=15 lift=7x stable=10/10 topic=ok ~Bundeli/Khariboli/Kumaoni/Hindi
- `w:हुए` df=17 lift=6x stable=10/10 topic=ok ~Bundeli/Khariboli/Kumaoni/Hindi
- `w:हुई` df=16 lift=6x stable=10/10 topic=ok ~Bundeli/Khariboli/Kumaoni/Hindi
- `b:है और` df=23 lift=5x stable=10/10 topic=ok ~Bundeli/Khariboli/Kumaoni/Marwari/Hindi
- `w:बादल` df=12 lift=31x stable=9/10 topic=untested
- `e3:ादल` df=12 lift=30x stable=9/10 topic=untested
- `e2:दल` df=12 lift=26x stable=9/10 topic=untested
- `w:अगल` df=12 lift=26x stable=9/10 topic=ok
- `w:हरे` df=11 lift=20x stable=9/10 topic=ok
- `b:है जिस` df=12 lift=88x stable=7/10 topic=ok
- `w:जिस` df=12 lift=73x stable=7/10 topic=ok
- `e3:सके` df=9 lift=8x stable=7/10 topic=ok ~Khariboli/Kumaoni/Hindi
- `w:खडे` df=9 lift=7x stable=7/10 topic=ok ~Bundeli/Khariboli/Marwari
  - removed as picture-topic: e3:फेद, w:सफेद, e2:ेद, w:हुआ

### Khariboli - not separable from text (15 markers; topic-flagged 17)
- `t:है यहा पर` df=29 lift=8x stable=10/10 topic=ok ~Bundeli/Kumaoni/Hindi
- `w:हमे` df=28 lift=5x stable=10/10 topic=ok ~Bundeli/Hindi
- `t:लग रही है` df=15 lift=11x stable=9/10 topic=ok
- `b:भी रखी` df=10 lift=12x stable=9/10 topic=ok ~Bundeli/Kumaoni
- `b:लग रही` df=15 lift=9x stable=9/10 topic=ok ~Bundeli
- `b:है यहा` df=57 lift=5x stable=9/10 topic=ok ~Angika/Bundeli/Kumaoni/Magahi/Maithili/Hindi
- `b:है ये` df=20 lift=4x stable=9/10 topic=ok ~Bundeli/Haryanvi/Kumaoni/Marwari/Hindi
- `b:हमे एक` df=15 lift=11x stable=8/10 topic=ok ~Jaipuri
- `t:रहा है और` df=17 lift=4x stable=8/10 topic=ok ~Bundeli/Jaipuri/Kumaoni/Magahi/Marwari/Hindi
- `b:बडे पेड` df=9 lift=12x stable=7/10 topic=ok ~Chhattisgarhi/Hindi
- `e3:लती` df=9 lift=11x stable=7/10 topic=ok ~Magahi
- `t:लगी हुई है` df=28 lift=5x stable=7/10 topic=ok ~Bundeli/Haryanvi/Jaipuri/Kumaoni/Hindi
- `b:ये एक` df=23 lift=5x stable=7/10 topic=ok ~Jaipuri/Kumaoni/Magahi
- `b:भी लगी` df=13 lift=7x stable=6/10 topic=ok ~Bundeli/Haryanvi/Kumaoni
- `t:देख सकते है` df=10 lift=6x stable=6/10 topic=ok ~Kumaoni/Maithili/Hindi
  - removed as picture-topic: b:यह एक, b:काफी सारे, b:यहा पर, w:काफी, e3:ाफी, w:जहा, b:लगी हुई, b:सकते है

### Khortha - not separable from text (2 markers; topic-flagged 0)
- `b:ही को` df=8 lift=33x stable=7/10 topic=ok
- `w:एगो` df=84 lift=4x stable=7/10 topic=ok ~Angika/Bajjika/Bhojpuri/Magahi/Maithili

### Kumaoni - shared with neighbours (24 markers; topic-flagged 9)
- `b:मा जी` df=54 lift=24x stable=10/10 topic=ok ~Garhwali
- `w:दिखेणी` df=24 lift=18x stable=9/10 topic=ok ~Garhwali
- `e3:ेणी` df=24 lift=17x stable=9/10 topic=ok ~Garhwali
- `w:पिछाडी` df=26 lift=15x stable=9/10 topic=ok ~Garhwali
- `w:कु` df=39 lift=10x stable=9/10 topic=ok ~Garhwali
- `t:यख मा जी` df=29 lift=22x stable=8/10 topic=ok ~Garhwali
- `b:यख मा` df=29 lift=21x stable=8/10 topic=ok ~Garhwali
- `e3:ेणु` df=27 lift=14x stable=8/10 topic=ok ~Garhwali
- `w:दिखेणु` df=26 lift=14x stable=8/10 topic=ok ~Garhwali
- `b:कलर की` df=73 lift=6x stable=8/10 topic=ok ~Jaipuri/Khariboli/Marwari/Hindi
- `w:छन` df=79 lift=15x stable=7/10 topic=ok ~Garhwali
- `w:यखमा` df=25 lift=17x stable=7/10 topic=ok ~Garhwali
- `w:अगाडी` df=10 lift=18x stable=7/10 topic=ok ~Garhwali
- `b:कई सारा` df=18 lift=14x stable=7/10 topic=ok ~Garhwali
- `w:बडु` df=19 lift=14x stable=7/10 topic=ok ~Garhwali
  - removed as picture-topic: t:दे रहा है, t:दे रहे है, t:दिखाई दे रहा, b:दे रहा, b:ब्लैक कलर, t:दिखाई दे रहे, w:हुए, w:व्हाइट

### Magahi - not separable from text (1 markers; topic-flagged 0)
- `b:ऊपर मे` df=10 lift=4x stable=6/10 topic=ok ~Angika/Awadhi/Bajjika/Chhattisgarhi/Maithili/Hindi

### Maithili - not separable from text (31 markers; topic-flagged 6)
- `b:देखने मे` df=97 lift=9x stable=10/10 topic=ok ~Magahi
- `w:देखने` df=113 lift=7x stable=10/10 topic=ok ~Magahi/Hindi
- `e3:खने` df=130 lift=7x stable=10/10 topic=ok ~Awadhi/Magahi/Hindi
- `b:बहुत बढिया` df=80 lift=5x stable=10/10 topic=ok ~Angika/Bhojpuri/Haryanvi/Khortha/Surjapuri
- `w:छी` df=36 lift=5x stable=10/10 topic=ok ~Bajjika/Garhwali/Kumaoni/Surjapuri
- `b:रहल छे` df=35 lift=23x stable=9/10 topic=ok
- `e3:रहल` df=22 lift=10x stable=9/10 topic=ok ~Bhojpuri
- `w:रहल` df=58 lift=8x stable=9/10 topic=ok ~Bajjika/Bhojpuri/Magahi
- `t:मे बहुत अच्छा` df=25 lift=9x stable=9/10 topic=ok ~Magahi
- `w:छै` df=200 lift=7x stable=9/10 topic=ok ~Angika/Jaipuri/Rajasthani/Surjapuri
- `b:जै छे` df=14 lift=9x stable=9/10 topic=ok ~Angika
- `w:सब` df=393 lift=4x stable=9/10 topic=ok ~Angika/Awadhi/Bajjika/Bhojpuri/Khortha/Magahi
- `t:बढिया लग रहा` df=22 lift=12x stable=8/10 topic=ok
- `b:बढिया लग` df=23 lift=10x stable=8/10 topic=ok
- `w:देखिये` df=25 lift=7x stable=8/10 topic=ok ~Bajjika/Kumaoni
  - removed as picture-topic: t:देख पा रहे, b:मे बहुत, t:पा रहे है, b:पा रहे, e3:्छे, w:अच्छे

### Marwari - not separable from text (38 markers; topic-flagged 2)
- `w:लाइटा` df=19 lift=25x stable=10/10 topic=ok ~Rajasthani
- `e3:यने` df=14 lift=25x stable=10/10 topic=ok
- `w:मायने` df=14 lift=25x stable=10/10 topic=ok
- `w:माइन` df=22 lift=22x stable=10/10 topic=ok ~Rajasthani
- `e3:इटा` df=19 lift=20x stable=10/10 topic=ok ~Rajasthani
- `e3:ेडा` df=33 lift=15x stable=10/10 topic=ok ~Rajasthani
- `w:अटे` df=18 lift=15x stable=10/10 topic=ok ~Rajasthani
- `b:है भी` df=10 lift=17x stable=10/10 topic=ok
- `b:पडी है` df=42 lift=9x stable=10/10 topic=ok ~Haryanvi/Jaipuri/Rajasthani
- `w:पडी` df=45 lift=7x stable=10/10 topic=ok ~Haryanvi/Jaipuri/Khariboli/Rajasthani
- `b:है दो` df=34 lift=7x stable=10/10 topic=ok ~Khariboli/Rajasthani
- `t:दिख रही है` df=101 lift=6x stable=10/10 topic=ok ~Bundeli/Haryanvi/Jaipuri/Rajasthani/Hindi
- `t:की फोटो है` df=19 lift=8x stable=10/10 topic=ok ~Haryanvi/Khariboli/Kumaoni/Rajasthani
- `b:दिख रही` df=108 lift=6x stable=10/10 topic=ok ~Bundeli/Haryanvi/Jaipuri/Rajasthani/Hindi
- `b:खडी है` df=48 lift=6x stable=10/10 topic=ok ~Bundeli/Haryanvi/Khariboli/Rajasthani
  - removed as picture-topic: b:रही है, w:दिख

### Rajasthani - not separable from text (48 markers; topic-flagged 0)
- `t:आ रही छे` df=117 lift=153x stable=10/10 topic=ok
- `t:दे रही छे` df=85 lift=116x stable=10/10 topic=ok
- `b:रही छे` df=160 lift=108x stable=10/10 topic=ok
- `t:को रग सफेद` df=65 lift=89x stable=10/10 topic=ok
- `b:को रग` df=161 lift=67x stable=10/10 topic=ok
- `b:रग हरो` df=48 lift=66x stable=10/10 topic=ok
- `w:दिखीरी` df=48 lift=66x stable=10/10 topic=ok
- `w:दिखीरु` df=47 lift=64x stable=10/10 topic=ok
- `b:रग सफेद` df=116 lift=58x stable=10/10 topic=ok
- `t:पेड को रग` df=45 lift=61x stable=10/10 topic=ok
- `t:आ रहे छे` df=44 lift=60x stable=10/10 topic=ok
- `w:री` df=65 lift=55x stable=10/10 topic=ok
- `e3:ीरु` df=47 lift=57x stable=10/10 topic=ok
- `w:भूरो` df=43 lift=57x stable=10/10 topic=ok
- `b:सफेद नजर` df=41 lift=56x stable=10/10 topic=ok

### Sadri - not separable from text (0 markers; topic-flagged 0)

### Surgujia - not separable from text (17 markers; topic-flagged 2)
- `w:हवे` df=48 lift=16x stable=10/10 topic=ok ~Chhattisgarhi
- `w:जग` df=11 lift=19x stable=10/10 topic=ok
- `w:ठे` df=13 lift=16x stable=10/10 topic=ok
- `w:मन` df=56 lift=9x stable=10/10 topic=ok ~Chhattisgarhi/Sadri
- `e2:खत` df=56 lift=7x stable=10/10 topic=ok ~Awadhi/Chhattisgarhi/Sadri
- `w:दिखत` df=51 lift=7x stable=10/10 topic=ok ~Awadhi/Chhattisgarhi/Sadri
- `e3:िखत` df=51 lift=7x stable=10/10 topic=ok ~Awadhi/Chhattisgarhi/Sadri
- `w:हर` df=20 lift=4x stable=10/10 topic=ok ~Angika/Chhattisgarhi/Haryanvi/Jaipuri/Sadri/Surjapuri
- `w:लगत` df=8 lift=6x stable=9/10 topic=ok ~Awadhi/Bhojpuri/Chhattisgarhi
- `e3:हाय` df=11 lift=44x stable=8/10 topic=ok
- `e2:ाय` df=12 lift=21x stable=8/10 topic=ok
- `w:ए` df=16 lift=4x stable=8/10 topic=ok ~Bajjika/Bhojpuri/Chhattisgarhi/Jaipuri/Maithili/Sadri
- `w:आहाय` df=8 lift=40x stable=6/10 topic=ok
- `b:एक ठे` df=12 lift=27x stable=6/10 topic=ok
- `e2:थे` df=8 lift=7x stable=6/10 topic=ok ~Chhattisgarhi/Sadri
  - removed as picture-topic: w:ज्यादा, e3:ादा

### Surjapuri - clear markers (14 markers; topic-flagged 0)
- `w:छे` df=86 lift=10x stable=10/10 topic=ok ~Angika/Maithili
- `w:ला` df=10 lift=15x stable=10/10 topic=ok ~Surgujia
- `e2:ाल` df=17 lift=5x stable=10/10 topic=ok ~Bajjika/Bundeli/Jaipuri
- `w:अच्छा` df=18 lift=4x stable=10/10 topic=ok ~Angika/Bajjika/Bhojpuri/Chhattisgarhi/Khariboli/Magahi/Maithili
- `e3:्छा` df=18 lift=4x stable=10/10 topic=ok ~Angika/Bajjika/Bhojpuri/Chhattisgarhi/Khariboli/Magahi/Maithili
- `e2:छा` df=18 lift=4x stable=10/10 topic=ok ~Angika/Awadhi/Bajjika/Bhojpuri/Chhattisgarhi/Khariboli/Khortha/Magahi/Maithili
- `e3:गाल` df=8 lift=51x stable=9/10 topic=ok
- `e2:गे` df=9 lift=5x stable=9/10 topic=ok ~Bundeli/Khortha/Maithili
- `e3:तला` df=9 lift=44x stable=8/10 topic=ok
- `w:लागे` df=8 lift=9x stable=8/10 topic=ok ~Khortha/Maithili
- `e3:ागे` df=8 lift=8x stable=8/10 topic=ok ~Khortha/Maithili
- `e3:डकी` df=9 lift=4x stable=7/10 topic=ok ~Angika/Bajjika/Bundeli/Haryanvi/Kumaoni/Magahi
- `w:लगाल` df=9 lift=41x stable=6/10 topic=ok
- `e3:तना` df=10 lift=6x stable=6/10 topic=ok ~Awadhi/Bajjika/Bhojpuri/Maithili

### Hindi - not separable from text (33 markers; topic-flagged 0)
- `w:मुझे` df=75 lift=14x stable=10/10 topic=ok
- `e3:ुझे` df=75 lift=12x stable=10/10 topic=ok
- `e2:झे` df=75 lift=11x stable=10/10 topic=ok
- `b:तस्वीर मे` df=56 lift=10x stable=10/10 topic=ok ~Kumaoni/Marwari
- `t:आ रहा है` df=72 lift=8x stable=10/10 topic=ok ~Khariboli/Marwari
- `b:देख पा` df=30 lift=9x stable=10/10 topic=ok ~Bhojpuri/Maithili
- `w:इस` df=217 lift=6x stable=10/10 topic=ok ~Khariboli
- `t:नजर आ रहा` df=68 lift=7x stable=10/10 topic=ok ~Khariboli/Kumaoni/Marwari/Rajasthani
- `b:आ रहा` df=74 lift=6x stable=10/10 topic=ok ~Khariboli/Kumaoni/Marwari/Rajasthani
- `e3:वीर` df=88 lift=5x stable=10/10 topic=ok ~Bhojpuri/Garhwali/Kumaoni/Marwari
- `w:तस्वीर` df=88 lift=5x stable=10/10 topic=ok ~Bhojpuri/Garhwali/Kumaoni/Marwari
- `w:पिक्चर` df=31 lift=6x stable=10/10 topic=ok ~Awadhi/Marwari
- `b:गया है` df=82 lift=5x stable=10/10 topic=ok ~Angika/Khariboli/Kumaoni/Magahi/Maithili
- `t:आ रहे है` df=53 lift=5x stable=10/10 topic=ok ~Angika/Bundeli/Khariboli/Kumaoni/Marwari
- `b:बहुत सारे` df=188 lift=4x stable=10/10 topic=ok ~Angika/Bundeli/Haryanvi/Khariboli/Kumaoni/Magahi/Maithili

## Hindi-vs-regional score, leave-one-variety-out

| held-out variety | in-distribution recall | UNSEEN recall | SVM unseen (ceiling) | no-evidence share | Hindi FPR |
|---|---|---|---|---|---|
| Angika | 0.71 | 0.71 | 0.84 | 0.15 | 0.367 |
| Awadhi | 0.56 | 0.50 | 0.95 | 0.40 | 0.289 |
| Bajjika | 0.39 | 0.54 | 0.95 | 0.29 | 0.324 |
| Bhojpuri | 0.69 | 0.40 | 0.86 | 0.40 | 0.361 |
| Bundeli | 0.43 | 0.46 | 0.69 | 0.27 | 0.367 |
| Chhattisgarhi | 0.63 | 0.59 | 0.86 | 0.31 | 0.350 |
| Garhwali | 0.60 | 0.61 | 0.96 | 0.30 | 0.373 |
| Haryanvi | 0.55 | 0.35 | 0.79 | 0.45 | 0.267 |
| Jaipuri | 0.71 | 0.59 | 0.45 | 0.03 | 0.453 |
| Khariboli | 0.43 | 0.51 | 0.44 | 0.22 | 0.384 |
| Khortha | 0.33 | 0.16 | 0.96 | 0.62 | 0.277 |
| Kumaoni | 0.64 | 0.60 | 0.51 | 0.10 | 0.380 |
| Magahi | 0.42 | 0.31 | 0.70 | 0.41 | 0.313 |
| Maithili | 0.60 | 0.58 | 0.84 | 0.25 | 0.324 |
| Marwari | 0.51 | 0.25 | 0.78 | 0.52 | 0.260 |
| Rajasthani | 0.51 | 0.39 | 0.83 | 0.38 | 0.328 |
| Sadri | 0.44 | 0.40 | 0.88 | 0.45 | 0.263 |
| Surgujia | 0.56 | 0.60 | 0.95 | 0.32 | 0.331 |
| Surjapuri | 0.74 | 0.71 | 0.98 | 0.25 | 0.320 |

Mean over varieties: in-distribution 0.55, unseen 0.49, SVM unseen 0.80, Hindi FPR 0.333. Configs: [[False, 0], [False, 1], [False, 2], [True, 0], [True, 1], [True, 2]]. K and the threshold maximise balanced accuracy; no Hindi-FPR cap was applied.

## Evon grounding check

**NOT RUN.** `BOLI_EVON_URL` is not set in this environment and no Modal endpoint is reachable, so there is no downstream Evon to compare 'markers' against 'extra transcript context'. No result is claimed.
