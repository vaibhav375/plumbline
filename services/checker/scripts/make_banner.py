"""Generate the §4.4 worked-example banner: low-contrast text, an off-palette pink block, a
logo stretched 12% wide, and no alt text. Uses Pillow's bundled font so output is the same
on every machine."""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CREAM, TEXT, PINK, INK = "#FBF6EC", "#B8B2A7", "#FF3EA5", "#2D2A27"
OUT = Path(__file__).resolve().parents[3] / "supabase" / "seed" / "aurelle" / "banner_v1.png"


def make(path: Path = OUT) -> Path:
    img = Image.new("RGB", (1080, 1080), CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 760, 1080, 1080), fill=PINK)
    font = ImageFont.load_default(size=110)
    for i, line in enumerate(("GLOW IN", "2 WEEKS")):
        d.text((90, 180 + i * 150), line, font=font, fill=TEXT)
    logo = Image.new("RGB", (420, 110), PINK)
    ImageDraw.Draw(logo).text((10, 10), "AURELLE", font=ImageFont.load_default(size=80), fill=INK)
    logo = logo.resize((int(420 * 1.12), 110))  # the 12% stretch (VI-04)
    img.paste(logo, (90, 880))
    img.save(path, optimize=True)
    return path


if __name__ == "__main__":
    print(make(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT))
