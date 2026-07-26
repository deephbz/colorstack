#!/usr/bin/env python3
"""Replace one explicit Colorstack-owned output bundle with another palette.

    ./switch.py modus --output-root ~/Downloads/colorstack-output
    ./switch.py kanagawa --output-root ~/Downloads/colorstack-output

This command never discovers, reads, edits, links, validates, or reloads an
application configuration. It replaces only an output bundle whose manifest and
file set prove Colorstack generated it. Copy the named payloads into your own
dotfiles convention afterwards.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

import gen
import palettes as P
import theme as T
from colorspace import contrast


def owned_bundle(root: Path) -> bool:
    """Return whether *root* contains exactly a Colorstack output bundle."""
    manifest_path = root / gen.MANIFEST_NAME
    if not root.is_dir() or root.is_symlink() or not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or manifest.get("generator") != "colorstack"
        or not isinstance(manifest.get("outputs"), dict)
    ):
        return False
    expected = {gen.MANIFEST_NAME}
    for key, row in manifest["outputs"].items():
        if key not in gen.OUTPUT_BY_KEY or not isinstance(row, dict):
            return False
        if row.get("path") != gen.OUTPUT_BY_KEY[key].relative_path.as_posix():
            return False
        expected.add(row["path"])
    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink() or (path.exists() and not path.is_file() and not path.is_dir()):
            return False
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    return actual == expected


def replace_bundle(*, scheme: str, ink: float, root: Path, keys: tuple[str, ...]) -> list[str]:
    """Atomically replace a fresh or proven-owned bundle at *root*."""
    if root.exists() and not owned_bundle(root):
        raise ValueError(
            f"refusing to replace {root}: it is not an intact Colorstack output bundle"
        )
    parent = root.parent
    gen.mkdir_no_symlink(parent)
    staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.colorstack-", dir=parent))
    backup = parent / f".{root.name}.colorstack-previous"
    try:
        if backup.exists():
            raise ValueError(f"refusing to overwrite unresolved Colorstack backup: {backup}")
        th = T.build(P.BY_KEY[scheme], ink_contrast=ink)
        if problems := th.check():
            raise ValueError("theme fails its own invariants: " + "; ".join(problems))
        _, log = gen.emit(th, scheme, ink, staging, keys, dry=False)
        if root.exists():
            os.replace(root, backup)
        try:
            os.replace(staging, root)
        except Exception:
            if backup.exists():
                os.replace(backup, root)
            raise
        if backup.exists():
            shutil.rmtree(backup)
        return log
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="replace an explicit Colorstack output bundle; never touch application config"
    )
    parser.add_argument("scheme", choices=sorted(P.BY_KEY))
    parser.add_argument("--output-root", required=True, help="caller-owned Colorstack output bundle")
    parser.add_argument("--key", action="append", help="output key (repeat or comma-separate); default is every payload")
    parser.add_argument("--ink", type=float, default=10.0, help="body text contrast target")
    args = parser.parse_args()
    try:
        root = gen.output_root(args.output_root)
        keys = gen.parse_keys(args.key)
        log = replace_bundle(scheme=args.scheme, ink=args.ink, root=root, keys=keys)
    except ValueError as error:
        parser.error(str(error))
    print(f"\n{P.BY_KEY[args.scheme].name}  output bundle {root}  ink {args.ink:g}:1\n")
    print("\n".join(log))
    print("\nCopy or merge the payloads into your own dotfiles convention. No application configuration was changed.\n")


if __name__ == "__main__":
    main()
