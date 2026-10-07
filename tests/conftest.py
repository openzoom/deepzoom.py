import os

import PIL.Image
import pytest

import deepzoom


@pytest.fixture
def collection():
    """Minimal DeepZoomCollection for testing instance methods."""
    return deepzoom.DeepZoomCollection("unused.dzc")


def _create_solid_dzi(directory, name, width, height, color, tile_size=510, tile_overlap=1):
    """Create a solid-color DZI pyramid and return the .dzi path."""
    image = PIL.Image.new("RGB", (width, height), color)
    destination = os.path.join(str(directory), f"{name}.dzi")
    creator = deepzoom.ImageCreator(
        tile_size=tile_size,
        tile_overlap=tile_overlap,
        tile_format="png",
        image_quality=1.0,
    )
    creator.create(image, destination)
    return destination


@pytest.fixture
def create_solid_dzi():
    """Fixture providing the solid DZI creator function."""
    return _create_solid_dzi
