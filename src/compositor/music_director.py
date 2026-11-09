import json
import re
import math
from pathlib import Path
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from ..config import config
from ..llm.client import OpenRouterClient
from ..llm.prompts import ScriptPayload, Scene


class TrackMetadata(BaseModel):
    id: str
    filename: str
    relative_path: str
    genre: str
    mood: str
    energy: str  # low | medium | high | crescendo
    tempo_feel: str  # slow | moderate | fast
    instrumentation: str
    ideal_structures: List[str]
    description: str


class VolumeKeyframe(BaseModel):
    time_sec: float
    volume_multiplier: float  # 0.0 to 1.5 relative to base volume
    narrative_beat: str  # hook | build | tension | climax | payoff | fade_out


class SelectiveSFXCue(BaseModel):
    timestamp: float
    sfx_type: str  # whoosh | pop | subtle_thud
    narrative_reason: str


class AudioScorePlan(BaseModel):
    track_path: Path
    track_title: str
    genre: str
    mood: str
    score_rationale: str
    base_bgm_volume: float = 0.14
    eq_carve_freq: int = 2500
    eq_carve_gain: float = -4.0  # dB
    ducking_threshold: float = 0.08
    ducking_ratio: float = 4.0
    ducking_attack_ms: int = 35
    ducking_release_ms: int = 220
    fade_in_duration: float = 0.6
    fade_out_duration: float = 1.8
    volume_keyframes: List[VolumeKeyframe] = Field(default_factory=list)
    sfx_cues: List[SelectiveSFXCue] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


