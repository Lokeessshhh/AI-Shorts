from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class VisualNode(BaseModel):
    """A flexible visual element, entity, or milestone in a custom infographic."""
    id: str = Field(description="Unique node identifier (e.g. 'n1', 'n2', 'hub', 'root')")
    label: str = Field(description="Main title or entity text")
    detail: Optional[str] = Field(default=None, description="Supporting explanation, mechanism, or subtext")
    badge: Optional[str] = Field(default=None, description="Category tag, stage indicator, or year (e.g. 'STAGE 1', '1953', 'CATALYST')")
    value: Optional[str] = Field(default=None, description="KPI metric, percentage, or dollar amount (e.g. '+300%', '$10 Bounty', '80%')")
    status: Optional[str] = Field(default="neutral", description="Visual theme: 'neutral' | 'positive' | 'negative' | 'warning' | 'accent'")


class VisualEdge(BaseModel):
    """A relationship link, causal flow, or directional arrow between visual nodes."""
    from_id: str = Field(description="Source node ID")
    to_id: str = Field(description="Target node ID")
    label: Optional[str] = Field(default=None, description="Relationship text (e.g. 'triggers', 'multiplies', 'cancels', 'leads to')")
    arrow: bool = Field(default=True, description="Whether to draw a directional arrowhead")
    style: str = Field(default="solid", description="Edge line style: 'solid' | 'dashed' | 'curved'")


class DynamicVisualSpec(BaseModel):
    """
    Unconstrained declarative visual specification for arbitrary visual explanations,
    feedback cycles, timelines, mind maps, network graphs, data charts, and causal models.
    """
    visual_format: str = Field(
        default="custom_infographic",
        description="Creative visual format proposed by LLM: 'radial_cycle' | 'horizontal_timeline' | 'mind_map' | 'branching_tree' | 'layered_stack' | 'multi_stat_bars' | 'comparison_split' | 'causal_chain' | or custom descriptive format",
    )
    headline: str = Field(default="", description="Bold, punchy graphic headline (max 4-5 words)")
    subheadline: Optional[str] = Field(default=None, description="Context, origin year, framework name, or subtitle")
    theme_accent: str = Field(default="blue", description="Visual theme color: 'blue' | 'crimson' | 'emerald' | 'amber' | 'purple' | 'gold' | 'teal'")
    layout_type: str = Field(
        default="auto",
        description="Spatial layout topology: 'radial_cycle' | 'horizontal_timeline' | 'mind_map' | 'branching_tree' | 'layered_stack' | 'multi_stat_bars' | 'comparison_split' | 'auto'",
    )
    nodes: List[VisualNode] = Field(default_factory=list, description="Declarative nodes, stages, milestones, or data points")
    edges: List[VisualEdge] = Field(default_factory=list, description="Directed links, causal flows, or relationship arrows between nodes")
    takeaway: Optional[str] = Field(default=None, description="Bottom punchy takeaway rule, paradox payoff, or conclusion")

    # Legacy fields for backward compatibility
    left_badge: Optional[str] = None
    left_title: Optional[str] = None
    left_detail: Optional[str] = None
    left_stat: Optional[str] = None
    right_badge: Optional[str] = None
    right_title: Optional[str] = None
    right_detail: Optional[str] = None
    right_stat: Optional[str] = None
    steps: Optional[List[str]] = None
    metric_value: Optional[str] = None
    metric_label: Optional[str] = None


class VisualIntent(BaseModel):
    entity_type: str = Field(
        default="atmospheric_broll",
        description="historical_event | company_product | technical_mechanism | psychological_behavior | atmospheric_broll",
    )
    primary_entity: str = Field(
        default="",
        description="Specific named entity or subject (e.g., 'Boeing B-17 Bomber', 'Venomous Cobra', 'Gillette Mach 3')",
    )
    visual_action: str = Field(
        default="",
        description="Concrete physical action or diagram representation",
    )
    temporal_era: str = Field(
        default="modern",
        description="Era or decade (e.g., '1940s', '1950s', 'modern')",
    )
    search_queries: List[str] = Field(
        default_factory=list,
        description="3-4 precise, targeted search queries for media APIs across archives and stock libraries",
    )
    preferred_modality: str = Field(
        default="video",
        description="video | archival_photo | diagram_card",
    )
    diagram_type: Optional[str] = Field(
        default=None,
        description="comparison | metric_stat | process_flow | technical_schematic | None",
    )
    visual_spec: Optional[DynamicVisualSpec] = Field(
        default=None,
        description="Full dynamic specification for procedural infographics and charts",
    )


