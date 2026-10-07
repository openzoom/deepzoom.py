"""Property-based tests using Hypothesis for the collection math."""

from hypothesis import given, assume
from hypothesis import strategies as st

import deepzoom


# Strategies
z_orders = st.integers(min_value=0, max_value=2**16 - 1)
grid_coords = st.integers(min_value=0, max_value=255)
levels = st.integers(min_value=0, max_value=8)
tile_sizes = st.sampled_from([256, 512, 1024])
image_dimensions = st.integers(min_value=1, max_value=50000)


@st.composite
def valid_descriptor_and_level(draw):
    width = draw(st.integers(min_value=1, max_value=10000))
    height = draw(st.integers(min_value=1, max_value=10000))
    tile_size = draw(st.sampled_from([128, 256, 510, 512]))
    tile_overlap = draw(st.integers(min_value=0, max_value=10))
    descriptor = deepzoom.DeepZoomImageDescriptor(
        width=width, height=height, tile_size=tile_size, tile_overlap=tile_overlap,
    )
    level = draw(st.integers(min_value=0, max_value=descriptor.num_levels - 1))
    return descriptor, level


# ---- Morton curve properties ----

class TestMortonProperties:
    @given(z=z_orders)
    def test_decode_encode_roundtrip(self, z):
        collection = deepzoom.DeepZoomCollection("unused.dzc")
        column, row = collection.get_position(z)
        assert collection.get_z_order(column, row) == z

    @given(column=grid_coords, row=grid_coords)
    def test_encode_decode_roundtrip(self, column, row):
        collection = deepzoom.DeepZoomCollection("unused.dzc")
        z = collection.get_z_order(column, row)
        assert collection.get_position(z) == (column, row)

    @given(z=z_orders)
    def test_decode_produces_non_negative(self, z):
        collection = deepzoom.DeepZoomCollection("unused.dzc")
        column, row = collection.get_position(z)
        assert column >= 0
        assert row >= 0

    @given(column=grid_coords, row=grid_coords)
    def test_encode_produces_non_negative(self, column, row):
        collection = deepzoom.DeepZoomCollection("unused.dzc")
        assert collection.get_z_order(column, row) >= 0

    @given(z=z_orders)
    def test_decode_is_deterministic(self, z):
        collection = deepzoom.DeepZoomCollection("unused.dzc")
        assert collection.get_position(z) == collection.get_position(z)

    @given(z1=z_orders, z2=z_orders)
    def test_different_z_orders_give_different_positions(self, z1, z2):
        assume(z1 != z2)
        collection = deepzoom.DeepZoomCollection("unused.dzc")
        assert collection.get_position(z1) != collection.get_position(z2)


# ---- Descriptor properties ----

class TestDescriptorProperties:
    @given(width=image_dimensions, height=image_dimensions)
    def test_num_levels_at_least_1(self, width, height):
        descriptor = deepzoom.DeepZoomImageDescriptor(width=width, height=height)
        assert descriptor.num_levels >= 1

    @given(width=image_dimensions, height=image_dimensions)
    def test_level_0_dimensions_are_1x1(self, width, height):
        descriptor = deepzoom.DeepZoomImageDescriptor(width=width, height=height)
        assert descriptor.get_dimensions(0) == (1, 1)

    @given(width=image_dimensions, height=image_dimensions)
    def test_max_level_dimensions_are_original(self, width, height):
        descriptor = deepzoom.DeepZoomImageDescriptor(width=width, height=height)
        assert descriptor.get_dimensions(descriptor.num_levels - 1) == (width, height)

    @given(width=image_dimensions, height=image_dimensions)
    def test_max_level_scale_is_1(self, width, height):
        descriptor = deepzoom.DeepZoomImageDescriptor(width=width, height=height)
        assert descriptor.get_scale(descriptor.num_levels - 1) == 1.0

    @given(data=st.data())
    def test_dimensions_monotonically_increase(self, data):
        descriptor, level = data.draw(valid_descriptor_and_level())
        if level == 0:
            return
        width_low, height_low = descriptor.get_dimensions(level - 1)
        width_high, height_high = descriptor.get_dimensions(level)
        assert width_high >= width_low
        assert height_high >= height_low

    @given(data=st.data())
    def test_dimensions_at_least_1(self, data):
        descriptor, level = data.draw(valid_descriptor_and_level())
        width, height = descriptor.get_dimensions(level)
        assert width >= 1
        assert height >= 1

    @given(data=st.data())
    def test_num_tiles_at_least_1x1(self, data):
        descriptor, level = data.draw(valid_descriptor_and_level())
        columns, rows = descriptor.get_num_tiles(level)
        assert columns >= 1
        assert rows >= 1

    @given(data=st.data())
    def test_tile_bounds_within_image(self, data):
        descriptor, level = data.draw(valid_descriptor_and_level())
        width, height = descriptor.get_dimensions(level)
        columns, rows = descriptor.get_num_tiles(level)
        column = data.draw(st.integers(min_value=0, max_value=columns - 1))
        row = data.draw(st.integers(min_value=0, max_value=rows - 1))
        x1, y1, x2, y2 = descriptor.get_tile_bounds(level, column, row)
        assert x1 >= 0 and y1 >= 0
        assert x2 <= width
        assert y2 <= height
        assert x2 > x1 and y2 > y1

    @given(data=st.data())
    def test_tiles_cover_full_image(self, data):
        descriptor, level = data.draw(valid_descriptor_and_level())
        width, height = descriptor.get_dimensions(level)
        columns, rows = descriptor.get_num_tiles(level)
        first = descriptor.get_tile_bounds(level, 0, 0)
        last = descriptor.get_tile_bounds(level, columns - 1, rows - 1)
        assert first[0] == 0
        assert first[1] == 0
        assert last[2] == width
        assert last[3] == height


# ---- Collection tile placement properties ----

class TestCollectionPlacementProperties:
    @given(z=st.integers(min_value=0, max_value=255), level=levels, tile_size=tile_sizes)
    def test_tile_position_non_negative(self, z, level, tile_size):
        column, row = deepzoom.collection_tile_position(z, level, tile_size)
        assert column >= 0
        assert row >= 0

    @given(z=st.integers(min_value=0, max_value=255), level=levels, tile_size=tile_sizes)
    def test_paste_position_within_tile(self, z, level, tile_size):
        x, y = deepzoom.collection_paste_position(z, level, tile_size)
        assert 0 <= x < tile_size
        assert 0 <= y < tile_size

    @given(tile_size=tile_sizes, level=levels)
    def test_no_collisions(self, tile_size, level):
        """Every item gets its own slot, across all collection tiles."""
        seen = {}
        for z in range(256):
            slot = (
                deepzoom.collection_tile_position(z, level, tile_size),
                deepzoom.collection_paste_position(z, level, tile_size),
            )
            assert slot not in seen, (
                f"z={z} collides with z={seen[slot]} at {slot}, level={level}"
            )
            seen[slot] = z

    @given(z=st.integers(min_value=0, max_value=255), tile_size=tile_sizes)
    def test_level_0_all_in_same_tile(self, z, tile_size):
        assert deepzoom.collection_tile_position(z, 0, tile_size) == (0, 0)
