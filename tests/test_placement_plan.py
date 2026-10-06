"""Tests for compute_placement_plan and module-level math functions."""

import deepzoom


class TestModuleLevelFunctions:
    """Verify the extracted module-level functions work independently."""

    def test_morton_decode(self):
        assert deepzoom.morton_decode(0) == (0, 0)
        assert deepzoom.morton_decode(1) == (1, 0)
        assert deepzoom.morton_decode(2) == (0, 1)
        assert deepzoom.morton_decode(3) == (1, 1)

    def test_morton_encode(self):
        assert deepzoom.morton_encode(0, 0) == 0
        assert deepzoom.morton_encode(1, 0) == 1
        assert deepzoom.morton_encode(0, 1) == 2
        assert deepzoom.morton_encode(1, 1) == 3

    def test_collection_tile_position(self):
        assert deepzoom.collection_tile_position(0, 8, 512) == (0, 0)
        assert deepzoom.collection_tile_position(4, 8, 512) == (1, 0)

    def test_collection_paste_position(self):
        assert deepzoom.collection_paste_position(0, 8, 512) == (0, 0)
        assert deepzoom.collection_paste_position(1, 8, 512) == (256, 0)
        assert deepzoom.collection_paste_position(2, 8, 512) == (0, 256)
        assert deepzoom.collection_paste_position(3, 8, 512) == (256, 256)


class TestComputePlacementPlan:
    def test_returns_all_levels(self):
        plan = deepzoom.compute_placement_plan(0, 8, 512, "jpg")
        assert len(plan) == 9
        levels = [step.level for step in plan]
        assert levels == list(range(8, -1, -1))

    def test_first_image_always_at_origin(self):
        plan = deepzoom.compute_placement_plan(0, 8, 512, "jpg")
        for step in plan:
            assert step.collection_tile == (0, 0)
            assert step.paste_position == (0, 0)

    def test_level_size_doubles(self):
        plan = deepzoom.compute_placement_plan(0, 8, 512, "jpg")
        for step in plan:
            assert step.level_size == 2 ** step.level

    def test_source_tile_path_suffix(self):
        plan = deepzoom.compute_placement_plan(0, 8, 512, "png")
        assert plan[0].source_tile_path_suffix == "8/0_0.png"
        assert plan[-1].source_tile_path_suffix == "0/0_0.png"

    def test_second_image_placement(self):
        plan = deepzoom.compute_placement_plan(1, 8, 512, "jpg")
        step_l8 = plan[0]
        assert step_l8.level == 8
        assert step_l8.collection_tile == (0, 0)
        assert step_l8.paste_position == (256, 0)

    def test_fifth_image_tile_boundary(self):
        plan = deepzoom.compute_placement_plan(4, 8, 512, "jpg")
        step_l8 = plan[0]
        assert step_l8.level == 8
        assert step_l8.collection_tile == (1, 0)
        assert step_l8.paste_position == (0, 0)

    def test_matches_instance_methods(self, collection):
        """Plan output must match the instance methods it replaces."""
        for z in range(16):
            plan = deepzoom.compute_placement_plan(z, 8, 512, "jpg")
            for step in plan:
                level = step.level
                assert step.collection_tile == collection.get_tile_position(z, level, 512)
                col, row = collection.get_position(z)
                level_size = step.level_size
                images_per_tile = step.images_per_tile
                expected_x = (col % images_per_tile) * level_size
                expected_y = (row % images_per_tile) * level_size
                assert step.paste_position == (expected_x, expected_y)
