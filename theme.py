"""Palette -> a concrete 16-colour terminal theme.

The ANSI 16 are *derived*, not transcribed from someone's table. Intent hues
plus floors go in; legible hexes come out. That is the whole claim of the
stack, so the terminal theme had better be produced that way too.

The ANSI convention INVERTS with polarity, and slots 0, 7 and 15 are where it
bites. Slots 1-6, 8 and 9-14 mean the same thing on both:

    1-6      accents at the TEXT floor -- you read code in these, so 4.5:1,
             not the 3.0 an accent gets when it is only decoration.
    8        "bright black" = comments and dimmed UI. The single most abused
             slot in light themes: left at a dark-theme value it becomes
             invisible. Floored at 3.0 against the surface.
    9-14     bright variants. "Brighter" must always mean FURTHER from the
             surface, never lighter in absolute terms -- so these go darker on
             a light theme and lighter on a dark one.

              slot | light surface              | dark surface
              -----|----------------------------|---------------------------
                0  | the ink; "black" is body    | a near-black below the
                   | text on a light surface     | surface -- TUIs paint
                   |                             | backgrounds with it
                7  | a light tier used as a      | the default light text,
                   | background by TUIs. Not     | i.e. the ink
                   | white.                      |
               15  | the lightest tier, white    | white

On a dark surface accents also acquire a CEILING (`colorspace.CEILINGS`) that
they do not have on light: contrast is nearly free below, so the failure mode
flips from "too faint to read" to "bright enough to halate".

Design: docs/ontology.md. The ink target and dark-surface comfort ceiling are
Theme-level obligations because they compose `repair()` and `soften()`.
"""

from __future__ import annotations

from dataclasses import dataclass

from colorspace import (
    CEILINGS,
    FLOORS,
    contrast,
    darken_oklab,
    lighten_oklab,
    lstar,
    mix_oklab,
    repair,
    soften,
)
from palettes import Palette

# Which palette role fills each ANSI slot. Missing roles fall back by hue.
ANSI_ROLES = ["red", "green", "yellow", "blue", "magenta", "cyan"]
ALIASES = {
    "magenta": ("magenta", "purple", "violet", "pink"),
    "cyan": ("cyan", "aqua", "teal"),
    "blue": ("blue",),
    "red": ("red",),
    "green": ("green",),
    "yellow": ("yellow", "orange"),
}


@dataclass(frozen=True)
class Theme:
    """A palette resolved against one surface. Every hex here is derived."""

    name: str
    bg: str
    fg: str
    cursor: str
    selection_bg: str
    selection_fg: str
    ansi: list[str]  # exactly 16
    dim: str  # comments / secondary text
    bg_soft: str
    bg_alt: str
    bg_hi: str
    source: Palette

    @property
    def is_light(self) -> bool:
        return lstar(self.bg) > 50

    def as_dict(self) -> dict:
        d = {
            "name": self.name,
            "bg": self.bg,
            "fg": self.fg,
            "cursor": self.cursor,
            "selection_bg": self.selection_bg,
            "selection_fg": self.selection_fg,
            "dim": self.dim,
            "bg_soft": self.bg_soft,
            "bg_alt": self.bg_alt,
            "bg_hi": self.bg_hi,
        }
        d.update({f"ansi{i}": c for i, c in enumerate(self.ansi)})
        return d

    def check(self) -> list[str]:
        """Every legibility claim this theme makes, verified against itself."""
        out = []
        if contrast(self.fg, self.bg) < FLOORS["text"]:
            out.append(f"body text {contrast(self.fg, self.bg):.2f}:1 < 4.5")
        for i in list(range(1, 7)) + list(range(9, 15)):
            c = contrast(self.ansi[i], self.bg)
            if c < FLOORS["text"] - 0.01:
                out.append(f"ansi{i} {self.ansi[i]} is {c:.2f}:1 < 4.5")
        c8 = contrast(self.ansi[8], self.bg)
        if c8 < FLOORS["accent"] - 0.01:
            out.append(f"ansi8 (comments) {c8:.2f}:1 < 3.0")
        if lstar(self.bg_soft) < lstar(self.bg):
            out.append("bg_soft is darker than bg -- surface has no headroom")

        # Polarity invariants for the neutral ramp. These are the claims that
        # were silently false for dark palettes before they were checked.
        light = lstar(self.bg) > 50
        if light:
            if lstar(self.ansi[0]) > lstar(self.bg):
                out.append("ansi0 is lighter than bg -- 'black' is not ink")
            if lstar(self.ansi[15]) < lstar(self.bg):
                out.append("ansi15 is darker than bg -- 'bright white' inverted")
        else:
            if lstar(self.ansi[0]) > lstar(self.bg):
                out.append("ansi0 is lighter than bg -- TUI boxes will invert")
            if lstar(self.ansi[7]) < lstar(self.bg):
                out.append("ansi7 is darker than bg -- 'white' is not light")
            for i in list(range(1, 7)) + list(range(9, 15)):
                c = contrast(self.ansi[i], self.bg)
                if c > CEILINGS["accent"] + 0.01:
                    out.append(f"ansi{i} {self.ansi[i]} is {c:.2f}:1 > 12 (glare)")
        # "Bright" must mean further from the surface, whichever way that is.
        for lo, hi in zip(range(1, 7), range(9, 15)):
            if contrast(self.ansi[hi], self.bg) < contrast(self.ansi[lo], self.bg) - 0.01:
                out.append(f"ansi{hi} is closer to bg than ansi{lo} -- bright inverted")
        return out


