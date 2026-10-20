"""Read fastfetch's JSONC (comments, trailing commas) and write plain JSON back."""
import json
import re
from pathlib import Path

_TOKEN_RE = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.S)


def _strip_comments(text: str) -> str:
    return _TOKEN_RE.sub(lambda m: m.group(0) if m.group(0).startswith('"') else "", text)


def _strip_trailing_commas(text: str) -> str:
    out, i = [], 0
    for m in re.finditer(r'"(?:\\.|[^"\\])*"|,(?=\s*[}\]])', text):
        out.append(text[i:m.start()])
        if m.group(0) != ",":
            out.append(m.group(0))
        i = m.end()
    out.append(text[i:])
    return "".join(out)


def loads(text: str):
    return json.loads(_strip_trailing_commas(_strip_comments(text)))


def load(path) -> dict:
    return loads(Path(path).read_text(encoding="utf-8"))


HEADER = "// edited with fastcat-tui · https://github.com/ParsaBordbar/fastcat-tui\n"


def dumps(obj) -> str:
    return HEADER + json.dumps(obj, indent=4, ensure_ascii=False) + "\n"


def save(path, obj) -> None:
    Path(path).write_text(dumps(obj), encoding="utf-8")
