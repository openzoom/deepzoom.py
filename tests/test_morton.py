"""Tests for Z-order (Morton) curve encode/decode functions."""


class TestMortonDecode:
    """get_position: z-order index → (column, row) in the image grid."""

    def test_origin(self, collection):
        assert collection.get_position(0) == (0, 0)

    def test_first_column_step(self, collection):
        assert collection.get_position(1) == (1, 0)

    def test_first_row_step(self, collection):
        assert collection.get_position(2) == (0, 1)

    def test_diagonal(self, collection):
        assert collection.get_position(3) == (1, 1)

    def test_second_2x2_block(self, collection):
        assert collection.get_position(4) == (2, 0)
        assert collection.get_position(5) == (3, 0)
        assert collection.get_position(6) == (2, 1)
        assert collection.get_position(7) == (3, 1)

    def test_third_2x2_block(self, collection):
        assert collection.get_position(8) == (0, 2)
        assert collection.get_position(9) == (1, 2)
        assert collection.get_position(10) == (0, 3)
        assert collection.get_position(11) == (1, 3)

    def test_fourth_2x2_block(self, collection):
        assert collection.get_position(12) == (2, 2)
        assert collection.get_position(13) == (3, 2)
        assert collection.get_position(14) == (2, 3)
        assert collection.get_position(15) == (3, 3)

    def test_start_of_second_4x4(self, collection):
        assert collection.get_position(16) == (4, 0)

    def test_large_value(self, collection):
        column, row = collection.get_position(1000)
        assert column >= 0 and row >= 0
        assert collection.get_z_order(column, row) == 1000


class TestMortonEncode:
    """get_z_order: (column, row) → z-order index."""

    def test_origin(self, collection):
        assert collection.get_z_order(0, 0) == 0

    def test_known_encodings(self, collection):
        assert collection.get_z_order(1, 0) == 1
        assert collection.get_z_order(0, 1) == 2
        assert collection.get_z_order(1, 1) == 3
        assert collection.get_z_order(2, 0) == 4
        assert collection.get_z_order(3, 0) == 5
        assert collection.get_z_order(3, 3) == 15
        assert collection.get_z_order(4, 0) == 16


class TestMortonRoundtrip:
    """Encode → decode and decode → encode produce identity."""

    def test_decode_encode_roundtrip_0_to_255(self, collection):
        for z in range(256):
            column, row = collection.get_position(z)
            assert collection.get_z_order(column, row) == z, f"roundtrip failed for z={z}"

    def test_encode_decode_roundtrip_grid(self, collection):
        for column in range(16):
            for row in range(16):
                z = collection.get_z_order(column, row)
                assert collection.get_position(z) == (column, row), (
                    f"roundtrip failed for ({column}, {row})"
                )

    def test_spatial_locality(self, collection):
        """Consecutive z-order indices within a 4×4 block map to nearby cells."""
        for z in range(15):
            first_column, first_row = collection.get_position(z)
            second_column, second_row = collection.get_position(z + 1)
            distance = abs(second_column - first_column) + abs(second_row - first_row)
            assert distance <= 4, (
                f"z={z}→({first_column},{first_row}), z={z+1}→({second_column},{second_row}): Manhattan distance {distance} > 4"
            )
