"""JPEG can’t store every image mode (e.g. alpha or palette images), so
ImageCreator must convert the source before writing JPEG tiles."""

import os

import PIL.Image
import pytest

import deepzoom

RED = (255, 0, 0)
WIDTH, HEIGHT = 300, 200


def _palette_image():
    image = PIL.Image.new("P", (WIDTH, HEIGHT), 0)
    image.putpalette(list(RED) + [0, 0, 0] * 255)
    return image


def _create_jpeg_tiles(image, directory):
    """Create JPEG tiles for image and return the deepest level’s directory."""
    destination = str(directory / "image.dzi")
    creator = deepzoom.ImageCreator(tile_format="jpg")
    creator.create(image, destination)
    max_level = creator.descriptor.num_levels - 1
    return os.path.join(str(directory), "image_files", str(max_level))


def _assert_close(actual, expected, tolerance=8):
    assert all(
        abs(actual_channel - expected_channel) <= tolerance
        for actual_channel, expected_channel in zip(actual, expected)
    ), actual


@pytest.mark.parametrize(
    "image, expected_color",
    [
        (PIL.Image.new("RGBA", (WIDTH, HEIGHT), RED + (255,)), RED),
        (PIL.Image.new("LA", (WIDTH, HEIGHT), (128, 255)), (128, 128, 128)),
        (_palette_image(), RED),
        (PIL.Image.new("I;16", (WIDTH, HEIGHT), 200), (200, 200, 200)),
    ],
    ids=["RGBA", "LA", "P", "I;16"],
)
def test_writes_jpeg_tiles_for_modes_jpeg_cannot_store(tmp_path, image, expected_color):
    level_dir = _create_jpeg_tiles(image, tmp_path)
    tile_names = sorted(os.listdir(level_dir))
    assert tile_names == ["0_0.jpg", "1_0.jpg"]
    for tile_name in tile_names:
        with PIL.Image.open(os.path.join(level_dir, tile_name)) as tile:
            assert tile.format == "JPEG"
            _assert_close(tile.convert("RGB").getpixel((20, 20)), expected_color)


def test_transparent_pixels_become_black(tmp_path):
    # Fully transparent green: the hidden RGB values must not show through
    image = PIL.Image.new("RGBA", (WIDTH, HEIGHT), (0, 255, 0, 0))
    level_dir = _create_jpeg_tiles(image, tmp_path)
    with PIL.Image.open(os.path.join(level_dir, "0_0.jpg")) as tile:
        _assert_close(tile.convert("RGB").getpixel((20, 20)), (0, 0, 0))


def test_png_tiles_keep_alpha(tmp_path):
    image = PIL.Image.new("RGBA", (WIDTH, HEIGHT), (0, 255, 0, 0))
    destination = str(tmp_path / "image.dzi")
    creator = deepzoom.ImageCreator(tile_format="png")
    creator.create(image, destination)
    max_level = creator.descriptor.num_levels - 1
    tile_path = os.path.join(str(tmp_path), "image_files", str(max_level), "0_0.png")
    with PIL.Image.open(tile_path) as tile:
        assert tile.mode == "RGBA"
        assert tile.getpixel((20, 20)) == (0, 255, 0, 0)
