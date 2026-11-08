"""Mode 3 AI Viral Highlight & Moment Detector (2-Pass Virality Funnel).
Pass 1: Semantic Chunking & Full-Timeline Candidate Extraction (Beginning, Middle, Climax).
Pass 2: 4-Signal Virality Scoring Tournament with Category Diversity & Whisper Word Snapping.
"""

import json
import re
from typing import Dict, List, Any, Optional
import requests

from ..config import config


SPONSOR_AND_BANTER_PATTERNS = [
    r"\b(sponsor|sponsored|brought to you by)\b",
    r"\b(subscribe to (the|my) channel|hit the bell|like and subscribe)\b",
    r"\b(promo code|discount code|link in (the|our) description)\b",
    r"\b(welcome back to|welcome to the show|thank you for coming|thanks for having me)\b",
    r"\b(check out our partner|support the podcast|leave a review)\b",
    r"\b(tune in next week|see you in the next episode)\b",
]

VIRAL_KEYWORDS = {
    # High emotional / curiosity triggers
    "money": 3, "billion": 3, "million": 3, "secret": 3, "truth": 3, "never": 2,
    "mistake": 3, "regret": 3, "failure": 3, "failed": 3, "hate": 2, "love": 2,
    "power": 2, "mindset": 2, "status": 3, "wealth": 3, "psychology": 3, "trap": 3,
    "crazy": 2, "danger": 2, "worst": 3, "best": 2, "lesson": 2, "rules": 2,
    "future": 2, "ai": 2, "world": 2, "human": 2, "god": 2, "death": 3, "died": 3,
}

HOOK_STARTERS = [
    "what", "why", "how", "if you", "the biggest", "nobody", "most people",
    "i think", "i believe", "the truth", "the reason", "there is a", "you should",
    "was there", "have you ever", "do you think", "one of the", "when i", "my biggest"
]

VIRALITY_TOURNAMENT_SYSTEM_PROMPT = """You are an elite short-form viral editor who has generated billions of views across YouTube Shorts, TikTok, and Instagram Reels for top podcasts (Diary of a CEO, Joe Rogan, Lex Fridman, Raj Shamani, Huberman Lab).

You are judging a VIRALITY TOURNAMENT of pre-screened narrative candidate clips extracted across the entire podcast (Beginning, Middle, and Climax).

EVALUATE EACH CANDIDATE USING THIS STRICT 4-SIGNAL RUBRIC:
1. HOOK STRENGTH (0-35 points):
   - 30-35: Explosive, scroll-stopping question, bold polarizing claim, or shocking confession in the first 3 seconds. Zero filler.
   - 20-29: Clear thesis or intriguing premise.
   - <20: Starts with conversational filler ("Yeah, so...", "Like I said...", "You know...").
2. NARRATIVE COMPLETENESS (0-30 points):
   - 25-30: Complete story or argument arc that resolves on a high-impact punchline, takeaway, or realization.
   - <20: Abrupt ending or unresolved thought.
3. COMMENT / DEBATE AROUSAL (0-20 points):
   - 16-20: Polarizing opinion, taboo topic, shocking numbers/money/status, psychological truth that provokes viewers to comment or debate.
4. INFORMATION DENSITY (0-15 points):
   - 12-15: Fast pace, zero dead air or repetitive stuttering, concise and impactful.

CATEGORIES (Assign one per candidate):
- "Personal Story & Mindset" (vulnerability, conviction, failure, identity, extreme habits)
- "Business, Money & Career" (startups, wealth, status games, leverage, negotiation, market truths)
- "Psychology & Human Nature" (dating, relationships, persuasion, human flaws, ego, fear)
- "Tech, AI & Future Truth" (superintelligence, societal transformation, frontier predictions)

BGM MOOD ARCHETYPE (Assign the best audio background mood for each candidate):
- "dark_suspense": Dark psychology, harsh truths, high stakes, betrayal, existential danger.
- "emotional_piano": Vulnerability, failure-to-success, heartbreak, emotional breakthrough, deep reflection.
- "high_energy": Business scaling, gym motivation, aggressive mindset, hustle, rapid speech.
- "curious_investigative": Science, "did you know?", counter-intuitive facts, trivia, mind-bending puzzles.
- "chill_lofi": Casual philosophy, relaxed life lessons, quiet mindset reflections.

OUTPUT FORMAT REQUIREMENTS:
Think briefly, then output valid JSON ONLY (no markdown fences, no conversational preamble):
{
  "ranked_candidates": [
    {
      "candidate_id": 1,
      "title": "Short Punchy Title (Under 45 chars)",
      "start_time": 1634.5,
      "end_time": 1672.6,
      "hook_sentence": "The exact opening hook sentence.",
      "clean_hook": "Hook sentence with leading filler stripped.",
      "punchline_resolution": "The closing punchline or realization of the clip.",
      "category": "Personal Story & Mindset",
      "mood": "emotional_piano",
      "hook_score": 33,
      "narrative_score": 28,
      "debate_score": 19,
      "density_score": 14,
      "total_score": 94,
      "virality_reason": "One sentence explaining why this clip will retain viewers and generate shares.",
      "hashtags": ["#topic1", "#topic2", "#shorts", "#viral", "#podcast"]
    }
  ]
}
"""


