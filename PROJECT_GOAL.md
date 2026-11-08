# All-in-One AI Shorts Generator Agent: Master Architecture & Goals

## 1. Project Overview & Vision
The goal of this project is to build an automated, modular AI Shorts Agent capable of generating high-retention vertical (9:16) short-form content for **YouTube Shorts, Instagram Reels, and TikTok** across 3 primary viral formats.

Each format shares a common multimedia core (voice synthesis, word-level subtitle rendering, audio ducking, and FFmpeg video compositing).

---

## 2. The 3 Supported Content Modes

```text
                               ┌───────────────────────────┐
                               │     AI SHORTS AGENT       │
                               └─────────────┬─────────────┘
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      ▼                                      ▼                                      ▼
[MODE 1: FACT/NARRATIVE]              [MODE 2: STORY/GAMEPLAY]              [MODE 3: SMART CLIPPER]
Based on MoneyPrinterTurbo            Based on RedditVideoMakerBot          Based on Clippyme / Anil-matcha
• LLM Script & Pexels B-roll          • Text/Reddit Story                   • yt-dlp Video Download
• Ken Burns 9:16 motion               • Background Gameplay loop            • Whisper timestamping
• Cinematic storytelling              • Split-screen or full-screen         • LLM viral highlight cut
                                                                            • OpenCV Face-Track crop
      └──────────────────────────────────────┼──────────────────────────────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────┐
                              │     SHARED HYBRID ENGINE    │
                              ├─────────────────────────────┤
                              │ • TTS: Edge-TTS / ElevenLabs│
                              │ • STT: faster-whisper       │
                              │ • Subtitles: Word-level ASS │
                              │ • Compositor: FFmpeg Engine │
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                                     [ Final 9:16 Video ]
```

### **Mode 1: Faceless Narrative & Facts (CURRENT FOCUS)**
* **Inspiration:** `harry0703/MoneyPrinterTurbo`, `kaomei/stickman-video-director`.
* **Input:** A topic, niche, or prompt (e.g., *"Dark psychology tricks"*, *"3 forbidden historical events"*).
* **Pipeline:**
  1. **LLM Scene Scripting:** Generates high-retention narration with visual search keywords for every 3–5 seconds.
  2. **Voice Synthesis (TTS):** Generates voiceover via free Microsoft Edge neural voices (`edge-tts`) or ElevenLabs.
  3. **Visual Ingestion:** Queries royalty-free 9:16 B-roll via Pexels API (or generates AI imagery with Ken Burns slow zoom).
  4. **Dynamic Subtitles:** Uses `faster-whisper` for word-level timestamps, generating bouncing "Hormozi-style" captions.
  5. **Compositing:** FFmpeg stitches video clips, applies audio ducking with background music, and burns subtitles into the final MP4.

---

### **Mode 2: Narrative + Gameplay (Split-Screen / Reddit Style)**
* **Inspiration:** `elebumm/RedditVideoMakerBot`.
* **Input:** A Reddit thread URL, custom dramatic story, or quiz format.
* **Pipeline:**
  1. Script formatting with aggressive 0–3 second hook.
  2. Fast-paced TTS synthesis.
  3. Seamless loop selection from local gameplay vault (Minecraft parkour, GTA stunt runs, Subway Surfers).
  4. Bold centered dynamic text overlay with sound effect accents.

---

### **Mode 3: Long-Form Video & Podcast Smart Clipper**
* **Inspiration:** `Anil-matcha/AI-Youtube-Shorts-Generator`, `fralapo/clippyme`.
* **Input:** YouTube video URL or local long-form MP4 (e.g., podcast, interview, documentary).
* **Pipeline:**
  1. `yt-dlp` extracts high-res video and audio track.
  2. `faster-whisper` produces full transcript with timestamps.
  3. LLM analyzes viral hook potential and selects optimal 30–60s segments.
  4. OpenCV / MediaPipe active-speaker tracking crops 16:9 into dynamic 9:16.
  5. Burns dynamic subtitles over the speaker.

---

## 3. Notable Reference Repositories & Agent Frameworks

