#!/usr/bin/env python3
"""Render og.png (1200x630 social card) from data/aiae.json and stamp its
version into index.html's og:image / twitter:image URLs so link previews refresh
when a new quarter arrives. Requires matplotlib."""
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "aiae.json").read_text())
OUT = ROOT / "og.png"
INDEX = ROOT / "index.html"

BG, CARD, BORDER = "#f4f3ef", "#fcfcfb", "#e2e0d9"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#7a7972", "#ebe9e3"
BLUE, ORANGE, REF = "#2a78d6", "#eb6834", "#8b8a84"
plt.rcParams["font.family"] = "DejaVu Sans"


def year(q):
    return int(q[:4]) + (int(q[-1]) - 1) / 4


def main():
    rows = [r for r in DATA["rows"] if r[0] >= "1952Q1"]
    q, a, d = rows[-1]
    prev_max = max(r[1] for r in rows[:-1])
    mean = sum(r[1] for r in rows) / len(rows)
    label_q = q.replace("Q", " Q")

    fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
    fig.add_artist(plt.Rectangle((0.025, 0.04), 0.95, 0.92, transform=fig.transFigure,
                                 facecolor=CARD, edgecolor=BORDER, linewidth=1.5, zorder=-10))

    fig.text(0.06, 0.855, "AIAE: original vs. detrended", fontsize=34, weight="bold", color=INK)
    fig.text(0.06, 0.79, f"Aggregate Investor Allocation to Equities  ·  data through {label_q}",
             fontsize=15, color=INK2)

    # Left column: the two headline readings.
    fig.text(0.06, 0.66, "ORIGINAL AIAE", fontsize=13, color=INK2, weight="bold")
    fig.text(0.06, 0.53, f"{a:.1f}%", fontsize=52, weight="bold", color=BLUE)
    note = "record high" if a > prev_max else f"long-run avg {mean:.1f}%"
    fig.text(0.06, 0.48, note, fontsize=14, color=INK2)

    fig.text(0.06, 0.36, "DETRENDED", fontsize=13, color=INK2, weight="bold")
    fig.text(0.06, 0.23, f"{d:+.1f} pts", fontsize=52, weight="bold", color=ORANGE)
    fig.text(0.06, 0.18, f"{'above' if d >= 0 else 'below'} its 20-year average", fontsize=14, color=INK2)

    fig.text(0.06, 0.085, "spinchange.com/aiae  ·  Fed Z.1 Financial Accounts via FRED",
             fontsize=13, color=MUTED)

    # Right column: two small charts sharing a timeline.
    def panel(rect, xs, ys, color, ref=None, zero=False):
        ax = fig.add_axes(rect, facecolor=CARD)
        ax.plot(xs, ys, color=color, linewidth=2.2, solid_joinstyle="round")
        ax.scatter([xs[-1]], [ys[-1]], s=60, color=color, edgecolor=CARD, linewidth=2, zorder=3)
        if ref is not None:
            ax.axhline(ref, color=REF, linewidth=1.3, linestyle=(0, (5, 4)))
        if zero:
            ax.axhline(0, color=MUTED, linewidth=1)
        ax.set_xlim(1952, xs[-1] + 0.5)
        ax.grid(axis="y", color=GRID, linewidth=1)
        ax.tick_params(colors=MUTED, labelsize=11, length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_axisbelow(True)
        return ax

    xs = [year(r[0]) for r in rows]
    top = panel([0.51, 0.47, 0.44, 0.27], xs, [r[1] for r in rows], BLUE, ref=mean)
    top.set_xticklabels([])
    top.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    det = [r for r in rows if r[2] is not None]
    bot = panel([0.51, 0.15, 0.44, 0.27], [year(r[0]) for r in det], [r[2] for r in det], ORANGE, zero=True)
    bot.yaxis.set_major_formatter(lambda v, _: f"{v:+.0f}" if v else "0")
    for ax in (top, bot):
        ax.set_xticks(range(1960, int(xs[-1]) + 1, 20))

    fig.savefig(OUT, dpi=100, facecolor=BG)
    print(f"Wrote {OUT.name} for {q}: AIAE {a:.1f}%, detrended {d:+.1f}")

    # Version the image URL so platforms re-fetch it when the quarter changes.
    html = INDEX.read_text()
    new = re.sub(r'(og\.png)(\?v=[0-9A-Za-z]+)?"', rf'\1?v={q}"', html)
    if new != html:
        INDEX.write_text(new)


if __name__ == "__main__":
    main()
