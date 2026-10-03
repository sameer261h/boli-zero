"""Private single-tester Vercel app with PostgreSQL-backed state.

Serializes requests deliberately: this is a small trial, not a multi-user service.
No downloaded dataset or developer routes are published.
"""
import base64
import hashlib
import hmac
import json
import functools
import os
import re
import secrets
import tempfile
import time
import uuid

import httpx
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from . import conversation_routes
from .clients import PrismaClient, TimbreClient
from .config import GnaniConfig, ROOT
from .contributions import register as register_contributions, verify_retry
from .conversation import AnthropicReply, Conversation, ConversationEngine, Turn, MAX_CONTEXT_TURNS, MAX_TEXT_CHARS, MAX_TURNS, SILENCE_PEAK, wav_peak
from .ledger import ClaudeUsage, Ledger, estimate_cost_inr
from .service import RecognitionError, RecognitionService, inspect_upload


def connect():
    import psycopg
    return psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10, sslmode='require', prepare_threshold=None)


def pack(engine, root):
    conversations = {}
    for cid, c in engine._conversations.items():
        if c.created < time.time() - 3600 or c.ended:
            continue
        conversations[cid] = {'id': cid, 'created': c.created, 'turns': {k: asdict(t) for k, t in c.turns.items()}, 'history': c.history}
    audio_ids = {t['audio_id'] for c in conversations.values() for t in c['turns'].values() if t['audio_id']}
    files = {}
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts[0] == 'cache' and (len(relative.parts) < 2 or relative.parts[1] != 'timbre' or path.stem not in audio_ids):
            continue
        files[str(relative)] = base64.b64encode(path.read_bytes()).decode()
    return {'conversations': conversations, 'files': files}


def restore(state, root):
    for name, value in state.get('files', {}).items():
        if not (name in ('gnani.jsonl', 'claude.jsonl') or name.startswith('cache/timbre/')):
            raise ValueError('Invalid persisted file')
        path = root / name
        if root.resolve() not in path.resolve().parents:
            raise ValueError('Invalid persisted path')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(value))
    config = GnaniConfig(os.environ.get('GNANI_API_KEY'), os.environ.get('GNANI_BASE_URL'), os.environ.get('GNANI_AUTH_HEADER'), root / 'cache')
    prisma, timbre = PrismaClient(config), TimbreClient(config)
    for client in (prisma, timbre):
        client._http = httpx.Client(timeout=httpx.Timeout(20, connect=5))
    ledger = Ledger(root / 'gnani.jsonl', float(os.environ.get('BOLI_BUDGET_INR', '25')))
    usage = ClaudeUsage(root / 'claude.jsonl', float(os.environ.get('BOLI_CLAUDE_BUDGET_USD', '.25')), 40)
    key = os.environ.get('ANTHROPIC_API_KEY')
    replier = AnthropicReply(key, AnthropicReply.DEFAULT_MODEL, usage, http=httpx.Client(timeout=httpx.Timeout(20, connect=5))) if key else None
    engine = ConversationEngine(RecognitionService(prisma, ledger), timbre, ledger, replier)
    for cid, value in state.get('conversations', {}).items():
        if value['created'] < time.time() - 3600:
            continue
        engine._conversations[cid] = Conversation(id=cid, created=value['created'], turns={k: Turn(**v) for k, v in value['turns'].items()}, history=value['history'])
    return engine


def reserve_budget(state, engine, operation, args):
    """Debit a conservative allowance before sending a paid request.

    Allowances are not refunded after ambiguous failures or process termination.
    This makes the cap survive serverless termination, at the cost of stopping early.
    """
    allowance = dict(state.get('reserved') or {'inr': max(engine.ledger.summary()['estimated_spent_inr'], float(os.environ.get('BOLI_PRIOR_GNANI_SPEND_INR', '0'))),
                                              'usd': engine.replier.usage.summary()['estimated_spent_usd'] if engine.replier else 0,
                                              'reply_requests': 0})
    inr, usd = 0, 0
    if operation in ('recognize', 'reply', 'speak'):
        conv = engine._live(args[0])
        turn = conv.turns.get(args[1])
        if operation == 'recognize' and not (turn and turn.recognized_text is not None):
            if len(conv.turns) >= MAX_TURNS:
                raise RecognitionError('conversation_full', 'Start a new conversation before adding more turns.', 409)
            info = inspect_upload(args[2])
            peak = wav_peak(args[2])
            if peak is not None and peak < SILENCE_PEAK:
                raise RecognitionError('silence', 'I could not hear anything. Check the microphone and try again.', 422)
            inr = estimate_cost_inr(info['duration_s'])
        elif operation == 'reply' and engine.replier and turn and turn.reply_text is None:
            messages = []
            for tid in conv.history[-MAX_CONTEXT_TURNS:]:
                past = conv.turns[tid]
                messages += [{'role': 'user', 'content': past.recognized_text[:MAX_TEXT_CHARS]}, {'role': 'assistant', 'content': past.reply_text[:MAX_TEXT_CHARS]}]
            messages.append({'role': 'user', 'content': turn.recognized_text[:MAX_TEXT_CHARS]})
            # UTF-8 byte count is deliberately more conservative than character count.
            usd = max(engine.replier._worst_case_usd(messages), engine.replier.cost_usd(
                2000 + sum(len(m['content'].encode()) for m in messages), engine.replier.max_tokens))
            if allowance['reply_requests'] >= 40:
                raise RecognitionError('budget_exhausted', 'The Claude trial request limit has been reached.', 409)
            allowance['reply_requests'] += 1
        elif operation == 'speak' and turn and turn.reply_text and turn.audio_id is None:
            inr = max(.01, round(len(turn.reply_text[:MAX_TEXT_CHARS]) * 27 / 10000, 2))
    if (inr and allowance['inr'] + inr > engine.ledger.budget_inr) or (usd and allowance['usd'] + usd > float(os.environ.get('BOLI_CLAUDE_BUDGET_USD', '.25'))):
        raise RecognitionError('budget_exhausted', 'The private trial spending allowance is exhausted.', 409)
    allowance['inr'] = round(allowance['inr'] + inr, 2)
    allowance['usd'] = round(allowance['usd'] + usd, 6)
    state['reserved'] = allowance


