"""Collection tile sizes must hold a whole number of items at every level, or
items overlap (non-power-of-two sizes) or placement divides by zero (items
larger than a tile)."""

import pytest

import deepzoom


@pytest.mark.parametrize("tile_size", [254, 300, 510])
def test_rejects_non_power_of_two_tile_size(tile_size):
    with pytest.raises(ValueError, match="power of two"):
        deepzoom.DeepZoomCollection("unused.dzc", tile_size=tile_size)


def test_rejects_max_level_items_larger_than_tile():
    # Level 9 items are 512 × 512 and don’t fit into a 256 × 256 tile
    with pytest.raises(ValueError, match="max_level"):
        deepzoom.DeepZoomCollection("unused.dzc", tile_size=256, max_level=9)


@pytest.mark.parametrize("tile_size, max_level", [(256, 7), (256, 8), (512, 8), (1, 0)])
def test_accepts_valid_tile_size_and_max_level(tile_size, max_level):
    deepzoom.DeepZoomCollection("unused.dzc", tile_size=tile_size, max_level=max_level)

