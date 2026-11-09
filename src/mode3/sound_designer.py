"""Mode 3: Sound Designer & Dual Voice TTS Synthesizer.
Synthesizes synchronized voices for both participants (Human User and ChatGPT AI),
procedural mechanical keyboard clicks, send whooshes, and AI completion chimes,
and mixes them into a broadcast-ready audio master track.
"""

import asyncio
import math
import struct
import wave
import random
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

import edge_tts
from ..config import config


class SoundDesigner:
    """Generates dual-character speech and procedural UI sound effects."""

    USER_VOICE = "en-US-ChristopherNeural"
    CHATGPT_VOICE = "en-US-AvaNeural"

    def __init__(self, sfx_dir: Optional[Path] = None):
        self.sfx_dir = sfx_dir or (config.root_dir / "temp" / "sfx")
        self.sfx_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = 44100
        self._ensure_base_sfx()

    def _ensure_base_sfx(self):
        """Generate procedural click, send whoosh, and chime if not present."""
        self.click_wav = self.sfx_dir / "key_click.wav"
        self.whoosh_wav = self.sfx_dir / "send_whoosh.wav"
        self.chime_wav = self.sfx_dir / "response_chime.wav"
        self.laugh_wav = self.sfx_dir / "sitcom_laugh.wav"
        self.boom_wav = self.sfx_dir / "vine_boom.wav"

        if not self.click_wav.exists():
            self._generate_click_sfx(self.click_wav)
        if not self.whoosh_wav.exists():
            self._generate_whoosh_sfx(self.whoosh_wav)
        if not self.chime_wav.exists():
            self._generate_chime_sfx(self.chime_wav)

    def _generate_click_sfx(self, path: Path):
        """Create a crisp mechanical key switch click (18ms)."""
        duration = 0.018
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.exp(-t * 280)
            noise = random.uniform(-1.0, 1.0)
            tone = math.sin(2 * math.pi * 1200 * t) * 0.4 + math.sin(2 * math.pi * 3200 * t) * 0.3
            val = (tone + noise * 0.3) * env * 0.35
            samples.append(int(max(-1.0, min(1.0, val)) * 32767))

        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    def _generate_whoosh_sfx(self, path: Path):
        """Create a smooth upward message send whoosh (140ms)."""
        duration = 0.14
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            progress = t / duration
            freq = 320 + 850 * progress
            env = math.sin(math.pi * progress)
            val = math.sin(2 * math.pi * freq * t) * env * 0.42
            samples.append(int(max(-1.0, min(1.0, val)) * 32767))

        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    def _generate_chime_sfx(self, path: Path):
        """Create a modern 2-tone pleasant AI completion chime (320ms)."""
        duration = 0.32
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            if t < 0.12:
                freq = 659.25  # E5
                env = math.exp(-t * 22)
            else:
                freq = 880.0   # A5
                env = math.exp(-(t - 0.12) * 16)
            tone = math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * freq * 2 * t)
            val = tone * env * 0.35
            samples.append(int(max(-1.0, min(1.0, val)) * 32767))

        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    def get_audio_duration(self, audio_path: Path) -> float:
        """Query precise duration using ffprobe."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", str(audio_path)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            return float(data["format"]["duration"])
        except Exception:
            # Fallback estimation
            return 3.0

    def synthesize_dialogue_speech(self, conversation: Dict[str, Any], temp_dir: Path) -> Dict[str, Any]:
        """
        Synthesize speech for both Human User (speaking while typing)
        and ChatGPT (speaking while streaming response).
        """
        temp_dir.mkdir(parents=True, exist_ok=True)
        turns = conversation.get("turns", [])

        async def _synth_turn(turn_idx: int, turn_data: Dict[str, Any]):
            speaker = turn_data.get("speaker", "user")
            text = turn_data.get("text", "")

            if speaker == "user":
                voice = self.USER_VOICE
                rate = "+12%"  # Energetic, natural speaking speed
            else:
                voice = self.CHATGPT_VOICE
                rate = "+8%"   # Crisp, clear AI voice

            mp3_path = temp_dir / f"speech_turn_{turn_idx}_{speaker}.mp3"
            wav_path = temp_dir / f"speech_turn_{turn_idx}_{speaker}.wav"

            comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
            await comm.save(str(mp3_path))

            # Convert to 44.1kHz mono WAV for high-fidelity mixing
            cmd = [
                "ffmpeg", "-y", "-v", "quiet",
                "-i", str(mp3_path),
                "-ar", str(self.sample_rate),
                "-ac", "1",
                str(wav_path)
            ]
            subprocess.run(cmd, check=True)

            dur = self.get_audio_duration(wav_path)
            turn_data["audio_path"] = str(wav_path)
            turn_data["audio_duration"] = dur

        async def _synth_all():
            tasks = [_synth_turn(idx, t) for idx, t in enumerate(turns)]
            await asyncio.gather(*tasks)

        asyncio.run(_synth_all())
        return conversation

    def _read_wav_samples(self, wav_path: Path) -> List[float]:
        """Read 16-bit PCM WAV into normalized float samples [-1.0, 1.0]."""
        with wave.open(str(wav_path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

            if sampwidth != 2:
                # Fallback via ffmpeg
                return []

            raw = struct.unpack(f"<{len(frames)//2}h", frames)
            # If stereo, take channel 0
            if n_channels == 2:
                raw = raw[0::2]
            return [s / 32768.0 for s in raw]

    def build_master_audio(
        self,
        conversation: Dict[str, Any],
        event_timeline: List[Dict[str, Any]],
        total_duration: float,
        output_wav: Path,
        bgm_path: Optional[Path] = None,
    ) -> Path:
        """
        Assemble a continuous synchronized master track containing:
        1. Human speech while typing
        2. Soft mechanical keyboard typing SFX
        3. Send message whoosh
        4. ChatGPT AI speech while token-streaming
        5. Completion chime
        6. Optional subtle background music
        """
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        total_samples = int(self.sample_rate * (total_duration + 0.8))
        mixed = [0.0] * total_samples

        def overlay(samples: List[float], start_time: float, gain: float = 1.0):
            idx = int(start_time * self.sample_rate)
            for i, s in enumerate(samples):
                dst = idx + i
                if dst < len(mixed):
                    mixed[dst] += s * gain

        # Pre-load base SFX
        click_samples = self._read_wav_samples(self.click_wav)
        whoosh_samples = self._read_wav_samples(self.whoosh_wav)
        chime_samples = self._read_wav_samples(self.chime_wav)
        laugh_samples = self._read_wav_samples(self.laugh_wav) if self.laugh_wav.exists() else []
        boom_samples = self._read_wav_samples(self.boom_wav) if self.boom_wav.exists() else []

        turns = conversation.get("turns", [])

        # 1. Overlay Speech from Turns
        for turn in turns:
            wav_path = turn.get("audio_path")
            speech_start = turn.get("speech_start_time")
            if wav_path and speech_start is not None and Path(wav_path).exists():
                speech_samples = self._read_wav_samples(Path(wav_path))
                overlay(speech_samples, speech_start, gain=1.10)

        # 2. Overlay Events (Typing clicks, Send whooshes, Chimes)
        for ev in event_timeline:
            ev_type = ev.get("type")
            t = ev.get("time", 0.0)

            if ev_type == "type_char":
                # Add subtle click sound for each typed character (subdued so voice is clear)
                click_gain = random.uniform(0.12, 0.22)
                overlay(click_samples, t, gain=click_gain)

            elif ev_type == "send_message":
                # Message sent whoosh
                overlay(whoosh_samples, t, gain=0.65)

            elif ev_type == "stream_end":
                # ChatGPT finished speaking chime
                overlay(chime_samples, t, gain=0.50)

            elif ev_type == "vine_boom":
                if boom_samples:
                    overlay(boom_samples, t, gain=0.85)

            elif ev_type == "laugh_track":
                if laugh_samples:
                    overlay(laugh_samples, t, gain=0.80)

        # 3. Optional Background Music (ambient ducked track)
        if bgm_path and Path(bgm_path).exists():
            bgm_wav = self.sfx_dir / "bgm_loop.wav"
            cmd = [
                "ffmpeg", "-y", "-v", "quiet",
                "-i", str(bgm_path),
                "-t", str(total_duration + 0.5),
                "-ar", str(self.sample_rate),
                "-ac", "1",
                str(bgm_wav)
            ]
            try:
                subprocess.run(cmd, check=True)
                bgm_samples = self._read_wav_samples(bgm_wav)
                overlay(bgm_samples, 0.0, gain=0.09)  # Soft background vibe
            except Exception:
                pass

        # 4. Master Limiter & Normalization
        max_val = max(max(abs(s) for s in mixed), 0.001)
        scale = 0.94 / max_val if max_val > 0.94 else 1.0

        int_samples = [int(max(-1.0, min(1.0, s * scale)) * 32767) for s in mixed]

        with wave.open(str(output_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(struct.pack(f"<{len(int_samples)}h", *int_samples))

        return output_wav

