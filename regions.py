"""Generated regions inside real config files.

The mechanism behind 'generate-and-override, not validate-only'. A layer's
config file is owned jointly: the human owns everything outside the markers,
the generator owns everything inside. Divergence is not detected and reported,
it is overwritten -- which makes it inexpressible rather than merely visible.

Three things are defects by construction:
  * a hex literal outside a region      (a color authored somewhere else)
  * a region nested inside a region     (unclear ownership)
  * a whole-theme directive in a layer  (a theme silently owns every key the
                                         generated region does not mention)

Design: docs/ontology.md (the ownership boundary and defect classes).
"""

from __future__ import annotations

import re

BEGIN = "colorstack:BEGIN"
END = "colorstack:END"

HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def _markers(text: str, name: str) -> tuple[int, int, int, int]:
    b = re.search(rf"^(.*){re.escape(BEGIN)} {re.escape(name)}.*$", text, re.M)
    e = re.search(rf"^(.*){re.escape(END)} {re.escape(name)}.*$", text, re.M)
    if not b or not e:
        raise KeyError(f"no region {name!r} in this file")
    return b.start(), b.end(), e.start(), e.end()


def ensure(text: str, name: str, comment: str = "#", top: bool = False) -> str:
    """Add an empty region to a file that has none yet. Idempotent.

    `top` prepends instead of appending, which TOML forces on us: a bare key
    such as `palette = "x"` written after any [table] header becomes a member
    of that table rather than a top-level key. So a selector goes at the top
    and the table it selects goes at the bottom -- two regions, not one.
    """
    try:
        _markers(text, name)
        return text
    except KeyError:
        block = f"{comment} {BEGIN} {name}\n{comment} {END} {name}\n"
        if top:
            return block + "\n" + text
        pad = "" if text.endswith("\n") or not text else "\n"
        return f"{text}{pad}\n{block}"


def splice(text: str, name: str, payload: str) -> str:
    """Replace the body of region `name` with `payload`. Idempotent."""
    _, be, es, _ = _markers(text, name)
    body = payload if payload.endswith("\n") else payload + "\n"
    return text[:be] + "\n" + body + text[es:]


def extract(text: str, name: str) -> str:
    _, be, es, _ = _markers(text, name)
    return text[be:es].strip("\n")


def drift(text: str, name: str, expected: str) -> list[str]:
    """What in this file no longer matches what the palette would generate."""
    problems = []
    actual = extract(text, name).strip()
    if actual != expected.strip():
        a, b = actual.splitlines(), expected.strip().splitlines()
        for i in range(max(len(a), len(b))):
            got = a[i] if i < len(a) else "<missing>"
            want = b[i] if i < len(b) else "<extra>"
            if got != want:
                problems.append(f"line {i + 1}: has {got!r}, palette says {want!r}")
    return problems


def stray_hexes(text: str, name: str) -> list[str]:
    """Hex literals living outside the generated region -- colors authored in
    a place the palette cannot reach."""
    _, be, es, _ = _markers(text, name)
    outside = text[:be] + text[es:]
    return HEX.findall(outside)
