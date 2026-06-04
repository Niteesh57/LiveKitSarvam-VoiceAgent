"""
Call Recording — Single-timeline mono recording of full conversation.

Records both agent and customer audio into ONE sequential mono buffer
in real-time order. The result sounds like listening to a natural phone
call — agent speaks, customer responds, back and forth.

Output: 48kHz, 16-bit, mono WAV.
"""

import asyncio
import array
import json
import logging
import time
import wave
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from livekit import rtc

from app.config.settings import settings

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
RECORDINGS_DIR = settings.data_dir / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2  # 16-bit PCM


class LocalCallRecorder:
    """
    Single-timeline conversation recorder.
    
    Both agent and customer audio go into ONE buffer in chronological order.
    The recording sounds like a natural phone conversation — alternating
    speakers as the call progresses.
    
    Uses time.monotonic() to place each audio chunk at the correct position
    in the timeline, so both voices are interleaved naturally.
    """

    def __init__(self, room_name: str, customer_phone: str):
        self._room_name = room_name
        self._customer_phone = customer_phone
        self._recording = False
        self._start_time: datetime | None = None
        self._start_mono: float = 0.0
        self._file_path: Path | None = None
        self._tasks: list[asyncio.Task] = []

        # Single timeline buffer: list of (start_sample_index, pcm_bytes)
        self._timeline: list[tuple[int, bytes]] = []
        self._lock = asyncio.Lock()

    @property
    def file_path(self) -> Path | None:
        return self._file_path

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self, room: rtc.Room) -> None:
        """Start recording."""
        self._recording = True
        self._start_time = datetime.now(IST)
        self._start_mono = time.monotonic()
        self._timeline = []

        # Capture remote tracks (customer)
        for participant in room.remote_participants.values():
            for pub in participant.track_publications.values():
                if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                    task = asyncio.create_task(
                        self._capture_customer(pub.track, participant.identity)
                    )
                    self._tasks.append(task)

        @room.on("track_subscribed")
        def _on_track_subscribed(track, publication, participant):
            if track.kind == rtc.TrackKind.KIND_AUDIO and self._recording:
                task = asyncio.create_task(
                    self._capture_customer(track, participant.identity)
                )
                self._tasks.append(task)

        logger.info("Recording started (mono timeline): %s", self._room_name)

    def _current_sample_pos(self) -> int:
        """Get current position in samples from recording start."""
        return int((time.monotonic() - self._start_mono) * SAMPLE_RATE)

    async def _capture_customer(self, track: rtc.Track, identity: str) -> None:
        """Capture customer audio into the shared timeline."""
        logger.debug("Recording customer: %s", identity)
        try:
            stream = rtc.AudioStream(
                track, sample_rate=SAMPLE_RATE, num_channels=1
            )
            async for event in stream:
                if not self._recording:
                    break
                if hasattr(event, "frame") and event.frame:
                    pos = self._current_sample_pos()
                    pcm = event.frame.data.tobytes()
                    async with self._lock:
                        self._timeline.append((pos, pcm))
        except Exception as e:
            logger.debug("Customer capture ended (%s): %s", identity, e)

    def add_agent_audio(self, pcm_data: bytes, source_rate: int = 24000) -> None:
        """
        Add agent TTS audio into the shared timeline at current time position.
        Upsamples from the TTS sample rate (24kHz) to the timeline rate (48kHz)
        so the agent voice plays at correct speed in the recording.
        """
        if not (self._recording and pcm_data):
            return
        # Upsample to 48kHz timeline if needed
        if source_rate != SAMPLE_RATE:
            pcm_data = _upsample_pcm(pcm_data, source_rate, SAMPLE_RATE)
        pos = self._current_sample_pos()
        self._timeline.append((pos, pcm_data))

    async def stop(self) -> str | None:
        """Stop recording, render timeline to mono WAV."""
        self._recording = False

        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        await asyncio.sleep(0.2)

        if not self._timeline:
            logger.warning("No audio captured for room: %s", self._room_name)
            return None

        logger.info("Rendering %d audio segments to timeline", len(self._timeline))

        # Generate filename
        ts = self._start_time.strftime("%Y%m%d_%H%M%S") if self._start_time else "unknown"
        phone = self._customer_phone.replace("+", "").replace(" ", "")
        filename = f"call_{phone}_{ts}.wav"
        self._file_path = RECORDINGS_DIR / filename

        try:
            # Find total duration
            max_end = 0
            for pos, pcm in self._timeline:
                end = pos + len(pcm) // SAMPLE_WIDTH
                if end > max_end:
                    max_end = end

            total_samples = max_end
            duration_seconds = total_samples / SAMPLE_RATE

            # Render all segments into a single mono buffer
            # Use int32 accumulator to handle overlaps without clipping
            accum = [0] * total_samples

            for pos, pcm in self._timeline:
                samples = array.array("h")
                samples.frombytes(pcm)
                for i, sample in enumerate(samples):
                    idx = pos + i
                    if idx < total_samples:
                        accum[idx] += sample

            # Convert to int16 with clipping
            output = array.array("h")
            for val in accum:
                output.append(max(-32768, min(32767, val)))

            # Normalize to -3 dB
            output = _normalize(output)

            # Write mono WAV
            with wave.open(str(self._file_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(output.tobytes())

            file_size_mb = self._file_path.stat().st_size / (1024 * 1024)
            logger.info(
                "Recording saved: %s (%.1fs, %.1f MB, mono 48kHz)",
                self._file_path.name, duration_seconds, file_size_mb,
            )

            self._save_metadata(duration_seconds)
            self._timeline.clear()

            return str(self._file_path)

        except Exception as e:
            logger.error("Failed to save recording: %s", e)
            return None

    def _save_metadata(self, duration: float) -> None:
        metadata = {
            "room_name": self._room_name,
            "customer_phone": self._customer_phone,
            "file_path": str(self._file_path),
            "filename": self._file_path.name if self._file_path else "",
            "duration_seconds": round(duration, 1),
            "recorded_at": self._start_time.isoformat() if self._start_time else "",
            "sample_rate": SAMPLE_RATE,
            "channels": 1,
            "format": "mono (agent+customer interleaved timeline)",
            "bit_depth": 16,
        }

        meta_file = settings.data_dir / "recordings_meta.json"
        existing = []
        if meta_file.exists():
            try:
                existing = json.loads(meta_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.append(metadata)
        meta_file.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def _upsample_pcm(pcm_data: bytes, src_rate: int, dst_rate: int) -> bytes:
    """
    Upsample 16-bit mono PCM from src_rate to dst_rate using linear interpolation.
    Used to convert 24kHz agent TTS audio to the 48kHz recording timeline.
    """
    if src_rate == dst_rate or not pcm_data:
        return pcm_data

    src = array.array("h")
    src.frombytes(pcm_data if len(pcm_data) % 2 == 0 else pcm_data[:-1])
    if len(src) == 0:
        return pcm_data

    ratio = dst_rate / src_rate
    out_len = int(len(src) * ratio)
    out = array.array("h", [0]) * out_len

    for i in range(out_len):
        src_pos = i / ratio
        idx = int(src_pos)
        frac = src_pos - idx
        if idx + 1 < len(src):
            val = src[idx] * (1 - frac) + src[idx + 1] * frac
        else:
            val = src[idx]
        out[i] = max(-32768, min(32767, int(val)))

    return out.tobytes()


def _normalize(samples: array.array) -> array.array:
    """Normalize to -3 dB peak."""
    if not samples:
        return samples

    peak = max(abs(s) for s in samples)
    if peak < 100:
        return samples

    target = 23197  # -3 dB
    gain = target / peak
    gain = min(gain, 4.0)

    if 0.95 <= gain <= 1.05:
        return samples

    result = array.array("h")
    for s in samples:
        result.append(max(-32768, min(32767, int(s * gain))))
    return result


def get_recordings() -> list[dict]:
    """Get all recording metadata."""
    meta_file = settings.data_dir / "recordings_meta.json"
    if meta_file.exists():
        try:
            return json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    recordings = []
    if RECORDINGS_DIR.exists():
        for wav_file in sorted(RECORDINGS_DIR.glob("*.wav")):
            recordings.append({
                "filename": wav_file.name,
                "file_path": str(wav_file),
                "size_bytes": wav_file.stat().st_size,
            })
    return recordings
