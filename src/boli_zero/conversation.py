"""Spoken conversation engine: microphone audio -> Prisma text -> reply text -> Timbre audio.

Each stage is its own idempotent call keyed by a client-chosen turn id, so a retry resumes at the failed stage and never
records a turn twice or pays twice (recognition and speech are cached by content). Conversations are bounded, can be ended
at any time, and anything that finishes after its conversation ended is discarded rather than attached anywhere.

Honest limits: Gnani documents no text-reply service (Evon has no hosted endpoint), so the reply stage works only with a
provider that the operator configures explicitly. Recognition runs in Hindi mode and speech uses a Hindi voice; neither is
native Bhojpuri.
"""
from __future__ import annotations

import array
import re
import threading
import time
import uuid
import wave
from contextlib import contextmanager
from dataclasses import dataclass, field
from io import BytesIO

import httpx

from .clients import GnaniApiError, NotConfigured, TimbreClient
from .ledger import BudgetExceeded, ClaudeUsage, Ledger
from .service import RecognitionError, RecognitionService, inspect_upload

MAX_CONTEXT_TURNS = 6  # earlier exchanges sent to the reply provider
MAX_TEXT_CHARS = 400  # per message sent as context, and the longest reply that is spoken
MAX_TURNS = 40  # per conversation
MAX_CONVERSATIONS = 50
SILENCE_PEAK = 0.02  # a WAV whose loudest sample is below this share of full scale is treated as silence (heuristic)
TTS_INR_PER_CHAR = 27.0 / 10_000

UNCLEAR_TAG = "[UNCLEAR]"

SYSTEM_PROMPT = (
    "You are a friendly voice assistant. Talk with the user in Bhojpuri, written in Devanagari script. "
    "Always answer what the user actually means: reply to a greeting with a greeting, give real, useful answers to questions, "
    "and use the earlier turns of this conversation to understand follow-ups (for example, what 'there' or 'it' refers to). "
    "Never translate or repeat the user's sentence back. "
    "Your reply will be spoken aloud, so keep it to one or two short, natural sentences with no lists, no emoji, no markup and no "
    "English unless the user used it. "
    "The user's words come from a speech recognizer that listens in Hindi, so they may be spelled like Hindi or contain mistakes: "
    "infer the intent. If the words are unclear or could mean different things, ask one short clarifying question instead of guessing. "
    "Do not comment on how the user speaks, on pronunciation, or on how good your own Bhojpuri is, and make no claims about language accuracy. "
    "Before answering, decide whether the words are a real, meaningful utterance. If they are nonsense or made-up sounds, a string of unrelated words, "
    "too broken to follow, or clearly another language or a different regional variety such as Bundeli (marked by forms like हओ, काए, तुमाओ, मोरो, जा रए), start your reply with the exact tag " + UNCLEAR_TAG + " followed by one short Bhojpuri sentence "
    "saying you did not understand (or that you only speak Bhojpuri) and asking them to say it again. Never invent a meaning for words you cannot follow. "
    "Short real utterances such as a greeting are meaningful and must not get the tag."
)


class ReplyError(RecognitionError):
    """A failure in the reply stage."""


