"""Owner-only accuracy review of the saved trial conversations. This does not train any model.

  python deploy/review.py export NEW_FOLDER   -> NEW_FOLDER/review.csv plus one .wav per spoken turn
  python deploy/review.py score FILLED.csv    -> plain numbers from the columns the speaker filled in
"""
import csv
import sys
from collections import Counter
from pathlib import Path

from boli_zero.config import ROOT, load_dotenv
from boli_zero.hosted import connect
from boli_zero.routing import label_clip

HEAD = ['when (UTC)', 'conversation', 'audio file', 'what Prisma heard', 'what Claude replied', 'app said it did not understand',
        'reply looks like (automatic guess)']
FILL = ['what I actually said', 'heard it right? (yes/partly/no)', 'reply made sense? (yes/partly/no)',
        'reply language (bhojpuri/mixed/hindi)', 'notes']


def export(folder):
    load_dotenv()
    load_dotenv(ROOT / '.env.hosted')
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    with connect() as db, (folder / 'review.csv').open('w', newline='', encoding='utf-8-sig') as out:  # BOM so Excel and Sheets read Devanagari
        sheet = csv.writer(out)
        sheet.writerow(HEAD + FILL)
        rows = db.execute('SELECT id,created,conversation_id,audio,recognized_text,error_code,reply_text,understood FROM boli_reviews ORDER BY created').fetchall()
        for n, (rid, created, cid, audio, heard, code, reply, understood) in enumerate(rows, 1):
            name = f'{n:03d}.wav'
            (folder / name).write_bytes(bytes(audio or b''))
            guess = label_clip(raw_output=reply, submitted_language_code='hi-IN').identification['summary'] if reply else ''
            sheet.writerow([created.strftime('%Y-%m-%d %H:%M:%S'), cid[:6], name, heard or f'(nothing heard: {code})', reply or '',
                            '' if understood is None else ('no' if understood else 'yes'), guess] + [''] * len(FILL))
    print(f'{len(rows)} turns exported. Fill the last five columns, then run the score step. Keep the folder private.')


def edits(a, b):
    """Word-level edit distance (insert, delete, replace)."""
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (x != y))
    return row[-1]


def score(path):
    rows = [r for r in csv.DictReader(path.open(encoding='utf-8-sig')) if any(r[c].strip() for c in FILL)]
    print(f'{len(rows)} reviewed turns')
    for column in FILL[1:4]:
        print(column, dict(Counter(r[column].strip().lower() or 'blank' for r in rows)))
    pairs = [(r['what I actually said'].split(), r['what Prisma heard'].split()) for r in rows if r['what I actually said'].strip()]
    if pairs:
        print(f'word error rate of the transcript: {sum(edits(a, b) for a, b in pairs) / sum(len(a) for a, b in pairs):.0%} over {len(pairs)} turns (0% = perfect)')


if __name__ == '__main__':
    export(Path(sys.argv[2]).resolve()) if sys.argv[1:2] == ['export'] else score(Path(sys.argv[2]))
