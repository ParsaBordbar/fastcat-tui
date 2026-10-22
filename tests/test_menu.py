import pytest

from fastcat_tui import menu


@pytest.fixture
def keys(monkeypatch):
    """Feed select() a list of keys instead of a terminal."""
    def feed(*pressed):
        it = iter(pressed)
        monkeypatch.setattr(menu, "read_key", lambda fd: next(it))
    monkeypatch.setattr(menu, "raw_mode", lambda: _null())
    monkeypatch.setattr(menu, "_draw", lambda *a: None)
    return feed


class _null:
    def __enter__(self):
        return 0

    def __exit__(self, *a):
        return False


OPTS = [("One", ""), ("Two", "")]


def test_back_entry_is_last_and_returns_none(keys):
    keys("up", "enter")
    assert menu.select("t", OPTS) is None
    keys("down", "enter")
    assert menu.select("t", OPTS) == 1


def test_back_entry_can_be_left_out(keys):
    keys("up", "enter")
    assert menu.select("t", OPTS, back=False) == 1


def test_back_entry_shows_the_previous_preview(keys):
    seen = []
    keys("up", "esc")
    menu.select("t", OPTS, preview=lambda i: seen.append(i) or [])
    assert seen == [0, 1]
