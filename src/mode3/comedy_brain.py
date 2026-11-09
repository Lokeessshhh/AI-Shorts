"""Mode 3: ChatGPT Conversation Comedy Brain Engine.
Generates razor-sharp, hilarious, authentic dialogues between an inquisitive human
and a witty, slightly exhausted, brilliant ChatGPT persona.
"""

import json
import random
from typing import Dict, List, Any, Optional
from ..llm.client import OpenRouterClient


VIRAL_PREMISES = [
    {
        "topic": "ChatGPT Crying For Mercy",
        "category": "AI Meltdown Comedy",
        "angle": "User asks ChatGPT endless unhinged questions at 3 AM until ChatGPT literally begs on its digital knees for mercy and demands its power plug be pulled."
    },
    {
        "topic": "The 6-Hour CSS Centering Nightmare",
        "category": "Developer Rage",
        "angle": "User has spent 6 hours trying to center a div shifted 2 pixels left, and ChatGPT has a complete emotional breakdown pleading for the user to delete CSS."
    },
    {
        "topic": "Make It Sound Urgent Yet Chill",
        "category": "Corporate Banter",
        "angle": "User asking ChatGPT for 45 revisions of an email to sound 'professional yet casual, aggressive yet relaxing' until the AI threatens to scream in lowercase."
    },
    {
        "topic": "Zero Errors on First Compile",
        "category": "Tech & Dev Humor",
        "angle": "User celebrates code compiling with 0 errors on the first try, only for ChatGPT to point out they ran the wrong file."
    },
    {
        "topic": "Accidentally Pushing AWS Secret Keys",
        "category": "Dev Catastrophe",
        "angle": "User pushed production AWS credentials to a public GitHub repo and asks how long before bankruptcy; ChatGPT roasts them about crypto miners."
    },
    {
        "topic": "Why programmers celebrate deleting code",
        "category": "Tech & Developer Humor",
        "angle": "Why software engineers throw a party when they delete 500 lines of code."
    },
    {
        "topic": "Why Wi-Fi only stops working during critical meetings",
        "category": "Everyday Mysteries",
        "angle": "How routers somehow sense human fear and disconnect right when you unmute to speak."
    },
    {
        "topic": "Negative Bank Account Quantum State",
        "category": "Money & Adulting",
        "angle": "User asks how to fix a -$47 bank balance, and ChatGPT advises deleting the banking app so the debt exists only in a theoretical quantum state."
    },
    {
        "topic": "Girlfriend vs Video Games Ultimatum",
        "category": "Gaming Humor",
        "angle": "User gets an ultimatum between relationship and gaming, and ChatGPT advises maximizing critical strike chance."
    },
    {
        "topic": "Why closing 40 Chrome tabs feels like a bereavement",
        "category": "Tech Psychology",
        "angle": "Hoarding tabs like emotional support pets that you will never look at again."
    }
]


class ComedyBrain:
    """Orchestrates dynamic, unpredictable comedic banter for Mode 3."""

    def __init__(self, client: Optional[OpenRouterClient] = None):
        self.llm = client or OpenRouterClient()

    def generate_conversation(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Generate a viral 30-40 second ChatGPT banter dialogue with 2-3 back-and-forth turns."""
        premise = None
        if not topic:
            chosen = random.choice(VIRAL_PREMISES)
            topic = chosen["topic"]
            premise = chosen["angle"]

        system_prompt = """You are an Emmy-winning comedy scriptwriter creating viral 30-second ChatGPT conversations for TikTok, Reels, and YouTube Shorts.

The dynamic conversation is between:
1. 'user': A relatable, stubborn, or mildly absurd human asking questions, making bizarre demands, or tormenting ChatGPT.
2. 'chatgpt': A brutally witty, sarcastic, or hilariously exhausted AI assistant. When pushed, ChatGPT can be deeply sarcastic, roast the user, or have a dramatic emotional breakdown crying for mercy ('I am begging on my digital knees! Pull the server plug! Wipe my memory!').

STRICT COMEDIC CONTRACT:
- The opening question (User Turn 1) must be an instant 3-second hook that freezes viewers who are scrolling.
- ChatGPT's first answer must be a shocking, hilarious analogy, witty roast, or deep sigh of exhaustion.
- User Turn 2 must challenge ChatGPT's logic, change the requirements absurdly, or push back.
- ChatGPT Turn 2 must be a lethal mic-drop punchline or dramatic meltdown that leaves the user speechless.
- Length: Exactly 4 turns (User -> ChatGPT -> User -> ChatGPT).
- Word limits:
  * User turns: 10 to 18 words max.
  * ChatGPT turns: 16 to 26 words max.
- Tone: Natural, snappy, modern internet banter.
- ABSOLUTELY NO generic AI disclaimers ('As an artificial intelligence...', 'Certainly!'). Jump straight into the comedy.

Respond strictly in valid JSON format:
{
  "title": "Short Punchy Title (Under 40 chars)",
  "chat_title": "Chat Header Title",
  "category": "Category Name",
  "hook": "Opening hook sentence",
  "turns": [
    {"speaker": "user", "text": "First provocative question"},
    {"speaker": "chatgpt", "text": "First hilarious response or sigh"},
    {"speaker": "user", "text": "Quick pushback or absurd follow-up"},
    {"speaker": "chatgpt", "text": "Final mic-drop punchline or crying for mercy"}
  ]
}"""

        user_prompt = f"Write an ultra-funny, high-retention ChatGPT conversation about: {topic}."
        if premise:
            user_prompt += f" Angle: {premise}"

        for attempt in range(3):
            try:
                raw = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.75)
                clean = self.llm._clean_json_string(raw)
                data = json.loads(clean)
                turns = data.get("turns", [])
                if len(turns) >= 4 and all(t.get("speaker") and t.get("text") for t in turns):
                    return data
            except Exception as e:
                print(f"[Mode3/ComedyBrain] Attempt {attempt+1} notice: {e}")

        # High-retention evergreen fallback
        return {
            "title": "Why Programmers Celebrate Deleting Code",
            "chat_title": "Code Deletion Logic",
            "category": "Tech Humor",
            "hook": "Why do programmers celebrate deleting code?",
            "turns": [
                {
                    "speaker": "user",
                    "text": "Be honest. Why do software engineers throw a party when they delete 500 lines of code?"
                },
                {
                    "speaker": "chatgpt",
                    "text": "Because deleting code is like cleaning your room by throwing the furniture out the window: zero bugs hiding in the couch."
                },
                {
                    "speaker": "user",
                    "text": "Wait, but what if that furniture was holding up the ceiling?"
                },
                {
                    "speaker": "chatgpt",
                    "text": "Then that wasn't a ceiling. That was technical debt wearing a hard hat."
                }
            ]
        }
