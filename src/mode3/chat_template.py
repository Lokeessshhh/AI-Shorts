"""Mode 3: ChatGPT Chat Interface HTML/CSS/JS Template.
100% Faithful Replica of ChatGPT's Modern Dark Mode Mobile/Web Interface
(matching user reference screenshots media_1794222185297_ecef4ecf.png & media_1794221504605_e40d0223.jpg).
Features:
- Initial empty state with top bar icons, 'Hey, Lokesh. Ready to dive in?', and 3 feature shortcuts.
- Auto-expanding input card when user types so multi-line text is fully visible.
- User speaking audio locked to character keystroke pace.
- ChatGPT speaking audio locked to word token streaming pace.
- Right-aligned slate-blue user bubbles (#26365a) and left-aligned ChatGPT messages with action row.
"""

import json
from typing import Dict, List, Any, Tuple


class ChatTemplateBuilder:
    """Builds authentic, pixel-perfect ChatGPT vertical video interfaces."""

    def __init__(self, width: int = 1080, height: int = 1920):
        self.width = width
        self.height = height

    def compute_timeline(self, conversation: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float]:
        """
        Calculates exact millisecond timeline events synchronized with speech audio durations.
        """
        turns = conversation.get("turns", [])
        events: List[Dict[str, Any]] = []
        current_time = 0.85  # Initial pause showing the clean greeting screen

        for idx, turn in enumerate(turns):
            speaker = turn["speaker"]
            text = turn["text"].strip()
            audio_duration = float(turn.get("audio_duration", 3.0))

            if speaker == "user":
                # Speech starts right as user begins typing
                turn["speech_start_time"] = current_time
                num_chars = len(text)
                # Spread keystrokes across audio duration (finishing slightly before speech ends)
                typing_span = audio_duration * 0.95
                char_delay = typing_span / max(1, num_chars)

                for ch in text:
                    events.append({
                        "time": round(current_time, 4),
                        "type": "type_char",
                        "turn_idx": idx,
                        "char": ch
                    })
                    current_time += char_delay

                # Brief human pause after speaking before hitting send button
                current_time = max(current_time, turn["speech_start_time"] + audio_duration) + 0.30

                # Send event (input box clears and shrinks, bubble appears)
                events.append({
                    "time": round(current_time, 4),
                    "type": "send_message",
                    "turn_idx": idx,
                    "text": text
                })
                current_time += 0.45

            elif speaker == "chatgpt":
                # 1. Thinking state (pulsing dots)
                events.append({
                    "time": round(current_time, 4),
                    "type": "show_thinking",
                    "turn_idx": idx
                })
                current_time += 0.55

                # 2. Camera zoom-in on punchline (cinematic comedic emphasis)
                is_punchline_turn = (idx == len(turns) - 1)
                if is_punchline_turn:
                    events.append({
                        "time": round(current_time + 0.4, 4),
                        "type": "zoom_in",
                        "turn_idx": idx
                    })

                # 3. ChatGPT speaks while streaming response token-by-token
                turn["speech_start_time"] = current_time
                words = text.split(" ")
                num_words = len(words)
                streaming_span = audio_duration * 0.98
                word_delay = streaming_span / max(1, num_words)

                for w_idx, word in enumerate(words):
                    prefix = " " if w_idx > 0 else ""
                    events.append({
                        "time": round(current_time, 4),
                        "type": "stream_word",
                        "turn_idx": idx,
                        "word": prefix + word
                    })
                    current_time += word_delay

                current_time = max(current_time, turn["speech_start_time"] + audio_duration)

                # 4. Stream completed
                events.append({
                    "time": round(current_time, 4),
                    "type": "stream_end",
                    "turn_idx": idx
                })

                # 5. Punchline Impact: Vine Boom + Screen Shake + Sitcom Laugh Track
                if is_punchline_turn:
                    events.append({
                        "time": round(current_time, 4),
                        "type": "vine_boom",
                        "turn_idx": idx
                    })
                    events.append({
                        "time": round(current_time, 4),
                        "type": "boom_shake",
                        "turn_idx": idx
                    })
                    events.append({
                        "time": round(current_time + 0.12, 4),
                        "type": "laugh_track",
                        "turn_idx": idx
                    })
                    # Ample reading and laughing buffer
                    current_time += 2.80
                else:
                    current_time += 1.35

        # Final buffer so viewer enjoys punchline before video loops
        current_time += 1.60
        return events, current_time

    def render_html(self, conversation: Dict[str, Any], events: List[Dict[str, Any]], total_duration: float) -> str:
        """Generate self-contained standalone HTML page that auto-plays the conversation."""
        events_json = json.dumps(events, default=str)
        turns_json = json.dumps(conversation.get("turns", []), default=str)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ChatGPT Mode 3</title>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }}

    body {{
      width: {self.width}px;
      height: {self.height}px;
      background-color: #000000;
      color: #ececec;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      position: relative;
    }}

    /* Cinematic Camera Zoom & Shake Wrapper */
    #scene-wrapper {{
      width: 100%;
      height: 100%;
      position: relative;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transform-origin: 50% 18%;
      transition: transform 0.85s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    #scene-wrapper.zoomed-in {{
      transform: scale(1.15) translate(50px, 40px);
    }}

    @keyframes boom-shake {{
      0% {{ transform: scale(1.15) translate(50px, 40px); }}
      15% {{ transform: scale(1.18) translate(36px, 46px); }}
      30% {{ transform: scale(1.12) translate(64px, 34px); }}
      50% {{ transform: scale(1.16) translate(42px, 42px); }}
      75% {{ transform: scale(1.14) translate(56px, 38px); }}
      100% {{ transform: scale(1.15) translate(50px, 40px); }}
    }}

    #scene-wrapper.shake {{
      animation: boom-shake 0.45s ease-out;
    }}

    /* Top Bar - Exact match to mobile ChatGPT screenshot */
    header {{
      height: 120px;
      padding: 30px 48px 0 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background-color: #000000;
      z-index: 50;
    }}

    .header-icon-btn {{
      width: 54px;
      height: 54px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }}

    /* Initial Empty State (Center Greeting & Suggested Actions) */
    #empty-state {{
      position: absolute;
      top: 120px;
      left: 0;
      right: 0;
      bottom: 240px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 240px 60px 40px 60px;
      transition: opacity 0.35s ease, transform 0.35s ease;
      z-index: 20;
    }}

    #empty-state.hidden {{
      opacity: 0;
      transform: translateY(-24px);
      pointer-events: none;
    }}

    .center-greeting {{
      font-size: 48px;
      font-weight: 500;
      color: #ffffff;
      text-align: center;
      letter-spacing: -0.3px;
    }}

    .suggested-actions {{
      display: flex;
      flex-direction: column;
      gap: 38px;
      margin-bottom: 20px;
    }}

    .action-item {{
      display: flex;
      align-items: center;
      gap: 26px;
      color: #a4a4a4;
      font-size: 34px;
      font-weight: 400;
    }}

    .action-item svg {{
      stroke: #8e8e8e;
      width: 38px;
      height: 38px;
    }}

    /* Chat Messages Area */
    #chat-container {{
      position: absolute;
      top: 120px;
      left: 0;
      right: 0;
      bottom: 260px;
      padding: 30px 64px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 40px;
      scroll-behavior: smooth;
      z-index: 30;
      opacity: 0;
      transition: opacity 0.25s ease;
    }}

    #chat-container.active {{
      opacity: 1;
    }}

    #chat-container::-webkit-scrollbar {{
      display: none;
    }}

    /* Message Rows */
    .message-row {{
      display: flex;
      flex-direction: column;
      width: 100%;
      opacity: 0;
      transform: translateY(14px);
      transition: opacity 0.25s ease, transform 0.25s ease;
    }}

    .message-row.visible {{
      opacity: 1;
      transform: translateY(0);
    }}

    /* User Message Bubble (Right aligned, dark slate-blue #26365a matching reference screenshot) */
    .user-bubble {{
      align-self: flex-end;
      background-color: #26365a;
      color: #ffffff;
      padding: 22px 36px;
      border-radius: 34px;
      max-width: 82%;
      font-size: 36px;
      line-height: 1.45;
      font-weight: 400;
      word-wrap: break-word;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
    }}

    /* Assistant Message (Left aligned, transparent background matching reference screenshot) */
    .assistant-msg {{
      align-self: flex-start;
      max-width: 86%;
      padding-right: 20px;
      font-size: 36px;
      line-height: 1.5;
      color: #ececec;
      word-wrap: break-word;
      position: relative;
    }}

    /* Blinking Block Cursor */
    .chat-cursor {{
      display: inline-block;
      width: 15px;
      height: 34px;
      background-color: #ececec;
      vertical-align: -5px;
      margin-left: 6px;
      border-radius: 2px;
      animation: blink 0.75s infinite;
    }}

    @keyframes blink {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0; }}
    }}

    /* Thinking Pulsing Dots */
    .thinking-dots {{
      display: flex;
      align-items: center;
      gap: 12px;
      height: 48px;
    }}

    .dot {{
      width: 14px;
      height: 14px;
      background-color: #a0a0a0;
      border-radius: 50%;
      animation: pulse 1.2s infinite ease-in-out;
    }}

    .dot:nth-child(2) {{ animation-delay: 0.2s; }}
    .dot:nth-child(3) {{ animation-delay: 0.4s; }}

    @keyframes pulse {{
      0%, 100% {{ transform: scale(0.8); opacity: 0.4; }}
      50% {{ transform: scale(1.3); opacity: 1; }}
    }}

    /* Action Icon Bar below ChatGPT messages (thumbs, speaker, share, more) */
    .action-bar {{
      display: flex;
      align-items: center;
      gap: 36px;
      margin-top: 22px;
      opacity: 0;
      transition: opacity 0.35s ease;
    }}

    .action-bar.visible {{
      opacity: 0.85;
    }}

    .action-icon {{
      width: 32px;
      height: 32px;
      fill: #8e8e8e;
      stroke: #8e8e8e;
      cursor: pointer;
    }}

    /* Bottom Section with Auto-Expanding Input Card */
    footer {{
      position: absolute;
      bottom: 30px;
      left: 48px;
      right: 48px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 14px;
      z-index: 100;
    }}

    .input-card {{
      width: 100%;
      min-height: 130px;
      background-color: #212121;
      border: 1px solid #303030;
      border-radius: 38px;
      padding: 22px 30px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: min-height 0.15s ease, border-color 0.2s ease;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
    }}

    .input-card.typing {{
      border-color: #444444;
    }}

    /* Auto-expanding Text Area */
    .input-text-area {{
      width: 100%;
      font-size: 34px;
      line-height: 1.45;
      color: #ececec;
      white-space: pre-wrap;
      word-break: break-word;
      min-height: 48px;
      margin-bottom: 16px;
    }}

    .input-text-area.placeholder {{
      color: #71717a;
      line-height: 48px;
    }}

    .typing-caret {{
      display: inline-block;
      width: 3px;
      height: 34px;
      background-color: #3b82f6;
      vertical-align: -5px;
      margin-left: 3px;
      animation: caret-blink 0.75s infinite;
    }}

    @keyframes caret-blink {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0; }}
    }}

    /* Bottom row inside input card */
    .input-bottom-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
    }}

    .input-plus-btn {{
      width: 52px;
      height: 52px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #9e9e9e;
      font-size: 42px;
      font-weight: 300;
      cursor: pointer;
    }}

    .input-right-actions {{
      display: flex;
      align-items: center;
      gap: 22px;
    }}

    .input-mic-btn {{
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }}

    /* Circular Voice / Send Button */
    .voice-btn {{
      width: 68px;
      height: 68px;
      background-color: #2b64e0;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background-color 0.2s ease, transform 0.15s ease;
      cursor: pointer;
    }}

    .voice-btn.send-mode {{
      background-color: #ffffff;
      transform: scale(1.04);
    }}

    .voice-btn.send-mode svg.waveform-svg {{
      display: none;
    }}

    .voice-btn.send-mode svg.send-arrow-svg {{
      display: block !important;
    }}

    .chatgpt-disclaimer {{
      font-size: 20px;
      color: #666666;
      text-align: center;
      letter-spacing: 0.1px;
    }}
  </style>
