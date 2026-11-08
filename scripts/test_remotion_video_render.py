import os
import subprocess
from pathlib import Path
from src.config import config
from src.motion.remotion_bridge import RemotionBridge, get_browser_executable

ROOT = config.root_dir
OUTPUT_MP4 = config.temp_dir / "test_remotion_render.mp4"

# Use default storyboard from Root.tsx / json
storyboard = {
    "title": "The Compounding Flywheel Effect",
    "totalDuration": 30.0,
    "theme": {
        "background": "#09090b",
        "primaryAccent": "#06b6d4",
        "secondaryAccent": "#8b5cf6",
        "text": "#f8fafc"
    },
    "scenes": [
        {
            "id": "scene_1",
            "component": "KineticTitleCard",
            "startTime": 0.0,
            "endTime": 4.5,
            "narration": "Most people stay broke because they trade hours for dollars.",
            "props": {
                "badge": "SYSTEMS & LEVERAGE",
                "headline": "THE 3 SKILLS THAT",
                "highlightWord": "PAY FOREVER",
                "subheadline": "Stop selling time. Build infinite assets."
            }
        }
    ]
}

bridge = RemotionBridge()
print("Starting Remotion test render (frames 0-90)...")

# Direct command with --frames=0-90 for fast verification
props_path = config.temp_dir / "remotion_test_props.json"
import json
with open(props_path, "w", encoding="utf-8") as f:
    json.dump({"storyboard": storyboard}, f)

cmd = [
    str(config.node_exe),
    str(bridge.cli_js),
    "render",
    "src/index.ts",
    "MainShort",
    str(OUTPUT_MP4),
    f"--props={props_path}",
    "--frames=0-90",
    "--concurrency=4",
    "--overwrite"
]
browser_exe = get_browser_executable()
if browser_exe:
    cmd.append(f"--browser-executable={browser_exe}")

env = bridge._get_env()
res = subprocess.run(cmd, cwd=str(config.motion_dir), env=env)
print(f"Exit code: {res.returncode}")
if OUTPUT_MP4.exists():
    print(f"Success! Rendered MP4: {OUTPUT_MP4} ({OUTPUT_MP4.stat().st_size} bytes)")
