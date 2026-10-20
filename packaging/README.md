# Releasing

A release goes out in three places: PyPI (`pipx` / `uv tool`), the Homebrew tap and the AUR.
PyPI is automatic; the other two take one script and two pushes.

## One-time setup

1. **GitHub**: push this repo to `github.com/ParsaBordbar/fastcat-tui`. Under *Settings → Environments*,
   create an environment called `pypi`.
2. **PyPI**: on pypi.org, *Your projects → Publishing → Add a new pending publisher* with
   project `fastcat-tui`, owner `ParsaBordbar`, repository `fastcat-tui`, workflow `release.yml`,
   environment `pypi`. No API token is needed.
3. **Homebrew**: create the repo `github.com/ParsaBordbar/homebrew-tap` with a `Formula/` folder.
   Users then install with `brew install parsabordbar/tap/fastcat-tui`.
4. **AUR**: make an account on aur.archlinux.org, add your SSH key, then
   `git clone ssh://aur@aur.archlinux.org/fastcat-tui.git` (an empty clone reserves the name on first push).

## Each release

```sh
# 1. bump __version__ in fastcat_tui/__init__.py, commit, then tag and push
git tag v0.2.0 && git push origin main v0.2.0
```

`.github/workflows/release.yml` runs the tests, checks the tag matches `__version__`, publishes to PyPI and
creates the GitHub release. When it has finished:

```sh
# 2. point the formula and PKGBUILD at the new tag (downloads it and fills in sha256)
packaging/update.sh 0.2.0
git commit -am "packaging: 0.2.0" && git push

# 3. Homebrew tap
cp packaging/homebrew/fastcat-tui.rb ../homebrew-tap/Formula/
cd ../homebrew-tap && git commit -am "fastcat-tui 0.2.0" && git push
brew update && brew upgrade fastcat-tui || brew install parsabordbar/tap/fastcat-tui
brew test fastcat-tui && brew audit --strict --online fastcat-tui

# 4. AUR
cp packaging/aur/PKGBUILD packaging/aur/.SRCINFO ../aur-fastcat-tui/
cd ../aur-fastcat-tui && git commit -am "0.2.0" && git push
```

On an Arch machine, `makepkg -si` in the AUR folder builds and installs it, and runs the tests. If you edit
the PKGBUILD beyond what `update.sh` changes, regenerate the metadata there with
`makepkg --printsrcinfo > .SRCINFO`.

## Later

- **homebrew-core**: once the project is well known (roughly 75+ stars), submit the formula there so
  `brew install fastcat-tui` works without the tap. It will need `brew audit --new --strict` to pass.
- **nixpkgs**: a `python3Packages.buildPythonApplication` with `pyproject = true` and `fastfetch` in
  `propagatedBuildInputs`.
- **Fedora (COPR)** and **openSUSE (OBS)**: self-serve RPM builds. OBS can also build `.deb` packages for
  Debian and Ubuntu.
- **Ubuntu PPA** (Launchpad): the quickest route to `apt install`. Official Debian needs a sponsor.
- **Snap and Flatpak** are not a good fit: their sandboxes keep the app from writing `~/.config/fastfetch`
  and from running the installed `fastfetch` and `git`.
