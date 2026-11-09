import time
import re
import concurrent.futures
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from ..config import config
from ..llm.client import OpenRouterClient
from ..llm.prompts import ScriptPayload
from ..voice.tts import TTSEngine, TTSResult
from ..visuals.visual_director import ContextVisualDirector
from ..subtitles.whisper_stt import WhisperTranscriber
from ..subtitles.ass_builder import ASSSubtitleBuilder, WordTimestamp
from ..compositor.ffmpeg_engine import FFmpegEngine
from ..compositor.audio_mixer import AudioMixer
from ..compositor.music_director import MusicDirector, AudioScorePlan
from .topic_evaluator import TopicEvaluator, TopicEvaluation


@dataclass
class GenerationResult:
    topic: str
    title: str
    video_path: Path
    duration_seconds: float
    script: ScriptPayload
    tts_result: TTSResult
    ass_subtitle_path: Path
    evaluation: Optional[TopicEvaluation] = None
    metadata_path: Optional[Path] = None
    score_plan: Optional[AudioScorePlan] = None


class FacelessShortsAgent:
    def __init__(
        self,
        openrouter_client: Optional[OpenRouterClient] = None,
        tts_engine: Optional[TTSEngine] = None,
        visual_director: Optional[ContextVisualDirector] = None,
        whisper_transcriber: Optional[WhisperTranscriber] = None,
        ass_builder: Optional[ASSSubtitleBuilder] = None,
        ffmpeg_engine: Optional[FFmpegEngine] = None,
        audio_mixer: Optional[AudioMixer] = None,
        music_director: Optional[MusicDirector] = None,
        topic_evaluator: Optional[TopicEvaluator] = None,
    ):
        self.llm = openrouter_client or OpenRouterClient()
        self.tts = tts_engine or TTSEngine()
        self.visuals = visual_director or ContextVisualDirector()
        self.whisper = whisper_transcriber or WhisperTranscriber()
        self.ass_builder = ass_builder or ASSSubtitleBuilder()
        self.ffmpeg = ffmpeg_engine or FFmpegEngine()
        self.audio_mixer = audio_mixer or AudioMixer(self.ffmpeg)
        self.music_director = music_director or MusicDirector(self.llm)
        self.evaluator = topic_evaluator or TopicEvaluator(self.llm)

    def _slugify(self, text: str) -> str:
        """Convert topic or title to clean filename string."""
        text = re.sub(r"[^\w\s-]", "", text).strip().lower()
        return re.sub(r"[-\s]+", "_", text)[:40]

    def _save_social_metadata(
        self,
        script: ScriptPayload,
        output_path: Path,
        evaluation: Optional[TopicEvaluation] = None,
        attributions: Optional[List[Dict[str, str]]] = None,
        verification_audit: Optional[List[Dict[str, Any]]] = None,
        pacing_metrics: Optional[Dict[str, Any]] = None,
        score_plan: Optional[AudioScorePlan] = None,
    ) -> Path:
        """Generate ready-to-copy social media title, description, and hashtags."""
        clean_title = script.title
        tags = [
            "#shorts", "#viral", "#psychology", "#facts", "#learn",
            "#educational", "#mindblowing", "#reels", "#fyp"
        ]
        topic_words = re.findall(r"\w+", script.title.lower())
        for w in topic_words[:3]:
            if len(w) > 3:
                tags.append(f"#{w}")

        score_info = f"TOPIC EVALUATION SCORE: {evaluation.total_score}/100" if evaluation else ""

        audio_lines = []
        if score_plan:
            audio_lines.append("\n=== DYNAMIC AUDIO SCORE & SOUNDTRACK DIRECTION ===")
            audio_lines.append(f"- Selected Soundtrack: {score_plan.track_title}")
            audio_lines.append(f"- Genre & Mood: {score_plan.genre} | {score_plan.mood}")
            audio_lines.append(f"- Score Rationale: {score_plan.score_rationale}")
            audio_lines.append(f"- Base Volume: {score_plan.base_bgm_volume:.2f} (EQ Carve: {score_plan.eq_carve_gain}dB @ {score_plan.eq_carve_freq}Hz)")
            audio_lines.append(f"- Dynamic Volume Keyframes: {len(score_plan.volume_keyframes)} points along narrative arc")
            audio_lines.append(f"- Narrative J-Cut SFX Cues: {len(score_plan.sfx_cues)} context-aware transitions")

        pacing_lines = []
        if pacing_metrics:
            pacing_lines.append("\n=== PACING & 80/20 VISUAL METRICS ===")
            pacing_lines.append(f"- Total Visual Cuts: {pacing_metrics.get('total_shots')} rapid shots")
            pacing_lines.append(f"- Average Shot Duration: {pacing_metrics.get('avg_shot_dur', 0):.2f}s per cut")
            pacing_lines.append(f"- Real Visual Media Ratio: {pacing_metrics.get('media_pct', 0):.1f}% ({pacing_metrics.get('media_dur', 0):.1f}s)")
            pacing_lines.append(f"- Dynamic Diagram Ratio: {pacing_metrics.get('diag_pct', 0):.1f}% ({pacing_metrics.get('diag_dur', 0):.1f}s)")
            pacing_lines.append("- Design Theme: Bright Editorial Studio (Off-White/Cream, High-Contrast Mobile Typography)")

        attrib_lines = []
        if attributions:
            attrib_lines.append("\n=== MEDIA ATTRIBUTIONS & LICENSING ===")
            for a in attributions:
                attrib_lines.append(f"- Cut {a.get('scene_id')}: {a.get('source')} | {a.get('attribution', 'Public')} | Score: {a.get('score')}")

        audit_lines = []
        if verification_audit:
            audit_lines.append("\n=== MUSE SPARK 1.3 VISUAL VERIFICATION AUDIT ===")
            for v in verification_audit:
                audit_lines.append(f"- Cut {v.get('scene_id')}: [{v.get('status')}] {v.get('selected_source')} (Score: {v.get('score')}/100) -> {v.get('reason')}")

        content = f"""=== YOUTUBE SHORTS / INSTAGRAM REELS AUDIENCE-FIRST METADATA ===
{score_info}
TITLE:
{clean_title}

TRIPLE-STACK HOOK:
- Text Hook (0-2s): "{script.text_hook}"
- Spoken Hook: "{script.hook}"
- Visual Hook: {script.visual_hook}

FORMAT:
{script.format_type.upper()}

DESCRIPTION:
{script.hook}
{evaluation.angle if evaluation else ''}

HASHTAGS:
{' '.join(tags)}

PINNED ENGAGEMENT QUESTION:
What would you do in this situation? Let us know below! 👇
{chr(10).join(audio_lines)}
{chr(10).join(pacing_lines)}
{chr(10).join(attrib_lines)}
{chr(10).join(audit_lines)}
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    def create_short(
        self,
        topic: Optional[str] = None,
        custom_voice: Optional[str] = None,
        custom_bgm: Optional[Path] = None,
        format_type: Optional[str] = None,
        angle: Optional[str] = None,
        skip_evaluation: bool = False,
        target_duration: float = 34.0,
        explicit_output_path: Optional[Path] = None,
        log_callback=print,
    ) -> GenerationResult:
        """Run the end-to-end Mode 1 automated generation pipeline with audience-first evaluation."""
        start_time = time.time()

        # Step 0: Autonomous Topic Discovery or 100-Point Topic Evaluation Gate
        evaluation: Optional[TopicEvaluation] = None
        if not topic:
            log_callback(f"\n=======================================================")
            log_callback(f"[START] Autonomous Audience-Driven AI Shorts Generator")
            log_callback(f"[TOPIC] (Auto-Discovery Mode Active)")
            log_callback(f"=======================================================")
            log_callback("\n[0/5] Brainstorming and evaluating candidates against 100-Point Audience Retention Rubric...")
            evaluation = self.evaluator.discover_and_select_best_topic()
            topic = evaluation.topic
            format_type = evaluation.format_type
            angle = evaluation.angle
            log_callback(f"  * Selected Winner: '{topic}'")
            log_callback(f"  * Audience Angle:  '{angle}'")
            log_callback(f"  * Total Score:     {evaluation.total_score}/100 | Format: {format_type}")
        else:
            log_callback(f"\n=======================================================")
            log_callback(f"[START] Audience-Driven AI Shorts Generator (Mode 1)")
            log_callback(f"[TOPIC] {topic}")
            log_callback(f"=======================================================")
            if not skip_evaluation:
                log_callback("\n[0/5] Evaluating topic candidate against 100-Point Audience Retention Rubric...")
                evaluation = self.evaluator.evaluate(topic)
                log_callback(f"  * Total Score: {evaluation.total_score}/100")
                for crit_key, crit in evaluation.criteria_breakdown.items():
                    log_callback(f"    - {crit.name}: {crit.score}/{crit.max_score} ({crit.feedback[:60]}...)")

                if not evaluation.approved:
                    reasons_str = "; ".join(evaluation.rejection_reasons)
                    log_callback(f"\n[REJECTED] Topic failed audience-first quality gate: {reasons_str}")
                    raise ValueError(f"Topic rejected by quality gate (Score {evaluation.total_score}/100): {reasons_str}")

                log_callback(f"  * APPROVED! Recommended Format: {evaluation.format_type}")
                if not format_type:
                    format_type = evaluation.format_type
                if not angle:
                    angle = evaluation.angle

        active_format = format_type or "counter_intuitive_truth"
        active_angle = angle or topic

        # Reset visual deduplication pool for this generation session
        self.visuals.reset_session()

        # Step 1: Viral Script Generation with Triple Stack Hook
        log_callback(f"\n[1/5] Generating viral script via OpenRouter (Format: {active_format})...")
        script = self.llm.generate_script(
            topic=topic,
            format_type=active_format,
            angle=active_angle,
        )
        log_callback(f"  * Title:      {script.title}")
        log_callback(f"  * Text Hook:  '{script.text_hook}' (Frames 0-2s)")
        log_callback(f"  * Spoken Hook:'{script.hook}'")
        log_callback(f"  * Cuts:       {len(script.scenes)} narrative scenes")

        # Step 2: Voiceover Synthesis with Studio Mastering
        log_callback("\n[2/5] Synthesizing natural conversational voiceover via edge-tts...")
        if custom_voice:
            self.tts.voice = custom_voice
        tts_filename = f"voice_{self._slugify(topic)}.mp3"
        tts_result = self.tts.synthesize(
            text=script.full_narration,
            output_filename=tts_filename,
            target_duration=target_duration,
        )
        total_duration = tts_result.duration_seconds
        log_callback(f"  * Audio Master: {tts_result.audio_path.name}")
        log_callback(f"  * Duration:     {total_duration:.2f} seconds")

        # Step 3: Context-Aware Visual Sourcing (Semantic Video + Graphic Cards)
        log_callback("\n[3/5] Directing & formatting context-aware 9:16 visuals in parallel...")
        total_words = max(1, sum(len(s.narration.split()) for s in script.scenes))
        scene_jobs = []
        scene_durations: List[float] = []
        transition_duration = 0.20

        slug = self._slugify(topic)
        video_temp_dir = config.temp_dir / slug
        video_temp_dir.mkdir(parents=True, exist_ok=True)

        # Ensure Scene 1 is NEVER a diagram (must be image-first real visual media)
        if script.scenes and script.scenes[0].visual_intent:
            script.scenes[0].visual_intent.preferred_modality = "archival_photo"
            script.scenes[0].visual_type = "video"

        # Cap diagram scenes at maximum 1 (only when genuinely requested by LLM; never forced)
        diagram_count = 0
        for s in script.scenes:
            is_diag = (s.visual_intent and (s.visual_intent.preferred_modality == "diagram_card" or s.visual_intent.visual_spec)) or s.visual_type == "graphic_card"
            if is_diag:
                if diagram_count == 0 and s.scene_id > 1:
                    diagram_count += 1
                else:
                    if s.visual_intent:
                        s.visual_intent.preferred_modality = "archival_photo"
                        s.visual_intent.diagram_type = None
                        s.visual_intent.visual_spec = None
                    s.visual_type = "video"

        scene_timelines: List[Dict[str, Any]] = []
        cum_scene_t = 0.0
        for i, scene in enumerate(script.scenes):
            scene_words = len(scene.narration.split())
            base_duration = max(2.2, (scene_words / total_words) * total_duration)
            scene_durations.append(base_duration)
            scene_timelines.append({
                "scene_id": scene.scene_id,
                "start_time": cum_scene_t,
                "end_time": cum_scene_t + base_duration,
                "narration": scene.narration,
            })
            cum_scene_t += base_duration
            prep_duration = base_duration + (transition_duration if i < len(script.scenes) - 1 else 0.0)
            scene_jobs.append((scene, prep_duration))

        def process_single_scene(job):
            scene, duration = job
            shots_data = self.visuals.fetch_scene_visual_shots(
                scene_id=scene.scene_id,
                narration=scene.narration,
                keywords=scene.visual_keywords,
                duration=duration,
                visual_intent=scene.visual_intent,
                visual_type=scene.visual_type,
                concept_query=scene.concept_query,
                work_dir=video_temp_dir,
            )
            sub_shot_clips = []
            motion_choice = getattr(scene, "camera_motion", None) or "push_in_focus"
            focus_choice = getattr(scene, "subject_focus", None) or "upper_third"

            for sub_idx, (shot_file, sub_dur, shot_kind, src_name) in enumerate(shots_data):
                norm_out = video_temp_dir / f"norm_shot_{scene.scene_id}_{sub_idx + 1}.mp4"
                if sub_idx == 1:
                    sub_motion = "pull_out_reveal" if motion_choice == "push_in_focus" else "subtle_drift"
                else:
                    sub_motion = motion_choice

                self.ffmpeg.prepare_clip(
                    input_path=shot_file,
                    output_path=norm_out,
                    duration=sub_dur,
                    width=config.video_width,
                    height=config.video_height,
                    fps=config.video_fps,
                    motion_type=sub_motion,
                    subject_focus=focus_choice,
                )
                sub_shot_clips.append((
                    scene.scene_id,
                    sub_idx + 1,
                    norm_out,
                    sub_dur,
                    shot_kind,
                    src_name,
                    shot_file.name
                ))
            return sub_shot_clips

        # Run parallel workers (max 4 concurrent)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            processed_results = list(executor.map(process_single_scene, scene_jobs))

        # Flatten in sequential scene order
        all_shots = []
        for scene_shots in processed_results:
            all_shots.extend(scene_shots)

        normalized_clips = []
        shot_durations = []
        for sid, subid, norm_path, sub_dur, kind, src_name, asset_name in all_shots:
            log_callback(f"  * Shot {sid}.{subid} ({sub_dur:.2f}s, {kind}): {asset_name} -> {norm_path.name}")
            normalized_clips.append(norm_path)
            shot_durations.append(sub_dur)

        # Calculate exact 80/20 Visual Metrics
        media_dur = sum(s[3] for s in all_shots if s[4] == "media")
        diag_dur = sum(s[3] for s in all_shots if s[4] == "diagram")
        tot_visual_dur = max(0.1, media_dur + diag_dur)
        media_pct = (media_dur / tot_visual_dur) * 100
        diag_pct = (diag_dur / tot_visual_dur) * 100
        avg_shot_dur = tot_visual_dur / max(1, len(all_shots))

        log_callback(f"\n[PACING METRICS]")
        log_callback(f"  * Total Visual Cuts:   {len(all_shots)} shots")
        log_callback(f"  * Average Shot Length: {avg_shot_dur:.2f} seconds")
        log_callback(f"  * Visual Ratio:        {media_pct:.1f}% Real Media / {diag_pct:.1f}% Dynamic Graphics")

        # Calculate exact cut timestamps for whoosh SFX
        cum_cut = 0.0
        cut_timestamps = []
        for d in shot_durations[:-1]:
            cum_cut += d
            cut_timestamps.append(cum_cut)

        # Concatenate video clips with seamless transitions
        log_callback("\n  * Concatenating visual sequence with seamless crossfade transitions...")
        concat_video = video_temp_dir / f"concat_{slug}.mp4"
        self.ffmpeg.concat_clips(
            clip_paths=normalized_clips,
            output_path=concat_video,
            scene_durations=shot_durations,
            transition="fade",
            transition_duration=transition_duration,
        )

        # Step 4: Word-Level Subtitle Alignment & Kinetic ASS Compilation with Pop Physics
        log_callback("\n[4/5] Transcribing words & generating kinetic typography subtitles with pop physics...")
        words: List[WordTimestamp] = self.whisper.transcribe_words(tts_result.audio_path)
        log_callback(f"  * Transcribed {len(words)} individual words with precise timing.")

        all_emphasis = []
        for s in script.scenes:
            if hasattr(s, "emphasis_words") and s.emphasis_words:
                all_emphasis.extend(s.emphasis_words)

        ass_file = video_temp_dir / f"subtitles_{slug}.ass"
        ass_file, emoji_events = self.ass_builder.build_ass(
            words=words,
            output_path=ass_file,
            header_hook=script.text_hook,
            emphasis_keywords=all_emphasis,
        )
        log_callback(f"  * Compiled kinetic ASS captions: {ass_file.name} (Text Hook: '{script.text_hook}', {len(all_emphasis)} emphasis words)")

        # Step 5: Dynamic Story-Aware Audio Direction & Master Audio Mix
        log_callback("\n[5/5] AI Music Director: Selecting video-aware soundtrack & composing dynamic score...")
        score_plan = self.music_director.select_and_score(
            script=script,
            scene_timelines=scene_timelines,
            total_duration=total_duration,
            topic=topic or script.title,
            custom_bgm_path=custom_bgm,
        )
        log_callback(
            f"  * Soundtrack Selected: '{score_plan.track_title}' [{score_plan.genre} | {score_plan.mood}]\n"
            f"  * Score Rationale: {score_plan.score_rationale}\n"
            f"  * Audio Dynamics: Base Vol {score_plan.base_bgm_volume:.2f}, "
            f"EQ Carve {score_plan.eq_carve_gain}dB @ {score_plan.eq_carve_freq}Hz, "
            f"{len(score_plan.volume_keyframes)} Volume Keyframes, "
            f"{len(score_plan.sfx_cues)} J-Cut Narrative SFX"
        )

        master_audio = config.temp_dir / f"master_audio_{self._slugify(topic)}.m4a"
        self.audio_mixer.mix_with_score_plan(
            voice_audio=tts_result.audio_path,
            output_path=master_audio,
            score_plan=score_plan,
            total_duration=total_duration,
            voice_volume=config.voice_volume,
        )

        base_slug = self._slugify(topic)
        timestamp_id = int(time.time())
        if explicit_output_path:
            final_video_path = explicit_output_path
            metadata_file = explicit_output_path.parent / f"{explicit_output_path.stem}_metadata.txt"
        else:
            final_video_path = config.output_dir / f"{base_slug}_{timestamp_id}.mp4"
            metadata_file = config.output_dir / f"{base_slug}_{timestamp_id}_metadata.txt"

        final_video_path.parent.mkdir(parents=True, exist_ok=True)

        self.ffmpeg.composite_final_short(
            concatenated_video=concat_video,
            master_audio=master_audio,
            ass_subtitles=ass_file,
            output_path=final_video_path,
            emoji_events=emoji_events,
            duration_limit=total_duration + 0.5,
        )

        # Generate social metadata with attributions, verification audit, and pacing metrics
        pacing_metrics_dict = {
            "total_shots": len(all_shots),
            "avg_shot_dur": avg_shot_dur,
            "media_dur": media_dur,
            "media_pct": media_pct,
            "diag_dur": diag_dur,
            "diag_pct": diag_pct,
        }
        self._save_social_metadata(
            script=script,
            output_path=metadata_file,
            evaluation=evaluation,
            attributions=self.visuals.get_attributions(),
            verification_audit=self.visuals.get_verification_audit(),
            pacing_metrics=pacing_metrics_dict,
            score_plan=score_plan,
        )

        elapsed = time.time() - start_time
        log_callback(f"\n[DONE] Video successfully generated in {elapsed:.1f}s!")
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
            evaluation=evaluation,
            metadata_path=metadata_file,
            score_plan=score_plan,
        )
