"""Collection levels derived from an item's max_level image must have the exact
Deep Zoom level size, so viewers sampling that size don't read the tile
background."""

import os

import PIL.Image

import deepzoom

MAX_LEVEL = 8
TILE_SIZE = 512
RED = (255, 0, 0)


def test_derived_levels_fill_exact_deep_zoom_size(tmp_path):
    # 300 × 200: Deep Zoom level 5 is ceil(18.75) × ceil(12.5) = 19 × 13.
    # Aspect-preserving thumbnail() made it 19 × 12, leaving a background row
    # that viewers sampling 19 × 13 rendered as a dark edge.
    dzi = str(tmp_path / "red.dzi")
    creator = deepzoom.ImageCreator(tile_size=254, tile_overlap=1, tile_format="png")
    creator.create(PIL.Image.new("RGB", (300, 200), RED), dzi)

    # Keep only the item's max_level tile, as for remote images whose lower
    # levels are derived from it
    files_path = str(tmp_path / "red_files")
    for level in range(MAX_LEVEL):
        level_path = os.path.join(files_path, str(level))
        for name in os.listdir(level_path):
            os.remove(os.path.join(level_path, name))

    dzc = str(tmp_path / "collection.dzc")
    collection = deepzoom.DeepZoomCollection(
        dzc, max_level=MAX_LEVEL, tile_size=TILE_SIZE, tile_format="png", image_quality=1.0
    )
    collection.append(dzi)
    collection.save()

    tile = PIL.Image.open(str(tmp_path / "collection_files" / "5" / "0_0.png"))
    last_column, last_row = 18, 12
    r, g, b = tile.getpixel((last_column, last_row))[:3]
    assert r > 200 and g < 50 and b < 50, f"Expected red in the last row, got ({r},{g},{b})"
    r, g, b = tile.getpixel((last_column + 1, last_row + 1))[:3]
    assert r < 10 and g < 10 and b < 10, f"Expected background past the item, got ({r},{g},{b})"
