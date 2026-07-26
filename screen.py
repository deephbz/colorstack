#!/usr/bin/env python3
"""Screen every theme Ghostty ships against our floors.

    python3 screen.py                 top light candidates, ranked
    python3 screen.py --all           every light theme, no cutoff
    python3 screen.py --warm          only warm surfaces (warmth > 2)
    python3 screen.py --show NAME     one theme in detail
    python3 screen.py --promote NAME  emit a palettes.py entry to paste

Why this exists. Picking candidates from memory is picking from whatever is
popular on the internet, and it gets hexes wrong. Ghostty ships ~460 themes as
files, so the whole space can be measured rather than recalled.

What this measures, and what it does NOT. A Ghostty theme is *derived output* --
sixteen already-resolved hexes -- not the authored intent a Palette holds. So a
screen answers exactly one question: as shipped, how much does this scheme
already satisfy the floors? That is `moved` and `fidelity`, and it is the honest
version of "how much of what I would see is the scheme versus repair output".

It cannot answer structure, because ANSI slot 7 is a light tier in some themes
and the ink in others (Rose Pine Dawn puts the ink there), so surface tiers are
unknowable from this file. Screening therefore leaves them None. A theme that
survives screening gets hand-promoted into palettes.py WITH real tiers read from
upstream -- `--promote` writes the stub, a human fills the tiers.

Design: docs/ontology.md (authored versus derived). Promotion remains a human
choice because a shipped theme file cannot reveal the source palette's tiers.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import theme as T
from colorspace import CEILINGS, FLOORS, contrast, lstar, repair, repair_delta
from palettes import Palette

THEME_DIRS = [
    Path("/Applications/Ghostty.app/Contents/Resources/ghostty/themes"),
    Path.home() / ".config/ghostty/themes",
]

PALETTE_LINE = re.compile(r"^\s*palette\s*=\s*(\d+)\s*=\s*(#[0-9a-fA-F]{6})", re.M)
KEY_LINE = re.compile(r"^\s*([a-z-]+)\s*=\s*(#[0-9a-fA-F]{6})", re.M)


def load(path: Path) -> Palette | None:
    """One Ghostty theme file -> a Palette, or None if it is not usable.

    Accents come from ANSI 1-6 and are keyed by index, not by hue name: the
    slots are scrambled relative to hue in several schemes and the role names
    would be fiction. Screening does not need them -- only whether six accents
    clear the floor and how far repair drags them.
    """
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return None
    slots = {int(i): c.lower() for i, c in PALETTE_LINE.findall(text)}
    keys = dict(KEY_LINE.findall(text))
    bg, fg = keys.get("background"), keys.get("foreground")
    if not bg or not fg or not all(i in slots for i in range(1, 7)):
        return None
    return Palette(
        name=path.name,
        bg=bg.lower(),
        fg=fg.lower(),
        accents={f"a{i}": slots[i] for i in range(1, 7)},
        # deliberately no tiers -- see the module docstring
        note=f"screened from {path.parent.name}/{path.name}",
    )


def all_themes() -> list[Palette]:
    out, seen = [], set()
    for d in THEME_DIRS:
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.name not in seen:
                p = load(f)
                if p:
                    out.append(p)
                    seen.add(f.name)
    return out


def light(pals: list[Palette], min_lstar: float = 85.0) -> list[Palette]:
    return [p for p in pals if lstar(p.bg) >= min_lstar]


def dark(pals: list[Palette], max_lstar: float = 25.0, min_lstar: float = 10.0) -> list[Palette]:
    """Dark surfaces, as a BAND rather than a cutoff.

    The lower bound is the load-bearing half. Near-black surfaces (L* < 10)
    maximise halation -- the bloom of a light glyph into a dark field is driven
    by the ratio, and pure black makes it as large as the panel allows. They
    also cap contrast at 21:1 total, which squeezes every accent into a narrow
    band and makes the numbers look better than the experience.

    The upper bound is conventional: past L* 25 a 'dark' theme is really a
    mid-grey one, and it fails the only thing dark is good for.
    """
    return [p for p in pals if min_lstar <= lstar(p.bg) <= max_lstar]


def score(p: Palette, floor: float) -> tuple:
    """Rank key, and it differs by polarity because the failure mode does.

    On a light surface the scarce thing is contrast, so rank by fidelity (how
    much repair had to invent) and break ties on coherence to white and warmth.

    On a dark surface contrast is free -- fidelity reads 0.00 for dozens of
    schemes and decides nothing -- so rank by glare (how far above comfort the
    accents sit) and break ties on spread, i.e. how tellable-apart they are.
    """
    if p.is_dark:
        return (p.accents_moved(floor), p.glare(), -p.accent_spread())
    return (p.fidelity(floor), p.step_to_white, -p.warmth)


HDR_LIGHT = (
    f"  {'theme':26s}{'bg':10s}{'L*':>6s}{'→white':>8s}"
    f"{'warm':>7s}{'moved':>7s}{'fidel':>8s}{'ink':>8s}"
)

HDR_DARK = (
    f"  {'theme':26s}{'bg':10s}{'L*':>6s}{'warm':>7s}"
    f"{'hot':>6s}{'glare':>8s}{'spread':>8s}{'ink':>8s}"
)


def row(p: Palette, floor: float) -> str:
    if p.is_dark:
        hot = f"{p.accents_glaring()}/{len(p.accents)}"
        return (
            f"  {p.name[:25]:26s}{p.bg:10s}{lstar(p.bg):6.1f}{p.warmth:7.1f}"
            f"{hot:>6s}{p.glare():8.2f}{p.accent_spread():8.1f}"
            f"{p.ink_contrast:7.1f}:1"
        )
    moved = f"{p.accents_moved(floor)}/{len(p.accents)}"
    return (
        f"  {p.name[:25]:26s}{p.bg:10s}{lstar(p.bg):6.1f}{p.step_to_white:8.1f}"
        f"{p.warmth:7.1f}{moved:>7s}{p.fidelity(floor):8.2f}"
        f"{p.ink_contrast:7.1f}:1"
    )


def show(p: Palette, floor: float) -> None:
    print(f"\n{p.name}   bg {p.bg}  L* {lstar(p.bg):.1f}  warmth {p.warmth:+.1f}")
    print(f"  ink {p.fg}  {p.ink_contrast:.2f}:1")
    for k, c in p.accents.items():
        r = contrast(c, p.bg)
        flag = ""
        if r < floor:
            flag = f"  -> {repair(c, p.bg, floor)}  ({repair_delta(c, p.bg, floor):.1f} L*)"
        print(f"  {k:4s} {c}  {r:5.2f}:1{flag}")
    th = T.build(p)
    problems = th.check()
    print("  builds clean" if not problems else f"  FAILS: {problems}")
    print()


def promote(p: Palette) -> str:
    """A palettes.py stub. Tiers are left as TODO on purpose -- they cannot be
    recovered from a Ghostty theme file and must be read from upstream."""
    ident = re.sub(r"[^A-Z0-9]+", "_", p.name.upper()).strip("_")
    lines = [
        f"{ident} = Palette(",
        f'    name="{p.name}",',
        f'    key="{p.name.split()[0].lower()}",',
        f'    bg="{p.bg}",',
        f'    fg="{p.fg}",',
        "    bg_soft=None,  # TODO from upstream: must sit ABOVE bg",
        "    bg_alt=None,   # TODO from upstream: the dim/comment tier",
        '    bg_hi="#ffffff",',
        "    accents={",
    ]
    lines += [f'        "{k}": "{c}",' for k, c in p.accents.items()]
    lines += [
        "    },",
        f'    note="screened from Ghostty; accents keyed by ANSI slot, rename by hue",',
        ")",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", type=float, default=FLOORS["text"])
    ap.add_argument("--min-lstar", type=float, default=85.0)
    ap.add_argument("--max-lstar", type=float, default=25.0)
    ap.add_argument("--min-dark-lstar", type=float, default=10.0)
    ap.add_argument("--dark", action="store_true", help="screen dark surfaces")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--warm", action="store_true")
    ap.add_argument("--show")
    ap.add_argument("--promote")
    a = ap.parse_args()

    pals = all_themes()
    if not pals:
        print("no Ghostty themes found; is Ghostty installed?", file=sys.stderr)
        raise SystemExit(2)

    if a.show or a.promote:
        want = (a.show or a.promote).lower()
        hit = [p for p in pals if p.name.lower() == want]
        if not hit:
            hit = [p for p in pals if want in p.name.lower()]
        if not hit:
            print(f"no theme matching {want!r}", file=sys.stderr)
            raise SystemExit(2)
        if a.promote:
            print(promote(hit[0]))
        else:
            for p in hit[:5]:
                show(p, a.floor)
        return

    if a.dark:
        cands = dark(pals, a.max_lstar, a.min_dark_lstar)
        band = f"dark (L* {a.min_dark_lstar}-{a.max_lstar})"
    else:
        cands = light(pals, a.min_lstar)
        band = f"light (L* >= {a.min_lstar})"
    if a.warm:
        cands = [p for p in cands if p.warmth > 2.0]
    cands.sort(key=lambda p: score(p, a.floor))

    print(f"\n{len(pals)} themes on disk, {len(cands)} {band}")
    if a.dark:
        print(f"ranked by floor failures, then glare (ceiling "
              f"{CEILINGS['accent']}), then spread\n")
        print(HDR_DARK)
    else:
        print(f"ranked by fidelity at floor {a.floor}, then coherence, then warmth\n")
        print(HDR_LIGHT)
    for p in cands if a.all else cands[: a.top]:
        print(row(p, a.floor))
    print()


if __name__ == "__main__":
    main()