# Rich catalog of local royalty-free music assets with musical & emotional metadata
KNOWN_TRACKS: Dict[str, Dict[str, Any]] = {
    "chill_lofi_starter_1.mp3": {
        "genre": "Lo-Fi Hip-Hop / Soul",
        "mood": "warm, contemplative, relaxed, curious",
        "energy": "low",
        "tempo_feel": "moderate",
        "instrumentation": "Rhodes piano chords, vinyl crackle, gentle downtempo drum loop",
        "ideal_structures": ["cognitive_dilemma", "everyday_economics", "psychological_habit"],
        "description": "Warm, mellow Rhodes piano and relaxed hip-hop beat. Perfect for relatable daily habits, thought experiments, and consumer psychology.",
    },
    "lofi_ambient_rhodes.mp3": {
        "genre": "Ambient Lo-Fi / Jazz",
        "mood": "introspective, analytical, floating, intellectual",
        "energy": "low",
        "tempo_feel": "slow",
        "instrumentation": "Lush electric piano chords, soft sub-bass, subtle atmospheric wash",
        "ideal_structures": ["cognitive_dilemma", "philosophical_paradox", "subtle_investigation"],
        "description": "Hypnotic, dreamlike ambient Rhodes with deep warmth. Creates space for thoughtful, mind-bending explanations without sensory overload.",
    },
    "temp_chill_lofi_beats.mp3": {
        "genre": "Modern Lo-Fi / Chillhop",
        "mood": "casual, rhythmic, modern, engaging",
        "energy": "medium",
        "tempo_feel": "moderate",
        "instrumentation": "Mellow synths, crisp boom-bap rhythm, warm 808 bassline",
        "ideal_structures": ["monopoly_exploit", "modern_business", "tech_loophole"],
        "description": "Engaging modern chillhop with head-bobbing rhythm. Ideal for exposing clever business models and consumer traps.",
    },
    "curious_scheming_weasel.mp3": {
        "genre": "Pizzicato Chamber / Inquisitive Comedy-Drama",
        "mood": "clever, mischievous, stealthy, eccentric puzzle",
        "energy": "medium",
        "tempo_feel": "moderate",
        "instrumentation": "Plucked strings (pizzicato violin/cello), playful bassoon, clockwork percussion",
        "ideal_structures": ["perverse_incentive_trap", "cobra_effect", "counter_intuitive_truth"],
        "description": "Playful pizzicato strings and clockwork rhythm evoking a scheming mind or unintended consequences. Ideal for historical loopholes and paradoxes.",
    },
    "curious_sneaky_adventure.mp3": {
        "genre": "Investigative Orchestral / Whimsical Mystery",
        "mood": "adventurous, inquisitive, uncovering secrets, detective discovery",
        "energy": "medium",
        "tempo_feel": "moderate",
        "instrumentation": "Rhythmic staccato strings, agile woodwinds, subtle marimba tick",
        "ideal_structures": ["counter_intuitive_truth", "scientific_discovery", "forensic_uncovering"],
        "description": "Fast-paced inquisitive strings and ticking percussion. Perfect for uncovering hidden scientific mechanisms and surprising truths.",
    },
    "dark_suspense_horror.mp3": {
        "genre": "Dark Cinematic Drone / Atmospheric Horror",
        "mood": "ominous, chilling, catastrophic, deep dread",
        "energy": "high",
        "tempo_feel": "slow",
        "instrumentation": "Sub-bass droning pulses, metallic bowed friction, eerie synth pads",
        "ideal_structures": ["catastrophic_disaster", "fatal_design_flaw", "historical_tragedy"],
        "description": "Deep, rumbling atmospheric dread with chilling metallic textures. Ideal for fatal engineering disasters and high-stakes warnings.",
    },
    "dark_suspense_tension.mp3": {
        "genre": "Cinematic Thriller / Ticking Pulse",
        "mood": "suspenseful, urgent, relentless countdown, investigative thriller",
        "energy": "high",
        "tempo_feel": "fast",
        "instrumentation": "Ticking clock ostinato, pulsing analog bass synthesizer, escalating strings",
        "ideal_structures": ["inverted_mystery", "domino_cascade", "forensic_investigation"],
        "description": "Relentless ticking clock pulse and brooding bass synthesizer. Drives intense curiosity and suspense for solving an impossible mystery.",
    },
    "emotional_piano_starter_1.mp3": {
        "genre": "Cinematic Neo-Classical / Bittersweet Piano",
        "mood": "poignant, touching, dramatic, bittersweet realization",
        "energy": "crescendo",
        "tempo_feel": "slow",
        "instrumentation": "Solo acoustic grand piano, swelling chamber violins, warm cello",
        "ideal_structures": ["human_tragedy", "unrecognized_genius", "heroic_sacrifice"],
        "description": "Deeply emotional acoustic piano with swelling cinematic strings. Perfect for poignant historical stories, human sacrifice, and bittersweet legacy.",
    },
    "emotional_piano_starter_2.mp3": {
        "genre": "Inspirational Cinematic / Soaring Piano",
        "mood": "hopeful, triumphant, awe-inspiring, human resilience",
        "energy": "crescendo",
        "tempo_feel": "moderate",
        "instrumentation": "Flowing piano arpeggios, uplifting violin melody, cinematic percussion",
        "ideal_structures": ["triumph_over_adversity", "scientific_breakthrough", "monumental_achievement"],
        "description": "Uplifting, soaring piano and orchestral progression. Ideal for monumental human breakthroughs and inspirational turnarounds.",
    },
    "high_energy_driving.mp3": {
        "genre": "Synthwave / Cyberpunk Electronic",
        "mood": "relentless, adrenaline, high-speed, futuristic drive",
        "energy": "high",
        "tempo_feel": "fast",
        "instrumentation": "Driving arpeggiated bass synth, crisp electronic drums, sidechained lead pads",
        "ideal_structures": ["race_against_time", "tech_disruption", "corporate_warfare"],
        "description": "High-octane synthwave with driving bass momentum. Excellent for fast-moving technology races, rapid disruption, and modern competition.",
    },
    "high_energy_starter_1.mp3": {
        "genre": "Electronic Rock / Cinematic Hybrid",
        "mood": "explosive, dramatic shock, peak impact, high-stakes collision",
        "energy": "high",
        "tempo_feel": "fast",
        "instrumentation": "Distorted synth riffs, massive hybrid drum hits, orchestral brass stabs",
        "ideal_structures": ["monumental_collapse", "extreme_exponential_event", "shocking_revelation"],
        "description": "Maximalist electronic rock with heavy cinematic impact. Ideal for shocking financial crashes and sudden exponential transformations.",
    },
}


