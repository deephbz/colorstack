"""Tests for the color kernel.

These pin the claims the lessons make. If a lesson tells you a number, there is
a test here that produces it -- otherwise the lesson is just an assertion in
prose, which is the thing the whole setup exists to avoid.

    python3 -m pytest test_colorstack.py -q
"""

from __future__ import annotations

import json
import os
import pwd
import subprocess
import sys
from pathlib import Path

import pytest

import gen
import palettes as P
import regions
import theme as T
from colorspace import (
    FLOORS,
    contrast,
    darken_hsl,
    darken_oklab,
    gray_at_lstar,
    hex_to_rgb,
    hsl_to_hex,
    lstar,
    luminance,
    oklab,
    oklab_to_rgb,
    oklch,
    oklch_to_hex,
    repair,
    repair_on,
    rgb_to_hex,
    warmth,
    y_from_lstar,
)

# -- round trips ----------------------------------------------------------


@pytest.mark.parametrize("h", ["#000000", "#ffffff", "#fbf1c7", "#3c3836", "#458588"])
def test_hex_roundtrip(h):
    assert rgb_to_hex(hex_to_rgb(h)) == h


@pytest.mark.parametrize("h", ["#000000", "#ffffff", "#fbf1c7", "#d79921", "#0000ff"])
def test_oklab_roundtrip(h):
    assert rgb_to_hex(oklab_to_rgb(oklab(h))) == h


def test_lstar_inverse():
    for l in (0, 15, 32.3, 50, 76.1, 95, 100):
        assert lstar(y_from_lstar(l)) == pytest.approx(l, abs=1e-6)


# -- lesson 1: gamma ------------------------------------------------------


def test_mid_gray_emits_about_a_fifth_of_white():
    assert luminance("#808080") == pytest.approx(0.216, abs=0.002)


def test_half_light_gray_is_much_lighter_than_half_code():
    assert gray_at_lstar(lstar(0.5)) == "#bcbcbc"


def test_luminance_endpoints():
    assert luminance("#000000") == pytest.approx(0.0)
    assert luminance("#ffffff") == pytest.approx(1.0)


# -- lesson 3: contrast ---------------------------------------------------


def test_contrast_is_symmetric():
    assert contrast("#3c3836", "#fbf1c7") == contrast("#fbf1c7", "#3c3836")


def test_max_contrast_is_21():
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)


def test_pure_yellow_is_invisible_on_cream():
    assert contrast("#ffff00", "#fbf1c7") == pytest.approx(1.06, abs=0.02)


def test_repairing_yellow_to_text_floor_costs_it_its_yellowness():
    fixed = repair("#ffff00", "#fbf1c7", FLOORS["text"])
    assert lstar("#ffff00") - lstar(fixed) > 35


# -- lesson 5: HSL is not a lightness -------------------------------------


def test_hsl_lightness_is_not_lightness():
    at50 = {h: hsl_to_hex((h, 1.0, 0.5)) for h in (60, 240)}
    assert lstar(at50[60]) == pytest.approx(97.1, abs=0.5)
    assert lstar(at50[240]) == pytest.approx(32.3, abs=0.5)


def test_oklab_darkening_is_more_uniform_than_hsl():
    hues = [0, 60, 120, 180, 240, 300]
    pure = [hsl_to_hex((h, 1.0, 0.5)) for h in hues]
    hsl_drops = [lstar(c) - lstar(darken_hsl(c, 0.20)) for c in pure]
    ok_drops = [lstar(c) - lstar(darken_oklab(c, 0.20)) for c in pure]
    hsl_spread = max(hsl_drops) - min(hsl_drops)
    ok_spread = max(ok_drops) - min(ok_drops)
    assert hsl_spread > 20
    assert ok_spread < 3
    assert hsl_spread / ok_spread > 5


# -- lesson 4/6: repair and the free surface ------------------------------


def test_repair_is_a_noop_when_the_floor_is_already_met():
    assert repair("#3c3836", "#fbf1c7", FLOORS["text"]) == "#3c3836"


def test_repair_preserves_hue():
    from colorspace import oklch

    for c in ("#cc241d", "#458588", "#98971a", "#b16286"):
        fixed = repair(c, "#fbf1c7", FLOORS["text"])
        drift = (oklch(fixed)[2] - oklch(c)[2] + 180) % 360 - 180
        assert abs(drift) < 3.0, f"{c} drifted {drift:.1f} degrees"


