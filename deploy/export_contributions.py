"""Owner-only export of consented recordings; this does not train any model."""
import json
import os
import sys
from pathlib import Path

from boli_zero.config import ROOT, load_dotenv
from boli_zero.hosted import connect

load_dotenv()
load_dotenv(ROOT / ".env.hosted")
folder = Path(sys.argv[1]).resolve()
folder.mkdir(parents=True, exist_ok=False, mode=0o700)
with connect() as db, (folder / 'manifest.jsonl').open('w') as manifest:
    os.chmod(folder / 'manifest.jsonl', 0o600)
    for cid, created, audio, metadata in db.execute('SELECT id,created,audio,metadata FROM boli_contributions WHERE created > now() - interval \'30 days\' ORDER BY created'):
        filename = cid + '.wav'
        path = folder / filename
        path.write_bytes(bytes(audio))
        path.chmod(0o600)
        manifest.write(json.dumps({'contribution_id': cid, 'created': created.isoformat(), 'audio_file': filename, **metadata}, ensure_ascii=False) + '\n')
print('Private export created. No training was performed. Protect exported copies and honor subsequent withdrawals before using them.')