class MusicDirector:
    """
    Intelligent, context-aware Music Director & Audio Supervisor.
    Analyzes the video script, narrative arc, emotional tone, scene breakdown, and vocal cadence
    to dynamically select, compose the volume automation curve, and mix the background music and sound design.
    """

    def __init__(self, llm_client: Optional[OpenRouterClient] = None):
        self.llm = llm_client or OpenRouterClient()
        self.catalog = self._scan_catalog()

    def _scan_catalog(self) -> Dict[str, TrackMetadata]:
        """Dynamically scan assets/bgm and index all available music files with metadata."""
        catalog: Dict[str, TrackMetadata] = {}
        bgm_root = config.bgm_dir

        if not bgm_root.exists():
            return catalog

        for p in bgm_root.rglob("*.mp3"):
            fname = p.name
            rel_path = str(p.relative_to(bgm_root)).replace("\\", "/")
            track_id = p.stem

            if fname in KNOWN_TRACKS:
                info = KNOWN_TRACKS[fname]
                catalog[track_id] = TrackMetadata(
                    id=track_id,
                    filename=fname,
                    relative_path=rel_path,
                    genre=info["genre"],
                    mood=info["mood"],
                    energy=info["energy"],
                    tempo_feel=info["tempo_feel"],
                    instrumentation=info["instrumentation"],
                    ideal_structures=info["ideal_structures"],
                    description=info["description"],
                )
            else:
                # Dynamically infer metadata for newly added user or royalty-free tracks
                parent_folder = p.parent.name.replace("_", " ").title()
                clean_name = p.stem.replace("_", " ").title()
                catalog[track_id] = TrackMetadata(
                    id=track_id,
                    filename=fname,
                    relative_path=rel_path,
                    genre=f"{parent_folder} Production Music",
                    mood=f"Atmospheric {parent_folder.lower()} mood",
                    energy="medium",
                    tempo_feel="moderate",
                    instrumentation="Mixed acoustic and electronic instrumentation",
                    ideal_structures=["general_narrative", "documentary"],
                    description=f"{clean_name} - Royalty-free background score from {parent_folder}.",
                )

        return catalog

    def _build_catalog_summary(self) -> str:
        """Format the available track library for LLM decision making."""
        lines = []
        for tid, meta in self.catalog.items():
            lines.append(
                f"- TRACK ID: '{tid}' (File: '{meta.relative_path}')\n"
                f"  Genre: {meta.genre} | Mood: {meta.mood} | Energy: {meta.energy} | Tempo: {meta.tempo_feel}\n"
                f"  Instrumentation: {meta.instrumentation}\n"
                f"  Best For: {', '.join(meta.ideal_structures)}\n"
                f"  Summary: {meta.description}"
            )
        return "\n\n".join(lines)

    def select_and_score(
        self,
        script: ScriptPayload,
        scene_timelines: List[Dict[str, Any]],
        total_duration: float,
        topic: str = "",
        custom_bgm_path: Optional[Path] = None,
    ) -> AudioScorePlan:
        """
        Dynamically select the optimal music track and generate the complete audio score plan
        based on the video's actual story, emotion, pacing, and scene timestamps.
        """
        # If user explicitly provided a custom BGM file, honor it while dynamically scoring its mix
        if custom_bgm_path and custom_bgm_path.exists():
            return self._score_custom_track(custom_bgm_path, script, scene_timelines, total_duration)

        # If catalog is empty, synthesize ambient bed
        if not self.catalog:
            return self._fallback_ambient_plan(total_duration, scene_timelines)

        # Query LLM Audio Director
        try:
            return self._llm_audio_direct(script, scene_timelines, total_duration, topic)
        except Exception as e:
            print(f"[MusicDirector] LLM Audio Supervisor fallback: {e}")
            return self._heuristic_audio_direct(script, scene_timelines, total_duration, topic)

    def _llm_audio_direct(
        self,
        script: ScriptPayload,
        scene_timelines: List[Dict[str, Any]],
        total_duration: float,
        topic: str,
    ) -> AudioScorePlan:
        """Use OpenRouter LLM as creative Music Director to select track and engineer volume automation curve."""
        catalog_text = self._build_catalog_summary()

        scenes_context = []
        for s in scene_timelines:
            idx = s.get("scene_id", 0)
            st = s.get("start_time", 0.0)
            et = s.get("end_time", 0.0)
            dur = et - st
            narr = s.get("narration", "")
            scenes_context.append(
                f"Scene {idx} [{st:.2f}s -> {et:.2f}s ({dur:.1f}s)]: \"{narr}\""
            )
        scenes_formatted = "\n".join(scenes_context)

        system_prompt = (
            "You are an award-winning Film & Short-Form Audio Director, Music Supervisor, and Sound Designer.\n"
            "Your job is to select the perfect background music track and design an expressive audio score plan\n"
            "for a high-retention short-form video. The music must feel composed specifically for this exact narrative,\n"
            "evolving dynamically with the hook, narrative tension, turning points, and final payoff.\n\n"
            "CRITICAL PRINCIPLES:\n"
            "1. NO STATIC BACKGROUND MUSIC: The volume and intensity must evolve with the story.\n"
            "2. VOCAL INTELLIGIBILITY: Background music must never overpower narration. Voice must remain clear.\n"
            "3. STORY ARC PROGRESSION:\n"
            "   - Hook (0.0s to ~3.5s): Hook the viewer with curiosity or suspense without blasting.\n"
            "   - Development/Build: Steady supportive accompaniment under exposition.\n"
            "   - Climax / Revelation (the big twist/turning point): Swell volume or intensity for peak impact.\n"
            "   - Resolution / Payoff: Harmonious resolve and smooth fade-out ending cleanly at the video conclusion.\n"
            "4. SELECTIVE, TASTEFUL SFX: NEVER put whooshes on every single cut (causes audio fatigue). Only choose 2-3\n"
            "   critical narrative pivot timestamps for subtle J-cut transition whooshes (where the scene transition\n"
            "   marks a major mental leap or twist).\n\n"
            "Return ONLY valid JSON matching the exact schema."
        )

        user_prompt = f"""VIDEO INFORMATION:
Topic: {topic or script.title}
Story Structure: {script.story_structure}
Text Hook: {script.text_hook}
Total Duration: {total_duration:.2f}s
Full Narration:
"{script.full_narration}"

SCENE TIMELINE:
{scenes_formatted}

AVAILABLE MUSIC CATALOG:
{catalog_text}

TASK:
1. Select the single best matching track from the catalog based on the narrative emotion, topic, and pacing.
2. Formulate a concise creative rationale explaining why this track's tempo, instrumentation, and mood serve this story.
3. Design a time-varying volume envelope across the narrative arc with keyframe multipliers (1.0 = base volume, 0.8 = dip during dense speech, 1.25 = climax swell, 0.0 = outro resolve).
4. Select 2-3 specific timestamps from the scene transition points where a subtle transition whoosh will punctuate a genuine narrative turning point.

Return JSON in this EXACT format:
{{
  "selected_track_id": "<track_id from catalog>",
  "musical_genre": "<concise genre>",
  "emotional_tone": "<2-4 descriptive adjectives>",
  "score_rationale": "<1-2 sentences on why this music enhances this specific story>",
  "base_bgm_volume": 0.14,
  "volume_keyframes": [
    {{"time_sec": 0.0, "volume_multiplier": 1.0, "narrative_beat": "hook"}},
    {{"time_sec": 4.0, "volume_multiplier": 0.9, "narrative_beat": "build"}},
    {{"time_sec": 18.0, "volume_multiplier": 1.25, "narrative_beat": "climax"}},
    {{"time_sec": {max(0.1, total_duration - 1.5):.2f}, "volume_multiplier": 0.8, "narrative_beat": "payoff"}},
    {{"time_sec": {total_duration:.2f}, "volume_multiplier": 0.0, "narrative_beat": "fade_out"}}
  ],
  "selective_sfx_timestamps": [
    {{"timestamp": <time_float>, "narrative_reason": "<why this cut deserves sound punctuation>"}}
  ]
}}
"""

        raw_response = self.llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=1000,
        )

        cleaned_json = self.llm._clean_json_string(raw_response)
        data = json.loads(cleaned_json)

        track_id = data.get("selected_track_id", "")
        meta = self.catalog.get(track_id)
        if not meta:
            # Fallback to closest match
            track_id = list(self.catalog.keys())[0]
            meta = self.catalog[track_id]

        track_path = config.bgm_dir / meta.relative_path

        keyframes = []
        for k in data.get("volume_keyframes", []):
            keyframes.append(VolumeKeyframe(
                time_sec=float(k.get("time_sec", 0.0)),
                volume_multiplier=float(k.get("volume_multiplier", 1.0)),
                narrative_beat=k.get("narrative_beat", "progression"),
            ))

        # Ensure monotonic order
        keyframes.sort(key=lambda x: x.time_sec)
        if not keyframes:
            keyframes = self._default_keyframes(total_duration)

        sfx_cues = []
        for s in data.get("selective_sfx_timestamps", []):
            t = float(s.get("timestamp", 0.0))
            if 0.5 < t < total_duration - 0.5:
                sfx_cues.append(SelectiveSFXCue(
                    timestamp=t,
                    sfx_type="whoosh",
                    narrative_reason=s.get("narrative_reason", "Narrative pivot"),
                ))

        base_vol = float(data.get("base_bgm_volume", 0.14))
        base_vol = max(0.08, min(0.22, base_vol))

        return AudioScorePlan(
            track_path=track_path,
            track_title=meta.filename,
            genre=data.get("musical_genre", meta.genre),
            mood=data.get("emotional_tone", meta.mood),
            score_rationale=data.get("score_rationale", meta.description),
            base_bgm_volume=base_vol,
            volume_keyframes=keyframes,
            sfx_cues=sfx_cues,
            fade_in_duration=0.5,
            fade_out_duration=1.6,
        )

    def _heuristic_audio_direct(
        self,
        script: ScriptPayload,
        scene_timelines: List[Dict[str, Any]],
        total_duration: float,
        topic: str,
    ) -> AudioScorePlan:
        """Intelligent heuristic matching when LLM API is unavailable."""
        topic_lower = f"{topic} {script.title} {script.story_structure} {script.full_narration}".lower()

        # Score catalog tracks by keyword resonance
        scored_tracks = []
        for tid, meta in self.catalog.items():
            score = 0
            # Structure matches
            if script.story_structure in meta.ideal_structures:
                score += 5
            # Mood keywords
            for word in meta.mood.replace(",", "").split():
                if word in topic_lower:
                    score += 2
            # Context keywords
            if any(k in topic_lower for k in ["crash", "disaster", "fail", "fatal", "mystery", "death", "lost"]):
                if "suspense" in tid or "horror" in tid:
                    score += 6
            elif any(k in topic_lower for k in ["cobra", "incentive", "loophole", "tax", "bounty", "clever"]):
                if "curious" in tid or "weasel" in tid:
                    score += 6
            elif any(k in topic_lower for k in ["bystander", "psychology", "habit", "brain", "think"]):
                if "chill" in tid or "lofi" in tid or "rhodes" in tid:
                    score += 6
            elif any(k in topic_lower for k in ["hero", "space", "triumph", "cure", "saved", "hope"]):
                if "emotional" in tid or "piano" in tid:
                    score += 6
            scored_tracks.append((score, tid, meta))

        scored_tracks.sort(key=lambda x: x[0], reverse=True)
        best_tid = scored_tracks[0][1] if scored_tracks else list(self.catalog.keys())[0]
        meta = self.catalog[best_tid]
        track_path = config.bgm_dir / meta.relative_path

        keyframes = self._default_keyframes(total_duration)

        # Select 2 key transition cuts for subtle whoosh
        sfx_cues = []
        if len(scene_timelines) >= 4:
            # Transition after hook (scene 1 -> scene 2)
            t1 = scene_timelines[0].get("end_time", 3.5)
            sfx_cues.append(SelectiveSFXCue(
                timestamp=t1,
                sfx_type="whoosh",
                narrative_reason="Hook to exposition transition",
            ))
            # Transition into climax (scene 4 -> scene 5)
            climax_idx = max(1, len(scene_timelines) - 3)
            t2 = scene_timelines[climax_idx].get("end_time", total_duration * 0.7)
            sfx_cues.append(SelectiveSFXCue(
                timestamp=t2,
                sfx_type="whoosh",
                narrative_reason="Climax reveal pivot",
            ))

        return AudioScorePlan(
            track_path=track_path,
            track_title=meta.filename,
            genre=meta.genre,
            mood=meta.mood,
            score_rationale=f"Selected '{meta.filename}' based on story resonance with {script.story_structure}.",
            base_bgm_volume=0.14,
            volume_keyframes=keyframes,
            sfx_cues=sfx_cues,
            fade_in_duration=0.5,
            fade_out_duration=1.6,
        )

    def _score_custom_track(
        self,
        custom_path: Path,
        script: ScriptPayload,
        scene_timelines: List[Dict[str, Any]],
        total_duration: float,
    ) -> AudioScorePlan:
        """Score an explicitly supplied custom BGM track."""
        keyframes = self._default_keyframes(total_duration)
        sfx_cues = []
        if len(scene_timelines) >= 3:
            sfx_cues.append(SelectiveSFXCue(
                timestamp=scene_timelines[0].get("end_time", 3.5),
                sfx_type="whoosh",
                narrative_reason="Hook to story build",
            ))

        return AudioScorePlan(
            track_path=custom_path,
            track_title=custom_path.name,
            genre="Custom Selected Track",
            mood="Video-adapted",
            score_rationale="Custom audio provided by user with video-adapted volume envelope.",
            base_bgm_volume=0.14,
            volume_keyframes=keyframes,
            sfx_cues=sfx_cues,
            fade_in_duration=0.5,
            fade_out_duration=1.5,
        )

    def _fallback_ambient_plan(
        self,
        total_duration: float,
        scene_timelines: List[Dict[str, Any]],
    ) -> AudioScorePlan:
        """Fallback to procedural synthesizer if no audio files exist."""
        ambient_path = config.temp_dir / "procedural_ambient.mp3"
        return AudioScorePlan(
            track_path=ambient_path,
            track_title="procedural_ambient.mp3",
            genre="Procedural Ambient Drone",
            mood="Warm subtle curiosity",
            score_rationale="Procedural ambient drone synthesized for dialogue clarity.",
            base_bgm_volume=0.12,
            volume_keyframes=self._default_keyframes(total_duration),
            sfx_cues=[],
            fade_in_duration=0.5,
            fade_out_duration=1.5,
        )

    def _default_keyframes(self, total_duration: float) -> List[VolumeKeyframe]:
        """Construct standard 5-point storytelling dynamic volume envelope."""
        dur = max(5.0, total_duration)
        return [
            VolumeKeyframe(time_sec=0.0, volume_multiplier=1.0, narrative_beat="hook"),
            VolumeKeyframe(time_sec=round(dur * 0.15, 2), volume_multiplier=0.90, narrative_beat="build"),
            VolumeKeyframe(time_sec=round(dur * 0.65, 2), volume_multiplier=1.20, narrative_beat="climax"),
            VolumeKeyframe(time_sec=round(dur * 0.88, 2), volume_multiplier=0.85, narrative_beat="payoff"),
            VolumeKeyframe(time_sec=round(dur, 2), volume_multiplier=0.0, narrative_beat="fade_out"),
        ]
