"""Tests for collection tile placement math."""

import math

import pytest


TILE_SIZE = 512
MAX_LEVEL = 8


class TestGetTilePosition:
    """get_tile_position: which output tile file an image lands in."""

    def test_first_image_at_max_level(self, collection):
        assert collection.get_tile_position(0, 8, TILE_SIZE) == (0, 0)

    def test_second_image_at_max_level(self, collection):
        # z=1 → (1, 0), level_size=256, x=1*256=256 < 512 → tile (0, 0)
        assert collection.get_tile_position(1, 8, TILE_SIZE) == (0, 0)

    def test_third_image_at_max_level(self, collection):
        # z=2 → (0, 1), level_size=256, y=1*256=256 < 512 → tile (0, 0)
        assert collection.get_tile_position(2, 8, TILE_SIZE) == (0, 0)

    def test_fourth_image_at_max_level(self, collection):
        # z=3 → (1, 1), still fits in tile (0, 0) at level 8
        assert collection.get_tile_position(3, 8, TILE_SIZE) == (0, 0)

    def test_fifth_image_crosses_tile_boundary(self, collection):
        # z=4 → (2, 0), level_size=256, x=2*256=512 → tile (1, 0)
        assert collection.get_tile_position(4, 8, TILE_SIZE) == (1, 0)

    def test_fifth_image_fits_at_lower_level(self, collection):
        # z=4 → (2, 0), level_size=128 at level 7, x=2*128=256 < 512 → tile (0, 0)
        assert collection.get_tile_position(4, 7, TILE_SIZE) == (0, 0)

    def test_at_level_0_everything_in_one_tile(self, collection):
        for z in range(64):
            assert collection.get_tile_position(z, 0, TILE_SIZE) == (0, 0), (
                f"z={z} should be in tile (0,0) at level 0"
            )

    def test_tile_positions_are_non_negative(self, collection):
        for z in range(64):
            for level in range(MAX_LEVEL + 1):
                col, row = collection.get_tile_position(z, level, TILE_SIZE)
                assert col >= 0 and row >= 0, (
                    f"z={z} level={level}: negative tile position ({col}, {row})"
                )


class TestImagesPerTile:
    """Verify the images_per_tile formula at each level."""

    @pytest.mark.parametrize(
        "level, expected",
        [
            (0, 512),
            (1, 256),
            (2, 128),
            (3, 64),
            (4, 32),
            (5, 16),
            (6, 8),
            (7, 4),
            (8, 2),
        ],
    )
    def test_images_per_tile(self, level, expected):
        level_size = 2 ** level
        images_per_tile = int(math.floor(TILE_SIZE / level_size))
        assert images_per_tile == expected


class TestPasteCoordinates:
    """Verify the (x, y) pixel position within a collection tile."""

    def _paste_position(self, collection, z_order, level, tile_size=TILE_SIZE):
        level_size = 2 ** level
        images_per_tile = int(math.floor(tile_size / level_size))
        column, row = collection.get_position(z_order)
        x = (column % images_per_tile) * level_size
        y = (row % images_per_tile) * level_size
        return x, y

    def test_first_image_always_at_origin(self, collection):
        for level in range(MAX_LEVEL + 1):
            assert self._paste_position(collection, 0, level) == (0, 0), (
                f"z=0 should be at (0,0) at level {level}"
            )

    def test_second_image_at_max_level(self, collection):
        # z=1 → (1, 0), level_size=256 → paste at (256, 0)
        assert self._paste_position(collection, 1, 8) == (256, 0)

    def test_third_image_at_max_level(self, collection):
        # z=2 → (0, 1), level_size=256 → paste at (0, 256)
        assert self._paste_position(collection, 2, 8) == (0, 256)

    def test_diagonal_image_at_max_level(self, collection):
        # z=3 → (1, 1), level_size=256 → paste at (256, 256)
        assert self._paste_position(collection, 3, 8) == (256, 256)

    def test_image_at_level_0(self, collection):
        # z=1 → (1, 0), level_size=1 → paste at (1, 0)
        assert self._paste_position(collection, 1, 0) == (1, 0)

    def test_image_at_level_7(self, collection):
        # z=1 → (1, 0), level_size=128 → paste at (128, 0)
        assert self._paste_position(collection, 1, 7) == (128, 0)

    def test_paste_never_exceeds_tile_size(self, collection):
        for z in range(64):
            for level in range(MAX_LEVEL + 1):
                x, y = self._paste_position(collection, z, level)
                assert x < TILE_SIZE, f"z={z} level={level}: x={x} >= {TILE_SIZE}"
                assert y < TILE_SIZE, f"z={z} level={level}: y={y} >= {TILE_SIZE}"

    def test_no_overlapping_positions_within_tile(self, collection):
        """Two images in the same tile must not share a paste position."""
        for level in range(MAX_LEVEL + 1):
            tiles = {}
            for z in range(64):
                tile = collection.get_tile_position(z, level, TILE_SIZE)
                paste = self._paste_position(collection, z, level)
                key = (tile, paste)
                assert key not in tiles, (
                    f"z={z} and z={tiles[key]} both paste at {paste} "
                    f"in tile {tile} at level {level}"
                )
                tiles[key] = z
