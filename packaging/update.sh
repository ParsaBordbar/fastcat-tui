#!/bin/sh
# After a release is tagged and pushed: point the Homebrew formula and the PKGBUILD at it.
#   packaging/update.sh 0.2.0
set -eu

version=${1:?usage: packaging/update.sh VERSION}
here=$(cd "$(dirname "$0")" && pwd)
url="https://github.com/ParsaBordbar/fastcat-tui/archive/refs/tags/v$version.tar.gz"

if command -v sha256sum >/dev/null; then
  sha=$(curl -fsSL "$url" | sha256sum | cut -d' ' -f1)
else
  sha=$(curl -fsSL "$url" | shasum -a 256 | cut -d' ' -f1)
fi

formula="$here/homebrew/fastcat-tui.rb"
pkgbuild="$here/aur/PKGBUILD"
sed -i.bak -e "s|^  url \".*\"|  url \"$url\"|" -e "s|^  sha256 \".*\"|  sha256 \"$sha\"|" "$formula"
sed -i.bak -e "s|^pkgver=.*|pkgver=$version|" -e "s|^pkgrel=.*|pkgrel=1|" \
  -e "s|^sha256sums=.*|sha256sums=('$sha')|" "$pkgbuild"
srcinfo="$here/aur/.SRCINFO"
sed -i.bak -e "s|^	pkgver = .*|	pkgver = $version|" -e "s|^	pkgrel = .*|	pkgrel = 1|" \
  -e "s|^	source = .*|	source = fastcat-tui-$version.tar.gz::$url|" \
  -e "s|^	sha256sums = .*|	sha256sums = $sha|" "$srcinfo"
rm -f "$formula.bak" "$pkgbuild.bak" "$srcinfo.bak"

echo "v$version  sha256 $sha"
echo "updated $formula"
echo "updated $pkgbuild and $srcinfo"
