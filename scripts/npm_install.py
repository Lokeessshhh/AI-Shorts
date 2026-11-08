import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE_DIR = ROOT / "tools" / "node"
MOTION_DIR = ROOT / "motion"

if not NODE_DIR.exists():
    print(f"Error: Node directory does not exist at {NODE_DIR}")
    sys.exit(1)

env = os.environ.copy()
env["PATH"] = str(NODE_DIR) + os.pathsep + env.get("PATH", "")

npm_cmd = str(NODE_DIR / "npm.cmd")
print(f"Running npm install in {MOTION_DIR} with Node at {NODE_DIR}...")
try:
    res = subprocess.run([npm_cmd, "install"], cwd=str(MOTION_DIR), env=env, text=True, check=True)
    print("npm install completed successfully!")
except subprocess.CalledProcessError as e:
    print(f"npm install failed with code {e.returncode}")
    sys.exit(e.returncode)