def _role(pal: Palette, name: str) -> str | None:
    for key in ALIASES.get(name, (name,)):
        if key in pal.accents:
            return pal.accents[key]
    return None


def build(pal: Palette, ink_contrast: float = 10.0) -> Theme:
    """Resolve a palette into a terminal theme against its own surface.

    `ink_contrast` is the comfort target for body text -- the ceiling the brief
    identified as missing. repair() only enforces floors, so we set the ink
    explicitly rather than letting the scheme's default stand.
    """
    bg = pal.bg
    light = lstar(bg) > 50

    # Body ink: aim at the comfort target from BOTH sides. repair() raises ink
    # that is too faint (Lotus ships 6.2:1); soften() lowers ink that is too
    # harsh (Flexoki 18.6:1, Modus 19.7:1). Without the second half a comparison
    # between schemes is partly a comparison of ink harshness.
    fg = soften(repair(pal.fg, bg, ink_contrast), bg, ink_contrast)

    # Accents at the TEXT floor -- these carry code, not decoration.
    normal = []
    for role in ANSI_ROLES:
        src = _role(pal, role)
        if src is None:  # scheme lacks this hue; borrow the ink
            normal.append(fg)
        else:
            normal.append(repair(src, bg, FLOORS["text"]))

    # Bright variants. "Bright" means further from the surface in both
    # polarities -- darker on a light theme, lighter on a dark one. Getting
    # this backwards is the single most common light-theme bug, and the naive
    # dark version (leave them equal to 1-6) silently wastes six slots.
    step = darken_oklab if light else lighten_oklab
    bright = [step(c, 0.10) for c in normal]
    bright = [repair(c, bg, FLOORS["text"]) for c in bright]
    if not light:
        # On dark, pushing brights toward white can send them past comfort.
        bright = [soften(c, bg, CEILINGS["accent"]) for c in bright]

    # Comments: dimmed but still legible. Floored at the accent level.
    dim = repair(pal.bg_alt or bg, bg, FLOORS["accent"])

    # Surface tiers. If the scheme's own "soft" tier sits at or below its
    # background -- true of Lotus, whose surface is the lightest thing it
    # ships -- there is no headroom for a raised panel, so synthesize one by
    # stepping toward white. Stated rather than silently papered over.
    white = "#ffffff"
    soft = pal.bg_soft
    if soft is None or lstar(soft) <= lstar(bg) + 0.5:
        soft = mix_oklab(bg, white, 0.45 if light else 0.10)

    # Slots 0, 7 and 15 are the neutral ramp, and they INVERT with polarity.
    # On a light theme 0 is the ink and 15 is white; on a dark theme 0 must be
    # a near-black (TUIs paint backgrounds with it) and 7 is the default light
    # text. Emitting the light mapping on a dark surface gives you a terminal
    # whose "black" is bright -- boxes and status bars come out inverted.
    if light:
        tier0 = fg
        tier7 = pal.bg_alt or bg
        tier15 = pal.bg_hi or white
        hi = tier15
    else:
        tier0 = mix_oklab(bg, "#000000", 0.5)
        tier7 = fg
        tier15 = white
        hi = pal.bg_hi if pal.bg_hi and lstar(pal.bg_hi) > lstar(bg) else soft

    ansi = [
        tier0,  # 0
        *normal,  # 1-6
        tier7,  # 7
        dim,  # 8
        *bright,  # 9-14
        tier15,  # 15
    ]
    assert len(ansi) == 16, len(ansi)

    return Theme(
        name=pal.name,
        bg=bg,
        fg=fg,
        cursor=repair(_role(pal, "red") or fg, bg, FLOORS["text"]),
        selection_bg=pal.bg_alt or pal.bg_soft or bg,
        selection_fg=fg,
        ansi=ansi,
        dim=dim,
        bg_soft=soft,
        bg_alt=pal.bg_alt or bg,
        bg_hi=hi,
        source=pal,
    )


def slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("(", "").replace(")", "")
