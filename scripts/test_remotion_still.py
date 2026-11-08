import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE_DIR = ROOT / "tools" / "node"
MOTION_DIR = ROOT / "motion"
NODE_EXE = NODE_DIR / "node.exe"
CLI_JS = MOTION_DIR / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
OUTPUT_PNG = ROOT / "temp" / "test_remotion_frame.png"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

env = os.environ.copy()
env["PATH"] = str(NODE_DIR) + os.pathsep + env.get("PATH", "")

cmd = [
    str(NODE_EXE),
    str(CLI_JS),
    "still",
    "src/index.ts",
    "MainShort",
    str(OUTPUT_PNG),
    "--frame=30",
    f"--browser-executable={EDGE_EXE}",
    "--log=info"
]

print(f"Executing: {' '.join(cmd)}")
# Stream live stdout/stderr
res = subprocess.run(cmd, cwd=str(MOTION_DIR), env=env)
print(f"Process finished with code {res.returncode}")
if OUTPUT_PNG.exists():
    print(f"Success! Still frame generated at {OUTPUT_PNG} (size: {OUTPUT_PNG.stat().st_size} bytes)")
