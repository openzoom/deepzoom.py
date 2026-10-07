"""Integration tests: create real collections from synthetic images, verify pixel output."""

import os

import PIL.Image
import pytest

import deepzoom


TILE_SIZE = 512
MAX_LEVEL = 8


def make_collection(tmp_path, dzi_paths, max_level=MAX_LEVEL, tile_size=TILE_SIZE,
                    tile_format="png", tile_background_color="#000000"):
    destination = os.path.join(str(tmp_path), "collection.dzc")
    collection = deepzoom.DeepZoomCollection(
        destination,
        max_level=max_level,
        tile_size=tile_size,
        tile_format=tile_format,
        tile_background_color=tile_background_color,
        image_quality=1.0,
    )
    for path in dzi_paths:
        collection.append(path)
    collection.save(max_workers=1)
    return destination


def open_tile(dzc_path, level, column, row, tile_format="png"):
    files_path = os.path.splitext(dzc_path)[0] + "_files"
    tile_path = os.path.join(files_path, str(level), f"{column}_{row}.{tile_format}")
    return PIL.Image.open(tile_path)


def sample_color(image, x, y, margin=2):
    """Sample average color in a small region to avoid edge artifacts."""
    red_total, green_total, blue_total, count = 0, 0, 0, 0
    for offset_x in range(margin):
        for offset_y in range(margin):
            pixel_x, pixel_y = x + offset_x, y + offset_y
            if pixel_x < image.width and pixel_y < image.height:
                red, green, blue = image.getpixel((pixel_x, pixel_y))[:3]
                red_total += red
                green_total += green
                blue_total += blue
                count += 1
    return (red_total // count, green_total // count, blue_total // count)


class TestSingleImage:
    def test_placed_at_origin(self, tmp_path, create_solid_dzi):
        dzi = create_solid_dzi(tmp_path, "red", 300, 300, (255, 0, 0))
        dzc = make_collection(tmp_path, [dzi])

        tile = open_tile(dzc, MAX_LEVEL, 0, 0)
        assert tile.size == (TILE_SIZE, TILE_SIZE)
        red, green, blue = sample_color(tile, 0, 0)
        assert red > 200 and green < 50 and blue < 50, f"Expected red, got ({red},{green},{blue})"

    def test_background_is_black(self, tmp_path, create_solid_dzi):
        dzi = create_solid_dzi(tmp_path, "small", 300, 300, (255, 255, 0))
        dzc = make_collection(tmp_path, [dzi])

        tile = open_tile(dzc, MAX_LEVEL, 0, 0)
        red, green, blue = sample_color(tile, 400, 400)
        assert red < 10 and green < 10 and blue < 10, f"Expected black, got ({red},{green},{blue})"


class TestTwoImages:
    def test_second_image_offset_in_x(self, tmp_path, create_solid_dzi):
        """z=1 → (1,0). At level 8, level_size=256 → paste at x=256."""
        red_dzi = create_solid_dzi(tmp_path, "red", 300, 300, (255, 0, 0))
        blue_dzi = create_solid_dzi(tmp_path, "blue", 300, 300, (0, 0, 255))
        dzc = make_collection(tmp_path, [red_dzi, blue_dzi])

        tile = open_tile(dzc, MAX_LEVEL, 0, 0)
        red, green, blue = sample_color(tile, 0, 0)
        assert red > 200 and blue < 50, f"Expected red at (0,0), got ({red},{green},{blue})"

        red, green, blue = sample_color(tile, 256, 0)
        assert blue > 200 and red < 50, f"Expected blue at (256,0), got ({red},{green},{blue})"


class TestFourImages:
    def test_four_quadrants(self, tmp_path, create_solid_dzi):
        """z=0→(0,0), z=1→(256,0), z=2→(0,256), z=3→(256,256) at level 8."""
        colors = [
            ("red", (255, 0, 0)),
            ("green", (0, 255, 0)),
            ("blue", (0, 0, 255)),
            ("yellow", (255, 255, 0)),
        ]
        dzis = [create_solid_dzi(tmp_path, name, 300, 300, color) for name, color in colors]
        dzc = make_collection(tmp_path, dzis)

        tile = open_tile(dzc, MAX_LEVEL, 0, 0)
        positions = [(0, 0), (256, 0), (0, 256), (256, 256)]
        for (name, expected_color), (x, y) in zip(colors, positions):
            red, green, blue = sample_color(tile, x, y)
            for actual, expected, channel in zip((red, green, blue), expected_color, "RGB"):
                if expected > 128:
                    assert actual > 200, f"{name} at ({x},{y}): {channel}={actual}"
                else:
                    assert actual < 50, f"{name} at ({x},{y}): {channel}={actual}"


class TestTileBoundary:
    def test_fifth_image_in_second_tile(self, tmp_path, create_solid_dzi):
        """z=4 → (2,0). At level 8: x=2*256=512 → tile (1,0)."""
        dzis = [create_solid_dzi(tmp_path, f"img{i}", 300, 300, (i * 50, 0, 0))
                for i in range(5)]
        dzc = make_collection(tmp_path, dzis)

        files_path = os.path.splitext(dzc)[0] + "_files"
        assert os.path.exists(os.path.join(files_path, str(MAX_LEVEL), "1_0.png"))

        tile = open_tile(dzc, MAX_LEVEL, 1, 0)
        red, green, blue = sample_color(tile, 0, 0)
        assert red > 150, f"Expected bright red for image 4, got ({red},{green},{blue})"


class TestMultiLevel:
    def test_positions_shrink_at_lower_levels(self, tmp_path, create_solid_dzi):
        """At level 7, level_size=128, so second image at x=128."""
        red_dzi = create_solid_dzi(tmp_path, "red", 300, 300, (255, 0, 0))
        blue_dzi = create_solid_dzi(tmp_path, "blue", 300, 300, (0, 0, 255))
        dzc = make_collection(tmp_path, [red_dzi, blue_dzi])

        tile = open_tile(dzc, 7, 0, 0)
        red, green, blue = sample_color(tile, 128, 0)
        assert blue > 200, f"At level 7, blue at x=128, got ({red},{green},{blue})"

    def test_level_0_each_image_1px(self, tmp_path, create_solid_dzi):
        red_dzi = create_solid_dzi(tmp_path, "red", 300, 300, (255, 0, 0))
        blue_dzi = create_solid_dzi(tmp_path, "blue", 300, 300, (0, 0, 255))
        dzc = make_collection(tmp_path, [red_dzi, blue_dzi])

        tile = open_tile(dzc, 0, 0, 0)
        first_red, first_green, first_blue = tile.getpixel((0, 0))[:3]
        second_red, second_green, second_blue = tile.getpixel((1, 0))[:3]
        assert first_red > 200, f"z=0 at level 0: expected red, got ({first_red},{first_green},{first_blue})"
        assert second_blue > 200, f"z=1 at level 0: expected blue, got ({second_red},{second_green},{second_blue})"


class TestBackgroundColor:
    def test_white_background(self, tmp_path, create_solid_dzi):
        dzi = create_solid_dzi(tmp_path, "small", 300, 300, (0, 0, 255))
        dzc = make_collection(tmp_path, [dzi], tile_background_color="#FFFFFF")

        tile = open_tile(dzc, MAX_LEVEL, 0, 0)
        red, green, blue = sample_color(tile, 400, 400)
        assert red > 240 and green > 240 and blue > 240, f"Expected white, got ({red},{green},{blue})"


class TestTileFormat:
    def test_png_output(self, tmp_path, create_solid_dzi):
        dzi = create_solid_dzi(tmp_path, "img", 300, 300, (128, 128, 128))
        dzc = make_collection(tmp_path, [dzi], tile_format="png")

        files_path = os.path.splitext(dzc)[0] + "_files"
        tile_path = os.path.join(files_path, str(MAX_LEVEL), "0_0.png")
        assert os.path.exists(tile_path)
        assert PIL.Image.open(tile_path).format == "PNG"

    def test_jpg_output(self, tmp_path, create_solid_dzi):
        dzi = create_solid_dzi(tmp_path, "img", 300, 300, (128, 128, 128))
        dzc = make_collection(tmp_path, [dzi], tile_format="jpg")

        files_path = os.path.splitext(dzc)[0] + "_files"
        tile_path = os.path.join(files_path, str(MAX_LEVEL), "0_0.jpg")
        assert os.path.exists(tile_path)
        assert PIL.Image.open(tile_path).format == "JPEG"


class TestFromFileRoundtrip:
    def test_preserves_items(self, tmp_path, create_solid_dzi):
        red_dzi = create_solid_dzi(tmp_path, "red", 200, 150, (255, 0, 0))
        blue_dzi = create_solid_dzi(tmp_path, "blue", 300, 250, (0, 0, 255))
        dzc = make_collection(tmp_path, [red_dzi, blue_dzi])

        loaded = deepzoom.DeepZoomCollection.from_file(dzc)
        assert len(loaded.items) == 2
        assert loaded.items[0].width == 200
        assert loaded.items[0].height == 150
        assert loaded.items[1].width == 300
        assert loaded.items[1].height == 250

    def test_preserves_settings(self, tmp_path, create_solid_dzi):
        dzi = create_solid_dzi(tmp_path, "img", 300, 300, (128, 128, 128))
        dzc = make_collection(tmp_path, [dzi], max_level=6, tile_size=256, tile_format="png")

        loaded = deepzoom.DeepZoomCollection.from_file(dzc)
        assert loaded.max_level == 6
        assert loaded.tile_size == 256
        assert loaded.tile_format == "png"
