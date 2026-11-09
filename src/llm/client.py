import json
import re
import requests
from typing import Optional, List, Dict, Any
from ..config import config
from .prompts import (
    SYSTEM_PROMPT,
    build_script_prompt,
    ScriptPayload,
)


class OpenRouterClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or config.openrouter_api_key
        self.model = model or config.openrouter_model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

        if not self.api_key:
            raise ValueError(
                "OpenRouter API key is missing. Set OPENROUTER_API_KEY in .env"
            )

    def _clean_json_string(self, text: str) -> str:
        """Strip markdown fences if model wraps JSON inside ```json ... ``` blocks."""
        cleaned = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
        return cleaned.strip()

    def _sanitize_narration(self, text: str) -> str:
        """Remove stage directions, sound cues like [whoosh], and extra quotes."""
        # Remove parenthetical or bracketed cues like [Sound: upbeat music] or (laugh)
        cleaned = re.sub(r"\[.*?\]", "", text)
        cleaned = re.sub(r"\(.*?\)", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def complete_vision(
        self,
        system_prompt: str,
        user_text: str,
        image_urls: List[str],
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str:
        """Execute a multimodal vision completion using Muse Spark 1.3 Contributor via OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/AI_Shorts",
            "X-Title": "AI Shorts Agent",
            "Content-Type": "application/json",
        }

        user_content: List[Dict[str, Any]] = [
            {"type": "text", "text": user_text}
        ]

        for url in image_urls:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=75,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenRouter Vision API error ({response.status_code}): {response.text}"
            )

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        """Execute a general chat completion via OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/AI_Shorts",
            "X-Title": "AI Shorts Agent",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenRouter API error ({response.status_code}): {response.text}"
            )

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_script(
        self,
        topic: str,
        format_type: str = "counter_intuitive_truth",
        angle: str = "",
    ) -> ScriptPayload:
        """Call OpenRouter model to generate structured viral short script conforming to ScriptPayload."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/AI_Shorts",
            "X-Title": "AI Shorts Agent",
            "Content-Type": "application/json",
        }

        user_prompt = build_script_prompt(topic, format_type=format_type, angle=angle)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 4000,
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenRouter API error ({response.status_code}): {response.text}"
            )

        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]
        cleaned_json = self._clean_json_string(raw_content)

        try:
            parsed = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            match = re.search(r"\{.*\}", cleaned_json, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
            else:
                raise ValueError(
                    f"Failed to parse LLM JSON response: {e}\nRaw output: {raw_content}"
                )

        script_obj = ScriptPayload.model_validate(parsed)

        # Sanitize narration texts
        for scene in script_obj.scenes:
            scene.narration = self._sanitize_narration(scene.narration)

        # Ensure full_narration is clean and assembled
        full_text = " ".join([s.narration for s in script_obj.scenes])
        script_obj.full_narration = self._sanitize_narration(full_text)

        return script_obj
