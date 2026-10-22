# Copy to Formula/fastcat-tui.rb in github.com/ParsaBordbar/homebrew-tap.
# packaging/update.sh fills in url and sha256 for each release.
class FastcatTui < Formula
  include Language::Python::Virtualenv

  desc "Browse, customise and create fastfetch themes from a terminal UI"
  homepage "https://github.com/ParsaBordbar/fastcat-tui"
  url "https://github.com/ParsaBordbar/fastcat-tui/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license all_of: ["Apache-2.0", "MIT"]

  depends_on "python-setuptools" => :build
  depends_on "fastfetch"
  depends_on "python@3.13"

  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      Icons need a Nerd Font in your terminal, for example:
        brew install --cask font-symbols-only-nerd-font
      Image -> logo needs Pillow:
        brew install pillow
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/fastcat-tui --version")
    ENV["FASTCAT_TUI_HOME"] = testpath
    assert_match "Originals/Venom", shell_output("#{bin}/fastcat-tui list")
  end
end
