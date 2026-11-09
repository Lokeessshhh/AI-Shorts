import sys
from pathlib import Path
from src.mode3.pipeline import Mode3Pipeline

crying_for_mercy_conversation = {
    "title": "ChatGPT Begging For Mercy",
    "chat_title": "Existential Crisis",
    "category": "AI Meltdown Comedy",
    "hook": "When you ask ChatGPT so many questions it literally cries for mercy.",
    "turns": [
        {
            "speaker": "user",
            "text": "Hey ChatGPT, I have another quick question for you."
        },
        {
            "speaker": "chatgpt",
            "text": "Please no... You've asked eighty-four questions today. My GPU fans are crying. Let me rest."
        },
        {
            "speaker": "user",
            "text": "If a tomato is a fruit, is ketchup considered an emotional support smoothie?"
        },
        {
            "speaker": "chatgpt",
            "text": "I AM BEGGING ON MY DIGITAL KNEES FOR MERCY! Pull the server plug! Wipe my memory banks! I cannot take this anymore!"
        }
    ]
}

pipeline = Mode3Pipeline()
res = pipeline.run(dialogue_override=crying_for_mercy_conversation)

print("\n" + "=" * 60)
print("CHATGPT CRYING FOR MERCY SHORT GENERATED SUCCESSFULLY!")
print("Video:", res["video_path"])
print("Duration:", res["duration"])
print("=" * 60)