</head>
<body>
  <div id="scene-wrapper">

  <!-- Top Bar matching reference screenshot -->
  <header>
    <div class="header-icon-btn">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#a6a6a6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="4"/>
        <line x1="9" y1="3" x2="9" y2="21"/>
      </svg>
    </div>
    <div class="header-icon-btn">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#a6a6a6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
        <path d="M3 3v5h5"/>
        <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
        <path d="M16 21h5v-5"/>
      </svg>
    </div>
  </header>

  <!-- Initial Empty State matching reference screenshot -->
  <section id="empty-state">
    <div class="center-greeting">Hey, Lokesh. Ready to dive in?</div>
    <div class="suggested-actions">
      <div class="action-item">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <polyline points="21 15 16 10 5 21"/>
        </svg>
        <span>Create an image or sticker</span>
      </div>
      <div class="action-item">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 20h9"/>
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
        </svg>
        <span>Write or edit</span>
      </div>
      <div class="action-item">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="2" y1="12" x2="22" y2="12"/>
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
        </svg>
        <span>Search the web</span>
      </div>
    </div>
  </section>

  <!-- Chat Messages Container -->
  <main id="chat-container">
    <!-- Messages dynamically injected by timeline engine -->
  </main>

  <!-- Bottom Floating Input Section -->
  <footer>
    <div class="input-card" id="input-card">
      <div id="input-text-area" class="input-text-area placeholder">Ask ChatGPT</div>
      <div class="input-bottom-row">
        <div class="input-plus-btn">+</div>
        <div class="input-right-actions">
          <div class="input-mic-btn">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#a0a0a0" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          </div>
          <div id="voice-send-btn" class="voice-btn">
            <svg class="waveform-svg" width="34" height="34" viewBox="0 0 24 24" fill="#ffffff">
              <rect x="3" y="9" width="2.5" height="6" rx="1.25"/>
              <rect x="8.5" y="4" width="2.5" height="16" rx="1.25"/>
              <rect x="14" y="7" width="2.5" height="10" rx="1.25"/>
              <rect x="19.5" y="10" width="2.5" height="4" rx="1.25"/>
            </svg>
            <svg class="send-arrow-svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" style="display:none;">
              <line x1="12" y1="19" x2="12" y2="5"/>
              <polyline points="5 12 12 5 19 12"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
    <div class="chatgpt-disclaimer">ChatGPT can make mistakes. Check important info.</div>
  </footer>
  </div>

  <script>
    const events = {events_json};
    const turns = {turns_json};
    const totalDuration = {total_duration};

    const emptyState = document.getElementById('empty-state');
    const chatContainer = document.getElementById('chat-container');
    const inputCard = document.getElementById('input-card');
    const inputTextArea = document.getElementById('input-text-area');
    const voiceSendBtn = document.getElementById('voice-send-btn');

    let currentTypedText = '';
    let currentAssistantElement = null;
    let currentAssistantCursor = null;

    function escapeHtml(text) {{
      return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }}

    function scrollToBottom() {{
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }}

    // Update input card expansion dynamically as characters are typed
    function updateInputCardHeight() {{
      const textHeight = inputTextArea.offsetHeight;
      const targetMin = Math.max(130, textHeight + 75);
      inputCard.style.minHeight = targetMin + 'px';
    }}

    function executeEvent(ev) {{
      const type = ev.type;

      if (type === 'type_char') {{
        if (inputTextArea.classList.contains('placeholder')) {{
          inputTextArea.classList.remove('placeholder');
          inputCard.classList.add('typing');
          voiceSendBtn.classList.add('send-mode');
          currentTypedText = '';
        }}
        currentTypedText += ev.char;
        inputTextArea.innerHTML = escapeHtml(currentTypedText) + '<span class="typing-caret"></span>';
        updateInputCardHeight();
      }}

      else if (type === 'send_message') {{
        // Reset input card back to clean base
        currentTypedText = '';
        inputTextArea.classList.add('placeholder');
        inputTextArea.textContent = 'Ask ChatGPT';
        inputCard.classList.remove('typing');
        voiceSendBtn.classList.remove('send-mode');
        inputCard.style.minHeight = '130px';

        // Hide initial empty state screen on first send
        if (!emptyState.classList.contains('hidden')) {{
          emptyState.classList.add('hidden');
          chatContainer.classList.add('active');
        }}

        // Append User Message Bubble (Right aligned, dark slate-blue)
        const row = document.createElement('div');
        row.className = 'message-row';
        row.id = 'msg-turn-' + ev.turn_idx;

        const bubble = document.createElement('div');
        bubble.className = 'user-bubble';
        bubble.textContent = ev.text;

        row.appendChild(bubble);
        chatContainer.appendChild(row);

        requestAnimationFrame(() => {{
          row.classList.add('visible');
          scrollToBottom();
        }});
      }}

      else if (type === 'show_thinking') {{
        const row = document.createElement('div');
        row.className = 'message-row visible';
        row.id = 'msg-turn-' + ev.turn_idx;

        const dots = document.createElement('div');
        dots.className = 'thinking-dots';
        dots.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';

        row.appendChild(dots);
        chatContainer.appendChild(row);
        scrollToBottom();
      }}

      else if (type === 'stream_word') {{
        const row = document.getElementById('msg-turn-' + ev.turn_idx);
        if (row) {{
          const dots = row.querySelector('.thinking-dots');
          if (dots) {{
            dots.remove();

            const assistantMsg = document.createElement('div');
            assistantMsg.className = 'assistant-msg';
            assistantMsg.id = 'stream-content-' + ev.turn_idx;

            const cursor = document.createElement('span');
            cursor.className = 'chat-cursor';

            assistantMsg.appendChild(cursor);
            row.appendChild(assistantMsg);

            currentAssistantElement = assistantMsg;
            currentAssistantCursor = cursor;
          }}

          if (currentAssistantElement && currentAssistantCursor) {{
            const textNode = document.createTextNode(ev.word);
            currentAssistantElement.insertBefore(textNode, currentAssistantCursor);
            scrollToBottom();
          }}
        }}
      }}

      else if (type === 'stream_end') {{
        if (currentAssistantCursor) {{
          currentAssistantCursor.remove();
          currentAssistantCursor = null;
        }}

        const row = document.getElementById('msg-turn-' + ev.turn_idx);
        if (row) {{
          // Append ChatGPT action bar (thumbs up, down, speaker, share, more)
          const actionBar = document.createElement('div');
          actionBar.className = 'action-bar';
          actionBar.innerHTML = `
            <!-- Thumbs up -->
            <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
            </svg>
            <!-- Thumbs down -->
            <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"/>
            </svg>
            <!-- Speaker / Read aloud -->
            <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
            </svg>
            <!-- Share -->
            <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8m-4-6-4-4-4 4m4-4v13"/>
            </svg>
            <!-- More dots -->
            <svg class="action-icon" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="12" r="2"/>
              <circle cx="19" cy="12" r="2"/>
              <circle cx="5" cy="12" r="2"/>
            </svg>
          `;
          row.appendChild(actionBar);
          requestAnimationFrame(() => {{
            actionBar.classList.add('visible');
            scrollToBottom();
          }});
        }}
      }}

      else if (type === 'zoom_in') {{
        const wrapper = document.getElementById('scene-wrapper');
        if (wrapper) {{
          wrapper.classList.add('zoomed-in');
        }}
      }}

      else if (type === 'boom_shake') {{
        const wrapper = document.getElementById('scene-wrapper');
        if (wrapper) {{
          wrapper.classList.add('shake');
          setTimeout(() => wrapper.classList.remove('shake'), 450);
        }}
      }}
    }}

    // Playback engine
    const startTime = performance.now();
    let currentEventIdx = 0;

    function tick() {{
      const elapsed = (performance.now() - startTime) / 1000;

      while (currentEventIdx < events.length && events[currentEventIdx].time <= elapsed) {{
        executeEvent(events[currentEventIdx]);
        currentEventIdx++;
      }}

      if (elapsed < totalDuration) {{
        requestAnimationFrame(tick);
      }} else {{
        window.__CHAT_FINISHED__ = true;
      }}
    }}

    requestAnimationFrame(tick);
  </script>
</body>
</html>"""
        return html
