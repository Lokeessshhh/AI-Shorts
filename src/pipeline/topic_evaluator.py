"""Audience-First 100-Point Topic Evaluation Framework.
Evaluates candidate topics against psychological retention criteria, shareability,
and audience demand before scriptwriting begins. Automatically eliminates generic trivia,
obscure facts, and unverifiable rumors.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from ..llm.client import OpenRouterClient


@dataclass
class CriterionScore:
    name: str
    max_score: int
    score: int
    feedback: str


@dataclass
class TopicEvaluation:
    topic: str
    angle: str
    target_audience: str
    format_type: str  # counter_intuitive_truth, mystery_breakdown, or psychological_dilemma
    total_score: int
    approved: bool
    rejection_reasons: List[str] = field(default_factory=list)
    criteria_breakdown: Dict[str, CriterionScore] = field(default_factory=dict)
    rationale: str = ""


TOPIC_EVALUATOR_SYSTEM_PROMPT = """You are a ruthless, data-driven Chief Content Officer for viral short-form video (YouTube Shorts, Instagram Reels, TikTok).
Your job is to objectively evaluate candidate topics before any script or video is produced.
You hate generic trivia, boring encyclopedia facts, unverified rumors, and topics that only an AI would find interesting.

You evaluate every topic strictly on this 100-point rubric:
1. Curiosity and Tension (max 25 pts): Does the premise open an immediate, irresistible cognitive gap or contradiction in the first 3 seconds?
2. Audience Relevance (max 20 pts): Does this affect real people's money, habits, psychology, health, everyday decisions, or relatable social dilemmas?
3. Shareability / DM Potential (max 20 pts): Would someone text this to a friend or post on their story with "This is literally you", "You need to see this", or "Did you know this?"
4. Visual Potential (max 15 pts): Can this be visualized with concrete, high-impact video, documents, schematics, or graphics (not abstract thoughts)?
5. Simplicity / Digestibility (max 10 pts): Can the core tension and payoff be grasped within 30-45 seconds without lengthy technical exposition?
6. Information Credibility (max 10 pts): Is this based on verified scientific, economic, historical, or legal consensus (not fake dark psychology or made-up statistics)?

MINIMUM ACCEPTANCE THRESHOLD: 75 / 100.

AUTOMATIC REJECTION CONDITIONS (Immediate Disqualification - Score < 50):
- Passive, textbook facts without stakes (e.g. "How bees make honey", "The history of pencils")
- Obscure academic topics that lack emotional or practical relevance
- Unverifiable "dark psychology tricks" or conspiracy clickbait
- Concepts that require more than 10 seconds of background setup before reaching the hook
- Abstract philosophical thoughts that cannot be shown visually

You must output strictly valid JSON with this structure:
{
  "angle": "Compelling, audience-focused hook angle (1-2 sentences)",
  "target_audience": "Specific audience description (e.g. young professionals, everyday consumers, tech enthusiasts)",
  "recommended_format": "counter_intuitive_truth" | "mystery_breakdown" | "psychological_dilemma",
  "curiosity_and_tension": {"score": 0-25, "reason": "..."},
  "audience_relevance": {"score": 0-20, "reason": "..."},
  "shareability": {"score": 0-20, "reason": "..."},
  "visual_potential": {"score": 0-15, "reason": "..."},
  "simplicity": {"score": 0-10, "reason": "..."},
  "information_credibility": {"score": 0-10, "reason": "..."},
  "rejection_reasons": ["list of reasons if rejected, empty if approved"],
  "rationale": "Honest assessment of viral potential and audience retention"
}
"""


class TopicEvaluator:
    """Evaluates candidate topics against audience-first criteria to prevent low-retention video production."""

    def __init__(self, llm_client: Optional[OpenRouterClient] = None):
        self.llm = llm_client or OpenRouterClient()

    def evaluate(self, topic: str) -> TopicEvaluation:
        """Evaluate a single topic candidate against the 100-point rubric."""
        user_prompt = f"""Evaluate this topic candidate for a 30-45 second short-form video:
Topic Candidate: "{topic}"

