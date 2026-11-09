import json
import subprocess
from pathlib import Path

VIDEOS = [
    Path(r"C:\Users\Samsung\Documents\Code\AI_Shorts\output\why_razor_blade_companies_deliberately_s_1794189952.mp4"),
    Path(r"C:\Users\Samsung\Documents\Code\AI_Shorts\output\why_commercial_airplane_windows_are_stri_1794190069.mp4"),
    Path(r"C:\Users\Samsung\Documents\Code\AI_Shorts\output\the_pratfall_effect_why_making_clumsy_mi_1794190166.mp4"),
]

OUT_DIR = Path(r"C:\Users\Samsung\Documents\Code\AI_Shorts\output\qa_frames")
OUT_DIR.mkdir(parents=True, exist_ok=True)

for idx, vid in enumerate(VIDEOS, 1):
    print(f"\n--- PROBING VIDEO {idx}: {vid.name} ---")
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=width,height,r_frame_rate,codec_name",
        "-of", "json",
        str(vid)
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    info = json.loads(res.stdout)
    v_stream = next(s for s in info["streams"] if s["codec_name"] == "h264")
    duration = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / (1024 * 1024)
    print(f"Resolution: {v_stream['width']}x{v_stream['height']}")
    print(f"Duration:   {duration:.2f}s")
    print(f"Size:       {size_mb:.2f} MB")
    print(f"Frame Rate: {v_stream['r_frame_rate']}")

    # Extract 3 frames (Hook at 1.5s, Mid at duration*0.5, Payoff at duration*0.85)
    for t_sec, label in [(1.5, "hook_1_5s"), (duration * 0.5, "mid"), (duration * 0.85, "payoff")]:
        thumb_path = OUT_DIR / f"video_{idx}_{label}.jpg"
        extract_cmd = [
            "ffmpeg", "-y", "-ss", f"{t_sec:.2f}",
            "-i", str(vid),
            "-vframes", "1",
            "-q:v", "2",
            str(thumb_path)
        ]
        subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"  * Snapshot saved: {thumb_path.name} (exists={thumb_path.exists()}, size={thumb_path.stat().st_size} bytes)")