class HighlightDetector:
    """Production-grade 2-Pass AI Viral Highlight & Moment Detector."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.openrouter_api_key
        self.model = model or config.openrouter_model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def _clean_json_string(self, text: str) -> str:
        """Strip markdown code fences and preamble."""
        cleaned = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
        return cleaned.strip()

    def _is_sponsor_or_banter(self, text: str) -> bool:
        """Check if sentence matches sponsor reads or channel banter."""
        text_lower = text.lower()
        for pattern in SPONSOR_AND_BANTER_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    def _clean_hook_text(self, text: str) -> str:
        """Strip common conversational crutches from the beginning of a hook."""
        cleaned = re.sub(r"^(>>\s*|um\b|uh\b|yeah\b|so\b|like\b|well\b|you know\b|i mean\b|and\b)[,\s]*", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(>>\s*|um\b|uh\b|yeah\b|so\b|like\b|well\b|and\b)[,\s]*", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _reconstruct_sentences(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group Whisper segments into complete grammatical sentences."""
        sentences: List[Dict[str, Any]] = []
        cur_texts: List[str] = []
        cur_words: List[Dict[str, Any]] = []
        cur_start: Optional[float] = None
        cur_end: Optional[float] = None

        for s in segments:
            text = s["text"].strip()
            if not text:
                continue

            if cur_start is None:
                cur_start = s["start"]
            cur_end = s["end"]
            cur_texts.append(text)
            if "words" in s and s["words"]:
                cur_words.extend(s["words"])

            # Check if this segment ends a sentence
            is_terminal = (
                text[-1] in ".?!"
                or (cur_end - cur_start) >= 12.0
            )

            if is_terminal:
                full_text = " ".join(cur_texts)
                sentences.append({
                    "start": cur_start,
                    "end": cur_end,
                    "duration": round(cur_end - cur_start, 2),
                    "text": full_text,
                    "words": cur_words,
                })
                cur_texts = []
                cur_words = []
                cur_start = None
                cur_end = None

        if cur_texts and cur_start is not None and cur_end is not None:
            sentences.append({
                "start": cur_start,
                "end": cur_end,
                "duration": round(cur_end - cur_start, 2),
                "text": " ".join(cur_texts),
                "words": cur_words,
            })

        return sentences

    def _pre_score_candidate(self, opening_sentence: str, full_text: str, duration: float) -> float:
        """Heuristic pre-scorer to select top candidates from each Act for tournament."""
        score = 50.0

        clean_opener = self._clean_hook_text(opening_sentence).lower()

        # Hook starter bonus
        for starter in HOOK_STARTERS:
            if clean_opener.startswith(starter):
                score += 15.0
                break

        # Question hook bonus
        if "?" in opening_sentence:
            score += 10.0

        # Virality keywords bonus
        text_lower = full_text.lower()
        keyword_hits = 0
        for kw, weight in VIRAL_KEYWORDS.items():
            if re.search(r"\b" + kw + r"\b", text_lower):
                score += weight
                keyword_hits += 1
                if keyword_hits >= 6:
                    break

        # Optimal short duration sweet spot (35s - 50s)
        if 35.0 <= duration <= 50.0:
            score += 8.0
        elif 30.0 <= duration <= 55.0:
            score += 4.0

        # Penalty for sponsor/banter hints
        if self._is_sponsor_or_banter(opening_sentence):
            score -= 40.0

        return score

    def _extract_candidates(
        self,
        sentences: List[Dict[str, Any]],
        total_duration: float,
        min_duration: float = 30.0,
        max_duration: float = 58.0,
    ) -> List[Dict[str, Any]]:
        """
        Pass 1: Build coherent narrative candidate blocks (30-60s) grouped across
        Act I (Beginning), Act II (Middle), and Act III (Climax).
        """
        raw_candidates: List[Dict[str, Any]] = []
        i = 0

        while i < len(sentences):
            start_s = sentences[i]
            # Skip blatant sponsor sentences at chunk start
            if self._is_sponsor_or_banter(start_s["text"]):
                i += 1
                continue

            start_t = start_s["start"]
            block_sentences = [start_s["text"]]
            end_t = start_s["end"]
            j = i + 1

            while j < len(sentences):
                candidate_dur = sentences[j]["end"] - start_t
                if candidate_dur > max_duration:
                    break
                block_sentences.append(sentences[j]["text"])
                end_t = sentences[j]["end"]
                j += 1
                if candidate_dur >= min_duration:
                    break

            dur = end_t - start_t
            if min_duration <= dur <= max_duration:
                full_block_text = " ".join(block_sentences)
                opening = block_sentences[0]
                closing = block_sentences[-1]
                clean_hook = self._clean_hook_text(opening)

                # Determine Act
                act_ratio = start_t / total_duration if total_duration > 0 else 0
                if act_ratio < 0.35:
                    act_name = "Act I (Beginning)"
                    act_num = 1
                elif act_ratio < 0.70:
                    act_name = "Act II (Middle)"
                    act_num = 2
                else:
                    act_name = "Act III (Climax)"
                    act_num = 3

                pre_score = self._pre_score_candidate(opening, full_block_text, dur)

                raw_candidates.append({
                    "start": round(start_t, 2),
                    "end": round(end_t, 2),
                    "duration": round(dur, 1),
                    "text": full_block_text,
                    "opening": opening,
                    "clean_hook": clean_hook,
                    "closing": closing,
                    "act": act_name,
                    "act_num": act_num,
                    "pre_score": pre_score,
                })

                # Advance window by ~20s to capture different narrative anchors
                target_t = start_t + 20.0
                while i < len(sentences) and sentences[i]["start"] < target_t:
                    i += 1
            else:
                i += 1

        # Group and select top 5 from each Act for the Pass 2 tournament
        act1 = sorted([c for c in raw_candidates if c["act_num"] == 1], key=lambda x: x["pre_score"], reverse=True)[:5]
        act2 = sorted([c for c in raw_candidates if c["act_num"] == 2], key=lambda x: x["pre_score"], reverse=True)[:6]
        act3 = sorted([c for c in raw_candidates if c["act_num"] == 3], key=lambda x: x["pre_score"], reverse=True)[:5]

        tournament_candidates = act1 + act2 + act3
        # Sort chronologically for easy LLM reading
        tournament_candidates.sort(key=lambda x: x["start"])

        # Re-index candidate IDs
        for idx, c in enumerate(tournament_candidates, 1):
            c["id"] = idx

        return tournament_candidates

    def detect_highlights(
        self,
        transcript_data: Dict[str, Any],
        num_clips: int = 3,
        min_duration: float = 30.0,
        max_duration: float = 60.0,
    ) -> List[Dict[str, Any]]:
        """
        2-Pass Virality Selection Funnel:
        Pass 1: Semantic Chunking & Timeline Candidate Extraction.
        Pass 2: LLM Virality Scoring Tournament with Category Diversity.
        """
        segments = transcript_data.get("segments", [])
        all_words = transcript_data.get("words", [])
        total_duration = transcript_data.get("duration", 0)

        if not segments:
            raise ValueError("Transcript data is empty or missing 'segments'.")

        # Step 1: Reconstruct grammatical sentences
        sentences = self._reconstruct_sentences(segments)
        print(f"[Clipper/Detector] Pass 1: Formed {len(sentences)} clean sentences across {total_duration:.1f}s.")

        # Step 2: Extract timeline-balanced candidates (Act I, Act II, Act III)
        candidates = self._extract_candidates(
            sentences=sentences,
            total_duration=total_duration,
            min_duration=min_duration,
            max_duration=max_duration - 2.0,
        )
        print(f"[Clipper/Detector] Pass 1: Selected {len(candidates)} high-potential tournament candidates across Beginning, Middle & Climax.")

        if not candidates:
            raise RuntimeError("No candidate blocks met the criteria in Pass 1.")

        # Step 3: Pass 2 - Virality Scoring Tournament via OpenRouter
        tournament_prompt = self._build_tournament_prompt(candidates, total_duration)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/AI_Shorts",
            "X-Title": "AI Shorts Mode 3 Clipper",
            "Content-Type": "application/json",
        }

        # Model candidates with automatic fallback
        model_queue = [self.model]
        for fallback_model in ["openai/gpt-4o-mini", "meta-llama/llama-3.3-70b-instruct"]:
            if fallback_model not in model_queue:
                model_queue.append(fallback_model)

        ranked_candidates = []
        last_error = ""

        for model_to_try in model_queue:
            payload = {
                "model": model_to_try,
                "messages": [
                    {"role": "system", "content": VIRALITY_TOURNAMENT_SYSTEM_PROMPT},
                    {"role": "user", "content": tournament_prompt},
                ],
                "temperature": 0.25,
                "max_tokens": 4000,
            }

            print(f"[Clipper/Detector] Pass 2: Running Virality Scoring Tournament on {len(candidates)} candidates ({model_to_try})...")
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
            except Exception as e:
                last_error = str(e)
                continue

            if response.status_code != 200:
                last_error = f"OpenRouter API error ({response.status_code}): {response.text}"
                continue

            resp_json = response.json()
            raw_content = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            cleaned_json = self._clean_json_string(raw_content)

            try:
                parsed = json.loads(cleaned_json)
                ranked_candidates = parsed.get("ranked_candidates", [])
            except json.JSONDecodeError:
                match = re.search(r"\"ranked_candidates\"\s*:\s*(\[[\s\S]*?\])", cleaned_json)
                if match:
                    try:
                        ranked_candidates = json.loads(match.group(1))
                    except Exception:
                        ranked_candidates = []
                else:
                    last_brace = cleaned_json.rfind("}")
                    if last_brace != -1:
                        repaired = cleaned_json[:last_brace + 1]
                        if not repaired.endswith("]}"):
                            repaired = repaired + "\n]}"
                        try:
                            parsed = json.loads(repaired)
                            ranked_candidates = parsed.get("ranked_candidates", [])
                        except Exception:
                            cand_matches = re.findall(r"\{[^{}]*\"candidate_id\"[^{}]*\}", cleaned_json)
                            ranked_candidates = []
                            for cm in cand_matches:
                                try:
                                    ranked_candidates.append(json.loads(cm))
                                except Exception:
                                    pass

            if ranked_candidates:
                print(f"[Clipper/Detector] Successfully extracted {len(ranked_candidates)} scored tournament clips using {model_to_try}.")
                break
            else:
                last_error = f"Failed to parse tournament JSON from {model_to_try}. Raw response snippet: {raw_content[:200]}"
                print(f"[Clipper/Detector] Warning: {last_error}, attempting fallback model...")

        if not ranked_candidates:
            raise RuntimeError(f"Virality Scoring Tournament failed across all models. Last error: {last_error}")

        # Map candidate_id back to candidate dictionary
        candidate_map = {c["id"]: c for c in candidates}

        # Step 4: Semantic Diversity Selection (Ensure 3 distinct categories / timeline acts)
        selected_candidates = self._enforce_semantic_diversity(
            ranked_candidates=ranked_candidates,
            candidate_map=candidate_map,
            num_clips=num_clips,
        )

        # Step 5: Snap timestamps to exact Whisper word boundaries & enrich
        snapped_highlights = self._snap_and_enrich_highlights(
            selected_candidates=selected_candidates,
            all_words=all_words,
            min_duration=min_duration,
            max_duration=max_duration,
        )

        return snapped_highlights

    def _build_tournament_prompt(self, candidates: List[Dict[str, Any]], total_duration: float) -> str:
        """Format candidate blocks with timeline zones and candidate IDs for tournament judging."""
        candidate_lines = []
        for c in candidates:
            candidate_lines.append(
                f"--- CANDIDATE #{c['id']} [{c['act']}] [{c['start']}s - {c['end']}s] ({c['duration']}s) ---\n"
                f"OPENING HOOK: \"{c['clean_hook']}\"\n"
                f"CONTENT:\n{c['text']}\n"
                f"CLOSING RESOLUTION: \"{c['closing']}\"\n"
            )

        return f"""PODCAST DURATION: {total_duration:.1f}s ({total_duration/60:.1f} min)
TOTAL CANDIDATES SUBMITTED: {len(candidates)}

INSTRUCTIONS:
Evaluate all candidate blocks using the 4-signal rubric:
1. Hook Strength (0-35)
2. Narrative Completeness (0-30)
3. Comment / Debate Arousal (0-20)
4. Information Density (0-15)

Select and return the TOP 6 highest-scoring candidates ranked in descending order of total_score.
Ensure the top candidates represent diverse topics (Story, Business/Money, Psychology/Human Behavior, Tech/Future) and different parts of the podcast.
Output valid JSON containing only the TOP 6 candidates.

CANDIDATES TO EVALUATE:
{chr(10).join(candidate_lines)}
"""

    def _enforce_semantic_diversity(
        self,
        ranked_candidates: List[Dict[str, Any]],
        candidate_map: Dict[int, Dict[str, Any]],
        num_clips: int,
    ) -> List[Dict[str, Any]]:
        """
        Select top N clips enforcing diversity in topic category and timeline position.
        """
        # Attach candidate reference data
        enriched_pool = []
        for r in ranked_candidates:
            cid = r.get("candidate_id")
            cand = candidate_map.get(cid, {})
            # Compute total_score if not explicitly present
            h_score = int(r.get("hook_score", 25))
            n_score = int(r.get("narrative_score", 22))
            d_score = int(r.get("debate_score", 15))
            dens_score = int(r.get("density_score", 12))
            calc_total = h_score + n_score + d_score + dens_score
            total_score = int(r.get("total_score", calc_total))

            enriched_pool.append({
                **r,
                "start_time": cand.get("start", r.get("start_time")),
                "end_time": cand.get("end", r.get("end_time")),
                "act": cand.get("act", "General"),
                "act_num": cand.get("act_num", 1),
                "hook_score": h_score,
                "narrative_score": n_score,
                "debate_score": d_score,
                "density_score": dens_score,
                "total_score": total_score,
                "category": r.get("category", "Mindset & Story"),
                "mood": r.get("mood", "chill_lofi"),
            })

        # Sort strictly by total score
        enriched_pool.sort(key=lambda x: x["total_score"], reverse=True)

        selected: List[Dict[str, Any]] = []
        seen_categories = set()
        seen_acts = set()

        # Pass A: Pick highest-scoring candidates with distinct categories
        for item in enriched_pool:
            cat = item["category"]
            if cat not in seen_categories:
                # Also ensure temporal non-overlap with already selected
                overlaps = False
                for s in selected:
                    if abs(item["start_time"] - s["start_time"]) < 80.0:
                        overlaps = True
                        break
                if not overlaps:
                    selected.append(item)
                    seen_categories.add(cat)
                    seen_acts.add(item["act_num"])
                    if len(selected) >= num_clips:
                        break

        # Pass B: If we still need more clips, pick next best non-overlapping candidates
        if len(selected) < num_clips:
            for item in enriched_pool:
                if item in selected:
                    continue
                overlaps = False
                for s in selected:
                    if abs(item["start_time"] - s["start_time"]) < 60.0:
                        overlaps = True
                        break
                if not overlaps:
                    selected.append(item)
                    if len(selected) >= num_clips:
                        break

        # Final fallback: take top num_clips
        if len(selected) < num_clips:
            selected = enriched_pool[:num_clips]

        return selected

    def _snap_and_enrich_highlights(
        self,
        selected_candidates: List[Dict[str, Any]],
        all_words: List[Dict[str, Any]],
        min_duration: float,
        max_duration: float,
    ) -> List[Dict[str, Any]]:
        """
        Snap candidate timestamps to precise Whisper word boundaries.
        Trim leading conversational filler words so the short opens with maximum impact.
        """
        highlights: List[Dict[str, Any]] = []
        filler_words = {"so", "yeah", "and", "um", "uh", "like", "well", ">>", "you", "know"}

        for rank, c in enumerate(selected_candidates, 1):
            raw_start = float(c.get("start_time", 0))
            raw_end = float(c.get("end_time", raw_start + 40.0))

            if not all_words:
                snapped_start = raw_start
                snapped_end = raw_end
                clip_words = []
            else:
                # Find start word index closest to raw_start
                start_word_idx = min(
                    range(len(all_words)),
                    key=lambda i: abs(all_words[i]["start"] - raw_start),
                )

                # Skip leading conversational filler words if present at hook start
                while start_word_idx < len(all_words) - 1:
                    w_clean = re.sub(r"[^\w]", "", all_words[start_word_idx]["word"].lower())
                    if w_clean in filler_words and (all_words[start_word_idx + 1]["start"] - raw_start) < 2.5:
                        start_word_idx += 1
                    else:
                        break

                # Find end word index closest to raw_end
                end_word_idx = min(
                    range(len(all_words)),
                    key=lambda i: abs(all_words[i]["end"] - raw_end),
                )

                if end_word_idx <= start_word_idx:
                    end_word_idx = min(len(all_words) - 1, start_word_idx + 15)

                snapped_start = all_words[start_word_idx]["start"]
                snapped_end = all_words[end_word_idx]["end"]

                # Ensure duration constraints
                dur = snapped_end - snapped_start
                if dur < min_duration:
                    target_end = snapped_start + min_duration
                    candidates_idx = [i for i in range(start_word_idx, len(all_words)) if all_words[i]["end"] >= target_end]
                    if candidates_idx:
                        end_word_idx = candidates_idx[0]
                        snapped_end = all_words[end_word_idx]["end"]

                if (snapped_end - snapped_start) > max_duration:
                    target_end = snapped_start + max_duration
                    for i in range(start_word_idx, end_word_idx + 1):
                        if all_words[i]["end"] <= target_end:
                            end_word_idx = i
                        else:
                            break
                    snapped_end = all_words[end_word_idx]["end"]

                # Prefer snapping end on a sentence-terminal word (. ? !)
                for i in range(end_word_idx, max(start_word_idx + 5, end_word_idx - 6), -1):
                    word_str = all_words[i]["word"].strip()
                    if word_str and word_str[-1] in ".?!":
                        # If duration remains >= min_duration, anchor to this clean punchline word!
                        if (all_words[i]["end"] - snapped_start) >= min_duration:
                            end_word_idx = i
                            snapped_end = all_words[end_word_idx]["end"]
                            break

                # Extract relative words for subtitle rendering
                clip_words = []
                for w in all_words[start_word_idx : end_word_idx + 1]:
                    clip_words.append({
                        "word": w["word"],
                        "start": round(w["start"] - snapped_start, 3),
                        "end": round(w["end"] - snapped_start, 3),
                        "abs_start": w["start"],
                        "abs_end": w["end"],
                    })

            actual_duration = round(snapped_end - snapped_start, 2)
            word_count = len(clip_words)
            wpm = round((word_count / actual_duration) * 60, 1) if actual_duration > 0 else 150.0

            # Multi-signal mood detection (Transcript category + LLM mood + Speech WPM)
            raw_mood = str(c.get("mood", "")).lower().strip()
            cat_lower = str(c.get("category", "")).lower()

            valid_moods = {"dark_suspense", "emotional_piano", "high_energy", "curious_investigative", "chill_lofi"}
            if raw_mood in valid_moods:
                assigned_mood = raw_mood
            else:
                if "story" in cat_lower or "mindset" in cat_lower:
                    assigned_mood = "emotional_piano"
                elif "business" in cat_lower or "money" in cat_lower or "career" in cat_lower:
                    assigned_mood = "high_energy"
                elif "tech" in cat_lower or "future" in cat_lower or "ai" in cat_lower:
                    assigned_mood = "curious_investigative"
                elif "psychology" in cat_lower or "danger" in cat_lower:
                    assigned_mood = "dark_suspense"
                else:
                    assigned_mood = "chill_lofi"

            # High speech velocity (WPM >= 170) pushes toward high_energy
            if wpm >= 170.0 and assigned_mood in ["chill_lofi", "emotional_piano"]:
                assigned_mood = "high_energy"

            highlights.append({
                "rank": rank,
                "title": c.get("title", f"Highlight #{rank}"),
                "start_time": round(snapped_start, 3),
                "end_time": round(snapped_end, 3),
                "duration": actual_duration,
                "hook_sentence": c.get("clean_hook") or c.get("hook_sentence", ""),
                "punchline_resolution": c.get("punchline_resolution", ""),
                "category": c.get("category", "General"),
                "mood": assigned_mood,
                "wpm": wpm,
                "hook_score": c.get("hook_score", 30),
                "narrative_score": c.get("narrative_score", 25),
                "debate_score": c.get("debate_score", 18),
                "density_score": c.get("density_score", 12),
                "viral_score": c.get("total_score", 85),
                "virality_reason": c.get("virality_reason", "High-retention moment."),
                "hashtags": c.get("hashtags", ["#podcast", "#shorts", "#viral"]),
                "act": c.get("act", "General"),
                "words": clip_words,
            })

        return highlights
