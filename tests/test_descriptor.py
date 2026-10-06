"""Tests for DeepZoomImageDescriptor pure math methods."""

import pytest

import deepzoom


def descriptor(width, height, tile_size=510, tile_overlap=1):
    return deepzoom.DeepZoomImageDescriptor(
        width=width,
        height=height,
        tile_size=tile_size,
        tile_overlap=tile_overlap,
    )


class TestNumLevels:
    def test_1x1(self):
        assert descriptor(1, 1).num_levels == 1

    def test_2x2(self):
        assert descriptor(2, 2).num_levels == 2

    def test_256x256(self):
        assert descriptor(256, 256).num_levels == 9

    def test_512x512(self):
        assert descriptor(512, 512).num_levels == 10

    def test_640x447(self):
        assert descriptor(640, 447).num_levels == 11

    def test_1024x768(self):
        assert descriptor(1024, 768).num_levels == 11

    def test_non_square_width_dominant(self):
        assert descriptor(1000, 1).num_levels == 11

    def test_non_square_height_dominant(self):
        assert descriptor(1, 1000).num_levels == 11

    def test_power_of_two_boundary(self):
        assert descriptor(128, 128).num_levels == 8

    def test_just_above_power_of_two(self):
        assert descriptor(129, 129).num_levels == 9


class TestGetScale:
    def test_level_0_is_smallest(self):
        d = descriptor(640, 447)
        scale = d.get_scale(0)
        assert scale == pytest.approx(1.0 / 1024)

    def test_max_level_is_1(self):
        d = descriptor(640, 447)
        assert d.get_scale(d.num_levels - 1) == 1.0

    def test_each_level_doubles(self):
        d = descriptor(640, 447)
        for level in range(1, d.num_levels):
            assert d.get_scale(level) == pytest.approx(d.get_scale(level - 1) * 2)

    def test_invalid_level_negative(self):
        d = descriptor(640, 447)
        with pytest.raises(AssertionError):
            d.get_scale(-1)

    def test_invalid_level_too_high(self):
        d = descriptor(640, 447)
        with pytest.raises(AssertionError):
            d.get_scale(d.num_levels)


class TestGetDimensions:
    def test_level_0_is_1x1(self):
        d = descriptor(640, 447)
        assert d.get_dimensions(0) == (1, 1)

    def test_max_level_is_original(self):
        d = descriptor(640, 447)
        assert d.get_dimensions(d.num_levels - 1) == (640, 447)

    def test_known_mid_level(self):
        d = descriptor(640, 447)
        w, h = d.get_dimensions(8)
        assert w == 160
        assert h == 112

    def test_dimensions_halve_down(self):
        d = descriptor(1024, 768)
        for level in range(d.num_levels - 1, 0, -1):
            w_high, h_high = d.get_dimensions(level)
            w_low, h_low = d.get_dimensions(level - 1)
            assert w_low <= w_high
            assert h_low <= h_high

    def test_dimensions_always_at_least_1(self):
        d = descriptor(640, 447)
        for level in range(d.num_levels):
            w, h = d.get_dimensions(level)
            assert w >= 1
            assert h >= 1

    def test_invalid_level(self):
        d = descriptor(640, 447)
        with pytest.raises(AssertionError):
            d.get_dimensions(d.num_levels)


class TestGetNumTiles:
    def test_single_tile_at_level_0(self):
        d = descriptor(640, 447, tile_size=510)
        assert d.get_num_tiles(0) == (1, 1)

    def test_multiple_tiles_at_max_level(self):
        d = descriptor(640, 447, tile_size=510)
        cols, rows = d.get_num_tiles(d.num_levels - 1)
        assert cols == 2
        assert rows == 1

    def test_large_image_many_tiles(self):
        d = descriptor(2048, 2048, tile_size=510)
        cols, rows = d.get_num_tiles(d.num_levels - 1)
        assert cols >= 4
        assert rows >= 4

    def test_exact_tile_size_boundary(self):
        d = descriptor(510, 510, tile_size=510)
        assert d.get_num_tiles(d.num_levels - 1) == (1, 1)

    def test_one_pixel_over_tile_size(self):
        d = descriptor(511, 511, tile_size=510)
        cols, rows = d.get_num_tiles(d.num_levels - 1)
        assert cols == 2
        assert rows == 2


class TestGetTileBounds:
    def test_origin_tile(self):
        d = descriptor(640, 447, tile_size=510, tile_overlap=1)
        x1, y1, x2, y2 = d.get_tile_bounds(d.num_levels - 1, 0, 0)
        assert x1 == 0
        assert y1 == 0
        assert x2 == 511
        assert y2 == 447

    def test_second_column_tile(self):
        d = descriptor(640, 447, tile_size=510, tile_overlap=1)
        x1, y1, x2, y2 = d.get_tile_bounds(d.num_levels - 1, 1, 0)
        assert x1 == 509
        assert y1 == 0
        assert x2 == 640
        assert y2 == 447

    def test_overlap_0(self):
        d = descriptor(640, 447, tile_size=510, tile_overlap=0)
        x1, y1, x2, y2 = d.get_tile_bounds(d.num_levels - 1, 0, 0)
        assert x1 == 0
        assert y1 == 0
        assert x2 == 510
        assert y2 == 447

    def test_overlap_2(self):
        d = descriptor(640, 447, tile_size=128, tile_overlap=2)
        x1, y1, x2, y2 = d.get_tile_bounds(d.num_levels - 1, 0, 0)
        assert x1 == 0
        assert y1 == 0
        assert x2 == 130
        assert y2 == 130

    def test_non_origin_includes_both_overlaps(self):
        d = descriptor(640, 447, tile_size=128, tile_overlap=2)
        x1, y1, x2, y2 = d.get_tile_bounds(d.num_levels - 1, 1, 1)
        assert x1 == 126
        assert y1 == 126

    def test_bounds_dont_exceed_image(self):
        d = descriptor(640, 447, tile_size=510, tile_overlap=1)
        for level in range(d.num_levels):
            cols, rows = d.get_num_tiles(level)
            w, h = d.get_dimensions(level)
            for col in range(cols):
                for row in range(rows):
                    x1, y1, x2, y2 = d.get_tile_bounds(level, col, row)
                    assert x2 <= w, f"x2={x2} > width={w} at level={level} col={col}"
                    assert y2 <= h, f"y2={y2} > height={h} at level={level} row={row}"
