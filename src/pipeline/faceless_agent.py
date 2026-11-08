import time
import re
import concurrent.futures
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

from ..config import config
from ..llm.client import OpenRouterClient
from ..llm.prompts import ScriptPayload
from ..voice.tts import TTSEngine, TTSResult
from ..visuals.pexels import PexelsVisualFetcher, VideoClipAsset
from ..subtitles.whisper_stt import WhisperTranscriber
from ..subtitles.ass_builder import ASSSubtitleBuilder, WordTimestamp
from ..compositor.ffmpeg_engine import FFmpegEngine
from ..compositor.audio_mixer import AudioMixer


@dataclass
class GenerationResult:
    topic: str
    title: str
    video_path: Path
    duration_seconds: float
    script: ScriptPayload
    tts_result: TTSResult
    ass_subtitle_path: Path
    metadata_path: Optional[Path] = None


class FacelessShortsAgent:
    def __init__(
        self,
        openrouter_client: Optional[OpenRouterClient] = None,
        tts_engine: Optional[TTSEngine] = None,
        visual_fetcher: Optional[PexelsVisualFetcher] = None,
        whisper_transcriber: Optional[WhisperTranscriber] = None,
        ass_builder: Optional[ASSSubtitleBuilder] = None,
        ffmpeg_engine: Optional[FFmpegEngine] = None,
        audio_mixer: Optional[AudioMixer] = None,
    ):
        self.llm = openrouter_client or OpenRouterClient()
        self.tts = tts_engine or TTSEngine()
        self.visuals = visual_fetcher or PexelsVisualFetcher()
        self.whisper = whisper_transcriber or WhisperTranscriber()
        self.ass_builder = ass_builder or ASSSubtitleBuilder()
        self.ffmpeg = ffmpeg_engine or FFmpegEngine()
        self.audio_mixer = audio_mixer or AudioMixer(self.ffmpeg)

    def _slugify(self, text: str) -> str:
        """Convert topic or title to clean filename string."""
        text = re.sub(r"[^\w\s-]", "", text).strip().lower()
        return re.sub(r"[-\s]+", "_", text)[:40]

    def _save_social_metadata(
        self, script: ScriptPayload, output_path: Path
    ) -> Path:
        """Generate ready-to-copy social media title, description, and hashtags."""
        clean_title = script.title
        tags = [
            "#shorts", "#viral", "#interesting", "#facts", "#learn",
            "#educational", "#didyouknow", "#mindblowing"
        ]
        topic_words = re.findall(r"\w+", script.title.lower())
        for w in topic_words[:3]:
            if len(w) > 3:
                tags.append(f"#{w}")

        content = f"""=== YOUTUBE SHORTS / INSTAGRAM REELS METADATA ===

TITLE:
{clean_title}

HOOK (First 3 Seconds):
"{script.hook}"

DESCRIPTION:
{script.hook}
Watch till the end to see the full breakdown!

HASHTAGS:
{' '.join(tags)}

PINNED COMMENT (High Engagement Driver):
What do you think about this? Let us know in the comments below! 👇
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    def create_short(
        self,
        topic: str,
        custom_voice: Optional[str] = None,
        custom_bgm: Optional[Path] = None,
        log_callback=print,
    ) -> GenerationResult:
        """Run the end-to-end Mode 1 automated generation pipeline with multi-threading."""
        start_time = time.time()
        log_callback(f"\n=======================================================")
        log_callback(f"[START] AI Shorts Generator (Mode 1: Faceless Narrative)")
        log_callback(f"[TOPIC] {topic}")
        log_callback(f"=======================================================")

        # Reset visual deduplication pool for this generation session
        self.visuals.reset_session()

        # Step 1: Script Generation
        log_callback("\n[1/5] Generating viral script via OpenRouter (meta/muse-spark-1.3-contributor)...")
        script = self.llm.generate_script(topic)
        log_callback(f"  * Title: {script.title}")
        log_callback(f"  * Hook:  {script.hook}")
        log_callback(f"  * Total Cuts/Scenes: {len(script.scenes)}")

        # Step 2: Voiceover Synthesis
        log_callback("\n[2/5] Synthesizing neural voiceover via edge-tts...")
        if custom_voice:
            self.tts.voice = custom_voice
        tts_filename = f"voice_{self._slugify(topic)}.mp3"
        tts_result = self.tts.synthesize(
            text=script.full_narration,
            output_filename=tts_filename,
            target_duration=config.target_video_duration,
        )
        total_duration = tts_result.duration_seconds
        log_callback(f"  * Audio generated: {tts_result.audio_path.name}")
        log_callback(f"  * Duration: {total_duration:.2f} seconds")

        # Step 3: Parallel Visual Assets Sourcing & Normalization
        log_callback("\n[3/5] Sourcing & formatting 9:16 vertical visual clips in PARALLEL...")
        total_words = max(1, sum(len(s.narration.split()) for s in script.scenes))
        scene_jobs = []
        scene_durations: List[float] = []
        transition_duration = 0.20

        for i, scene in enumerate(script.scenes):
            scene_words = len(scene.narration.split())
            base_duration = max(2.5, (scene_words / total_words) * total_duration)
            scene_durations.append(base_duration)
            # Add padding for xfade overlap on all clips except the last one
            prep_duration = base_duration + (transition_duration if i < len(script.scenes) - 1 else 0.0)
            scene_jobs.append((scene, prep_duration))

        def process_single_scene(job):
            scene, duration = job
            clip_asset = self.visuals.fetch_clip_for_scene(
                scene_id=scene.scene_id,
                keywords=scene.visual_keywords,
                duration=duration,
            )
            norm_output = config.temp_dir / f"norm_scene_{scene.scene_id}.mp4"
            self.ffmpeg.prepare_clip(
                input_path=clip_asset.file_path,
                output_path=norm_output,
                duration=duration,
                width=config.video_width,
                height=config.video_height,
                fps=config.video_fps,
            )
            return scene.scene_id, norm_output, clip_asset

        # Run parallel workers (max 4 concurrent)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            processed_results = list(executor.map(process_single_scene, scene_jobs))

        # Sort back into scene order
        processed_results.sort(key=lambda x: x[0])
        normalized_clips = []
        for sid, norm_path, asset in processed_results:
            log_callback(f"  * Cut {sid}: Keyword '{asset.keyword}' -> {asset.file_path.name}")
            normalized_clips.append(norm_path)

        # Calculate exact cut timestamps for whoosh SFX
        cum_cut = 0.0
        cut_timestamps = []
        for d in scene_durations[:-1]:
            cum_cut += d
            cut_timestamps.append(cum_cut)

        # Concatenate video clips with seamless transitions
        log_callback("  * Concatenating visual sequence with seamless crossfade transitions...")
        concat_video = config.temp_dir / "concatenated_raw.mp4"
        self.ffmpeg.concat_clips(
            clip_paths=normalized_clips,
            output_path=concat_video,
            scene_durations=scene_durations,
            transition="fade",
            transition_duration=transition_duration,
        )
        log_callback(f"  * Visual timeline ready: {concat_video.name}")

        # Step 4: Word-Level Subtitle Alignment & ASS Compilation
        log_callback("\n[4/5] Transcribing words & generating dynamic Hormozi subtitles (with 3D Color Emojis)...")
        words: List[WordTimestamp] = self.whisper.transcribe_words(tts_result.audio_path)
        log_callback(f"  * Transcribed {len(words)} individual words with precise timing.")

        ass_file = config.temp_dir / f"subtitles_{self._slugify(topic)}.ass"
        ass_file, emoji_events = self.ass_builder.build_ass(words, ass_file)
        log_callback(f"  * Compiled ASS captions: {ass_file.name} ({len(emoji_events)} 3D color emoji triggers)")

        # Step 5: Audio Mixing & Master Render (Pop SFX removed per user request)
        log_callback("\n[5/5] Mixing audio ducking & transition whooshes...")
        master_audio = config.temp_dir / f"master_audio_{self._slugify(topic)}.m4a"
        self.audio_mixer.mix_voice_and_bgm(
            voice_audio=tts_result.audio_path,
            output_path=master_audio,
            bgm_path=custom_bgm,
            cut_timestamps=cut_timestamps,
            impact_timestamps=None,
            voice_volume=config.voice_volume,
            bgm_volume=config.bgm_volume,
        )

        base_slug = self._slugify(topic)
        timestamp_id = int(time.time())
        final_video_path = config.output_dir / f"{base_slug}_{timestamp_id}.mp4"
        metadata_file = config.output_dir / f"{base_slug}_{timestamp_id}_metadata.txt"

        self.ffmpeg.composite_final_short(
            concatenated_video=concat_video,
            master_audio=master_audio,
            ass_subtitles=ass_file,
            output_path=final_video_path,
            emoji_events=emoji_events,
            duration_limit=config.target_video_duration,
        )

        # Generate social metadata
        self._save_social_metadata(script, metadata_file)

        elapsed = time.time() - start_time
        log_callback(f"\n[DONE] Video successfully generated in {elapsed:.1f}s (Optimized)!")
        log_callback(f"[OUTPUT] Master Video: {final_video_path.resolve()}")
        log_callback(f"[OUTPUT] Metadata File: {metadata_file.resolve()}\n")

        return GenerationResult(
            topic=topic,
            title=script.title,
            video_path=final_video_path,
            duration_seconds=total_duration,
            script=script,
            tts_result=tts_result,
            ass_subtitle_path=ass_file,
            metadata_path=metadata_file,
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Shorts Faceless Video Generator")
    parser.add_argument(
        "--topic",
        type=str,
        default="The Bizarre Psychology of Why Supermarkets Have No Windows",
        help="Topic or premise for the short",
    )
    parser.add_argument("--voice", type=str, default=None, help="edge-tts voice name")
    args = parser.parse_args()

    agent = FacelessShortsAgent()
    agent.create_short(topic=args.topic, custom_voice=args.voice)
