import sys

import PIL.Image

import deepzoom


def test_main_converts_image_above_decompression_bomb_limit(monkeypatch, tmp_path):
    # Lower the limit so a small image trips Pillow’s `DecompressionBombError`
    # (raised above twice the limit). Patching the attribute first also ensures
    # monkeypatch restores the original after `main()` overrides it.
    monkeypatch.setattr(PIL.Image, "MAX_IMAGE_PIXELS", 1000)
    image_path = tmp_path / "large.png"
    PIL.Image.new("RGB", (100, 100)).save(image_path)
    destination = tmp_path / "out.dzi"
    monkeypatch.setattr(
        sys, "argv", ["deepzoom", "-d", str(destination), str(image_path)]
    )

    deepzoom.main()

    assert destination.exists()
