"""`safe_open` must read local paths that don’t survive a naive `file://` URL."""

import deepzoom

CONTENT = b"deepzoom"


def test_reads_path_with_url_special_characters(tmp_path):
    # `#` starts a URL fragment and `%` an escape sequence in `file://` URLs
    path = tmp_path / "100% #1 image.dzi"
    path.write_bytes(CONTENT)
    assert deepzoom.safe_open(str(path)).read() == CONTENT


def test_reads_relative_path(tmp_path, monkeypatch):
    (tmp_path / "image.dzi").write_bytes(CONTENT)
    monkeypatch.chdir(tmp_path)
    assert deepzoom.safe_open("image.dzi").read() == CONTENT


def test_reads_path_that_parses_as_url_scheme(tmp_path, monkeypatch):
    # Like a Windows drive letter (`C:\…`), `c:image.dzi` parses as scheme `c`
    (tmp_path / "c:image.dzi").write_bytes(CONTENT)
    monkeypatch.chdir(tmp_path)
    assert deepzoom.safe_open("c:image.dzi").read() == CONTENT