# --- reply provider: Claude through the documented Messages API ---------------------------------------------------------------------------
class AnthropicReply:
    """Reply generation with Claude (docs: platform.claude.com/docs/en/api/messages, checked 2026-10-03).
    The system instructions travel in the `system` field; the user's recognized words only ever appear as user messages."""

    DEFAULT_MODEL = "claude-haiku-4-5-20251001"
    API_URL = "https://api.anthropic.com"
    VERSION = "2023-06-01"
    PRICES_USD_PER_MTOK = {"claude-haiku-4-5-20251001": (1.0, 5.0), "claude-sonnet-5-5": (2.0, 10.0),
                           "claude-opus-5-5": (4.0, 20.0), "claude-fable-5-1": (10.0, 50.0)}  # (input, output), model overview page

    def __init__(self, api_key: str, model: str, usage: ClaudeUsage, base_url: str | None = None, http: httpx.Client | None = None, max_tokens: int = 120):
        if model not in self.PRICES_USD_PER_MTOK:
            raise ValueError(f"no price known for model {model!r}; refusing to spend without a cost estimate")
        self._key, self.model, self.usage, self.max_tokens = api_key, model, usage, max_tokens
        self.base_url = (base_url or self.API_URL).rstrip("/")
        self.http = http or httpx.Client(timeout=60)
        self.name = f"Claude ({model}) via the Anthropic Messages API"

    def cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        price_in, price_out = self.PRICES_USD_PER_MTOK[self.model]
        return round((input_tokens * price_in + output_tokens * price_out) / 1_000_000, 6)

    def _worst_case_usd(self, messages: list[dict]) -> float:
        # Devanagari can cost about a token per character: count every character of input as a token, and the full output allowance.
        chars = len(SYSTEM_PROMPT) + sum(len(m["content"]) for m in messages)
        return self.cost_usd(chars, self.max_tokens)

    def reply(self, history: list[dict], user_text: str) -> str:
        return self.reply_with_usage(history, user_text)[0]

    def reply_with_usage(self, history: list[dict], user_text: str) -> tuple[str, dict]:
        messages = [*history, {"role": "user", "content": user_text}]
        try:
            self.usage.check(self._worst_case_usd(messages))
        except BudgetExceeded as error:
            raise ReplyError("budget_exhausted", str(error), 409) from error
        started = time.time()
        try:
            response = self.http.post(f"{self.base_url}/v1/messages", headers={"x-api-key": self._key, "anthropic-version": self.VERSION, "content-type": "application/json"},
                                      json={"model": self.model, "max_tokens": self.max_tokens, "system": SYSTEM_PROMPT, "messages": messages})
        except httpx.HTTPError as error:
            self.usage.record(outcome="network_error", cost_usd=0, model=self.model)
            raise ReplyError("reply_unreachable", "The answer service could not be reached.", 502) from error
        seconds = round(time.time() - started, 2)
        try:
            body = response.json()
        except ValueError:
            body = {}
        problem = (body.get("error") or {}) if isinstance(body, dict) else {}
        if response.status_code != 200:
            self.usage.record(outcome=f"http_{response.status_code}", cost_usd=0, model=self.model, error_type=problem.get("type"))
            if response.status_code == 401:
                raise ReplyError("reply_auth", "The answer service rejected the server's key.", 502)
            if response.status_code == 402 or "credit" in str(problem.get("message", "")).lower():
                raise ReplyError("reply_billing", "The answer service reports a billing or credit problem, so no reply can be made.", 502)
            if response.status_code == 429:
                raise ReplyError("reply_rate_limited", "The answer service is busy. Try again in a moment.", 429, retry_after=response.headers.get("retry-after") or "10")
            raise ReplyError("reply_failed", f"The answer service had a problem (HTTP {response.status_code}). Try again.", 502)
        text = "".join(block.get("text", "") for block in body.get("content", []) if block.get("type") == "text").strip()
        used = body.get("usage") or {}
        tokens_in, tokens_out = int(used.get("input_tokens", 0)), int(used.get("output_tokens", 0))
        cost = self.cost_usd(tokens_in, tokens_out)
        self.usage.record(outcome="success", cost_usd=cost, model=self.model, input_tokens=tokens_in, output_tokens=tokens_out, stop_reason=body.get("stop_reason"),
                          request_id=response.headers.get("request-id"), seconds=seconds)
        if body.get("stop_reason") == "max_tokens":  # a cut-off sentence sounds wrong aloud: keep up to the last full sentence if there is one
            cut = max(text.rfind(m) for m in "।.?!")
            text = text[:cut + 1] if cut > 0 else text
        if not text:
            raise ReplyError("reply_failed", "The answer service did not give a usable reply.", 502)
        return text[:MAX_TEXT_CHARS], {"input_tokens": tokens_in, "output_tokens": tokens_out, "cost_usd": cost, "stop_reason": body.get("stop_reason"),
                                       "request_id": response.headers.get("request-id"), "seconds": seconds}


