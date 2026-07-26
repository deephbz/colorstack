"""Candidate schemes, as data.

A Palette is what a human authors. Everything downstream is derived, so this is
the only place a color is chosen rather than computed.

Note what a Palette does NOT contain: no per-application keys, no ANSI indices,
no config syntax. Those belong to layers. A palette holds intent hues, the
surface family, and the contrast floors that intent must satisfy.

Design: docs/ontology.md. Palette notes capture candidate-specific tradeoffs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from colorspace import (
    CEILINGS,
    FLOORS,
    contrast,
    delta_e,
    lstar,
    repair,
    repair_delta,
    soften_delta,
    warmth,
)


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str  # the surface -- a free parameter, see lesson 6
    fg: str  # body ink, as the scheme's author shipped it
    accents: dict[str, str]  # intent hues, by role name
    bg_soft: str | None = None  # secondary surface; must sit ABOVE bg
    bg_alt: str | None = None
    bg_hi: str | None = None  # highest surface, pairs with a role-as-background
    floors: dict[str, float] = field(default_factory=lambda: dict(FLOORS))
    note: str = ""
    key: str = ""  # CLI name; authored, because deriving it from `name` collides
                   # ("Gruvbox Light" vs "Gruvbox Material Light") and dies on
                   # non-ASCII ("Rose Pine Dawn" is spelled with an e-acute).

    # -- derived measurements -------------------------------------------

    @property
    def surface_lstar(self) -> float:
        return lstar(self.bg)

    @property
    def step_to_white(self) -> float:
        """L* distance to #ffffff. Chrome, Jupyter and Obsidian page content is
        near-white and cannot be re-tinted, so this is the app-switch jolt."""
        return 100 - lstar(self.bg)

    @property
    def warmth(self) -> float:
        return warmth(self.bg)

    @property
    def ink_contrast(self) -> float:
        return contrast(self.fg, self.bg)

    def accents_moved(self, floor: float | None = None) -> int:
        floor = self.floors["accent"] if floor is None else floor
        return sum(1 for c in self.accents.values() if contrast(c, self.bg) < floor)

    def fidelity(self, floor: float | None = None) -> float:
        """Mean L* distance repair must drag the scheme's own accents. High
        means you are running repair output, not the scheme.

        The floor is an argument because the answer depends on it entirely: at
        3.0 almost nothing moves and every scheme looks faithful, so a fidelity
        number quoted without its floor is not a measurement.
        """
        floor = self.floors["accent"] if floor is None else floor
        d = [repair_delta(c, self.bg, floor) for c in self.accents.values()]
        return sum(d) / len(d) if d else 0.0

    @property
    def is_dark(self) -> bool:
        return lstar(self.bg) <= 50

    def accents_glaring(self, ceiling: float | None = None) -> int:
        ceiling = CEILINGS["accent"] if ceiling is None else ceiling
        return sum(1 for c in self.accents.values() if contrast(c, self.bg) > ceiling)

    def glare(self, ceiling: float | None = None) -> float:
        """Mean L* distance soften must pull the scheme's own accents back.

        The dark-surface mirror of fidelity(). On a dark background nearly every
        accent clears the text floor, so fidelity reads 0.00 for dozens of
        schemes and decides nothing; what separates them is how many accents sit
        far ABOVE comfort. High glare means a scheme that will bloom at night.
        """
        ceiling = CEILINGS["accent"] if ceiling is None else ceiling
        d = [soften_delta(c, self.bg, ceiling) for c in self.accents.values()]
        return sum(d) / len(d) if d else 0.0

    def accent_spread(self) -> float:
        """Mean pairwise OKLab distance among accents -- how tellable-apart the
        palette is, independent of polarity. Low spread is the failure the brief
        called convergence: eight roles that all read as the same muddy colour.
        Measured on the accents as authored, so it is a property of the scheme
        rather than of our repair."""
        vals = list(self.accents.values())
        pairs = [
            delta_e(a, b) for i, a in enumerate(vals) for b in vals[i + 1 :]
        ]
        return sum(pairs) / len(pairs) if pairs else 0.0

    def repaired(self, floor: float | None = None) -> dict[str, str]:
        floor = self.floors["accent"] if floor is None else floor
        return {k: repair(v, self.bg, floor) for k, v in self.accents.items()}

    def structure_ok(self) -> bool:
        """The surface may not be the lightest tier of its own family: bg_soft
        and bg_hi have to have somewhere above the surface to sit. bg_alt is
        excluded -- it is legitimately a darker tier on a light theme."""
        above = [s for s in (self.bg_soft, self.bg_hi) if s]
        return all(lstar(s) >= lstar(self.bg) for s in above) if above else True


GRUVBOX_LIGHT_TUNED = Palette(
    name="Gruvbox Light (tuned)",
    key="gruvbox",
    bg="#fbf1c7",
    fg="#3c3836",
    bg_soft="#f9f5d7",
    bg_alt="#ebdbb2",
    bg_hi="#ffffff",
    accents={
        "red": "#cc241d",
        "green": "#98971a",
        "yellow": "#d79921",
        "blue": "#458588",
        "purple": "#b16286",
        "aqua": "#689d6a",
        "orange": "#d65d0e",
    },
    note="reference Gruvbox palette; ink is resolved to the requested target",
)

FLEXOKI_LIGHT = Palette(
    name="Flexoki Light",
    key="flexoki",
    bg="#fffcf0",
    fg="#100f0f",
    bg_soft="#f2f0e5",
    bg_alt="#e6e4d9",
    bg_hi="#ffffff",
    accents={
        "red": "#af3029",
        "orange": "#bc5215",
        "yellow": "#ad8301",
        "green": "#66800b",
        "cyan": "#24837b",
        "blue": "#205ea6",
        "purple": "#5e409d",
        "magenta": "#a02f6f",
    },
    note="best numbers, least warm; native ink is 18.6:1 which is too harsh",
)

SELENIZED_LIGHT = Palette(
    name="Selenized Light",
    key="selenized",
    bg="#fbf3db",
    fg="#53676d",
    bg_soft="#ece3cc",
    bg_alt="#d5cdb6",
    bg_hi="#ffffff",
    accents={
        "red": "#d2212d",
        "green": "#489100",
        "yellow": "#ad8900",
        "blue": "#0072d4",
        "magenta": "#ca4898",
        "cyan": "#009c8f",
        "orange": "#c25d1e",
        "violet": "#8265d6",
    },
    note="native ink only 5.4:1; ink is a free parameter so this is fixable",
)

KANAGAWA_LOTUS = Palette(
    name="Kanagawa Lotus",
    key="kanagawa",
    bg="#f2ecbc",
    fg="#545464",
    bg_soft="#f2ecbc",
    bg_alt="#e7dba0",
    bg_hi="#ffffff",
    accents={
        "red": "#c84053",
        "green": "#6f894e",
        "yellow": "#77713f",
        "blue": "#4d699b",
        "violet": "#624c83",
        "aqua": "#597b75",
        "orange": "#cc6d00",
    },
    note="warmest surface; pays a 7.2 L* step on every app switch",
)

SOLARIZED_LIGHT = Palette(
    name="Solarized Light",
    key="solarized",
    bg="#fdf6e3",
    fg="#657b83",
    bg_soft="#eee8d5",
    bg_alt="#e6dfcc",
    bg_hi="#ffffff",
    accents={
        "red": "#dc322f",
        "green": "#859900",
        "yellow": "#b58900",
        "blue": "#268bd2",
        "magenta": "#d33682",
        "cyan": "#2aa198",
        "orange": "#cb4b16",
        "violet": "#6c71c4",
    },
    note="eliminated: every accent needs repair, so all character is repair output",
)

CATPPUCCIN_LATTE = Palette(
    name="Catppuccin Latte",
    key="catppuccin",
    bg="#eff1f5",
    fg="#4c4f69",
    bg_soft="#e6e9ef",
    bg_alt="#dce0e8",
    bg_hi="#ffffff",
    accents={
        "red": "#d20f39",
        "green": "#40a02b",
        "yellow": "#df8e1d",
        "blue": "#1e66f5",
        "mauve": "#8839ef",
        "teal": "#179299",
        "peach": "#fe640b",
    },
    note="popular but cool-toned; rejected on measured contrast, not on taste",
)

# --------------------------------------------------------------------------
# Found by screening Ghostty's 464 shipped themes (see screen.py). Only 14 of
# them are both light and warm, so this is close to the whole warm-light space
# rather than a sample of it.
# --------------------------------------------------------------------------

VIMBONES = Palette(
    name="Vimbones",
    key="vimbones",
    bg="#f0f0ca",
    fg="#353535",
    bg_soft=None,  # ships no tier above its surface; theme.build synthesizes one
    bg_alt="#acac89",
    bg_hi="#ffffff",
    accents={
        "red": "#a8334c",
        "green": "#4f6c31",
        "orange": "#944927",
        "blue": "#286486",
        "magenta": "#88507d",
        "cyan": "#3b8992",
    },
    note="warm and already at the text floor: only cyan needs repair",
)

GRUVBOX_MATERIAL_LIGHT = Palette(
    name="Gruvbox Material Light",
    key="gruvbox-material",
    bg="#fbf1c7",
    fg="#654735",
    bg_soft="#f9f5d7",  # upstream's "hard" background, genuinely lighter
    bg_alt="#e5d5ad",
    bg_hi="#ffffff",
    accents={
        "red": "#c14a4a",
        "orange": "#c35e0a",
        "yellow": "#b47109",
        "green": "#6c782e",
        "aqua": "#4c7a5d",
        "blue": "#45707a",
        "purple": "#945e80",
    },
    note="the old Gruvbox surface with accents that mostly clear the floor",
)

MODUS_OPERANDI_TINTED = Palette(
    name="Modus Operandi Tinted",
    key="modus",
    bg="#fbf7f0",
    fg="#000000",  # 21:1 as shipped; the ink ceiling in theme.build tames it
    bg_soft=None,
    bg_alt="#efe9dd",
    bg_hi="#ffffff",
    accents={
        "red": "#a60000",
        "green": "#006800",
        "yellow": "#6f5500",
        "blue": "#0031a9",
        "magenta": "#721045",
        "cyan": "#005e8b",
    },
    note="built to WCAG AAA, so nothing moves; near-white and barely warm",
)

EVERFOREST_LIGHT = Palette(
    name="Everforest Light",
    key="everforest",
    bg="#fdf6e3",
    fg="#5c6a72",
    bg_soft="#fffbef",  # upstream's "hard" background
    bg_alt="#e6e2cc",
    bg_hi="#ffffff",
    accents={
        "red": "#f85552",
        "orange": "#f57d26",
        "yellow": "#dfa000",
        "green": "#8da101",
        "aqua": "#35a77c",
        "blue": "#3a94c5",
        "purple": "#df69ba",
    },
    note="popular and low-contrast by design; kept to record that it fails here. "
    "Ghostty's own 'Everforest Light Med' is worse still -- it pairs this "
    "background with the DARK variant's accents, so screen.py scores the file, "
    "not the scheme.",
)

# --------------------------------------------------------------------------
# Dark surfaces. A different competition, not the same one upside down: on a
# dark background nearly every accent clears the text floor, so `fidelity`
# reads 0.00 for dozens of schemes and decides nothing. What separates them is
# glare (accents sitting far above comfort) and spread (whether the roles are
# tellable apart). See decisions.md D12.
#
# Surfaces are kept in the L* 10-25 band. Near-black maximises halation and
# caps total contrast at 21:1, which flatters the numbers and hurts the eyes.
# --------------------------------------------------------------------------

GRUVBOX_MATERIAL_DARK = Palette(
    name="Gruvbox Material Dark",
    key="gruvbox-material-dark",
    bg="#282828",
    fg="#d4be98",
    bg_soft="#32302f",
    bg_alt="#45403d",
    bg_hi="#5a524c",
    accents={
        "red": "#ea6962",
        "orange": "#e78a4e",
        "yellow": "#d8a657",
        "green": "#a9b665",
        "aqua": "#89b482",
        "blue": "#7daea3",
        "purple": "#d3869b",
    },
    note="the tightest accent band measured: every accent 4.7-6.7:1, nothing "
    "glares, nothing needs repair. Dark sibling of the light scheme.",
)

ZENBONES_DARK = Palette(
    name="Zenbones Dark",
    key="zenbones-dark",
    bg="#1c1917",
    fg="#b4bdc3",
    bg_soft="#252220",
    bg_alt="#2c2827",
    bg_hi="#3d3839",
    accents={
        "red": "#de6e7c",
        "green": "#819b69",
        "orange": "#b77e64",
        "blue": "#6099c0",
        "magenta": "#b279a7",
        "cyan": "#66a5ad",
    },
    note="warmest dark surface in the corpus (+0.5) and the tightest spread "
    "after Gruvbox Material; sibling of Vimbones.",
)

KANAGAWA_WAVE = Palette(
    name="Kanagawa Wave",
    key="kanagawa-wave",
    bg="#1f1f28",
    fg="#dcd7ba",
    bg_soft="#2a2a37",
    bg_alt="#363646",
    bg_hi="#54546d",
    accents={
        "red": "#c34043",
        "green": "#76946a",
        "yellow": "#c0a36e",
        "blue": "#7e9cd8",
        "violet": "#957fb8",
        "aqua": "#6a9589",
        "orange": "#ffa066",
    },
    note="dark sibling of Lotus. Its red is 3.22:1 -- the only accent in any "
    "promoted dark scheme that fails the text floor, so repair moves it 9.6 L*.",
)

MODUS_VIVENDI_TINTED = Palette(
    name="Modus Vivendi Tinted",
    key="modus-dark",
    bg="#0d0e1c",
    fg="#ffffff",
    bg_soft="#1d2235",
    bg_alt="#2a3045",
    bg_hi="#3a3f5a",
    accents={
        "red": "#ff5f59",
        "green": "#44bc44",
        "yellow": "#d0bc00",
        "blue": "#2fafff",
        "magenta": "#feacd0",
        "cyan": "#00d3d0",
    },
    note="accessibility-first, and it shows the dark failure mode: L* 4.4 is "
    "below the halation band and three accents exceed the comfort ceiling.",
)

ALL = [
    GRUVBOX_LIGHT_TUNED,
    FLEXOKI_LIGHT,
    SELENIZED_LIGHT,
    KANAGAWA_LOTUS,
    SOLARIZED_LIGHT,
    CATPPUCCIN_LATTE,
    VIMBONES,
    GRUVBOX_MATERIAL_LIGHT,
    MODUS_OPERANDI_TINTED,
    EVERFOREST_LIGHT,
    GRUVBOX_MATERIAL_DARK,
    ZENBONES_DARK,
    KANAGAWA_WAVE,
    MODUS_VIVENDI_TINTED,
]

BY_KEY = {p.key or p.name.split()[0].lower(): p for p in ALL}

assert len(BY_KEY) == len(ALL), "two palettes share a CLI key"
