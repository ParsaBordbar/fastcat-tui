# Releasing

A release goes out in four places: PyPI (`pipx` / `uv tool`), the GitHub release, the Homebrew tap and
the AUR. Pushing a version tag does all of it.

## One-time setup

1. **PyPI**: on pypi.org, *Your projects → Publishing → Add a new pending publisher* with
   project `fastcat-tui`, owner `ParsaBordbar`, repository `fastcat-tui`, workflow `release.yml`,
   environment `pypi`. Then on GitHub, *Settings → Environments → New environment* `pypi`.
   No API token is needed.
2. **Homebrew tap**: create the repo `github.com/ParsaBordbar/homebrew-tap` (public). Users then install
   with `brew install parsabordbar/tap/fastcat-tui`. Make a fine-grained token at *GitHub → Settings →
   Developer settings → Fine-grained tokens*, repository access *only homebrew-tap*, permission
   *Contents: read and write*, and save it in this repo as the Actions secret `HOMEBREW_TAP_TOKEN`.
3. **AUR**: make an account on aur.archlinux.org. Create a key just for releases,
   `ssh-keygen -t ed25519 -N "" -C "fastcat-tui release" -f aur_release`, add `aur_release.pub` to your
   AUR account (*My Account → SSH Public Key*, one key per line next to your own), and save the private
   key `aur_release` in this repo as the Actions secret `AUR_SSH_KEY`. The first release creates the
   package.

Until a secret is set, its job is skipped with a notice, so you can set these up one at a time.

## Each release

```sh
# bump __version__ in fastcat_tui/__init__.py, commit, then tag and push
git tag v0.2.0 && git push origin main v0.2.0
```

`.github/workflows/release.yml` runs the tests and checks the tag matches `__version__`, then:

- publishes to PyPI and creates the GitHub release;
- **homebrew**: fills the new url and sha256 into the formula with `packaging/update.sh`, builds it from
  source on macOS, runs `brew test` and `brew audit --strict`, then pushes it to the tap;
- **aur**: does the same for the PKGBUILD in an Arch container, regenerates `.SRCINFO`, builds the package
  with `makepkg` (which runs the tests), then pushes it to the AUR.

A job that fails pushes nothing, so the tap or the AUR never gets a broken package. Re-run the failed job
from the Actions tab once it's fixed.

The files in `packaging/` are the templates those jobs start from; the version and sha256 in them are
only placeholders. To do a channel by hand instead, run `packaging/update.sh 0.2.0` and copy the formula
to `homebrew-tap/Formula/`, or the PKGBUILD and `.SRCINFO` (`makepkg --printsrcinfo > .SRCINFO`) to a
clone of `ssh://aur@aur.archlinux.org/fastcat-tui.git`.

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
