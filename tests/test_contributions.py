"""Real SQLite and upload validation; conversation recognition is supplied, not live."""
import io
import json
import wave
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from boli_zero.contributions import CONSENT_VERSION, ContributionStore, register


def audio():
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b'\x01\x02' * 96000)
    return buf.getvalue()


@pytest.fixture
def setup(tmp_path):
    store = ContributionStore(tmp_path / 'private.sqlite')
    turn = SimpleNamespace(recognized_text='रउआ', reply_text='प्रणाम', dev={})
    engine = SimpleNamespace(_live=lambda cid: SimpleNamespace(turns={'turn': turn}))
    app = FastAPI()
    register(app, engine, store)
    return TestClient(app), store


def send(client, **changes):
    data = dict(contribution_id='a'*32, withdrawal_token='b'*43, conversation_id='conversation', turn_id='turn', consent='true', consent_version=CONSENT_VERSION,
                corrected_text='रउवा', feedback='Natural speech')
    data.update(changes)
    return client.post('/api/contributions', data=data, files={'file': ('capture.wav', audio(), 'audio/wav')})


@pytest.mark.parametrize('changes', [{'consent': 'false'}, {'consent_version': 'outdated'}, {'corrected_text': 'x' * 4001}, {'turn_id': 'missing'}])
def test_rejected_contributions_store_nothing(setup, changes):
    client, store = setup
    assert send(client, **changes).status_code in (404, 422)
    assert not store.path.exists()


def test_original_audio_and_separate_correction_persist(setup):
    client, store = setup
    receipt = send(client).json()
    reopened = ContributionStore(store.path)
    with reopened.connect() as db:
        raw, metadata, token_hash = db.execute('SELECT audio,metadata,token_hash FROM contributions').fetchone()
    assert raw == audio()
    metadata = json.loads(metadata)
    assert metadata['recognized_text_unverified'] == 'रउआ'
    assert metadata['corrected_text_user_supplied'] == 'रउवा'
    assert metadata['training_status'] == 'collected_not_trained'
    assert token_hash != receipt['withdrawal_token']
    assert store.path.stat().st_mode & 0o777 == 0o600


def test_withdrawal_requires_receipt_and_deletes_recording(setup):
    client, store = setup
    receipt = send(client).json()
    url = '/api/contributions/' + receipt['contribution_id']
    assert client.delete(url).status_code == 404
    assert client.delete(url, headers={'Authorization': 'Bearer wrong'}).status_code == 404
    assert client.delete(url, headers={'Authorization': 'Bearer ' + receipt['withdrawal_token']}).json() == {'deleted': True}
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM contributions').fetchone()[0] == 0


def test_expired_contributions_removed_on_storage_operation(setup):
    client, store = setup
    send(client)
    with store.connect() as db:
        db.execute('UPDATE contributions SET created=0')
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM contributions').fetchone()[0] == 0


def test_browser_wav_validation_does_not_require_ffprobe(monkeypatch):
    from boli_zero.service import inspect_upload
    def forbidden(*args, **kwargs):
        raise AssertionError("WAV validation must not launch ffprobe")
    monkeypatch.setattr("boli_zero.service.subprocess.run", forbidden)
    assert inspect_upload(audio())["duration_s"] == 2.0


def test_truncated_browser_wav_is_rejected():
    from boli_zero.service import inspect_upload, RecognitionError
    with pytest.raises(RecognitionError, match="read completely"):
        inspect_upload(audio()[:-100])


def test_timbre_streaming_pcm_header_has_measured_duration():
    import struct
    from boli_zero.service import inspect_upload
    data = bytearray(audio())
    struct.pack_into('<I', data, 4, 0xffffffff)
    struct.pack_into('<I', data, 40, 0xffffffff)
    assert inspect_upload(bytes(data))['duration_s'] == 2.0


def test_save_retry_returns_same_receipt_and_stores_only_one_recording(setup):
    client, store = setup
    first = send(client)
    assert first.status_code == 200
    assert send(client).json() == first.json()
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM contributions').fetchone()[0] == 1
    assert send(client, withdrawal_token='c'*43).status_code == 409
    assert send(client, corrected_text='changed after save').status_code == 409
