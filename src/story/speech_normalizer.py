"""Mode 2 Speech Normalizer & Acronym Expander.
Transforms raw Reddit text into smooth, natural spoken narration by expanding abbreviations,
cleaning up Markdown syntax, and normalizing symbols for Edge-TTS.
"""

import re
from typing import Dict

REDDIT_ACRONYMS: Dict[str, str] = {
    r"\bAITA\b": "Am I the jerk",
    r"\bWIBTA\b": "Would I be the jerk",
    r"\bNTA\b": "Not the jerk",
    r"\bYTA\b": "You are the jerk",
    r"\bESH\b": "Everyone is at fault",
    r"\bNAH\b": "No jerks here",
    r"\bTIFU\b": "Today I messed up",
    r"\bTL;?DR\b": "In short",
    r"\bOP\b": "the author",
    r"\bMIL\b": "Mother-in-law",
    r"\bFIL\b": "Father-in-law",
    r"\bSIL\b": "Sister-in-law",
    r"\bBIL\b": "Brother-in-law",
    r"\bSO\b": "significant other",
    r"\bGF\b": "girlfriend",
    r"\bBF\b": "boyfriend",
    r"\bPOV\b": "Point of view",
    r"\bDM\b": "direct message",
    r"\bDMs\b": "direct messages",
    r"\bw/o\b": "without",
    r"\bw/\b": "with",
    r"\bvs\.?\b": "versus",
    r"\betc\.?\b": "et cetera",
    r"\be\.g\.?\b": "for example",
    r"\bi\.e\.?\b": "that is",
    r"\bETA\b": "Update",
    r"\bTBH\b": "To be honest",
    r"\bIDK\b": "I don't know",
    r"\bSMH\b": "Shaking my head",
    r"\bIRL\b": "in real life",
    r"\bBFF\b": "best friend",
}


def normalize_for_speech(text: str) -> str:
    """
    Clean and expand raw text for ultra-natural speech synthesis.
    Expands acronyms, converts age/gender tokens (e.g. 28M -> 28 year old male),
    removes URLs, strips Markdown formatting, and normalizes conversational cadence.
    """
    if not text:
        return ""

    # 1. Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    # 2. Expand age/gender indicators: (28M) or 28M -> 28 year old male
    text = re.sub(r"\(?\b(\d{1,2})\s*([mM])\b\)?", r"\1 year old male", text)
    text = re.sub(r"\(?\b(\d{1,2})\s*([fF])\b\)?", r"\1 year old female", text)

    # 3. Expand Reddit Acronyms
    for pattern, replacement in REDDIT_ACRONYMS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 4. Clean Reddit Markdown (bold, italic, strikethrough, quotes)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)     # **bold**
    text = re.sub(r"\*([^*]+)\*", r"\1", text)         # *italic*
    text = re.sub(r"~~([^~]+)~~", r"\1", text)         # ~~strikethrough~~
    text = re.sub(r"^>+\s*", "", text, flags=re.MULTILINE)  # Quote blocks
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE) # Headers
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [anchor](url)

    # 5. Symbol expansion for spoken fluency
    text = text.replace("&", " and ").replace("+", " plus ").replace("@", " at ")
    text = text.replace("%", " percent ").replace("$", " dollars ")

    # 6. Normalize common currency numbers e.g. $15k -> 15 thousand dollars
    text = re.sub(r"\$(\d+)\s*[kK]\b", r"\1 thousand dollars", text)
    text = re.sub(r"\$(\d+)\b", r"\1 dollars", text)

    # 7. Clean up weird characters while preserving punctuation and dialogue quotes
    text = re.sub(r"[^\w\s.,!?'\"-]", " ", text)

    # 8. Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text
