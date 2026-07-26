"""Pure color math kernel.

No I/O, no config, no terminal. Everything else in the color stack derives from
these functions, so this file is the one place where a physics or perception
claim is encoded.

Vocabulary used throughout:

    rgb        tuple of three floats in [0, 1], gamma-ENCODED sRGB
    linear     tuple of three floats in [0, 1], linear-light sRGB
    Y          relative luminance, 0 = black, 1 = white (linear light)
    L*         CIE lightness, 0 = black, 100 = white (perceptual)
    oklab      (L, a, b) with L in [0, 1] -- perceptually uniform, hue-stable
    oklch      (L, C, h) polar form of oklab, h in degrees

Design: docs/ontology.md (verbs and authored-versus-derived boundary).
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------
# hex <-> rgb
# --------------------------------------------------------------------------


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    h = value.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"not a hex color: {value!r}")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


def rgb_to_255(rgb: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(round(max(0.0, min(1.0, c)) * 255) for c in rgb)  # type: ignore[return-value]


# --------------------------------------------------------------------------
# gamma <-> linear light, and luminance
# --------------------------------------------------------------------------


def srgb_to_linear(c: float) -> float:
    """Undo the sRGB transfer function: encoded value -> linear light."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    """Apply the sRGB transfer function: linear light -> encoded value."""
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def luminance(color: str | tuple[float, float, float]) -> float:
    """Relative luminance Y. Weights are cone density, not aesthetics."""
    r, g, b = hex_to_rgb(color) if isinstance(color, str) else color
    return (
        0.2126 * srgb_to_linear(r)
        + 0.7152 * srgb_to_linear(g)
        + 0.0722 * srgb_to_linear(b)
    )


def _lab_f(t: float) -> float:
    return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29


def lstar(color: str | tuple[float, float, float] | float) -> float:
    """CIE L*, the perceptual lightness of a color (or of a bare Y value)."""
    y = color if isinstance(color, float) else luminance(color)
    return 116 * _lab_f(y) - 16


def y_from_lstar(l: float) -> float:
    """Inverse of lstar() for a neutral: what Y does this L* correspond to?"""
    fy = (l + 16) / 116
    return fy**3 if fy > 6 / 29 else (fy - 4 / 29) * (108 / 841)


def gray_at_lstar(l: float) -> str:
    """The neutral gray whose perceptual lightness is L*."""
    c = linear_to_srgb(y_from_lstar(l))
    return rgb_to_hex((c, c, c))


# --------------------------------------------------------------------------
# contrast
# --------------------------------------------------------------------------


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio. The 0.05 models ambient light reflecting off glass;
    it is why differences among bright colors collapse on a light surface."""
    ya, yb = luminance(a), luminance(b)
    hi, lo = max(ya, yb), min(ya, yb)
    return (hi + 0.05) / (lo + 0.05)


# --------------------------------------------------------------------------
# CIELAB (D65) -- used for the warmth axis b*
# --------------------------------------------------------------------------

_D65 = (0.95047, 1.00000, 1.08883)