@functools.lru_cache(maxsize=1)
def static_capabilities():
    """What the page needs at load time. It depends only on settings, not on saved conversations, so no database call is made."""
    with tempfile.TemporaryDirectory() as directory:
        return restore({}, Path(directory)).capabilities()


def stored_audio(audio_id):
    """A spoken reply by id, read straight from the saved state: no lock, no rebuild of the whole state, no write."""
    if not re.fullmatch(r'[0-9a-f]{64}', audio_id or ''):
        return None
    with connect() as db:
        row = db.execute("SELECT payload->'files'->>%s FROM boli_runtime WHERE id=1", (f'cache/timbre/{audio_id[:2]}/{audio_id}.bin',)).fetchone()
    return base64.b64decode(row[0]) if row and row[0] else None


def log_review(db, operation, args, result, error):
    """Keep the speaker's audio, what Prisma heard and Claude's reply for the maker's accuracy review (30 days, see schema.sql)."""
    code = getattr(error, 'code', None)
    result = result or {}
    try:
        with db.transaction():  # a savepoint: failing to keep a review copy must never fail the turn
            if operation == 'recognize' and (not error or code == 'no_speech'):
                db.execute('INSERT INTO boli_reviews(id,conversation_id,turn_id,audio,recognized_text,error_code,recognition) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(id) DO NOTHING',
                           (f'{args[0]}:{args[1]}', args[0], args[1], args[2], result.get('recognized_text'), code, json.dumps((result.get('developer') or {}).get('recognition'))))
            elif operation == 'reply' and not error:
                reply = (result.get('developer') or {}).get('reply') or {}
                db.execute('UPDATE boli_reviews SET reply_text=%s, understood=%s, reply=%s::jsonb WHERE id=%s',
                           (result.get('reply_text'), reply.get('understood'), json.dumps(reply), f'{args[0]}:{args[1]}'))
    except Exception:
        pass


class PersistentEngine:
    def __getattr__(self, operation):
        if operation == 'capabilities':
            return static_capabilities
        if operation == 'audio':
            return stored_audio

        def invoke(*args, **kwargs):
            error = None
            with connect() as db, tempfile.TemporaryDirectory() as directory:
                # One locked state row ensures independent Vercel instances share
                # conversation history and spend checks, including failure events.
                if not db.execute('SELECT pg_try_advisory_lock(78120403)').fetchone()[0]:
                    raise RecognitionError('busy', 'Another trial request is running. Please retry shortly.', 409)
                db.execute("SET LOCAL lock_timeout = '5s'")
                row = db.execute("SELECT payload FROM boli_runtime WHERE id=1 FOR UPDATE").fetchone()
                if row is None:
                    raise RuntimeError('Apply deploy/schema.sql before running the app')
                root = Path(directory)
                state = row[0]
                engine = restore(state, root)
                reserve_budget(state, engine, operation, args)
                db.execute('UPDATE boli_runtime SET payload=%s::jsonb WHERE id=1', (json.dumps(state),))
                db.commit()  # session advisory lock remains held across this commit
                try:
                    result = getattr(engine, operation)(*args, **kwargs)
                except Exception as exc:
                    error = exc
                log_review(db, operation, args, None if error else result, error)
                updated = pack(engine, root)
                updated['reserved'] = state['reserved']
                db.execute('UPDATE boli_runtime SET payload=%s::jsonb WHERE id=1', (json.dumps(updated),))
            if error:
                raise error
            return result
        return invoke


