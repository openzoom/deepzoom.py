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

    def test_item_source_tile_path(self):
        assert deepzoom.item_source_tile_path("images/red.dzi", 8, "png") == (
            "images/red_files/8/0_0.png"
        )


class TestComputePlacementPlan:
    def test_returns_all_levels(self):
        plan = deepzoom.compute_placement_plan(0, 8, 512)
        assert len(plan) == 9
        levels = [step.level for step in plan]
        assert levels == list(range(8, -1, -1))

    def test_first_image_always_at_origin(self):
        plan = deepzoom.compute_placement_plan(0, 8, 512)
        for step in plan:
            assert step.collection_tile == (0, 0)
            assert step.paste_position == (0, 0)

    def test_second_image_placement(self):
        plan = deepzoom.compute_placement_plan(1, 8, 512)
        max_level_step = plan[0]
        assert max_level_step.level == 8
        assert max_level_step.collection_tile == (0, 0)
        assert max_level_step.paste_position == (256, 0)

    def test_fifth_image_tile_boundary(self):
        plan = deepzoom.compute_placement_plan(4, 8, 512)
        max_level_step = plan[0]
        assert max_level_step.level == 8
        assert max_level_step.collection_tile == (1, 0)
        assert max_level_step.paste_position == (0, 0)

    def test_eleventh_image_across_levels(self):
        # z=10 → (0, 3): at level `level`, row 3 starts at y = 3 * 2**level,
        # which wraps into tile row 1 once 2**level × 4 exceeds the tile size
        expected = {
            8: ((0, 1), (0, 256)),
            7: ((0, 0), (0, 384)),
            6: ((0, 0), (0, 192)),
            0: ((0, 0), (0, 3)),
        }
        plan = {step.level: step for step in deepzoom.compute_placement_plan(10, 8, 512)}
        for level, (collection_tile, paste_position) in expected.items():
            assert plan[level].collection_tile == collection_tile, level
            assert plan[level].paste_position == paste_position, level
