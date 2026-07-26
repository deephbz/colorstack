# Colorstack

Colorstack derives a coherent set of application theme payloads from one
palette. It is a generator, not a dotfile manager: it never discovers, reads,
edits, links, reloads, or selects an application's configuration.

## Quick start

Requires Python 3.11+; the core has no runtime dependencies.

```sh
git clone https://github.com/deephbz/colorstack
cd colorstack

# Inspect palette candidates.
python3 gen.py --compare

# Render one fresh, caller-chosen bundle.
python3 gen.py modus --output-root "$HOME/Downloads/colorstack-output"

# Replace only that proven Colorstack bundle on later palette changes.
./switch.sh kanagawa --output-root "$HOME/Downloads/colorstack-output"
```

The output directory contains `.colorstack-manifest.json` and named payloads
under `outputs/`. Copy or merge them through your own dotfile convention. The
switcher refuses a nonempty directory unless it is exactly a bundle created by
Colorstack; it never modifies application config files or HOME state outside
that explicit bundle.

Run the test suite with:

```sh
uv run --group dev pytest -q
```

## Payloads

| Key | What to copy or merge yourself |
| --- | --- |
| `ghostty-theme` | A Ghostty theme file. Add your own `config-file` include. |
| `tmux-include` | A tmux include file. Source it from your own tmux config. |
| `bat-theme` | A `.tmTheme`; install it in Bat's theme directory and rebuild Bat's cache. |
| `shell-env` | Environment exports for shell/FZF/Bat. Source it from your shell startup file. |
| `css` | CSS custom properties plus an optional JupyterLab block. |
| `starship-select`, `starship-palette` | Two fragments to merge into your Starship TOML. |
| `herdr` | A `[theme]`/`[theme.custom]` TOML fragment to merge into your Herdr config. |
| `pi-theme` | A complete Pi theme JSON. Copy it to `~/.pi/agent/themes/colorstack.json`, then choose `colorstack` once in Pi's settings. Pi hot-reloads an active custom theme; Colorstack never edits `settings.json`. |
| `jupyter-css`, `jupyter-cfg`, `jupyter-theme` | CSS, Python configuration, and theme-settings fragments for manual JupyterLab integration. |

A generated payload is intentionally not a claim that the target application
has accepted it. Its own documentation and runtime checks remain the oracle.

## Model

A `Palette` contains authored intent hues, surface tiers, and contrast floors.
`Theme` resolves those inputs into ANSI slots and UI roles. The emitters turn
that derived theme into application-specific payloads. See
[the ontology](docs/ontology.md) and [integration notes](docs/integrations.md).

## Boundaries

- Colorstack owns palette-to-payload derivation and output manifests.
- You own your selected palette, destination paths, dotfiles, application
  lifecycle, and any live verification.
- Generated bundle contents are disposable. Keep your palette definition and
  the exact Colorstack revision as the reproducible source.

Licensed under [MIT](LICENSE).
