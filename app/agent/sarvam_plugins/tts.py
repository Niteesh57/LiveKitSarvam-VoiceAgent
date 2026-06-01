"""
Sarvam AI Text-to-Speech plugin for LiveKit Agents.

Uses Sarvam Bulbul v3 REST API at 48kHz for clear audio output.
"""

import base64
import io
import logging
import uuid
import wave
from dataclasses import dataclass

import aiohttp

from livekit.agents import tts, APIConnectOptions

from app.config.settings import settings

logger = logging.getLogger(__name__)

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


@dataclass
class SarvamTTSOptions:
    model: str = "bulbul:v3"
    target_language_code: str = "hi-IN"
    speaker: str = "shubh"
    pace: float = 1.0
    speech_sample_rate: int = 48000
    enable_preprocessing: bool = True


class SarvamTTS(tts.TTS):
    """
    Sarvam Bulbul v3 TTS — high quality Indian language speech synthesis.
    """

    def __init__(
        self,
        *,
        model: str = "bulbul:v3",
        target_language_code: str = "hi-IN",
        speaker: str = "shubh",
        pace: float = 1.0,
        speech_sample_rate: int = 48000,
        enable_preprocessing: bool = True,
        api_key: str | None = None,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=speech_sample_rate,
            num_channels=1,
        )
        self._api_key = api_key or settings.sarvam_api_key
        self._opts = SarvamTTSOptions(
            model=model,
            target_language_code=target_language_code,
            speaker=speaker,
            pace=pace,
            speech_sample_rate=speech_sample_rate,
            enable_preprocessing=enable_preprocessing,
        )
        self._session: aiohttp.ClientSession | None = None

    def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def synthesize(self, text: str, *, conn_options=None) -> "SarvamChunkedStream":
        if conn_options is None:
            conn_options = APIConnectOptions()
        return SarvamChunkedStream(
            tts=self,
            input_text=text,
            opts=self._opts,
            api_key=self._api_key,
            session_factory=self._ensure_session,
            conn_options=conn_options,
        )

    async def aclose(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


class SarvamChunkedStream(tts.ChunkedStream):
    """Synthesize text via Sarvam TTS REST API."""

    def __init__(self, *, tts, input_text, opts, api_key, session_factory, conn_options):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._opts = opts
        self._api_key = api_key
        self._session_factory = session_factory

    async def _run(self, output_emitter) -> None:
        request_id = str(uuid.uuid4())
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=self._opts.speech_sample_rate,
            num_channels=1,
            mime_type="audio/pcm",
        )

        session = self._session_factory()
        text = self.input_text.strip()
        if not text:
            return

        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": self._api_key,
        }

        payload = {
            "text": text,
            "target_language_code": _resolve_tts_language(self._opts.target_language_code),
            "speaker": self._opts.speaker,
            "model": self._opts.model,
            "pace": self._opts.pace,
            "speech_sample_rate": self._opts.speech_sample_rate,
            "enable_preprocessing": self._opts.enable_preprocessing,
        }

        async with session.post(SARVAM_TTS_URL, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.error("Sarvam TTS error (%d): %s", resp.status, error_text)
                from livekit.agents._exceptions import APIError
                raise APIError(f"Sarvam TTS returned {resp.status}: {error_text}")

            data = await resp.json()
            audio_b64 = data.get("audios", [None])[0]

            if not audio_b64:
                from livekit.agents._exceptions import APIError
                raise APIError("No audio in Sarvam TTS response")

            audio_bytes = base64.b64decode(audio_b64)

            # Extract raw PCM from WAV
            if audio_bytes[:4] == b"RIFF":
                buf = io.BytesIO(audio_bytes)
                with wave.open(buf, "rb") as wf:
                    pcm = wf.readframes(wf.getnframes())
                    logger.debug(
                        "TTS: %d bytes PCM, %.2fs audio",
                        len(pcm),
                        wf.getnframes() / wf.getframerate(),
                    )
                    output_emitter.push(pcm)
            else:
                output_emitter.push(audio_bytes)


def _resolve_tts_language(language_code: str) -> str:
    """Map language codes to valid Sarvam TTS language codes."""
    mapping = {
        "hi-IN": "hi-IN",
        "en-IN": "en-IN",
        "mr-IN": "mr-IN",
        "hi-EN": "hi-IN",
        "unknown": "hi-IN",
    }
    return mapping.get(language_code, "hi-IN")