@pytest.mark.parametrize(
    "surface",
    ["#ffffff", "#fbf1c7", "#f9f5d7", "#f2ecbc", "#ebdbb2", "#3c3836", "#1d2021"],
)
def test_the_surface_is_a_free_parameter(surface):
    """No surface can make the stack unreadable. This is the whole payoff."""
    for role, color in P.GRUVBOX_LIGHT_TUNED.accents.items():
        fixed = repair(color, surface, FLOORS["accent"])
        assert contrast(fixed, surface) >= FLOORS["accent"] - 0.01, role
    ink = repair(P.GRUVBOX_LIGHT_TUNED.fg, surface, FLOORS["text"])
    assert contrast(ink, surface) >= FLOORS["text"] - 0.01


# -- the comfort ceiling (D4) ---------------------------------------------


def test_soften_is_a_noop_below_the_ceiling():
    from colorspace import soften

    assert soften("#545464", "#f2ecbc", 10.0) == "#545464"


def test_soften_lands_on_the_ceiling_from_above():
    from colorspace import soften

    for c in ("#100f0f", "#000000", "#3c3836", "#721045"):
        assert contrast(c, "#fffcf0") > 8.0, f"{c} is not above the ceiling"
        eased = soften(c, "#fffcf0", 8.0)
        assert contrast(eased, "#fffcf0") == pytest.approx(8.0, abs=0.05), c


def test_soften_preserves_hue_like_repair_does():
    """Only meaningful for chromatic ink: the hue angle of a near-neutral is
    numerically unstable, so #3c3836 (chroma 0.008) 'drifts' 5 degrees while
    remaining the same visually-gray brown."""
    from colorspace import oklch, soften

    for c in ("#1e66f5", "#a60000", "#3d2b5a", "#5c6a72"):
        assert oklch(c)[1] > 0.02, f"{c} is not chromatic enough to test"
        eased = soften(c, "#fffcf0", 4.0)
        drift = (oklch(eased)[2] - oklch(c)[2] + 180) % 360 - 180
        assert abs(drift) < 3.0, f"{c} drifted {drift:.1f} degrees"


@pytest.mark.parametrize("pal", P.ALL)
def test_every_scheme_builds_to_the_same_ink_so_a_comparison_is_fair(pal):
    """D4's comfort target has to bind from both sides.

    repair() only moves away from the surface, so on its own it raises faint
    ink (Lotus 6.2:1) and leaves harsh ink alone (Flexoki 18.6:1, Modus
    19.7:1). A scheme comparison run that way is partly a comparison of ink
    harshness rather than of the schemes.
    """
    th = T.build(pal, ink_contrast=10.0)
    assert contrast(th.fg, th.bg) == pytest.approx(10.0, abs=0.15), pal.name


# -- gamut and surfaces ---------------------------------------------------


