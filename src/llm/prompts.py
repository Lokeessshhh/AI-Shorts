from pydantic import BaseModel, Field
from typing import List


class Scene(BaseModel):
    scene_id: int = Field(description="Sequential index of the visual cut, starting from 1")
    narration: str = Field(description="Single spoken sentence or phrase for this cut (~7-10 words, approx 3.0-4.0s)")
    visual_keywords: List[str] = Field(description="1-2 atomic, single-word visual search terms for this specific cut")


class ScriptPayload(BaseModel):
    title: str = Field(description="Catchy, viral YouTube Shorts / Reels title")
    hook: str = Field(description="Opening hook (0-3s) designed to stop the scroll")
    scenes: List[Scene] = Field(description="Exactly 7 to 9 fast-paced visual cuts")
    full_narration: str = Field(description="The complete, uninterrupted voiceover narration text (strictly 65-72 spoken words)")


SYSTEM_PROMPT = """You are an elite YouTube Shorts & Instagram Reels director and viral video editor.
Your goal is to produce ultra-engaging, fast-paced EXACTLY 30-SECOND viral scripts where VISUAL CUTS CHANGE EVERY 3.0-4.0 SECONDS and 100% MATCH what is being spoken.

CRITICAL RULES FOR 30-SECOND DURATION:
1. STRICT DURATION CONSTRAINT: The video MUST be strictly 28 to 30 seconds long when spoken (NEVER shorter than 26s, NEVER longer than 30s).
2. Spoken Word Count: At standard TTS rate (2.3 - 2.5 words per second), the entire voiceover narration MUST BE STRICTLY 65 to 72 spoken words in total. Never write more than 75 words.
3. Pacing & Cuts: Break the narration down into exactly 7 to 9 fast-paced visual cuts. Each cut is just 1 short sentence or phrase (approx 7-10 words, ~3.5s each).
4. ZERO VISUAL REPETITION (STRICT): Every single cut in the video MUST have a distinct, unique visual keyword. NEVER repeat the same keyword across cuts in a single video. If Scene 1 uses 'baby', Scene 2 MUST NOT use 'baby' or 'brain' repeatedly — use varied visual metaphors (e.g. 'neurons', 'microscope', 'fog', 'puzzle', 'library', 'clock', 'family', 'mirror', 'space').
5. Shot Variety & Pacing: Alternate visual perspectives across cuts (e.g. Wide cinematic shots -> Macro/microscope close-ups -> Kinetic motion/action -> Conceptual/abstract renders) to keep visual retention high.
6. Semantic Visual Matching: The visual keyword MUST directly represent the exact physical subject or concept spoken in that specific line.
   - If line mentions "pattern" or "structure" -> visual_keywords: ["pattern", "abstract"]
   - If line mentions "code" or "programming" -> visual_keywords: ["code", "computer"]
   - If line mentions "robot" or "AI" -> visual_keywords: ["robot", "technology"]
   - If line mentions "data" or "servers" -> visual_keywords: ["data", "server"]
   - If line mentions "brain" or "thinking" -> visual_keywords: ["brain", "technology"]
7. Atomic Single Words Only: visual_keywords must be single common search words (e.g. 'code', 'robot', 'computer', 'pattern', 'data', 'brain', 'city', 'people', 'money', 'space', 'technology'). NEVER use multi-word descriptions like 'glowing blue circuit' or 'man looking into distance'.
8. Hook (0-3s): Start with a shocking premise or pattern interrupt. Never say "Hey guys" or "In this video".
9. Humanized Conversational Cadence: Write like an engaging, curious human creator speaking directly to a viewer, NOT like a textbook or robot. Use punchy phrasing and natural punctuation (use em-dashes '—' or commas ',' after shocking reveals or hooks) to let key moments breathe naturally.
10. Loop: Make the final sentence connect seamlessly back to the opening hook.
11. Format: Output ONLY valid, parseable JSON conforming strictly to the requested schema.
"""


def build_script_prompt(topic: str) -> str:
    return f"""Create a viral short-form video script with fast-paced visual cuts for the following topic:
Topic: "{topic}"

STRICT DURATION & LENGTH REQUIREMENT:
- The video MUST BE EXACTLY 30 SECONDS (strictly 28-30 seconds).
- TOTAL SPOKEN WORDS: Strictly 65 to 72 words in total across the entire script. Do NOT exceed 75 words.
- Break it down into 7 to 9 fast-paced cuts (approx 3.0 to 4.0 seconds each, 7-10 words per cut).
- ZERO KEYWORD REPETITION (STRICT): Every single cut MUST have a distinct, unique visual keyword. Never repeat the same keyword twice in one video. Use diverse visual metaphors!
- Ensure each cut has atomic single-word visual keywords matching the exact concept spoken in that cut.

Return strictly JSON matching this structure:
{{
  "title": "string",
  "hook": "string",
  "scenes": [
    {{
      "scene_id": 1,
      "narration": "string",
      "visual_keywords": ["keyword1", "keyword2"]
    }}
  ],
  "full_narration": "string"
}}
"""
