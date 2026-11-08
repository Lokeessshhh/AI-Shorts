from pathlib import Path
from typing import List, Optional
from .ass_builder import WordTimestamp

# Compatibility shim for PyAV 19+ with faster-whisper
try:
    import av
    _orig_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception:
    pass


class WhisperTranscriber:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _get_model(self):
        """Lazy load Whisper model."""
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe_words(self, audio_path: Path) -> List[WordTimestamp]:
        """Extract word-level timestamps from audio track."""
        model = self._get_model()
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400),
        )

        word_timestamps: List[WordTimestamp] = []
        for segment in segments:
            if segment.words:
                for w in segment.words:
                    word_timestamps.append(
                        WordTimestamp(
                            word=w.word.strip(),
                            start=round(w.start, 2),
                            end=round(w.end, 2),
                        )
                    )
            else:
                # Fallback if alignment omitted words
                word_timestamps.append(
                    WordTimestamp(
                        word=segment.text.strip(),
                        start=round(segment.start, 2),
                        end=round(segment.end, 2),
                    )
                )

        return word_timestamps
