import os
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE_DIR = ROOT / "tools" / "node"
MOTION_DIR = ROOT / "motion"
NODE_EXE = NODE_DIR / "node.exe"
CLI_JS = MOTION_DIR / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ARTIFACTS_DIR = Path(r"C:\Users\Samsung\.gemini\antigravity\brain\330bc3f6-58fb-4fe8-b133-9e6e85a58350")

env = os.environ.copy()
env["PATH"] = str(NODE_DIR) + os.pathsep + env.get("PATH", "")

test_frames = [
    (30, "scene1_kinetic_title.png"),
    (200, "scene2_glass_metric.png"),
    (450, "scene3_process_flow.png"),
    (750, "scene4_mental_model.png"),
]

for frame, filename in test_frames:
    dest_temp = ROOT / "temp" / filename
    dest_artifact = ARTIFACTS_DIR / filename

    cmd = [
        str(NODE_EXE),
        str(CLI_JS),
        "still",
        "src/index.ts",
        "MainShort",
        str(dest_temp),
        f"--frame={frame}",
        f"--browser-executable={EDGE_EXE}",
        "--log=error"
    ]
    print(f"Rendering frame {frame} -> {filename}...")
    res = subprocess.run(cmd, cwd=str(MOTION_DIR), env=env)
    if res.returncode == 0 and dest_temp.exists():
        shutil.copy(dest_temp, dest_artifact)
        print(f"  Frame {frame} saved to {dest_artifact}")
    else:
        print(f"  Failed rendering frame {frame}")

print("All test frames rendered!")
