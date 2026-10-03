"""Hosting contracts tested locally; live Supabase/Vercel are separate checks."""
import base64
import time

from fastapi.testclient import TestClient

from boli_zero.conversation import Conversation, Turn
from boli_zero.hosted import create_hosted_app, log_review, pack, restore
from boli_zero.service import RecognitionError


def test_restarted_engine_preserves_turn_history_budget_and_speech(tmp_path, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    root = tmp_path / 'first'
    root.mkdir()
    engine = restore({}, root)
    engine._conversations['private'] = Conversation(id='private', turns={'turn': Turn(id='turn', recognized_text='रउआ', reply_text='प्रणाम', audio_id='a' * 64)}, history=['turn'])
    engine.ledger.record(outcome='success', cost_estimate_inr=21.3)
    path = root / 'cache' / 'timbre' / 'aa' / ('a' * 64 + '.bin')
    path.parent.mkdir(parents=True)
    path.write_bytes(b'original speech bytes')
    state = pack(engine, root)
    other = tmp_path / 'second'
    other.mkdir()
    restarted = restore(state, other)
    assert restarted._live('private').history == ['turn']
    assert restarted._live('private').turns['turn'].recognized_text == 'रउआ'
    assert restarted.ledger.summary()['estimated_spent_inr'] == 21.3
    assert (other / path.relative_to(root)).read_bytes() == b'original speech bytes'


def test_expired_context_and_unreferenced_cache_are_not_persisted(tmp_path):
    engine = restore({}, tmp_path)
    engine._conversations['old'] = Conversation(id='old', created=time.time() - 3601)
    path = tmp_path / 'cache' / 'prisma' / 'old.json'
    path.parent.mkdir(parents=True)
    path.write_text('private old transcript')
    state = pack(engine, tmp_path)
    assert state['conversations'] == {}
    assert state['files'] == {}


def test_hosted_page_requires_private_invitation_and_lab_is_not_published(monkeypatch):
    monkeypatch.setenv('BOLI_INVITE_PASSWORD', 'test-private-invitation')
    with TestClient(create_hosted_app()) as client:
        assert 'Invitation password' in client.get('/').text
        assert client.get('/', auth=('friend', 'wrong')).status_code == 401
        response = client.get('/', auth=('friend', 'test-private-invitation'))
        assert response.status_code == 200
        assert 'Optional: contribute your speech' in response.text
        assert client.get('/lab', auth=('friend', 'test-private-invitation')).status_code == 404
        assert client.get('/docs', auth=('friend', 'test-private-invitation')).status_code == 404


def test_missing_invitation_fails_closed(monkeypatch):
    monkeypatch.delenv('BOLI_INVITE_PASSWORD', raising=False)
    with TestClient(create_hosted_app()) as client:
        assert client.get('/').status_code == 503


def test_open_access_needs_the_explicit_switch_and_still_blocks_other_websites(monkeypatch):
    monkeypatch.delenv('BOLI_INVITE_PASSWORD', raising=False)
    monkeypatch.setenv('BOLI_OPEN_ACCESS', '0')
    with TestClient(create_hosted_app()) as client:
        assert client.get('/').status_code == 503  # anything but "1" stays closed
    monkeypatch.setenv('BOLI_OPEN_ACCESS', '1')
    with TestClient(create_hosted_app()) as client:
        page = client.get('/')
        assert page.status_code == 200 and 'Invitation password' not in page.text and 'Optional: contribute your speech' in page.text
        assert client.get('/lab').status_code == 404
        assert client.post('/api/conversations', headers={'origin': 'https://elsewhere.example'}).status_code == 403


def test_withdrawal_receipt_works_without_basic_password(monkeypatch):
    from boli_zero.hosted import PostgresContributions
    monkeypatch.setenv('BOLI_INVITE_PASSWORD', 'private')
    seen = []
    monkeypatch.setattr(PostgresContributions, 'withdraw', lambda self, cid, token: seen.append((cid, token)) or token == 'valid-receipt')
    with TestClient(create_hosted_app()) as client:
        assert client.delete('/api/contributions/item', headers={'Authorization': 'Bearer wrong'}).status_code == 404
        assert client.delete('/api/contributions/item', headers={'Authorization': 'Bearer valid-receipt'}).json() == {'deleted': True}
    assert seen == [('item', 'wrong'), ('item', 'valid-receipt')]


def test_conservative_budget_survives_restart_and_refuses_overspend(tmp_path, monkeypatch):
    import io
    import wave
    import pytest
    from boli_zero.hosted import reserve_budget
    from boli_zero.service import RecognitionError
    monkeypatch.setenv('BOLI_BUDGET_INR', '.01')
    engine = restore({}, tmp_path)
    engine._conversations['trial'] = Conversation(id='trial')
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes((8000).to_bytes(2, 'little', signed=True) * 32000)
    with pytest.raises(RecognitionError, match='allowance is exhausted'):
        reserve_budget({}, engine, 'recognize', ('trial', 'turn', buf.getvalue()))


def test_completed_stage_retry_does_not_reserve_again(tmp_path):
    from boli_zero.hosted import reserve_budget
    engine = restore({}, tmp_path)
    engine._conversations['trial'] = Conversation(id='trial', turns={'turn': Turn(id='turn', recognized_text='प्रणाम')})
    state = {'reserved': {'inr': 21.3, 'usd': 0, 'reply_requests': 0}}
    reserve_budget(state, engine, 'recognize', ('trial', 'turn', b'not used'))
    assert state['reserved']['inr'] == 21.3


def test_persisted_path_cannot_escape_private_temporary_folder(tmp_path):
    import pytest
    with pytest.raises(ValueError, match='Invalid persisted file'):
        restore({'files': {'../../outside': base64.b64encode(b'bad').decode()}}, tmp_path)


def test_silent_input_is_rejected_without_reserving_spend(tmp_path):
    import io
    import wave
    import pytest
    from boli_zero.hosted import reserve_budget
    from boli_zero.service import RecognitionError
    engine = restore({}, tmp_path)
    engine._conversations['trial'] = Conversation(id='trial')
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(b'\x00\x00' * 32000)
    state = {}
    with pytest.raises(RecognitionError, match='could not hear'):
        reserve_budget(state, engine, 'recognize', ('trial', 'turn', buf.getvalue()))
    assert 'reserved' not in state


def test_invitation_form_uses_private_session_cookie(monkeypatch):
    monkeypatch.setenv('BOLI_INVITE_PASSWORD', 'private-invitation')
    with TestClient(create_hosted_app(), base_url='https://trial.example') as client:
        assert client.post('/login', data={'password':'wrong'}).status_code == 401
        response = client.post('/login', data={'password':'private-invitation'}, follow_redirects=False)
        assert response.status_code == 303
        cookie = response.headers['set-cookie'].lower()
        assert 'httponly' in cookie and 'secure' in cookie and 'samesite=strict' in cookie
        assert 'private-invitation' not in cookie
        assert 'Optional: contribute your speech' in client.get('/').text
        assert client.post('/api/conversations', headers={'Origin':'https://attacker.example'}).status_code == 403


def test_tampered_session_does_not_grant_access(monkeypatch):
    monkeypatch.setenv('BOLI_INVITE_PASSWORD', 'private-invitation')
    with TestClient(create_hosted_app()) as client:
        client.cookies.set('boli_session', str(int(time.time()) + 3600) + '.tampered')
        assert client.post('/api/conversations').status_code == 401


def test_speech_audio_is_read_without_rebuilding_the_state_and_only_by_valid_id(monkeypatch):
    import boli_zero.hosted as hosted
    asked = []

    class Result:
        def __init__(self, value): self.value = value
        def fetchone(self): return (self.value,)

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, sql, params):
            asked.append((sql, params))
            return Result(base64.b64encode(b'spoken reply bytes').decode())

    monkeypatch.setattr(hosted, 'connect', lambda: Connection())
    audio_id = 'ab' + '0' * 62
    assert hosted.stored_audio(audio_id) == b'spoken reply bytes'
    assert asked == [("SELECT payload->'files'->>%s FROM boli_runtime WHERE id=1", (f'cache/timbre/ab/{audio_id}.bin',))]  # one read, no lock, no update
    asked.clear()
    for bad in ('', '../../x', 'g' * 64, 'a' * 63, None):
        assert hosted.stored_audio(bad) is None
    assert asked == []