class PostgresContributions:
    def save(self, audio, metadata, receipt=None):
        cid, token = (receipt["contribution_id"], receipt["withdrawal_token"]) if receipt else (uuid.uuid4().hex, secrets.token_urlsafe(32))
        with connect() as db:
            db.execute('INSERT INTO boli_contributions(id,token_hash,audio,metadata) VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(id) DO NOTHING',
                       (cid, hashlib.sha256(token.encode()).hexdigest(), audio, json.dumps(metadata, ensure_ascii=False)))
            saved = db.execute('SELECT token_hash,audio,metadata FROM boli_contributions WHERE id=%s', (cid,)).fetchone()
            verify_retry(saved, token, audio, metadata)
        return {'contribution_id': cid, 'withdrawal_token': token, 'retention_days': 30}

    def withdraw(self, cid, token):
        with connect() as db:
            return db.execute('DELETE FROM boli_contributions WHERE id=%s AND token_hash=%s',
                              (cid, hashlib.sha256(token.encode()).hexdigest())).rowcount == 1


LOGIN_HTML = """<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Boli Zero — private trial</title>
<style>body{font:18px system-ui;background:#faf6ef;color:#29251f;max-width:420px;margin:12vh auto;padding:24px}input,button{box-sizing:border-box;width:100%;padding:14px;margin-top:16px;font:inherit;border-radius:12px;border:1px solid #aaa}button{background:#b3261e;color:white;border:0}</style>
<h1>Boli Zero</h1><p>Enter your invitation password to try a Bhojpuri conversation.</p>
<form method="post" action="/login"><label for="password">Invitation password</label><input id="password" name="password" type="password" autocomplete="current-password" required><button>Open conversation</button></form></html>"""


def valid_session(cookie, password):
    try:
        expires, signature = cookie.split('.', 1)
        expiry = int(expires)
        expected = hmac.new(password.encode(), expires.encode(), hashlib.sha256).hexdigest()
        return time.time() < expiry <= time.time() + 86400 and hmac.compare_digest(signature, expected)
    except (ValueError, AttributeError):
        return False


def create_hosted_app():
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def private_trial(request: Request, call_next):
        # The form sends the invitation to our server; the session cookie is HttpOnly.
        password = os.environ.get('BOLI_INVITE_PASSWORD', '')
        open_access = os.environ.get('BOLI_OPEN_ACCESS') == '1'  # explicit opt-in: a lost password setting still fails closed
        if not password and not open_access:
            return JSONResponse({'error': 'Private trial has not been configured.'}, status_code=503)
        origin = request.headers.get('origin')
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'error': 'This request came from a different website.'}, status_code=403)
        if request.url.path == '/login' and request.method == 'POST' and not open_access:
            entered = (await request.form()).get('password', '')
            if not isinstance(entered, str) or not secrets.compare_digest(entered.encode(), password.encode()):
                return HTMLResponse(LOGIN_HTML.replace('<form ', '<p>The invitation password did not match. Try again.</p><form '), status_code=401)
            expires = str(int(time.time()) + 86400)
            signature = hmac.new(password.encode(), expires.encode(), hashlib.sha256).hexdigest()
            response = RedirectResponse('/', status_code=303)
            response.set_cookie('boli_session', expires + '.' + signature, httponly=True,
                                secure=request.url.hostname not in ('127.0.0.1', 'localhost', '::1'), samesite='strict', max_age=86400)
            response.headers['Cache-Control'] = 'no-store'
            return response
        header = request.headers.get('authorization', '')
        supplied = ''
        if header.startswith('Basic '):
            try:
                supplied = base64.b64decode(header[6:], validate=True).decode().split(':', 1)[1]
            except (ValueError, UnicodeError, IndexError):
                pass
        withdrawal = request.method == 'DELETE' and request.url.path.startswith('/api/contributions/') and header.startswith('Bearer ')
        authenticated = open_access or valid_session(request.cookies.get('boli_session'), password) or (bool(supplied) and secrets.compare_digest(supplied.encode(), password.encode()))
        if not withdrawal and not authenticated:
            if request.url.path in ('/', '/login') and not header:
                return HTMLResponse(LOGIN_HTML, headers={'Cache-Control': 'no-store'})
            return JSONResponse({'error': 'Use your private trial invitation password.'}, status_code=401)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.exception_handler(RecognitionError)
    async def recognition_error(request, error):
        return JSONResponse({'error': {'code': error.code, 'message': error.message, **error.extra}}, status_code=error.status)

    @app.exception_handler(Exception)
    async def unavailable(request, error):
        # Never return database URLs, credentials, or provider error bodies.
        return JSONResponse({'error': {'code': 'server_unavailable', 'message': 'The private trial service is unavailable. Please try later.'}}, status_code=503)

    engine = PersistentEngine()
    conversation_routes.register(app, engine)
    register_contributions(app, engine, PostgresContributions())

    @app.get('/')
    def home():
        return FileResponse(ROOT / 'web' / 'talk.html')

    return app
