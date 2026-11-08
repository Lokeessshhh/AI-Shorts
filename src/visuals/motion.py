"""
Dynamic Ken Burns (pan & zoom) camera motion effects for static clips and B-roll.
"""


def get_ken_burns_filter(
    duration_seconds: float,
    fps: int = 30,
    direction: str = "in",
    width: int = 1080,
    height: int = 1920,
) -> str:
    """Generate FFmpeg zoompan filter string for subtle cinematic push-in or pull-out."""
    frames = int(duration_seconds * fps)
    if direction == "out":
        zoom_expr = f"1.15-0.15*on/{frames}"
    else:
        # Subtle 1.0 -> 1.15x push-in
        zoom_expr = f"1.0+0.15*on/{frames}"

    return (
        f"zoompan=z='{zoom_expr}':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={width}x{height}:fps={fps}"
    )