def _hue_gap(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def test_out_of_gamut_oklch_keeps_lightness_and_hue():
    """A saturated violet lifted on a dark surface used to drift ~9 degrees
    under a per-channel clamp. Chroma gives way instead."""
    L, C, h = oklch("#8500ff")
    L2, C2, h2 = oklch(oklch_to_hex((0.65, C, h)))
    assert L2 == pytest.approx(0.65, abs=0.005)
    assert _hue_gap(h, h2) < 1.0
    assert C2 < C


def test_repair_on_clears_the_strictest_surface():
    surfaces = ("#fbf1c7", "#ebdbb2")
    fixed = repair_on("#d79921", surfaces, FLOORS["text"])
    assert all(contrast(fixed, s) >= FLOORS["text"] - 0.01 for s in surfaces)


def test_loud_scheme_tier_is_softened_to_a_panel():
    """Vimbones ships a 2.0:1 alt tier; as a selection it would cost every
    accent its fidelity, so the theme quiets it first."""
    from colorspace import CEILINGS

    th = T.build(P.VIMBONES)
    assert contrast(th.bg_alt, th.bg) <= CEILINGS["panel"] + 0.01
    assert contrast(th.selection_bg, th.bg) <= CEILINGS["panel"] + 0.01


def test_pi_tool_panels_are_theme_surfaces():
    th = T.build(P.MODUS_OPERANDI_TINTED)
    tokens = json.loads(gen.pi_theme(th))["vars"]
    assert tokens["errorBg"] == th.panels["error"]
    assert th.panels["error"] in th.surfaces


# -- polarity (D12) -------------------------------------------------------


@pytest.mark.parametrize("pal", P.ALL)
def test_every_scheme_passes_its_own_check(pal):
    assert T.build(pal).check() == [], pal.name


@pytest.mark.parametrize("pal", [p for p in P.ALL if p.is_dark])
def test_dark_themes_put_a_near_black_in_slot_zero(pal):
    """ANSI 0 is painted as a BACKGROUND by TUIs. On a dark theme the light
    mapping (slot 0 = the ink) inverts every box and status bar."""
    th = T.build(pal)
    assert lstar(th.ansi[0]) < lstar(th.bg), pal.name
    assert lstar(th.ansi[7]) > lstar(th.bg), pal.name


@pytest.mark.parametrize("pal", P.ALL)
def test_bright_means_further_from_the_surface_in_both_polarities(pal):
    """The bright variants must never sit closer to the background than the
    normal ones -- 'lighter' is the wrong rule on a light theme, and leaving
    them equal (the old dark behaviour) wastes six slots."""
    th = T.build(pal)
    for lo, hi in zip(range(1, 7), range(9, 15)):
        assert contrast(th.ansi[hi], th.bg) >= contrast(th.ansi[lo], th.bg) - 0.01


@pytest.mark.parametrize("pal", [p for p in P.ALL if p.is_dark])
def test_dark_accents_respect_the_comfort_ceiling(pal):
    from colorspace import CEILINGS

    th = T.build(pal)
    for i in list(range(1, 7)) + list(range(9, 15)):
        assert contrast(th.ansi[i], th.bg) <= CEILINGS["accent"] + 0.01


def test_fidelity_does_not_discriminate_on_dark_surfaces():
    """Why dark needs its own rank key: the metric that decided the light
    comparison is degenerate here, because contrast is nearly free below."""
    dark = [p for p in P.ALL if p.is_dark]
    assert len(dark) >= 3
    assert sum(1 for p in dark if p.fidelity(4.5) == 0.0) >= 2


def test_light_and_dark_emitters_differ_where_polarity_matters():
    light = gen.ghostty(T.build(P.GRUVBOX_MATERIAL_LIGHT))
    dark = gen.ghostty(T.build(P.GRUVBOX_MATERIAL_DARK))
    assert "font-thicken = true" in light
    assert "font-thicken = false" in dark
    assert 'data-jp-theme-light="true"' in gen.jupyter_css(T.build(P.FLEXOKI_LIGHT))
    assert 'data-jp-theme-light="false"' in gen.jupyter_css(T.build(P.ZENBONES_DARK))
    assert "JupyterLab Dark" in gen.jupyter_theme(T.build(P.ZENBONES_DARK))


# -- the brief's published measurements -----------------------------------


@pytest.mark.parametrize(
    "pal,l,step,warm",
    [
        (P.FLEXOKI_LIGHT, 98.9, 1.1, 1.6),
        (P.SELENIZED_LIGHT, 95.9, 4.1, 3.3),
        (P.KANAGAWA_LOTUS, 92.8, 7.2, 6.1),
        (P.SOLARIZED_LIGHT, 97.0, 3.0, 2.6),
    ],
)
def test_reproduces_published_surface_measurements(pal, l, step, warm):
    assert pal.surface_lstar == pytest.approx(l, abs=0.05)
    assert pal.step_to_white == pytest.approx(step, abs=0.05)
    assert pal.warmth == pytest.approx(warm, abs=0.05)


@pytest.mark.parametrize(
    "pal,ink",
    [
        (P.GRUVBOX_LIGHT_TUNED, 10.2),
        (P.FLEXOKI_LIGHT, 18.6),
        (P.SELENIZED_LIGHT, 5.4),
        (P.KANAGAWA_LOTUS, 6.2),
    ],
)
def test_reproduces_published_ink_contrast(pal, ink):
    assert pal.ink_contrast == pytest.approx(ink, abs=0.05)


def test_fidelity_ranking_reproduces_at_the_text_floor_not_the_accent_floor():
    """The published finalist table was computed at 4.5, not at 3.0.

    At the accent floor the metric does not discriminate at all, which is the
    finding lesson 10 is built on.
    """
    at_3 = {p.name: p.fidelity(3.0) for p in P.ALL}
    at_45 = {p.name: p.fidelity(4.5) for p in P.ALL}
    assert at_3[P.FLEXOKI_LIGHT.name] == pytest.approx(0.0, abs=0.01)
    assert at_3[P.KANAGAWA_LOTUS.name] == pytest.approx(0.0, abs=0.01)
    # at 4.5 the published ordering appears: Flexoki most faithful of the three
    assert at_45[P.FLEXOKI_LIGHT.name] < at_45[P.KANAGAWA_LOTUS.name]
    assert at_45[P.KANAGAWA_LOTUS.name] < at_45[P.SELENIZED_LIGHT.name]
    assert at_45[P.FLEXOKI_LIGHT.name] == pytest.approx(1.4, abs=0.4)


def test_structure_rule_rejects_a_surface_with_no_headroom():
    """#f9f5d7 was rejected as a surface because bg_soft had nowhere to go."""
    assert P.GRUVBOX_LIGHT_TUNED.structure_ok()
    no_headroom = P.Palette(
        name="too high",
        bg="#f9f5d7",
        fg="#3c3836",
        accents={"red": "#cc241d"},
        bg_soft="#fbf1c7",
        bg_hi="#ffffff",
    )
    assert not no_headroom.structure_ok()


# -- generated application themes ----------------------------------------


def test_jupyter_css_preserves_data_width_and_removes_chrome_latency():
    css = gen.jupyter_css(T.build(P.FLEXOKI_LIGHT, ink_contrast=10.0))
    assert "--jp-content-font-size1: 15px" in css
    assert "--jp-code-line-height: 1.5" in css
    assert "max-width: 1180px" in css
    assert "max-width: 72ch" in css
    assert "font-variant-numeric: tabular-nums" in css
    assert ".lm-TabBar-tab" in css and "transition: none !important" in css
    assert "@import" not in css  # no remote font or stylesheet startup cost


# -- lesson 7: regions ----------------------------------------------------

SAMPLE = f"""font-family = Berkeley Mono
# {regions.BEGIN} ghostty
# {regions.END} ghostty
keybind = cmd+k=clear_screen
"""


def test_splice_is_idempotent():
    once = regions.splice(SAMPLE, "ghostty", "background = fbf1c7")
    twice = regions.splice(once, "ghostty", "background = fbf1c7")
    assert once == twice
    assert regions.extract(once, "ghostty") == "background = fbf1c7"


def test_splice_leaves_human_owned_lines_alone():
    out = regions.splice(SAMPLE, "ghostty", "background = fbf1c7")
    assert "font-family = Berkeley Mono" in out
    assert "keybind = cmd+k=clear_screen" in out


def test_drift_is_detected():
    good = regions.splice(SAMPLE, "ghostty", "background = fbf1c7")
    bad = good.replace("fbf1c7", "1d2021")
    assert regions.drift(good, "ghostty", "background = fbf1c7") == []
    assert regions.drift(bad, "ghostty", "background = fbf1c7")


def test_stray_hexes_outside_the_region_are_found():
    out = regions.splice(SAMPLE, "ghostty", "background = fbf1c7")
    out += "cursor-color = #ff0000\n"
    assert regions.stray_hexes(out, "ghostty") == ["#ff0000"]


def test_missing_region_is_an_error_not_a_silent_skip():
    with pytest.raises(KeyError):
        regions.splice(SAMPLE, "tmux", "anything")


# -- public output bundle switching ---------------------------------------


def test_pi_theme_is_a_complete_named_payload():
    payload = json.loads(gen.pi_theme(T.build(P.MODUS_OPERANDI_TINTED)))
    assert payload["name"] == "colorstack"
    assert payload["colors"]["accent"] == "blue"
    required = {
        "accent", "border", "success", "error", "warning", "selectedBg",
        "toolPendingBg", "mdHeading", "syntaxKeyword", "thinkingXhigh", "bashMode",
    }
    assert required <= payload["colors"].keys()


def test_switch_replaces_only_a_proven_colorstack_bundle(tmp_path):
    bundle = tmp_path / "colorstack-output"
    switch = Path(gen.__file__).with_name("switch.py")
    command = [sys.executable, str(switch), "modus", "--output-root", str(bundle)]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    manifest = json.loads((bundle / ".colorstack-manifest.json").read_text())
    assert manifest["scheme"] == "modus"
    assert set(manifest["outputs"]) == set(gen.OUTPUT_BY_KEY)
    assert (bundle / "outputs/pi-theme").is_file()

    second = subprocess.run(
        [sys.executable, str(switch), "vimbones", "--output-root", str(bundle)],
        capture_output=True,
        text=True,
    )
    assert second.returncode == 0, second.stderr
    assert json.loads((bundle / ".colorstack-manifest.json").read_text())["scheme"] == "vimbones"

    (bundle / "not-colorstack-owned").write_text("keep me\n")
    refused = subprocess.run(
        [sys.executable, str(switch), "modus", "--output-root", str(bundle)],
        capture_output=True,
        text=True,
    )
    assert refused.returncode != 0
    assert "not an intact Colorstack output bundle" in refused.stderr
    assert json.loads((bundle / ".colorstack-manifest.json").read_text())["scheme"] == "vimbones"


# -- test HOME isolation -----------------------------------------------------


def test_tests_run_in_a_fresh_home():
    operator = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    assert Path.home().resolve() != operator
    assert Path.home().name.startswith("colorstack-test-home-")