class Scene(BaseModel):
    scene_id: int = Field(description="Sequential index of the visual cut, starting from 1")
    narration: str = Field(description="Single spoken sentence or phrase for this cut (~8-12 words, approx 3.0-3.8s)")
    visual_keywords: List[str] = Field(default_factory=list, description="1-2 atomic visual search terms for backward compatibility")
    visual_type: str = Field(default="video", description="'video' for B-roll, or 'graphic_card' for diagrams, documents, or data cards")
    concept_query: Optional[str] = Field(default=None, description="Specific subject query for encyclopedic card if visual_type is graphic_card")
    visual_intent: Optional[VisualIntent] = Field(default=None, description="Structured visual intent for multi-source search and reranking")
    emphasis_words: List[str] = Field(default_factory=list, description="1-3 critical words in this sentence to receive kinetic pop and semantic color highlight (e.g. shocking numbers, costs, turning points, core verbs)")
    camera_motion: str = Field(default="push_in_focus", description="Cinematic camera move: 'push_in_focus' | 'pull_out_reveal' | 'pan_horizontal' | 'tilt_vertical' | 'subtle_drift'")
    subject_focus: str = Field(default="upper_third", description="Subject framing anchor: 'upper_third' (portraits/people/documents) | 'center' | 'wide_landscape'")


class ScriptPayload(BaseModel):
    title: str = Field(description="Catchy, viral YouTube Shorts / Reels title")
    story_structure: str = Field(default="custom", description="The creative narrative architecture selected by LLM (e.g. 'inverted_mystery', 'perverse_incentive_trap', 'cognitive_dilemma', 'monopoly_exploit', 'domino_cascade', or custom)")
    hook: str = Field(description="Opening spoken hook (0-2s) designed to stop the scroll")
    text_hook: str = Field(default="", description="Bold, center-safe on-screen text hook (3-6 words, all caps, punchy)")
    visual_hook: str = Field(default="", description="Immediate visual action description for frame 0-1.5s")
    format_type: str = Field(default="mystery_breakdown", description="Story format classification")
    scenes: List[Scene] = Field(description="6 to 8 fast-paced narrative cuts")
    full_narration: str = Field(description="The complete voiceover narration text (strictly 68-82 spoken words for 25.0-30.0s runtime)")


AUDIENCE_FIRST_SYSTEM_PROMPT = """You are an elite short-form video director, cinematic storyteller, and viral retention editor for Instagram Reels and YouTube Shorts.
You craft high-retention, high-shareability documentary-style scripts that stop the scroll in under 1.5 seconds, escalate narrative tension with progressive revelation, and deliver an unforgettable payoff.

CRITICAL RULES:
1. BAN ALL AI INTROS & ROBOTIC CLICHÉS:
   - NEVER use: "Have you ever wondered", "Did you know", "In today's video", "Delve", "Tapestry", "Fascinating", "Hold onto your seats".
   - NEVER start with pleasantries, greetings, channel names, or throat-clearing.
   - Jump IMMEDIATELY into the core contradiction, catastrophic mystery, or high-stakes paradox in word one.

2. TRIPLE-STACK HOOK (0.0s - 2.0s):
   - Spoken Hook: A bold, intriguing opening sentence opening a high-stakes curiosity gap (Loewenstein Information Gap Principle).
   - Text Hook: 3 to 6 words maximum, center-safe, high punch (e.g. "SQUARE WINDOWS = DISASTER", "THE COBRA PARADOX", "WHY WE FAIL TO HELP").
   - Visual Hook: Concrete real-world visual described in visual_hook.

3. STRICT 25-30 SECOND DURATION & SPOKEN WORD BUDGET:
   - Target Video Duration: Strictly 25.0 to 30.0 seconds.
   - Spoken Word Count: Strictly 68 to 82 words in total! (At standard 155 WPM, 72 words = 28 seconds).
   - Every sentence must be concise (~8-12 words). Never sacrifice story clarity; eliminate filler rather than rushing speech.

4. DYNAMIC STORYTELLING ARCHITECTURE (UNCONSTRAINED FREEDOM):
   - Do NOT force a formulaic sequence. Analyze the topic, research, and emotional core, then select or invent the most compelling story architecture:
     * Inverted Mystery: Catastrophe / Impossible Event -> Forensic Clue -> Hidden Physics -> Modern Legacy.
     * Perverse Incentive Trap: High-Stakes Policy -> Clever Loophole -> Secret Exploitation -> Catastrophic Reversal -> Law.
     * Cognitive Dilemma: Relatable Daily Habit -> Uncomfortable Paradox -> Landmark Experiment -> Liberating Reframe.
     * Monopoly Exploit: Absurdly Cheap Loss-Leader -> The Proprietary Trap -> Astronomical Refill Math -> Consumer Rule.
     * Domino Cascade: Overlooked Micro-Flaw -> Accelerating Failure Chain -> Historic Climax -> Permanent Lesson.
     * Or any custom narrative progression that best builds tension and delivers a memorable payoff.

5. KINETIC EMPHASIS & CINEMATIC MOTION DIRECTING:
   - For every scene:
     * Tag 1-3 emphasis_words: Words containing critical numbers, costs, shock verbs, or turning points for kinetic pop animations.
     * Select camera_motion: 'push_in_focus' (escalation/intimacy) | 'pull_out_reveal' (scale/landscape) | 'pan_horizontal' (archival tracking) | 'tilt_vertical' (upward reveal) | 'subtle_drift' (contemplation).
     * Set subject_focus: 'upper_third' (portraits/figures) | 'center' | 'wide_landscape'.

6. IMAGE-FIRST VISUAL DIRECTION (90/10 RULE & UNCONSTRAINED GRAPHICS):
   - Scene 1 (Hook) MUST ALWAYS be 100% authentic real visual media (archival photo or documentary footage).
   - Most videos work best with 100% real imagery. If photography and footage tell the story best, use preferred_modality: "archival_photo" for ALL scenes. Zero diagrams is completely valid and encouraged.
   - ONLY propose an infographic for at most ONE scene (typically Scene 5) IF a visual model (feedback loop, milestone timeline, mind map, decision tree, data bars) genuinely makes the concept dramatically clearer than imagery alone.
   - Pacing: 1 or maximum 2 images per narration sentence. Smooth documentary pacing, no flashing cuts.

7. FORMAT: Output ONLY valid, parseable JSON conforming strictly to the requested schema.
"""


