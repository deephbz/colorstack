"""Terminal rendering primitives.

Every demo paints its own explicit background rather than inheriting the
terminal's, so what you see does not depend on whatever theme is currently
loaded. That independence is the whole point: this is the test pattern for
things no oracle can query, i.e. what the glass actually shows a human.
"""

from __future__ import annotations

import os
import shutil
import textwrap

from colorspace import contrast, lstar, rgb_to_255

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
ITALIC = "\x1b[3m"


def width() -> int:
    return min(shutil.get_terminal_size((80, 24)).columns, 92)


def bg(color: str) -> str:
    r, g, b = rgb_to_255(_rgb(color))
    return f"\x1b[48;2;{r};{g};{b}m"


def fg(color: str) -> str:
    r, g, b = rgb_to_255(_rgb(color))
    return f"\x1b[38;2;{r};{g};{b}m"


def _rgb(color: str):
    from colorspace import hex_to_rgb

    return hex_to_rgb(color)


def on(fore: str, back: str, text: str) -> str:
    return f"{bg(back)}{fg(fore)}{text}{RESET}"


def swatch(color: str, w: int = 8) -> str:
    return f"{bg(color)}{' ' * w}{RESET}"


def swatch_row(colors: list[str], w: int = 6) -> str:
    return "".join(swatch(c, w) for c in colors)


def readable_on(back: str) -> str:
    """Pick black or white ink for a label sitting on `back`."""
    return "#000000" if lstar(back) > 55 else "#ffffff"


def labeled_swatch(color: str, label: str, w: int = 14) -> str:
    text = label.center(w)[:w]
    return f"{bg(color)}{fg(readable_on(color))}{text}{RESET}"


def panel(lines: list[str], back: str, fore: str, pad: int = 2) -> str:
    """A block of text on an explicit surface, padded to a fixed width."""
    w = width()
    inner = w - 2 * pad
    out = [f"{bg(back)}{' ' * w}{RESET}"]
    for line in lines:
        body = line[:inner].ljust(inner)
        out.append(f"{bg(back)}{fg(fore)}{' ' * pad}{body}{' ' * pad}{RESET}")
    out.append(f"{bg(back)}{' ' * w}{RESET}")
    return "\n".join(out)


Segments = list[tuple[str, str]]  # (text, fg color)


def seg_line(segments: Segments, back: str, pad: int = 2) -> str:
    """Render coloured segments on one painted row, padded to full width."""
    w = width()
    visible = sum(len(t) for t, _ in segments)
    body = "".join(f"{fg(c)}{t}" for t, c in segments)
    tail = " " * max(0, w - visible - 2 * pad)
    return f"{bg(back)}{' ' * pad}{body}{tail}{' ' * pad}{RESET}"


def code_panel(back: str, fore: str, accents: dict[str, str]) -> str:
    """A fake source listing -- the actual thing you stare at for hours."""
    a = list(accents.values())

    def pick(i: int) -> str:
        return a[i % len(a)]

    rows: list[Segments] = [
        [("def ", pick(4)), ("repair", pick(5)), ("(color, bg, floor):", fore)],
        [("    # move away from the surface until legible", pick(1))],
        [("    if", pick(4)), (" contrast(color, bg) ", fore), (">=", pick(6)),
         (" floor:", fore)],
        [("        return", pick(4)), (" color", fore)],
        [("    L, C, h ", fore), ("=", pick(6)), (" oklch(color)", fore)],
        [("    warn", pick(2)), ("  accent floor ", fore), ("3.0", pick(3)),
         (" unreachable", fore)],
        [("    error", pick(0)), ("  surface is the lightest tier", fore)],
    ]
    blank = f"{bg(back)}{' ' * width()}{RESET}"
    return "\n".join([blank, *(seg_line(r, back) for r in rows), blank])


def ratio_bar(value: float, target: float = 21.0, w: int = 24) -> str:
    filled = max(0, min(w, round(w * value / target)))
    return "█" * filled + DIM + "░" * (w - filled) + RESET


def contrast_line(fore: str, back: str, label: str) -> str:
    c = contrast(fore, back)
    mark = "  " if c >= 4.5 else (" ~" if c >= 3.0 else " x")
    return (
        f"  {labeled_swatch(back, '', 3)}{on(fore, back, ' ' + label.ljust(18))}"
        f"  {c:6.2f}:1 {mark}  {ratio_bar(c)}"
    )


def hr(char: str = "─") -> str:
    return DIM + char * width() + RESET


def title(text: str) -> str:
    return f"\n{BOLD}{text}{RESET}\n{hr()}"


def wrap(text: str, indent: str = "") -> str:
    """Reflow prose to the terminal width.

    A line beginning with '|' is emitted verbatim (minus the marker) instead of
    being reflowed, so tables and lists can live inside prose blocks without
    being collapsed into a paragraph.
    """
    w = width()
    out = []
    for para in text.strip("\n").split("\n\n"):
        lines = textwrap.dedent(para).splitlines()
        if any(line.lstrip().startswith("|") for line in lines):
            out.append(
                "\n".join(
                    indent + (s[1:] if (s := line.lstrip()).startswith("|") else s)
                    for line in lines
                )
            )
        else:
            joined = " ".join(line.strip() for line in lines)
            out.append(
                textwrap.fill(
                    joined, width=w, initial_indent=indent, subsequent_indent=indent
                )
            )
    return "\n\n".join(out)


def clear() -> None:
    if os.environ.get("COLORLAB_NOCLEAR"):
        print("\n" * 2)
    else:
        print("\x1b[2J\x1b[H", end="")


def supports_truecolor() -> bool:
    return os.environ.get("COLORTERM", "") in ("truecolor", "24bit")