| Repository | GitHub Link | Core Strength / Key Concept |
| :--- | :--- | :--- |
| **MoneyPrinterTurbo** | [`harry0703/MoneyPrinterTurbo`](https://github.com/harry0703/MoneyPrinterTurbo) | Gold standard for zero-cost faceless shorts (Edge-TTS + Pexels + Whisper + FFmpeg). |
| **RedditVideoMakerBot**| [`elebumm/RedditVideoMakerBot`](https://github.com/elebumm/RedditVideoMakerBot) | Automated Reddit-to-video pipeline with background gameplay loops and UI snapshotting. |
| **Clippyme** | [`fralapo/clippyme`](https://github.com/fralapo/clippyme) | Automated podcast highlight extraction with smart reframing and transcription. |
| **AI Shorts Generator**| [`Anil-matcha/AI-Youtube-Shorts-Generator`](https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator) | Open-source Opus Clip alternative for long-to-short conversion. |
| **HyperFrames** | [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes) | HeyGen's agentic framework for deterministic HTML/CSS-to-MP4 video generation. |
| **Stickman Video Director** | [`kaomei/stickman-video-director`](https://github.com/kaomei/stickman-video-director) | Autonomous AI storyboard director for animated shorts. |
| **AniDoodle** | [`alexgreensh/anidoodle`](https://github.com/alexgreensh/anidoodle) | Procedural hand-drawn/watercolor/sketch animation written as code. |
| **Hypit** | [`hypit-ai/hypit`](https://github.com/hypit-ai/hypit) | Viral video DSL (`.svml`) using word-anchored timings to clone short-form templates. |

---

## 4. Shared Core Engine Specification

To keep the codebase maintainable and DRY (Don't Repeat Yourself), the following modules form the core engine:
* `src/core/audio.py`: TTS generation (`edge-tts` / ElevenLabs) + BGM mixer with audio ducking.
* `src/core/subtitles.py`: `faster-whisper` word-level alignment $\rightarrow$ `.ass` karaoke subtitle generator.
* `src/core/video.py`: FFmpeg compositing wrapper (scaling to 1080x1920, transitions, subtitle burning).
* `src/core/config.py`: Centralized configuration, API keys, paths, and default styles.

---

## 5. Development Roadmap & Progress

- [x] **Phase 1: Environment & Shared Core Engine**
  - [x] Check / configure FFmpeg and Python environment
  - [x] Implement `src/voice/tts.py` (Edge-TTS) & `src/compositor/audio_mixer.py` (BGM ducking)
  - [x] Implement `src/subtitles/` (Whisper word-level `.ass` generator with active word pop)
  - [x] Implement `src/compositor/ffmpeg_engine.py` (FFmpeg 9:16 rendering pipeline)
- [x] **Phase 2: Mode 1 Implementation (Faceless Facts & Stories)**
  - [x] LLM Scriptwriter (`src/llm/` using OpenRouter `meta/muse-spark-1.3-contributor`)
  - [x] Visual B-roll fetcher (`src/visuals/pexels.py` & Ken Burns motion)
  - [x] End-to-end CLI command: `python run.py --mode facts --topic "..."`
  - [x] Production verification: 1080x1920 MP4 generated with subtitle burn-in and audio ducking
- [ ] **Phase 3: Mode 2 Implementation (Stories + Gameplay)** *(Next Chat)*
  - [ ] Gameplay asset vault manager
  - [ ] Reddit / custom story parser & hook optimizer
  - [ ] Split-screen compositor
- [x] **Phase 4: Mode 3 Implementation (Smart Clipper)**
  - [x] `yt-dlp` video & audio ingestion with local caching
  - [x] `faster-whisper` word-level alignment & `.ass` subtitle generator
  - [x] OpenRouter LLM viral highlight detector with scoring & hook extraction
  - [x] OpenCV YuNet Dynamic Shot-Aware Reframer (solo speaker 9:16 + automatic dual-speaker split screen)
  - [x] Polish engine: micro-zoom punch-in, glowing progress bar, and broadcast loudness mastering
- [ ] **Phase 5: Unified Agent Interface & Automation**
  - [ ] Interactive CLI / Web UI
  - [ ] Auto-scheduling / platform upload integration