Be brutally honest. Grade rigorously according to the 100-point rubric.
Return ONLY valid JSON conforming to the requested schema.
"""
        raw_response = self.llm.complete(
            system_prompt=TOPIC_EVALUATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,  # Low temperature for objective scoring
        )

        try:
            cleaned = self.llm._clean_json_string(raw_response)
            data = json.loads(cleaned)
        except Exception as e:
            # Fallback if JSON parsing fails
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                raise ValueError(f"Failed to parse topic evaluation response: {e}\nRaw: {raw_response}")

        scores = {
            "curiosity_and_tension": CriterionScore(
                name="Curiosity and Tension",
                max_score=25,
                score=min(25, max(0, int(data.get("curiosity_and_tension", {}).get("score", 0)))),
                feedback=data.get("curiosity_and_tension", {}).get("reason", ""),
            ),
            "audience_relevance": CriterionScore(
                name="Audience Relevance",
                max_score=20,
                score=min(20, max(0, int(data.get("audience_relevance", {}).get("score", 0)))),
                feedback=data.get("audience_relevance", {}).get("reason", ""),
            ),
            "shareability": CriterionScore(
                name="Shareability (DM Potential)",
                max_score=20,
                score=min(20, max(0, int(data.get("shareability", {}).get("score", 0)))),
                feedback=data.get("shareability", {}).get("reason", ""),
            ),
            "visual_potential": CriterionScore(
                name="Visual Potential",
                max_score=15,
                score=min(15, max(0, int(data.get("visual_potential", {}).get("score", 0)))),
                feedback=data.get("visual_potential", {}).get("reason", ""),
            ),
            "simplicity": CriterionScore(
                name="Simplicity & Digestibility",
                max_score=10,
                score=min(10, max(0, int(data.get("simplicity", {}).get("score", 0)))),
                feedback=data.get("simplicity", {}).get("reason", ""),
            ),
            "information_credibility": CriterionScore(
                name="Information Credibility",
                max_score=10,
                score=min(10, max(0, int(data.get("information_credibility", {}).get("score", 0)))),
                feedback=data.get("information_credibility", {}).get("reason", ""),
            ),
        }

        total_score = sum(c.score for c in scores.values())
        rejections = data.get("rejection_reasons", [])
        if not isinstance(rejections, list):
            rejections = [str(rejections)]

        # Explicit rejection conditions
        if total_score < 75:
            if not rejections:
                rejections.append(f"Total score {total_score}/100 is below the 75-point quality threshold.")
            approved = False
        elif rejections and any(len(r.strip()) > 0 for r in rejections):
            approved = False
        else:
            approved = True

        return TopicEvaluation(
            topic=topic,
            angle=data.get("angle", topic),
            target_audience=data.get("target_audience", "General short-form video viewers"),
            format_type=data.get("recommended_format", "counter_intuitive_truth"),
            total_score=total_score,
            approved=approved,
            rejection_reasons=rejections if not approved else [],
            criteria_breakdown=scores,
            rationale=data.get("rationale", ""),
        )

    def select_top_candidates(
        self,
        candidate_pool: List[str],
        required_count: int = 3,
    ) -> List[TopicEvaluation]:
        """Evaluate a batch of candidate topics and return the strongest approved candidates."""
        evaluated: List[TopicEvaluation] = []
        for candidate in candidate_pool:
            eval_res = self.evaluate(candidate)
            print(f"[TopicEvaluator] '{candidate[:45]}...' -> Score: {eval_res.total_score}/100 | Approved: {eval_res.approved}")
            if eval_res.approved:
                evaluated.append(eval_res)

        # Sort by total score descending
        evaluated.sort(key=lambda x: x.total_score, reverse=True)
        return evaluated[:required_count]

    def brainstorm_candidate_topics(self, count: int = 5) -> List[Dict[str, str]]:
        """Autonomously discover fresh, high-demand viral short-form video topics."""
        prompt = f"""You are a master viral YouTube Shorts and Instagram Reels strategist.
Generate {count} unique, high-retention, high-curiosity video topic ideas that meet these criteria:
1. Opens an irresistible cognitive gap or contradiction in the first 3 seconds.
2. Directly touches human psychology, surprising historical events, everyday money traps, or bizarre real phenomena.
3. Can be visualized with real historical photography, documentary footage, and verified records.
4. Spans across our 3 proven formats:
   - Counter-Intuitive Truth (Business/Economics)
   - Mystery Breakdown (Real History/Engineering)
   - Psychological Dilemma (Human Behavior/Social Paradox)

Output strictly valid JSON with this format:
[
  {{"topic": "...", "angle": "...", "format_type": "counter_intuitive_truth"}},
  ...
]
"""
        raw = self.llm.complete(
            system_prompt="You are a data-driven short-form content director. Output ONLY a valid JSON list.",
            user_prompt=prompt,
            temperature=0.7,
        )
        try:
            cleaned = self.llm._clean_json_string(raw)
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return [
                {"topic": "Why McDonald's Ice Cream Machines Are Kept Perpetually Broken", "angle": "The multi-million dollar copyright lawsuit behind the secret repair code on fast-food machines.", "format_type": "counter_intuitive_truth"},
                {"topic": "The 1904 Olympic Marathon: The Most Chaotic Race in Human History", "angle": "Rat poison, stolen cars, and wild dogs: how the weirdest marathon ever was won.", "format_type": "mystery_breakdown"},
                {"topic": "The Pygmalion Effect: Why Other People's Expectations Literally Change Your IQ", "angle": "Harvard psychologists tricked teachers into thinking random students were geniuses—and their test scores doubled.", "format_type": "psychological_dilemma"}
            ]

    def discover_and_select_best_topic(self) -> TopicEvaluation:
        """Autonomously discover candidate topics, evaluate them through the 100-point rubric, and return the champion."""
        candidates = self.brainstorm_candidate_topics(5)
        best_eval = None
        for cand in candidates:
            topic_str = cand.get("topic", "")
            eval_res = self.evaluate(topic_str)
            if cand.get("angle") and not eval_res.angle:
                eval_res.angle = cand["angle"]
            if cand.get("format_type"):
                eval_res.format_type = cand["format_type"]
            print(f"[TopicEvaluator] '{topic_str[:50]}' -> Score: {eval_res.total_score}/100 | Approved: {eval_res.approved}")
            if eval_res.approved:
                if best_eval is None or eval_res.total_score > best_eval.total_score:
                    best_eval = eval_res

        if best_eval is None and candidates:
            all_evals = [self.evaluate(c["topic"]) for c in candidates]
            all_evals.sort(key=lambda x: x.total_score, reverse=True)
            best_eval = all_evals[0]

        return best_eval