# --- state ------------------------------------------------------------------------------------------------------------
@dataclass
class Turn:
    id: str
    recognized_text: str | None = None
    reply_text: str | None = None
    audio_id: str | None = None
    dev: dict = field(default_factory=dict)


@dataclass
class Conversation:
    id: str
    created: float = field(default_factory=time.time)
    ended: bool = False
    turns: dict[str, Turn] = field(default_factory=dict)  # every turn seen, by id
    history: list[str] = field(default_factory=list)  # ids of turns that have a reply, in order
    inflight: set[str] = field(default_factory=set)
    lock: threading.Lock = field(default_factory=threading.Lock)


def wav_peak(data: bytes) -> float | None:
    """Loudest sample as a share of full scale for 16-bit PCM WAV; None when it cannot be measured."""
    try:
        with wave.open(BytesIO(data)) as w:
            if w.getsampwidth() != 2:
                return None
            samples = array.array("h")
            samples.frombytes(w.readframes(w.getnframes()))
    except (wave.Error, EOFError):
        return None
    return max((abs(x) for x in samples), default=0) / 32768


class ConversationEngine:
    def __init__(self, recognizer: RecognitionService, timbre: TimbreClient, ledger: Ledger, replier=None, voice: str | None = None):
        self.recognizer, self.timbre, self.ledger, self.replier, self.voice = recognizer, timbre, ledger, replier, voice
        self._conversations: dict[str, Conversation] = {}
        self._guard = threading.Lock()

    # conversations
    def start(self) -> dict:
        with self._guard:
            if len(self._conversations) >= MAX_CONVERSATIONS:  # forget the oldest ended ones first
                for cid in [c.id for c in sorted(self._conversations.values(), key=lambda c: (not c.ended, c.created))][:10]:
                    del self._conversations[cid]
            conv = Conversation(id=uuid.uuid4().hex)
            self._conversations[conv.id] = conv
        return {"conversation_id": conv.id, **self.capabilities()}

    def end(self, cid: str) -> dict:
        conv = self._conversations.get(cid)
        if conv:
            with conv.lock:
                conv.ended = True
        return {"conversation_id": cid, "ended": True}

    def capabilities(self) -> dict:
        return {"reply_provider": getattr(self.replier, "name", None), "reply_ready": self.replier is not None,
                "recognition_mode": "Hindi mode (hi-IN); Bhojpuri is not offered by Prisma",
                "speech_mode": f"Timbre {TimbreClient.MODEL}, Hindi language code hi-IN, voice {self.voice or TimbreClient.DEFAULT_VOICE}; Bhojpuri is not offered, pronunciation unverified",
                "limits": {"max_turns": MAX_TURNS, "context_turns": MAX_CONTEXT_TURNS, "max_seconds": 30}}

    def _live(self, cid: str) -> Conversation:
        conv = self._conversations.get(cid)
        if conv is None:
            raise RecognitionError("conversation_not_found", "This conversation no longer exists. Start a new one.", 404)
        if conv.ended:
            raise RecognitionError("conversation_ended", "This conversation was ended.", 410)
        return conv

    @contextmanager
    def _claim(self, conv: Conversation, turn_id: str):
        """Run one stage of one turn at a time per conversation; a second click while it runs is refused, not queued."""
        with conv.lock:
            if conv.ended:
                raise RecognitionError("conversation_ended", "This conversation was ended.", 410)
            if conv.inflight:
                raise RecognitionError("busy", "Still working on the previous step. Please wait.", 409)
            conv.inflight.add(turn_id)
        try:
            yield
        finally:
            with conv.lock:
                conv.inflight.discard(turn_id)

    @staticmethod
    def _commit(conv: Conversation, apply) -> None:
        """Attach a finished result only if its conversation is still live; otherwise discard it."""
        with conv.lock:
            if conv.ended:
                raise RecognitionError("conversation_ended", "This conversation was ended while that step was running; the result was discarded.", 410)
            apply()

    @staticmethod
    def view(turn: Turn) -> dict:
        return {"id": turn.id, "recognized_text": turn.recognized_text, "reply_text": turn.reply_text,
                "audio_url": f"/api/speech/{turn.audio_id}" if turn.audio_id else None, "developer": turn.dev}

    # stage 1: recognition
    def recognize(self, cid: str, turn_id: str, audio: bytes) -> dict:
        conv = self._live(cid)
        if len(conv.turns) >= MAX_TURNS and turn_id not in conv.turns:
            raise RecognitionError("conversation_full", "This conversation is long enough. Start a new one.", 409)
        with self._claim(conv, turn_id):
            existing = conv.turns.get(turn_id)
            if existing and existing.recognized_text is not None:
                return self.view(existing)  # retry of a finished stage: nothing is sent again
            info = inspect_upload(audio)
            peak = wav_peak(audio)
            if peak is not None and peak < SILENCE_PEAK:
                raise RecognitionError("silence", "I could not hear anything. Check the microphone and try again.", 422)
            result = self.recognizer.recognize(audio, info["duration_s"], mode="baseline")
            text = result["recognition"]["raw_output"].strip()
            if not text:
                raise RecognitionError("no_speech", "I could not make out any speech in that recording.", 422)
            turn = Turn(id=turn_id, recognized_text=text, dev={"recognition": {
                "mode": "Hindi mode (hi-IN), a workaround: Prisma does not offer Bhojpuri", "source": result["source"],
                "request_id": result["recognition"]["request_id"], "duration_s": info["duration_s"], "format": info["format"],
                "proposed_variety": result["identification"]["summary"], "raw_output": result["recognition"]["raw_output"]}})
            self._commit(conv, lambda: conv.turns.__setitem__(turn_id, turn))
        return self.view(turn)

    # stage 2: reply
    def reply(self, cid: str, turn_id: str) -> dict:
        conv = self._live(cid)
        turn = conv.turns.get(turn_id)
        if turn is None or turn.recognized_text is None:
            raise RecognitionError("turn_not_recognized", "That turn has not been recognized yet.", 409)
        if turn.reply_text is not None:
            return self.view(turn)
        if self.replier is None:
            raise ReplyError("reply_not_configured", "The assistant's answering service is not connected yet, so I can show what I heard but cannot reply.", 503)
        with self._claim(conv, turn_id):
            context = []
            for tid in conv.history[-MAX_CONTEXT_TURNS:]:
                past = conv.turns[tid]
                if not past.dev.get("reply", {}).get("understood", True):
                    continue  # a turn nobody understood must not steer later answers
                context += [{"role": "user", "content": past.recognized_text[:MAX_TEXT_CHARS]}, {"role": "assistant", "content": past.reply_text[:MAX_TEXT_CHARS]}]
            started = time.time()
            if hasattr(self.replier, "reply_with_usage"):
                text, usage = self.replier.reply_with_usage(context, turn.recognized_text[:MAX_TEXT_CHARS])
            else:
                text, usage = self.replier.reply(context, turn.recognized_text[:MAX_TEXT_CHARS]), {}
            understood = not text.startswith(UNCLEAR_TAG)
            text = text.removeprefix(UNCLEAR_TAG).strip() or "मैं समझ नहीं पाया, कृपया फिर से बोलिए।"  # tag with no sentence
            info = {"provider": self.replier.name, "model": getattr(self.replier, "model", None), "context_turns_sent": len(context) // 2,
                    "seconds": round(time.time() - started, 2), "understood": understood, **usage}

            def apply():
                turn.reply_text, turn.dev["reply"] = text, info
                conv.history.append(turn_id)

            self._commit(conv, apply)
        return self.view(turn)

    # stage 3: speech
    def speak(self, cid: str, turn_id: str) -> dict:
        conv = self._live(cid)
        turn = conv.turns.get(turn_id)
        if turn is None or turn.reply_text is None:
            raise RecognitionError("turn_not_replied", "There is no reply to speak yet.", 409)
        if turn.audio_id is not None:
            return self.view(turn)
        with self._claim(conv, turn_id):
            text = turn.reply_text[:MAX_TEXT_CHARS]
            audio, key, info = self._synthesize(text, self.voice, {"turn_id": turn_id})

            def apply():
                turn.audio_id, turn.dev["speech"] = key, info

            self._commit(conv, apply)
        return self.view(turn)

    def _synthesize(self, text: str, voice: str | None, who_extra: dict) -> tuple[bytes, str, dict]:
        """One Timbre request (cached by content), counted against the spend cap. Returns audio, cache key and details."""
        params = self.timbre.request_params(text, "hi-IN", voice)
        key = self.timbre.key_for("synthesize", params)
        source = "cache" if self.timbre.peek("synthesize", params) else "live"
        cost = max(0.01, round(len(text) * TTS_INR_PER_CHAR, 2)) if source == "live" else 0
        who = {"service": "timbre", "chars": len(text), **who_extra}
        started = time.time()
        try:
            if source == "live":
                self.ledger.check(cost)
            audio = self.timbre.synthesize(text, "hi-IN", voice)
        except BudgetExceeded as error:
            self.ledger.record(outcome="budget_blocked", cost_estimate_inr=0, **who)
            raise RecognitionError("budget_exhausted", str(error), 409)
        except NotConfigured:
            self.ledger.record(outcome="not_configured", cost_estimate_inr=0, **who)
            raise RecognitionError("not_configured", "Gnani credentials are not configured on the server, so no voice can be made.", 503)
        except GnaniApiError as error:
            outcome, code, status, message = RecognitionService._classify(error)
            self.ledger.record(outcome=outcome, cost_estimate_inr=0, gnani_status=error.status, gnani_error=error.error_type, **who)
            raise RecognitionError(code, message, status, retry_after=error.retry_after or "20") from error
        except httpx.HTTPError as error:
            self.ledger.record(outcome="network_error", cost_estimate_inr=0, **who)
            raise RecognitionError("gnani_unreachable", "Could not reach Gnani (network error or timeout).", 502) from error
        self.ledger.record(outcome="success" if source == "live" else "cache_replay", cost_estimate_inr=cost, **who)
        entry = self.timbre.peek("synthesize", params) or {}
        return audio, key, {"mode": f"Timbre {TimbreClient.MODEL}, language code hi-IN (Hindi) reading Bhojpuri text; pronunciation unverified",
                            "voice": params["voice"], "source": source, "chars": len(text), "text_sent": text, "estimated_cost_inr": cost, "bytes": len(audio),
                            "seconds": round(time.time() - started, 2), "audio_format": f"{params['audio_config']['container']} {params['audio_config']['sample_rate']} Hz mono",
                            "cached_at": entry.get("cached_at"), "origin": entry.get("origin")}

    def synthesize_text(self, text: str, voice: str | None = None) -> bytes:
        """Direct speech for the developer route: same cache, same spend cap and ledger as conversation speech."""
        return self._synthesize(text[:MAX_TEXT_CHARS], voice, {"purpose": "direct synthesis"})[0]

    def audio(self, audio_id: str) -> bytes | None:
        """Bytes of a synthesized reply by id. Only keys of this app's own speech cache can be asked for."""
        if not re.fullmatch(r"[0-9a-f]{64}", audio_id or ""):
            return None
        hit = self.timbre.cache.get("timbre", audio_id)
        return hit[1] if hit else None

    def snapshot(self, cid: str) -> dict:
        conv = self._conversations.get(cid)
        if conv is None:
            raise RecognitionError("conversation_not_found", "This conversation no longer exists.", 404)
        return {"conversation_id": cid, "ended": conv.ended, "turns": [self.view(conv.turns[t]) for t in conv.history]}
