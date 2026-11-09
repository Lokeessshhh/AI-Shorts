"""Mode 3 Long-Form Audio Transcriber.
Uses faster-whisper with word-level timestamps, formats structured sentence chunks,
and caches transcripts to avoid redundant speech-to-text processing.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from faster_whisper import WhisperModel


class LongFormTranscriber:
    """Fast speech-to-text transcriber tailored for long-form video highlight extraction."""

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            print(f"[Clipper] Loading faster-whisper model ({self.model_size}, {self.device}, {self.compute_type})...")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        cache_json_path: Optional[Path] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe audio file into word-level timestamps and formatted chunks.
        """
        # Check cache
        if cache_json_path and cache_json_path.exists():
            try:
                with open(cache_json_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if "segments" in cached and "words" in cached:
                    print(f"[Clipper] Loaded transcript from cache: {cache_json_path.name}")
                    return cached
            except Exception as e:
                print(f"[Clipper] Warning: Could not read cached transcript ({e}), re-transcribing...")

        # Fast path: Check for YouTube json3 captions downloaded alongside video
        if audio_path.parent.exists():
            json3_candidates = sorted(
                audio_path.parent.glob("*.json3"),
                key=lambda p: (0 if ".en.json3" in p.name else 1 if "en-orig" in p.name else 2)
            )
            for jc in json3_candidates:
                try:
                    parsed_captions = self._parse_youtube_json3(jc)
                    if parsed_captions and parsed_captions.get("words"):
                        print(f"[Clipper] Loaded word timestamps from YouTube captions: {jc.name}")
                        if cache_json_path:
                            cache_json_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(cache_json_path, "w", encoding="utf-8") as f:
                                json.dump(parsed_captions, f, indent=2, ensure_ascii=False)
                        return parsed_captions
                except Exception as e:
                    print(f"[Clipper] Could not parse YouTube json3 {jc.name} ({e}), trying next...")

        model = self._get_model()
        print(f"[Clipper] Transcribing audio with word timestamps ({audio_path.name})...")

        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400),
        )

        all_words: List[Dict[str, Any]] = []
        segments: List[Dict[str, Any]] = []
        formatted_blocks: List[str] = []

        for seg in segments_iter:
            seg_words = []
            if seg.words:
                for w in seg.words:
                    word_obj = {
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 3),
                    }
                    seg_words.append(word_obj)
                    all_words.append(word_obj)

            segment_data = {
                "id": seg.id,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": seg_words,
            }
            segments.append(segment_data)

            # Format formatted block: [MM:SS - MM:SS] Text
            m_s = int(seg.start // 60)
            s_s = int(seg.start % 60)
            m_e = int(seg.end // 60)
            s_e = int(seg.end % 60)
            formatted_blocks.append(
                f"[{m_s:02d}:{s_s:02d} - {m_e:02d}:{s_e:02d}] ({seg.start:.1f}s - {seg.end:.1f}s) {seg.text.strip()}"
            )

        result = {
            "language": info.language,
            "duration": round(info.duration, 2),
            "total_words": len(all_words),
            "segments": segments,
            "words": all_words,
            "formatted_transcript": "\n".join(formatted_blocks),
        }

        # Cache result
        if cache_json_path:
            cache_json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"[Clipper] Saved transcript cache -> {cache_json_path.name}")

        return result

    def _parse_youtube_json3(self, json3_path: Path) -> Dict[str, Any]:
        """Parse YouTube json3 format into word timestamps and segments."""
        with open(json3_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        events = data.get("events", [])
        all_words: List[Dict[str, Any]] = []
        segments: List[Dict[str, Any]] = []
        formatted_blocks: List[str] = []
        seg_id = 0

        for e in events:
            tStart = e.get("tStartMs", 0) / 1000.0
            dDur = e.get("dDurationMs", 0) / 1000.0
            segs = e.get("segs", [])
            if not segs:
                continue

            seg_text = "".join(s.get("utf8", "") for s in segs).strip()
            if not seg_text or seg_text == "\n":
                continue

            seg_words = []
            for s in segs:
                w_text = s.get("utf8", "").strip()
                if not w_text:
                    continue
                offset = s.get("tOffsetMs", 0) / 1000.0 if s.get("tOffsetMs") is not None else 0.0
                w_start = round(tStart + offset, 3)
                w_end = round(min(tStart + dDur, w_start + 0.35), 3)
                word_obj = {
                    "word": w_text,
                    "start": w_start,
                    "end": max(round(w_start + 0.1, 3), w_end),
                    "probability": 0.99,
                }
                seg_words.append(word_obj)
                all_words.append(word_obj)

            if seg_words:
                segments.append({
                    "id": seg_id,
                    "start": round(tStart, 3),
                    "end": round(tStart + dDur, 3),
                    "text": seg_text,
                    "words": seg_words,
                })
                m_s, s_s = int(tStart // 60), int(tStart % 60)
                m_e, s_e = int((tStart + dDur) // 60), int((tStart + dDur) % 60)
                formatted_blocks.append(
                    f"[{m_s:02d}:{s_s:02d} - {m_e:02d}:{s_e:02d}] ({tStart:.1f}s - {tStart+dDur:.1f}s) {seg_text}"
                )
                seg_id += 1

        total_dur = all_words[-1]["end"] if all_words else 0.0
        return {
            "language": "en",
            "duration": round(total_dur, 2),
            "total_words": len(all_words),
            "segments": segments,
            "words": all_words,
            "formatted_transcript": "\n".join(formatted_blocks),
        }
