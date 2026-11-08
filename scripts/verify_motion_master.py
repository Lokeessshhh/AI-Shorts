import subprocess
import shutil
import json
from pathlib import Path

VIDEO_PATH = Path(r"C:\Users\Samsung\Documents\Code\AI_Shorts\output\motion_the_3_solopreneur_skills_that_pay_foreve_1793530212.mp4")
METADATA_PATH = Path(r"C:\Users\Samsung\Documents\Code\AI_Shorts\output\motion_the_3_solopreneur_skills_that_pay_foreve_1793530212_metadata.txt")
ARTIFACTS_DIR = Path(r"C:\Users\Samsung\.gemini\antigravity\brain\330bc3f6-58fb-4fe8-b133-9e6e85a58350")
TEMP_DIR = Path(r"C:\Users\Samsung\Documents\Code\AI_Shorts\temp")

import imageio_ffmpeg
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

# 1. Check video specs via ffmpeg probe
cmd = [ffmpeg_exe, "-i", str(VIDEO_PATH)]
res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
print("=== VIDEO PROBE ===")
for line in res.stderr.splitlines():
    if any(k in line for k in ["Duration:", "Stream #0:0", "Stream #0:1"]):
        print(line.strip())

# 2. Extract 4 verification frames matching each scene
sample_times = [
    (2.5, "verify_motion_cut1_hook.jpg"),
    (8.0, "verify_motion_cut2_metric.jpg"),
    (16.0, "verify_motion_cut3_flow.jpg"),
    (26.0, "verify_motion_cut4_nexus.jpg")
]

for sec, fname in sample_times:
    out_tmp = TEMP_DIR / fname
    out_art = ARTIFACTS_DIR / fname
    extract_cmd = [
        ffmpeg_exe, "-y",
        "-ss", str(sec),
        "-i", str(VIDEO_PATH),
        "-vframes", "1",
        "-q:v", "2",
        str(out_tmp)
    ]
    subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    shutil.copy(out_tmp, out_art)
    print(f"Extracted {fname} at {sec}s (size: {out_art.stat().st_size} bytes)")

# 3. Read metadata file
print("\n=== METADATA ===")
print(METADATA_PATH.read_text(encoding="utf-8"))