def test_capabilities_need_no_database(monkeypatch):
    import boli_zero.hosted as hosted
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    hosted.static_capabilities.cache_clear()
    monkeypatch.setattr(hosted, 'connect', lambda: (_ for _ in ()).throw(AssertionError('database must not be used')))
    caps = hosted.PersistentEngine().capabilities()
    assert caps['reply_ready'] is False and 'Hindi mode' in caps['recognition_mode']
    hosted.static_capabilities.cache_clear()


class FakeDb:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def transaction(self):
        import contextlib
        return contextlib.nullcontext()

    def execute(self, sql, params=()):
        if self.fail:
            raise RuntimeError('database down')
        self.calls.append((sql.split()[0], params))


def test_review_copy_keeps_audio_text_and_reply_and_never_fails_the_turn():
    heard = {'recognized_text': 'रउआ कइसन बानी', 'developer': {'recognition': {'raw_output': 'रउआ कइसन बानी'}}}
    db = FakeDb()
    log_review(db, 'recognize', ('c' * 8, 't' * 8, b'wav bytes'), heard, None)
    assert db.calls[0][0] == 'INSERT' and db.calls[0][1][:5] == ('cccccccc:tttttttt', 'cccccccc', 'tttttttt', b'wav bytes', 'रउआ कइसन बानी')
    answered = {'reply_text': 'हम ठीक बानी', 'developer': {'reply': {'understood': False}}}
    log_review(db, 'reply', ('c' * 8, 't' * 8), answered, None)
    assert db.calls[1][0] == 'UPDATE' and db.calls[1][1][:2] == ('हम ठीक बानी', False)
    unheard = FakeDb()
    log_review(unheard, 'recognize', ('c' * 8, 't' * 8, b'quiet speech'), None, RecognitionError('no_speech', 'x', 422))
    assert unheard.calls[0][1][3:6] == (b'quiet speech', None, 'no_speech')  # audio Prisma could not read is worth keeping
    rejected = FakeDb()
    log_review(rejected, 'recognize', ('c' * 8, 't' * 8, b'junk'), None, RecognitionError('unsupported_format', 'x', 415))
    log_review(rejected, 'speak', ('c' * 8, 't' * 8), answered, None)
    assert rejected.calls == []  # bad uploads and the speech step are not kept
    log_review(FakeDb(fail=True), 'recognize', ('c' * 8, 't' * 8, b'wav'), heard, None)  # must not raise
