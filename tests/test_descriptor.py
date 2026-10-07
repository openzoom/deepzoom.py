"""Tests for DeepZoomImageDescriptor pure math methods."""

import pytest

import deepzoom


def make_descriptor(width, height, tile_size=510, tile_overlap=1):
    return deepzoom.DeepZoomImageDescriptor(
        width=width,
        height=height,
        tile_size=tile_size,
        tile_overlap=tile_overlap,
    )


class TestNumLevels:
    def test_1x1(self):
        assert make_descriptor(1, 1).num_levels == 1

    def test_2x2(self):
        assert make_descriptor(2, 2).num_levels == 2

    def test_256x256(self):
        assert make_descriptor(256, 256).num_levels == 9

    def test_512x512(self):
        assert make_descriptor(512, 512).num_levels == 10

    def test_640x447(self):
        assert make_descriptor(640, 447).num_levels == 11

    def test_1024x768(self):
        assert make_descriptor(1024, 768).num_levels == 11

    def test_non_square_width_dominant(self):
        assert make_descriptor(1000, 1).num_levels == 11

    def test_non_square_height_dominant(self):
        assert make_descriptor(1, 1000).num_levels == 11

    def test_power_of_two_boundary(self):
        assert make_descriptor(128, 128).num_levels == 8

    def test_just_above_power_of_two(self):
        assert make_descriptor(129, 129).num_levels == 9


class TestGetScale:
    def test_level_0_is_smallest(self):
        descriptor = make_descriptor(640, 447)
        scale = descriptor.get_scale(0)
        assert scale == pytest.approx(1.0 / 1024)

    def test_max_level_is_1(self):
        descriptor = make_descriptor(640, 447)
        assert descriptor.get_scale(descriptor.num_levels - 1) == 1.0

    def test_each_level_doubles(self):
        descriptor = make_descriptor(640, 447)
        for level in range(1, descriptor.num_levels):
            assert descriptor.get_scale(level) == pytest.approx(descriptor.get_scale(level - 1) * 2)

    def test_invalid_level_negative(self):
        descriptor = make_descriptor(640, 447)
        with pytest.raises(AssertionError):
            descriptor.get_scale(-1)

    def test_invalid_level_too_high(self):
        descriptor = make_descriptor(640, 447)
        with pytest.raises(AssertionError):
            descriptor.get_scale(descriptor.num_levels)


class TestGetDimensions:
    def test_level_0_is_1x1(self):
        descriptor = make_descriptor(640, 447)
        assert descriptor.get_dimensions(0) == (1, 1)

    def test_max_level_is_original(self):
        descriptor = make_descriptor(640, 447)
        assert descriptor.get_dimensions(descriptor.num_levels - 1) == (640, 447)

    def test_known_mid_level(self):
        descriptor = make_descriptor(640, 447)
        width, height = descriptor.get_dimensions(8)
        assert width == 160
        assert height == 112

    def test_dimensions_halve_down(self):
        descriptor = make_descriptor(1024, 768)
        for level in range(descriptor.num_levels - 1, 0, -1):
            width_high, height_high = descriptor.get_dimensions(level)
            width_low, height_low = descriptor.get_dimensions(level - 1)
            assert width_low <= width_high
            assert height_low <= height_high

    def test_dimensions_always_at_least_1(self):
        descriptor = make_descriptor(640, 447)
        for level in range(descriptor.num_levels):
            width, height = descriptor.get_dimensions(level)
            assert width >= 1
            assert height >= 1

    def test_invalid_level(self):
        descriptor = make_descriptor(640, 447)
        with pytest.raises(AssertionError):
            descriptor.get_dimensions(descriptor.num_levels)


class TestGetNumTiles:
    def test_single_tile_at_level_0(self):
        descriptor = make_descriptor(640, 447, tile_size=510)
        assert descriptor.get_num_tiles(0) == (1, 1)

    def test_multiple_tiles_at_max_level(self):
        descriptor = make_descriptor(640, 447, tile_size=510)
        columns, rows = descriptor.get_num_tiles(descriptor.num_levels - 1)
        assert columns == 2
        assert rows == 1

    def test_large_image_many_tiles(self):
        descriptor = make_descriptor(2048, 2048, tile_size=510)
        columns, rows = descriptor.get_num_tiles(descriptor.num_levels - 1)
        assert columns >= 4
        assert rows >= 4

    def test_exact_tile_size_boundary(self):
        descriptor = make_descriptor(510, 510, tile_size=510)
        assert descriptor.get_num_tiles(descriptor.num_levels - 1) == (1, 1)

    def test_one_pixel_over_tile_size(self):
        descriptor = make_descriptor(511, 511, tile_size=510)
        columns, rows = descriptor.get_num_tiles(descriptor.num_levels - 1)
        assert columns == 2
        assert rows == 2


class TestGetTileBounds:
    def test_origin_tile(self):
        descriptor = make_descriptor(640, 447, tile_size=510, tile_overlap=1)
        x1, y1, x2, y2 = descriptor.get_tile_bounds(descriptor.num_levels - 1, 0, 0)
        assert x1 == 0
        assert y1 == 0
        assert x2 == 511
        assert y2 == 447

    def test_second_column_tile(self):
        descriptor = make_descriptor(640, 447, tile_size=510, tile_overlap=1)
        x1, y1, x2, y2 = descriptor.get_tile_bounds(descriptor.num_levels - 1, 1, 0)
        assert x1 == 509
        assert y1 == 0
        assert x2 == 640
        assert y2 == 447

    def test_overlap_0(self):
        descriptor = make_descriptor(640, 447, tile_size=510, tile_overlap=0)
        x1, y1, x2, y2 = descriptor.get_tile_bounds(descriptor.num_levels - 1, 0, 0)
        assert x1 == 0
        assert y1 == 0
        assert x2 == 510
        assert y2 == 447

    def test_overlap_2(self):
        descriptor = make_descriptor(640, 447, tile_size=128, tile_overlap=2)
        x1, y1, x2, y2 = descriptor.get_tile_bounds(descriptor.num_levels - 1, 0, 0)
        assert x1 == 0
        assert y1 == 0
        assert x2 == 130
        assert y2 == 130

    def test_non_origin_includes_both_overlaps(self):
        descriptor = make_descriptor(640, 447, tile_size=128, tile_overlap=2)
        x1, y1, x2, y2 = descriptor.get_tile_bounds(descriptor.num_levels - 1, 1, 1)
        assert x1 == 126
        assert y1 == 126

    def test_bounds_dont_exceed_image(self):
        descriptor = make_descriptor(640, 447, tile_size=510, tile_overlap=1)
        for level in range(descriptor.num_levels):
            columns, rows = descriptor.get_num_tiles(level)
            width, height = descriptor.get_dimensions(level)
            for column in range(columns):
                for row in range(rows):
                    x1, y1, x2, y2 = descriptor.get_tile_bounds(level, column, row)
                    assert x2 <= width, f"x2={x2} > width={width} at level={level} column={column}"
                    assert y2 <= height, f"y2={y2} > height={height} at level={level} row={row}"
