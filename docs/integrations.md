# Integration notes

Colorstack deliberately stops at generated payloads. Each application below has
its own configuration authority; use its native include/import mechanism or
copy the generated values through your dotfile workflow.

## Ghostty and tmux

Keep your normal config under your own management. Point Ghostty at the
`ghostty-theme` payload with `config-file`, and source the `tmux-include`
payload from tmux. Reload behavior belongs to those applications, not
Colorstack.

## Bat and shell

Install `bat-theme` where your Bat installation discovers `.tmTheme` files, set
`BAT_THEME=colorstack`, and rebuild Bat's cache. Source `shell-env` from your
shell startup if you want its FZF, Bat, Eza, and pager values.

## Starship and Herdr

Both share a configuration file with unrelated settings. Treat the generated
payloads as fragments: create a named region or manually merge them according
to the application's syntax. Do not overwrite a whole configuration merely to
change colors.

## Pi

Copy `pi-theme` to `~/.pi/agent/themes/colorstack.json` and select `colorstack`
with Pi's settings UI or in your own settings-management workflow. Pi requires
a complete custom-theme token set and hot-reloads the active custom file. Never
store credentials in a theme file, and Colorstack never edits `settings.json`.

## JupyterLab and CSS

`jupyter-css` is the style payload. `jupyter-cfg` and `jupyter-theme` are
configuration fragments, not files that Colorstack owns in an existing Jupyter
installation. Merge them with your existing configuration, then restart or
refresh JupyterLab according to its documentation.
