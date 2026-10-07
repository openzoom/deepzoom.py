"""`ImageCreator.create` logs progress by share of all tiles, since the last
levels hold most of them."""

import logging
import re

import PIL.Image

import deepzoom


def create(tmp_path, caplog, width, height):
    image = PIL.Image.new("RGB", (width, height), (255, 0, 0))
    creator = deepzoom.ImageCreator(tile_size=254, tile_format="png")
    with caplog.at_level(logging.INFO, logger="deepzoom"):
        creator.create(image, str(tmp_path / "image.dzi"))
    return [record.getMessage() for record in caplog.records]


def percentages(messages):
    return [int(match.group(1)) for message in messages
            for match in [re.match(r"\s*(\d+)%", message)] if match]


def test_reports_progress_up_to_100_percent(tmp_path, caplog):
    messages = create(tmp_path, caplog, 3000, 2000)
    reported = percentages(messages)
    assert reported == sorted(reported)
    assert reported[-1] == 100
    # 12 × 8 tiles at the max level alone; enough for several steps
    assert len(reported) >= 5


def test_progress_counts_tiles_not_levels(tmp_path, caplog):
    messages = create(tmp_path, caplog, 3000, 2000)
    # Levels 0–11 hold 41 of 137 tiles, level 12 the other 96 (12 × 8).
    # Counting levels, level 12 would start at 92%; counting tiles, at 30%
    max_level_reports = [message for message in messages if "level 12/12" in message]
    assert percentages(max_level_reports)[0] < 50


def test_logs_summary(tmp_path, caplog):
    messages = create(tmp_path, caplog, 300, 200)
    assert any("300 × 200" in message and "tiles" in message for message in messages)
    assert any(message.startswith("Saved") for message in messages)