def cielab(color: str | tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = hex_to_rgb(color) if isinstance(color, str) else color
    rl, gl, bl = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl
    y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl
    z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl
    fx, fy, fz = (_lab_f(v / w) for v, w in zip((x, y, z), _D65))
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def warmth(color: str) -> float:
    """The yellow-blue axis, x100: positive is warm, negative is cool.

    Measured as OKLab b, not CIELAB b*, so warmth is reported in the same space
    repair() moves colors through. The two agree on ordering but differ by
    roughly 3.8x in magnitude, so a number without its space is meaningless.
    """
    return 100 * oklab(color)[2]


# --------------------------------------------------------------------------
# OKLab / OKLch -- Bjorn Ottosson's uniform space
# --------------------------------------------------------------------------


def oklab(color: str | tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = hex_to_rgb(color) if isinstance(color, str) else color
    rl, gl, bl = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    l = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
    m = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
    s = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_rgb(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = (v**3 for v in (l_, m_, s_))
    rl = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    gl = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(linear_to_srgb(v) for v in (rl, gl, bl))  # type: ignore[return-value]


def oklch(color: str | tuple[float, float, float]) -> tuple[float, float, float]:
    L, a, b = oklab(color)
    return (L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)


def oklch_to_hex(lch: tuple[float, float, float]) -> str:
    L, C, h = lch
    rad = math.radians(h)
    return rgb_to_hex(oklab_to_rgb((L, C * math.cos(rad), C * math.sin(rad))))


def mix_oklab(a: str, b: str, t: float) -> str:
    """Blend two colors in OKLab. t=0 gives `a`, t=1 gives `b`.

    Uniform in the same space repair() works in, so a half-mix looks half-way
    rather than merely being half-way arithmetically. Used to synthesize
    surface tiers when a scheme ships none above its own background.
    """
    la, lb = oklab(a), oklab(b)
    return rgb_to_hex(oklab_to_rgb(tuple(x + (y - x) * t for x, y in zip(la, lb))))


def delta_e(a: str, b: str) -> float:
    """Perceptual distance in OKLab, scaled x100 so the numbers read like CIE
    dE. Includes lightness, chroma and hue -- a full 'how different is this'."""
    la, aa, ba = oklab(a)
    lb, ab, bb = oklab(b)
    return 100 * math.dist((la, aa, ba), (lb, ab, bb))


# --------------------------------------------------------------------------
# HSL -- only kept so the tutorial can show what NOT to darken in
# --------------------------------------------------------------------------


def rgb_to_hsl(color: str) -> tuple[float, float, float]:
    r, g, b = hex_to_rgb(color)
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return (0.0, 0.0, l)
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return (h * 60, s, l)


def hsl_to_hex(hsl: tuple[float, float, float]) -> str:
    h, s, l = hsl
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    seg = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)]
    r, g, b = seg[int(h // 60) % 6]
    return rgb_to_hex((r + m, g + m, b + m))


def darken_hsl(color: str, amount: float) -> str:
    """Naive darkening: drop HSL lightness. Shifts hue. Used as a foil."""
    h, s, l = rgb_to_hsl(color)
    return hsl_to_hex((h, s, max(0.0, l - amount)))


def darken_oklab(color: str, amount: float) -> str:
    """Hue-preserving darkening: drop OKLab L, scale chroma with it."""
    L, C, h = oklch(color)
    newL = max(0.0, L - amount)
    scale = newL / L if L > 0 else 0.0
    return oklch_to_hex((newL, C * scale, h))


def lighten_oklab(color: str, amount: float) -> str:
    """Hue-preserving lightening: raise OKLab L, hold chroma.

    Deliberately NOT the mirror of darken_oklab. That one scales chroma with
    lightness, which is right going down -- a colour approaching black loses
    saturation. Going up, the same rule would scale chroma UP, pushing colours
    out of gamut so the conversion clips them and the hue shifts. Holding
    chroma keeps the hue and lets the colour desaturate naturally as it nears
    white, which is what the eye expects of a 'bright' variant.
    """
    L, C, h = oklch(color)
    return oklch_to_hex((min(1.0, L + amount), C, h))


# --------------------------------------------------------------------------
# repair -- the one verb that makes floors work
# --------------------------------------------------------------------------

# Contrast floors by role class. These are intent, not decoration.
FLOORS = {"text": 4.5, "accent": 3.0, "decor": 2.0, "hard_min": 1.5}


def repair(color: str, bg: str, floor: float, steps: int = 96) -> str:
    """Move `color` away from `bg` in OKLab lightness until it clears `floor`.

    Chroma is scaled with lightness so the hue survives the move -- the result
    still reads as 'the red one', just legible. Returns `color` unchanged if it
    already clears the floor. Returns the best achievable color if the floor is
    unreachable (fully black or white still short of it).
    """
    if contrast(color, bg) >= floor:
        return color
    L0, C0, h = oklch(color)
    target = 0.0 if lstar(bg) > 50 else 1.0  # move away from the surface
    lo, hi = (0.0, L0) if target == 0.0 else (L0, 1.0)
    best = color
    for _ in range(steps):
        mid = (lo + hi) / 2
        scale = mid / L0 if L0 > 0 else 0.0
        cand = oklch_to_hex((mid, C0 * min(scale, 1.0) if target == 0.0 else C0, h))
        if contrast(cand, bg) >= floor:
            best = cand
            lo, hi = (mid, hi) if target == 0.0 else (lo, mid)
        else:
            lo, hi = (lo, mid) if target == 0.0 else (mid, hi)
    return best


def soften(color: str, bg: str, ceiling: float, steps: int = 96) -> str:
    """Move `color` TOWARD `bg` until it no longer exceeds `ceiling`.

    The mirror of repair(), and deliberately a separate verb rather than a
    clamp inside it: repair is 'move away until legible', and bolting 'move
    back if too legible' onto it makes one name mean two things. Contrast has a
    floor for legibility and a ceiling for comfort, and they are different
    concerns that happen to act on the same axis.

    Returns `color` unchanged if it is already at or under the ceiling.
    """
    if contrast(color, bg) <= ceiling:
        return color
    L0, C0, h = oklch(color)
    Lbg = oklch(bg)[0]
    lo, hi = (L0, Lbg) if Lbg > L0 else (Lbg, L0)
    best = color
    for _ in range(steps):
        mid = (lo + hi) / 2
        cand = oklch_to_hex((mid, C0, h))
        if contrast(cand, bg) <= ceiling:
            best = cand
            lo, hi = (lo, mid) if Lbg > L0 else (mid, hi)
        else:
            lo, hi = (mid, hi) if Lbg > L0 else (lo, mid)
    return best


def repair_delta(color: str, bg: str, floor: float) -> float:
    """How far repair had to move a color, in L* units. High values mean you
    are looking at repair output rather than at the scheme you chose."""
    return abs(lstar(repair(color, bg, floor)) - lstar(color))


def soften_delta(color: str, bg: str, ceiling: float) -> float:
    """How far soften had to pull a color back, in L* units.

    The dark-surface counterpart of repair_delta. On a light surface the risk
    is accents that are too faint to read; on a dark surface almost everything
    clears the floor trivially and the risk inverts -- accents so hot they
    halate. Measuring only repair on a dark theme measures nothing.
    """
    return abs(lstar(soften(color, bg, ceiling)) - lstar(color))


# Comfort ceilings, the mirror of FLOORS. Only meaningful on dark surfaces,
# where light-on-dark glyphs bloom: a 19:1 accent on near-black is not "extra
# legible", it is a light source with a shape. 12.0 is a judgement, not a
# standard -- WCAG defines no upper bound, because it models legibility and not
# comfort. Anchored only by preference, and labelled as such.
CEILINGS = {"text": 12.0, "accent": 12.0}
