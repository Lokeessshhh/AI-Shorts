"""Autonomous Trend Scout for AI Shorts.
Scouts Google Trends RSS, Hacker News API, and YouTube podcast feeds with zero API costs.
Uses LLM reasoning to synthesize the highest-virality, fresh topics for Modes 1, 2, and 3.
"""

import sys
import json
import re
import random
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import concurrent.futures
from typing import Dict, List, Optional, Any

from ..config import config
from ..llm.client import OpenRouterClient
from .state_manager import StateManager


class TrendScout:
    """Scouts internet sources and reasons over trending signals for short-form video generation."""

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        llm_client: Optional[OpenRouterClient] = None,
    ):
        self.state = state_manager or StateManager()
        self.llm = llm_client or OpenRouterClient()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    # =========================================================================
    # MODE 1: Faceless Facts & Educational Mysteries (Google Trends RSS)
    # =========================================================================
    def scout_mode1_topic(self, max_attempts: int = 3) -> str:
        """
        Scout Google Trends RSS, analyze trending concepts, and synthesize a
        high-retention educational mystery short topic.
        """
        print("[TrendScout/Mode1] Querying Google Trends RSS (geo=US)...")
        trending_signals = self._fetch_google_trends()
        if not trending_signals:
            print("[TrendScout/Mode1] Trends feed quiet; using curated high-virality trend seeds.")
            trending_signals = [
                "Aviation mysteries and aerodynamics quirks",
                "Deep ocean extreme pressure phenomena",
                "Human cognitive perception and optical illusions",
                "Historical engineering feats and accidental inventions",
                "Everyday architectural tricks and consumer psychology",
            ]

        recent_completed = self.state.get_completed_topics()[-20:]

        system_prompt = (
            "You are an elite short-form content director specializing in viral educational mysteries, "
            "psychology quirks, science phenomena, and 'Why X Exists' faceless YouTube Shorts and TikToks. "
            "Your hooks achieve 80%+ retention in the first 2 seconds. "
            "Respond ONLY with valid JSON."
        )

        user_prompt = f"""Analyze these current trending news items and cultural signals:
{json.dumps(trending_signals[:12], indent=2)}

Task:
Synthesize or extract ONE mind-blowing, counter-intuitive educational mystery, psychological quirk, 
everyday engineering secret, or science phenomenon inspired by or tangentially linked to these trends.

STRICT CONSTRAINTS:
1. Must begin with an irresistible curiosity hook (e.g. "Why X...", "The Bizarre Reason Why X...", "What Actually Happens When X...").
2. Must NOT be shallow celebrity gossip, breaking political news, or sports scores.
3. Must be educational, universally relatable, and visually engaging for a 30-second vertical video.
4. Do NOT choose or resemble any of these already completed topics:
{json.dumps(recent_completed, indent=2)}

Return strictly in this JSON format:
{{
  "topic": "Concise, punchy video premise (e.g. Why Jet Engines Have Spirals Painted on the Nose Cone)",
  "hook": "First sentence hook that forces curiosity",
  "reasoning": "Why this will achieve viral retention"
}}"""

        for attempt in range(max_attempts):
            try:
                raw_response = self.llm.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.8,
                )
                clean_json = self.llm._clean_json_string(raw_response)
                parsed = json.loads(clean_json)
                topic = parsed.get("topic", "").strip()

                if topic and self.state.is_topic_fresh(topic):
                    print(f"[TrendScout/Mode1] Selected Viral Topic: \"{topic}\"")
                    print(f"  * Curiosity Hook: \"{parsed.get('hook', '')}\"")
                    print(f"  * Virality Logic: {parsed.get('reasoning', '')}")
                    return topic
                else:
                    print(f"[TrendScout/Mode1] Topic '{topic}' already produced or similar; retrying attempt {attempt+1}...")
            except Exception as e:
                print(f"[TrendScout/Mode1] LLM generation error ({e}); retrying...")

        # Robust evergreen fallback
        evergreen_fallback = "Why Airplane Windows Always Have That Tiny Hole at the Bottom"
        if not self.state.is_topic_fresh(evergreen_fallback):
            evergreen_fallback = f"The Shocking Reason Why Clocks Tick Clockwise Instead of Counter-Clockwise"
        return evergreen_fallback

    def _fetch_google_trends(self) -> List[str]:
        """Fetch trending query titles from Google Trends RSS feed."""
        url = "https://trends.google.com/trending/rss?geo=US"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                content = response.read()
                tree = ET.fromstring(content)
                titles = []
                for item in tree.findall(".//item"):
                    title_elem = item.find("title")
                    if title_elem is not None and title_elem.text:
                        clean_text = title_elem.text.strip()
                        if clean_text:
                            titles.append(clean_text)
                return titles
        except Exception as e:
            print(f"[TrendScout/Mode1] Warning: Google Trends fetch failed ({e})")
            return []

    # =========================================================================
    # MODE 2: Dev vs Claude Tech Dialogue (Hacker News API)
    # =========================================================================
    def scout_mode2_topic(self, max_attempts: int = 3) -> str:
        """
        Scout Hacker News top stories API, identify a hot computing / software dilemma,
        and formulate a punchy premise with a real-world physical analogy.
        """
        print("[TrendScout/Mode2] Querying Hacker News Top Stories API...")
        hn_stories = self._fetch_hacker_news_stories(limit=15)
        if not hn_stories:
            print("[TrendScout/Mode2] HN feed unavailable; using core system architecture archetypes.")
            hn_stories = [
                "How SSD garbage collection actually works under the hood",
                "Why distributed databases can never have consistency, availability, and partition tolerance all at once",
                "How operating systems swap memory to disk when RAM is full",
                "Why TCP does a 3-way handshake before sending a single byte",
                "How GPU parallel processing differs fundamentally from CPU cores",
            ]

        recent_completed = self.state.get_completed_topics()[-20:]

        system_prompt = (
            "You are a lead software engineer and educator specializing in high-engagement technical dialogues "
            "between a curious, skeptical human developer and an ultra-smart AI assistant (Claude). "
            "Your short-form videos explain deep technical computing dilemmas using tangible, real-world physical metaphors "
            "that make senior engineers smile and beginners instantly understand. "
            "Respond ONLY with valid JSON."
        )

        user_prompt = f"""Analyze these top technical articles and discussions from Hacker News:
{json.dumps(hn_stories, indent=2)}

Task:
Identify ONE fundamental computing, software architecture, networking, or hardware concept 
relevant to modern engineering. Formulate a captivating conversational premise for a 2-person 
dialogue between Dev and Claude.

STRICT CONSTRAINTS:
1. Must feature a vivid physical real-world analogy (e.g. shipping containers, bank tellers, postal routing, library cards).
2. Must be punchy, debate-worthy, and concise (under 12 words).
3. Do NOT choose or resemble any of these already completed topics:
{json.dumps(recent_completed, indent=2)}

Return strictly in this JSON format:
{{
  "topic": "Concise premise (e.g. Why Databases Write To A Log First: The Bank Ledger Analogy)",
  "physical_analogy": "The concrete object/metaphor (e.g. A physical spiral notebook on a teller desk)",
  "core_dilemma": "What the developer is confused about"
}}"""

        for attempt in range(max_attempts):
            try:
                raw_response = self.llm.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.8,
                )
                clean_json = self.llm._clean_json_string(raw_response)
                parsed = json.loads(clean_json)
                topic = parsed.get("topic", "").strip()

                if topic and self.state.is_topic_fresh(topic):
                    print(f"[TrendScout/Mode2] Selected Tech Topic: \"{topic}\"")
                    print(f"  * Physical Analogy: \"{parsed.get('physical_analogy', '')}\"")
                    print(f"  * Core Dilemma: {parsed.get('core_dilemma', '')}")
                    return topic
                else:
                    print(f"[TrendScout/Mode2] Topic '{topic}' already produced or similar; retrying attempt {attempt+1}...")
            except Exception as e:
                print(f"[TrendScout/Mode2] LLM generation error ({e}); retrying...")

        # Robust fallback
        fallback = "Why Modern Web Browsers Spawn Separate Processes For Every Single Tab"
        if not self.state.is_topic_fresh(fallback):
            fallback = "How Virtual Memory Actually Prevents One Crashing App From Nuking Your Entire OS"
        return fallback

    def _fetch_hacker_news_stories(self, limit: int = 15) -> List[str]:
        """Fetch top story titles from Hacker News Firebase REST API."""
        top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        try:
            req = urllib.request.Request(top_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=6) as response:
                story_ids = json.loads(response.read().decode())[:limit]

            def fetch_title(item_id: int) -> Optional[str]:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
                try:
                    item_req = urllib.request.Request(item_url, headers=self.headers)
                    with urllib.request.urlopen(item_req, timeout=5) as r:
                        data = json.loads(r.read().decode())
                        return data.get("title")
                except Exception:
                    return None

            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                results = list(executor.map(fetch_title, story_ids))

            return [t for t in results if t]
        except Exception as e:
            print(f"[TrendScout/Mode2] Warning: Hacker News fetch failed ({e})")
            return []

    # =========================================================================
    # MODE 3: Podcast & Video Smart Clipper (YouTube Feeds via yt-dlp)
    # =========================================================================
    def scout_mode2_podcast(self) -> Dict[str, str]:
        """Alias for Mode 2 Podcast Clipper."""
        return self._scout_podcast()

    scout_mode3_podcast = scout_mode2_podcast

    def _scout_podcast(self) -> Dict[str, str]:
        """
        Inspect curated high-profile podcast channels, select the newest unclipped
        video URL using yt-dlp flat-playlist metadata.
        """
        watchlist = [
            ("Andrew Huberman", "https://www.youtube.com/@hubermanlab/videos"),
            ("The Diary Of A CEO", "https://www.youtube.com/@TheDiaryOfACEO/videos"),
            ("Raj Shamani", "https://www.youtube.com/@RajShamani/videos"),
        ]
        # Shuffle to distribute variety across runs
        channels = list(watchlist)
        random.shuffle(channels)

        print("[TrendScout/Mode3] Scouting podcast watchlist for unclipped episodes...")

        for channel_name, channel_url in channels:
            print(f"  * Checking channel: {channel_name} ({channel_url})...")
            try:
                cmd = [
                    sys.executable,
                    "-m",
                    "yt_dlp",
                    "--flat-playlist",
                    "--dump-json",
                    "--extractor-args",
                    "youtube:player_client=android",
                    "-I",
                    "1:6",
                    channel_url,
                ]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=25,
                )

                if proc.returncode != 0:
                    print(f"  * Warning: yt-dlp failed on {channel_name} ({proc.stderr.strip()[:100]})")
                    continue

                for line in proc.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        vid_id = entry.get("id")
                        title = entry.get("title", "Podcast Episode")
                        duration = entry.get("duration", 0)

                        if not vid_id:
                            continue

                        # Filter out YouTube Shorts from candidate list (must be > 5 mins long-form)
                        if duration and duration < 300:
                            continue

                        if not self.state.is_video_clipped(vid_id):
                            video_url = f"https://www.youtube.com/watch?v={vid_id}"
                            print(f"[TrendScout/Mode3] Found Unclipped Episode from {channel_name}:")
                            print(f"  * Title: \"{title}\"")
                            print(f"  * URL: {video_url}")
                            return {
                                "url": video_url,
                                "video_id": vid_id,
                                "title": title,
                                "channel": channel_name,
                            }
                        else:
                            print(f"  * Skipping previously clipped ID: {vid_id} ('{title[:30]}...')")
                    except Exception:
                        continue

            except Exception as e:
                print(f"  * Error scouting {channel_name}: {e}")

        # Fallback podcast URL if all watchlist videos were already clipped or unreachable
        print("[TrendScout/Mode3] All recent uploads processed; selecting standard high-retention fallback episode.")
        return {
            "url": "https://www.youtube.com/watch?v=yUdg7drjrZY",
            "video_id": "yUdg7drjrZY",
            "title": "Essentials: Cold & Heat Exposure for Metabolic Health | Dr. Susanna Soberg",
            "channel": "Andrew Huberman",
        }
