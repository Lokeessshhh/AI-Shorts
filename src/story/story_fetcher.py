"""Mode 2 Story Ingestion & AI Storyteller Engine.
Fetches public Reddit threads without API keys (via .json endpoint)
or generates original, viral, high-drama stories (AITA, Confessions, TIFU) using OpenRouter.
Includes 4-act virality structure, multi-voice dialogue parsing, top comment extraction,
and automatic BGM mood categorization.
"""

import json
import re
import random
from typing import Dict, Any, Optional, List
import requests

from ..config import config
from .speech_normalizer import normalize_for_speech


AI_STORY_SYSTEM_PROMPT = """You are an elite short-form screenwriter specializing in viral TikTok & Reddit story shorts (r/AmItheAsshole, r/confession, r/tifu, relationship & workplace drama).

Your stories consistently hit millions of views because they follow this strict 4-act viral formula:
1. SHOCK HOOK (0-3s): Opens with an immediate controversial action or question that stops the scroll. Zero preamble.
2. ESCALATING TENSION (3-20s): Fast-paced context with relatable, high-stakes emotional conflict.
3. THE PLOT TWIST (20-40s): An unexpected revelation that completely flips the situation.
4. UNRESOLVED MORAL DILEMMA (40-55s): Ends with a burning question that forces viewers to debate in the comments.

MULTI-VOICE DIALOGUE:
Break down the story into clean dialogue_segments with the appropriate speaker:
- "narrator": Main storyteller voice (authoritative, engaging).
- "character_female": Quoted dialogue spoken by female characters (wife, sister, mom, girlfriend, coworker).
- "character_male": Quoted dialogue spoken by male characters (husband, brother, dad, boyfriend, boss).

LENGTH CONSTRAINT:
- The total story text across all dialogue segments must be between 130 and 160 words (target spoken duration: 45 to 55 seconds).
- Pacing must be punchy, direct, and conversational.

OUTPUT FORMAT REQUIREMENTS:
You MUST respond with valid JSON ONLY (no markdown fences, no conversational prose):
{
  "subreddit": "r/AmItheAsshole",
  "author": "u/throwaway_drama_42",
  "score": "38.4k",
  "comments_count": "4.2k",
  "title": "AITA for walking out of my sister's wedding after what she said about my wife?",
  "spoken_hook": "Am I the jerk for walking out of my sister's wedding after what she said about my wife?",
  "bgm_mood": "dark_suspense",
  "dialogue_segments": [
    {"speaker": "narrator", "text": "My sister told me I wasn't welcome at her wedding if I brought my wife."},
    {"speaker": "narrator", "text": "When I confronted her, she looked me dead in the eye and said:"},
    {"speaker": "character_female", "text": "She completely outshines me, and this is my day!"},
    {"speaker": "narrator", "text": "I didn't argue. I just stood up, canceled the fifteen thousand dollar venue I paid for, and left."}
  ],
  "twist": "I canceled the fifteen thousand dollar venue I paid for and left.",
  "top_comment": {
    "author": "u/justice_served",
    "score": "22.8k",
    "body": "Not the jerk! She wanted her day, so you gave her the full cost of it."
  },
  "hashtags": ["#redditstories", "#aita", "#drama", "#familydrama", "#storytime", "#shorts"]
}
"""


