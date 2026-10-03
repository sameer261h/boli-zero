"""Run locally once after DATABASE_URL is added privately to .env.
Seeds prior spend rather than silently resetting the already-used trial cap.
"""
import base64
import json
import sys
from pathlib import Path

from boli_zero.config import ROOT, load_dotenv
from boli_zero.hosted import connect

load_dotenv()
load_dotenv(ROOT / ".env.hosted")
with connect() as db:
    db.execute((ROOT / 'deploy' / 'schema.sql').read_text())
    state = db.execute('SELECT payload FROM boli_runtime WHERE id=1 FOR UPDATE').fetchone()[0]
    if not state['files']:
        for name, source in [('gnani.jsonl', '.cache/spend_ledger.jsonl'), ('claude.jsonl', '.cache/claude_usage.jsonl')]:
            path = Path(sys.argv[1]) if name == 'gnani.jsonl' and len(sys.argv) > 1 else ROOT / source
            if path.exists():
                state['files'][name] = base64.b64encode(path.read_bytes()).decode()
        db.execute('UPDATE boli_runtime SET payload=%s::jsonb WHERE id=1', (json.dumps(state),))
print('Private tables, hourly retention and existing spend history configured.')
