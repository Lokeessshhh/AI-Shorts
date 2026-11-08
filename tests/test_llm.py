import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.llm.client import OpenRouterClient
from src.llm.prompts import ScriptPayload


def test_openrouter_script_generation():
    client = OpenRouterClient()
    topic = "The secret psychology of why casinos have no clocks"
    script = client.generate_script(topic)

    assert isinstance(script, ScriptPayload)
    assert len(script.title) > 0
    assert len(script.hook) > 0
    assert len(script.scenes) >= 3
    assert len(script.full_narration) > 50

    for scene in script.scenes:
        assert scene.scene_id > 0
        assert len(scene.narration) > 0
        assert len(scene.visual_keywords) > 0

    print("\n[PASSED] LLM Script Generation verified with model:", client.model)
    print("Title:", script.title)
    print("Hook:", script.hook)
    print(f"Scenes count: {len(script.scenes)}")


if __name__ == "__main__":
    test_openrouter_script_generation()
