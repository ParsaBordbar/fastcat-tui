# fastcat-tui

Browse, customise and create [fastfetch](https://github.com/fastfetch-cli/fastfetch) themes from a terminal UI.

- **Browse** bundled themes, the [FastCat](https://github.com/m3tozz/FastCat) pack, your own folders and the
  [community gallery](https://parsabordbar.github.io/fastcat-gallery/), with a live preview beside the list.
- **Apply** any of them in one keypress. Your current config is backed up first, and every backup can be restored.
- **Customise** your config: logo and key colours (match the logo, one colour, gradients), text colour,
  which lines show and in what order, Nerd Font icons, key width, separator, centring beside the logo.
- **Image → logo**: turn a PNG or JPEG into a coloured braille logo and save it as a theme.
- **Share** a theme to the gallery through a pre-filled form. No git needed.

Works on macOS and Linux. Needs Python 3.10+ and fastfetch. Icons need a [Nerd Font](https://www.nerdfonts.com/)
in your terminal; image → logo needs Pillow.

## Install

```sh
# Homebrew (macOS, Linux)
brew install parsabordbar/tap/fastcat-tui

# Arch Linux (AUR)
yay -S fastcat-tui

# Anywhere with Python
pipx install 'fastcat-tui[image]'      # or: uv tool install 'fastcat-tui[image]'
```

Drop `[image]` if you don't need image → logo. From a checkout, `python3 run.py` runs it without installing.

## Use

Run `fastcat-tui` with no arguments for the interactive app. Arrow keys or `j`/`k` move, enter selects,
esc (or the **← Back** entry at the bottom of each menu) goes back, `q` quits.

Every action is also a command:

```sh
fastcat-tui list                              # every theme it can see
fastcat-tui preview Venom                     # run fastfetch with a theme, change nothing
fastcat-tui apply Originals/Venom             # install a theme (backs up your config first)
fastcat-tui gallery                           # list community themes
fastcat-tui gallery cat neon                  # only those matching every word, like the site's search
fastcat-tui get neon-cat --apply              # install one by its code (and apply it)
fastcat-tui share --name "Neon Cat"           # submit your config to the gallery
fastcat-tui logo ~/Pictures/cat.png --width 36 --name Kitty --apply
fastcat-tui fix-icons                         # one-cell Nerd Font icons in your config
fastcat-tui restore                           # put the newest backup back (--list to see them)
fastcat-tui paths                             # where everything lives
```

## Where files go

| What | Where |
|---|---|
| Your fastfetch config | `$XDG_CONFIG_HOME/fastfetch` (`~/.config/fastfetch`) |
| Your themes, gallery installs, backups, the FastCat pack | `$XDG_DATA_HOME/fastcat-tui` (`~/.local/share/fastcat-tui`) |
| Preferences | `$XDG_CONFIG_HOME/fastcat-tui/settings.json` |

Set `FASTCAT_TUI_HOME` to keep fastcat-tui's own files in one folder, and `FASTCAT_GALLERY_URL` to use a
gallery fork or a local copy.

## Gallery safety

Gallery themes are checked before they are saved: every file must match the SHA-256 in the gallery index,
only `.jsonc`, `.json`, `.txt` and `.png` files are accepted, text files may not contain terminal control
characters, the logo must be one of the theme's own files, and themes using the `command` module (which runs
programs) are refused.

## Development

```sh
uv run pytest
```

See [packaging/README.md](packaging/README.md) for how releases reach PyPI, Homebrew and the AUR.

## License

Apache-2.0, see [LICENSE](LICENSE) and [NOTICE](NOTICE). The bundled theme configs build on FastCat by
Metin Zühre, used under the MIT License ([fastcat_tui/themes/LICENSE-FastCat](fastcat_tui/themes/LICENSE-FastCat)).