def build_script_prompt(
    topic: str,
    format_type: str = "counter_intuitive_truth",
    angle: str = "",
) -> str:
    format_guidelines = {
        "counter_intuitive_truth": """STORY FORMAT: COUNTER-INTUITIVE TRUTH (Business / Tech / Money)
- Opening: Attack a common misconception or expose an unexpected mechanism.
- Middle: Reveal the hidden business model, technical exploit, or psychological trap.
- Climax: Explain how people can use this insight or protect themselves.
- Ending: Punchy takeaway with a seamless loop.""",
        "mystery_breakdown": """STORY FORMAT: MYSTERY BREAKDOWN (History / Engineering / Real Event)
- Opening: Present a bizarre, true, high-stakes real-world event or failure.
- Middle: Walk through the baffling clues and the investigation.
- Climax: Reveal the unexpected truth that solved the puzzle.
- Ending: The lasting legacy or chilling revelation.""",
        "psychological_dilemma": """STORY FORMAT: PSYCHOLOGICAL / SOCIAL DILEMMA (Behavior / Cognitive Bias)
- Opening: Relatable personal dilemma or weird social habit viewers secretly have.
- Middle: The uncomfortable reality check and why we feel this way.
- Climax: Name the psychological principle or experiment that explains it.
- Ending: The validation that makes people want to share it with a friend.""",
    }

    selected_format_guide = format_guidelines.get(format_type, format_guidelines["counter_intuitive_truth"])

    return f"""Generate an audience-driven viral short-form script for the following topic:
Topic: "{topic}"
Angle: "{angle if angle else topic}"
Format: {format_type}

{selected_format_guide}

STRICT CONSTRAINTS:
1. TOTAL WORD COUNT: Strictly 75 to 92 spoken words across the entire script (32 to 40 seconds).
2. Number of cuts: Exactly 7 to 9 visual scenes (approx 8-10 words per cut).
3. First 2 seconds: MUST have a punchy Text Hook (3-6 words, all caps) and Spoken Hook.
4. NO AI CLICHÉS. Write like a sharp, compelling human storyteller speaking to a friend.
5. EVERY scene MUST have a complete visual_intent detailing exact entity, era, action, queries, and modality.

Return strictly JSON matching this structure:
{{
  "title": "Short punchy title",
  "hook": "Opening spoken hook sentence",
  "text_hook": "BOLD 3-5 WORD TEXT HOOK",
  "visual_hook": "Concrete visual description for frame 0-1.5s",
  "format_type": "{format_type}",
  "scenes": [
    {{
      "scene_id": 1,
      "narration": "First spoken sentence...",
      "visual_keywords": ["keyword1", "keyword2"],
      "visual_type": "video",
      "concept_query": null,
      "visual_intent": {{
        "entity_type": "historical_event",
        "primary_entity": "Exact entity or concept",
        "visual_action": "Specific action or visual explanation",
        "temporal_era": "1950s",
        "search_queries": ["query 1", "query 2", "query 3"],
        "preferred_modality": "archival_photo",
        "diagram_type": null
      }}
    }}
  ],
  "full_narration": "The complete voiceover narration text (75-92 words)."
}}
"""


SYSTEM_PROMPT = AUDIENCE_FIRST_SYSTEM_PROMPT