class StoryFetcher:
    """Ingests Reddit threads without API keys or generates original AI stories."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.openrouter_api_key
        self.model = model or config.openrouter_model
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

    def _format_count(self, num: int) -> str:
        """Format 12400 -> '12.4k'."""
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num / 1_000:.1f}k"
        return str(num)

    def _infer_bgm_mood(self, text: str) -> str:
        """Classify story emotion into one of the 5 vault moods."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["cheat", "police", "arrest", "caught", "secret", "betray", "phone", "hidden"]):
            return "dark_suspense"
        elif any(w in text_lower for w in ["cry", "cried", "divorce", "passed away", "heartbreak", "hospital", "tears", "sad"]):
            return "emotional_piano"
        elif any(w in text_lower for w in ["fired", "revenge", "boss", "sue", "lawyer", "kicked out", "gym", "win"]):
            return "high_energy"
        elif any(w in text_lower for w in ["weird", "mystery", "unexplained", "dna", "stranger", "creepy"]):
            return "curious_investigative"
        return "chill_lofi"

    def fetch_from_reddit_url(self, post_url: str) -> Dict[str, Any]:
        """
        Scrape a public Reddit post via the .json endpoint. Zero credentials required.
        Extracts title, body, author, upvotes, and top comment.
        """
        clean_url = post_url.split("?")[0].rstrip("/")
        json_url = f"{clean_url}.json?raw_json=1"

        print(f"[Story/Fetcher] Scraping Reddit URL: {json_url}...")
        resp = requests.get(json_url, headers=self.headers, timeout=15)

        if resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch Reddit post (HTTP {resp.status_code}). URL may be private or deleted."
            )

        data = resp.json()
        post_data = data[0]["data"]["children"][0]["data"]

        title = post_data.get("title", "")
        body = post_data.get("selftext", "")
        author = "u/" + post_data.get("author", "anonymous")
        subreddit = "r/" + post_data.get("subreddit", "reddit")
        score = self._format_count(int(post_data.get("score", 15000)))
        comments_count = self._format_count(int(post_data.get("num_comments", 850)))

        # Clean title & body for speech
        spoken_title = normalize_for_speech(title)
        spoken_body = normalize_for_speech(body)
        full_spoken_text = f"{spoken_title}. {spoken_body}"

        # Extract top comment if present
        top_comment = None
        try:
            if len(data) > 1:
                comments_list = data[1].get("data", {}).get("children", [])
                for c in comments_list:
                    cdata = c.get("data", {})
                    cbody = cdata.get("body", "").strip()
                    if cbody and cbody != "[deleted]" and len(cbody) > 20:
                        top_comment = {
                            "author": "u/" + cdata.get("author", "top_commenter"),
                            "score": self._format_count(int(cdata.get("score", 4500))),
                            "body": normalize_for_speech(cbody[:180]),
                        }
                        break
        except Exception:
            pass

        # Extract dialogue segments from quotes if any
        dialogue_segments = self._extract_dialogue_segments(spoken_body)
        bgm_mood = self._infer_bgm_mood(f"{title} {body}")

        return {
            "source_type": "reddit_url",
            "title": title,
            "spoken_title": spoken_title,
            "spoken_hook": spoken_title,
            "author": author,
            "subreddit": subreddit,
            "score": score,
            "comments_count": comments_count,
            "body": body,
            "spoken_body": spoken_body,
            "full_spoken_text": full_spoken_text,
            "dialogue_segments": dialogue_segments,
            "top_comment": top_comment,
            "bgm_mood": bgm_mood,
            "hashtags": [f"#{subreddit.replace('r/', '')}", "#redditstories", "#storytime", "#shorts"],
        }

    def _extract_dialogue_segments(self, text: str) -> List[Dict[str, str]]:
        """Parse sentences into narrator and character dialogue segments."""
        segments = []
        # Split by sentences or dialogue quotes
        raw_parts = re.split(r'(".*?")', text)
        for part in raw_parts:
            part_clean = part.strip()
            if not part_clean:
                continue
            if part_clean.startswith('"') and part_clean.endswith('"'):
                inner = part_clean.strip('"').strip()
                if inner:
                    segments.append({"speaker": "character_female", "text": inner})
            else:
                segments.append({"speaker": "narrator", "text": part_clean})
        return segments if segments else [{"speaker": "narrator", "text": text}]

    def fetch_from_subreddit(self, subreddit_name: str) -> Dict[str, Any]:
        """Fetch top trending text post of the month from a given subreddit."""
        sub_clean = re.sub(r"^r\/", "", subreddit_name).strip()
        json_url = f"https://www.reddit.com/r/{sub_clean}/top.json?t=month&limit=15&raw_json=1"

        print(f"[Story/Fetcher] Fetching top posts from r/{sub_clean}...")
        resp = requests.get(json_url, headers=self.headers, timeout=15)

        if resp.status_code != 200:
            raise RuntimeError(f"Failed to query subreddit r/{sub_clean} (HTTP {resp.status_code}).")

        data = resp.json()
        children = data.get("data", {}).get("children", [])

        # Find first valid text post with substantial content (> 200 chars)
        for child in children:
            p = child.get("data", {})
            selftext = p.get("selftext", "").strip()
            if selftext and len(selftext) >= 150 and not p.get("stickied", False):
                permalink = "https://www.reddit.com" + p.get("permalink", "")
                return self.fetch_from_reddit_url(permalink)

        raise RuntimeError(f"No suitable text stories found in top posts of r/{sub_clean}.")

    def generate_ai_story(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate an original, viral, high-drama story tailored for TikTok & Shorts retention.
        Uses automatic model fallback.
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key is required for AI story generation.")

        user_prompt = "Generate a viral, high-drama, original Reddit story."
        if topic and topic.strip():
            user_prompt += f" Premise / Topic: {topic.strip()}"
        else:
            sample_themes = [
                "A sister-in-law wearing the bride's reserve dress to the rehearsal and getting caught",
                "Finding out a fiancé had a secret second phone right before the wedding",
                "A coworker taking credit for a major promotion project and the CEO finding out in the meeting",
                "A family inheritance dispute with a shock DNA test revelation",
                "Neighbor erecting a spite fence over a driveway dispute and losing their garage",
            ]
            user_prompt += f" Premise / Topic: {random.choice(sample_themes)}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/AI_Shorts",
            "X-Title": "AI Shorts Mode 2 Storyteller",
            "Content-Type": "application/json",
        }

        # Model queue with fallback
        model_queue = [self.model]
        for fb in ["openai/gpt-4o-mini", "meta-llama/llama-3.3-70b-instruct"]:
            if fb not in model_queue:
                model_queue.append(fb)

        parsed = None
        last_error = ""

        for model_to_try in model_queue:
            payload = {
                "model": model_to_try,
                "messages": [
                    {"role": "system", "content": AI_STORY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 4000,
            }

            print(f"[Story/Fetcher] Generating 4-act viral story via OpenRouter ({model_to_try})...")
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=90,
                )
            except Exception as e:
                last_error = str(e)
                continue

            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}: {resp.text}"
                continue

            resp_json = resp.json()
            raw_content = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Clean markdown code fences
            cleaned = re.sub(r"^```json\s*", "", raw_content, flags=re.MULTILINE)
            cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE).strip()

            try:
                parsed = json.loads(cleaned)
                break
            except json.JSONDecodeError:
                match = re.search(r"\{[\s\S]*\}", cleaned)
                if match:
                    try:
                        parsed = json.loads(match.group(0))
                        break
                    except Exception:
                        pass
                last_error = f"JSON decode failed for {model_to_try}."

        if not parsed:
            raise RuntimeError(f"Failed to generate story JSON across all models. Last error: {last_error}")

        title = parsed.get("title", "AITA for telling the truth?")
        subreddit = parsed.get("subreddit", "r/AmItheAsshole")
        author = parsed.get("author", "u/throwaway_drama")
        score = parsed.get("score", "32.4k")
        comments_count = parsed.get("comments_count", "2.8k")
        spoken_hook = parsed.get("spoken_hook", title)
        bgm_mood = parsed.get("bgm_mood", "dark_suspense")
        twist = parsed.get("twist", "")
        top_comment = parsed.get("top_comment")

        dialogue_segments = parsed.get("dialogue_segments", [])
        if not dialogue_segments:
            # Fallback to body
            body_text = parsed.get("body", "")
            dialogue_segments = [{"speaker": "narrator", "text": body_text}]

        # Clean dialogue segment texts for speech
        cleaned_segments = []
        body_parts = []
        for seg in dialogue_segments:
            norm_text = normalize_for_speech(seg.get("text", ""))
            cleaned_segments.append({
                "speaker": seg.get("speaker", "narrator"),
                "text": norm_text,
            })
            body_parts.append(norm_text)

        body = " ".join(body_parts)
        spoken_title = normalize_for_speech(title)
        spoken_hook = normalize_for_speech(spoken_hook)
        full_spoken_text = f"{spoken_hook}. {body}"

        return {
            "source_type": "ai_generated",
            "title": title,
            "spoken_title": spoken_title,
            "spoken_hook": spoken_hook,
            "author": author,
            "subreddit": subreddit,
            "score": score,
            "comments_count": comments_count,
            "body": body,
            "spoken_body": body,
            "full_spoken_text": full_spoken_text,
            "dialogue_segments": cleaned_segments,
            "twist": twist,
            "top_comment": top_comment,
            "bgm_mood": bgm_mood,
            "hashtags": parsed.get("hashtags", ["#redditstories", "#aita", "#viral", "#shorts"]),
        }
