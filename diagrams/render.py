"""Regenerate editable drawings and optimized WebP from the supplied CSV examples."""
import csv
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
INK = "#132b43"
TEAL = "#006b68"
PURPLE = "#58409a"
LINE = "#c7d9df"


def base(title, subtitle, h):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="880" height="{h}" viewBox="0 0 880 {h}">'
        f'<rect width="880" height="{h}" rx="24" fill="#eef6f7"/>'
        '<g font-family="DejaVu Sans, sans-serif">'
        + label(42, 58, title, 34, bold=True)
        + label(42, 104, subtitle, 22)
    )


def label(x, y, words, size, fill=INK, center=False, bold=False):
    anchor = ' text-anchor="middle"' if center else ""
    weight = ' font-weight="700"' if bold else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}"{anchor}{weight}>{words}</text>'


def read(name):
    with (HERE.parent / "examples" / name).open(newline="", encoding="utf-8") as fp:
        return [(int(r["A"]), int(r["B"])) for r in csv.DictReader(fp)]


def waveform():
    xy = [160, 313, 466, 619, 772]
    data = read("forward.csv")
    svg = base("One electrical cycle", "A leads B. Each observed edge adds one X4 count.", 490)
    for x in xy:
        svg += f'<path d="M{x} 132V402" stroke="{LINE}" stroke-width="2" stroke-dasharray="6 8"/>'
    for chan, high, color in ((0, 165, TEAL), (1, 277, PURPLE)):
        svg += label(48, high + 45, "A" if chan == 0 else "B", 31, color, bold=True)
        svg += label(101, high + 7, "1", 22) + label(101, high + 64, "0", 22)
        levels = [high + 57 * (1 - row[chan]) for row in data]
        path = f"M128 {levels[0]}" + "".join(f"H{x}V{y}" for x, y in zip(xy, levels)) + "H830"
        svg += f'<path d="{path}" stroke="{color}" stroke-width="6" stroke-linejoin="round" fill="none"/>'
        for x, y in zip(xy, levels):
            svg += f'<circle cx="{x}" cy="{y}" r="7" fill="{color}" stroke="#fff" stroke-width="2"/>'
    for i, (x, (a, b)) in enumerate(zip(xy, data)):
        svg += label(x, 395, f"{a}{b}", 28, center=True, bold=True)
        svg += label(x, 443, str(i), 26, TEAL, center=True)
    svg += label(40, 395, "A/B", 24) + label(40, 443, "Count", 24)
    return svg


def scaling():
    svg = base("Where is the encoder mounted?", "Same 2,000 X4 counts per encoder turn.", 510)
    for y, heading, detail, count, step in [
        (137, "Direct output encoder", "1 encoder turn per output turn", "2,000", "0.180°"),
        (320, "Motor encoder before reduction", "12 encoder turns per output turn", "24,000", "0.015°"),
    ]:
        svg += f'<rect x="42" y="{y}" width="796" height="160" rx="18" fill="white" stroke="{LINE}" stroke-width="2"/>'
        svg += label(64, y + 40, heading, 30, bold=True)
        svg += label(64, y + 79, detail, 22)
        svg += label(64, y + 127, f"{count} counts / output turn", 23, PURPLE, bold=True)
        svg += label(519, y + 127, f"{step} / count", 25, TEAL, bold=True)
    return svg


def render():
    for name, drawing in (("encoder-ab-cycle", waveform()), ("encoder-mounting", scaling())):
        source = HERE / f"{name}.svg"
        source.write_text(drawing + "</g></svg>\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as work:
            png = Path(work) / "drawing.png"
            subprocess.run(
                ["inkscape", str(source), f"--export-filename={png}"],
                check=True, capture_output=True,
            )
            with Image.open(png) as image:
                image.convert("RGB").save(HERE / f"{name}.webp", "WEBP", quality=86, method=6)


if __name__ == "__main__":
    render()
