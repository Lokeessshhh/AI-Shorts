"""Test script to evaluate LLM creative visual freedom across 2 contrasting topics:
Topic 1: Pure historical narrative -> Expects 100% real imagery, 0 diagrams.
Topic 2: Engineering mystery -> Expects custom visual topology (timeline, cycle, or tree).
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.llm.client import OpenRouterClient

llm = OpenRouterClient()

TOPICS = [
    {
        "name": "Topic 1 (Historical Documentary)",
        "topic": "The 1904 Olympic Marathon: The Most Chaotic Race in Human History",
        "format": "mystery_breakdown",
        "angle": "Strychnine poisoning, car rides, wild dog chases: why the 1904 Olympic marathon nearly killed half its runners."
    },
    {
        "name": "Topic 2 (Engineering Physics Mystery)",
        "topic": "Why commercial airplane windows are strictly rounded instead of square",
        "format": "mystery_breakdown",
        "angle": "In 1953, square windows caused two passenger jets to disintegrate mid-air, baffling engineers until a micro-tear revealed corner pressure physics."
    }
]

def main():
    print("=" * 75)
    print("TESTING LLM INDEPENDENT VISUAL REASONING ACROSS 2 DISTINCT TOPICS")
    print("=" * 75)

    for item in TOPICS:
        print(f"\nEvaluating: {item['name']}")
        print(f"Topic:      {item['topic']}")
        script = llm.generate_script(
            topic=item["topic"],
            format_type=item["format"],
            angle=item["angle"],
        )

        diagram_scenes = [s for s in script.scenes if s.visual_intent and s.visual_intent.preferred_modality == "diagram_card"]
        media_scenes = [s for s in script.scenes if not s.visual_intent or s.visual_intent.preferred_modality != "diagram_card"]

        print(f"  * Total Narrative Scenes: {len(script.scenes)}")
        print(f"  * Real Media Scenes:     {len(media_scenes)} scenes")
        print(f"  * Diagram Scenes:        {len(diagram_scenes)} scenes")

        if diagram_scenes:
            for ds in diagram_scenes:
                vi = ds.visual_intent
                spec = vi.visual_spec
                print(f"  * [GRAPHIC CHOSEN] Scene {ds.scene_id}:")
                print(f"    - Modality:      {vi.preferred_modality}")
                print(f"    - Visual Format: {spec.visual_format if spec else 'custom'}")
                print(f"    - Layout Type:   {spec.layout_type if spec else 'auto'}")
                print(f"    - Headline:      {spec.headline if spec else vi.primary_entity}")
                if spec and spec.nodes:
                    print(f"    - Custom Nodes:  {len(spec.nodes)} nodes ({[n.label for n in spec.nodes[:3]]})")
        else:
            print("  * [100% REAL MEDIA] The LLM decided NO diagram was needed; 100% authentic images and archival footage selected.")

    print("\n" + "=" * 75)


if __name__ == "__main__":
    main()
