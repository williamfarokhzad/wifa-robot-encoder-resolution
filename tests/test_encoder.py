from fractions import Fraction
from itertools import product
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from encoder import audit, load_states, trace_steps

ROOT = Path(__file__).resolve().parents[1]


class EncoderTests(unittest.TestCase):
    def test_closed_cycle_at_any_start(self):
        ring = ("00", "10", "11", "01")
        for start in range(4):
            cycle = ring[start:] + ring[:start + 1]
            self.assertEqual(trace_steps(cycle), (4, 4, 0))
            self.assertEqual(trace_steps(reversed(cycle)), (-4, 4, 0))

    def test_independent_generated_moves(self):
        # Generate wave samples from an unwrapped simulated electrical position.
        # Expected net motion is final position minus initial position.
        for initial in range(4):
            for moves in product((-1, 0, 1), repeat=5):
                position = initial
                positions = [position]
                for move in moves:
                    position += move
                    positions.append(position)
                samples = [
                    f"{int(p % 4 in (1, 2))}{int(p % 4 in (2, 3))}"
                    for p in positions
                ]
                self.assertEqual(
                    trace_steps(samples),
                    (positions[-1] - positions[0], sum(map(abs, moves)), moves.count(0)),
                )

    def test_all_two_bit_jumps_fail(self):
        for pair in (("00", "11"), ("11", "00"), ("10", "01"), ("01", "10")):
            with self.assertRaisesRegex(ValueError, "CSV line 3: two-bit jump"):
                trace_steps(pair)

    def test_first_sample_is_reference_not_motion(self):
        self.assertEqual(trace_steps(["11"]), (0, 0, 0))
        with self.assertRaisesRegex(ValueError, "at least one"):
            trace_steps([])

    def test_exact_units_and_noninteger_ratio(self):
        # A 60-cycle encoder turns 7/3 times per output turn: 560 edges/rev.
        # Four edges represent 4/560 of an output turn, i.e. 18/7 degrees.
        result = audit(["00", "10", "11", "01", "00"], cycles=60, gear="7/3")
        self.assertEqual(result, (4, 4, 0, 240, 560, Fraction(9, 14), Fraction(18, 7)))

    def test_already_decoded_counts_are_not_multiplied(self):
        self.assertEqual(
            audit(["00", "10"], x4_counts=2000, gear="12"),
            (1, 1, 0, 2000, 24000, Fraction(3, 200), Fraction(3, 200)),
        )

    def test_bad_resolution_and_ratio(self):
        for options in ({}, {"cycles": 1, "x4_counts": 4}, {"cycles": 0},
                        {"x4_counts": -1}, {"cycles": True}, {"cycles": 2, "gear": "-1"},
                        {"cycles": 2, "gear": "3/0"}):
            with self.subTest(options=options), self.assertRaises((ValueError, ZeroDivisionError)):
                audit(["00"], **options)

    def test_csv_rejects_wrong_header_shape_and_nonbit(self):
        for data in ("B,A\n0,1\n", "A,B\n0,1,0\n", "A,B\n0,2\n", "A,B\n\n"):
            with tempfile.TemporaryDirectory() as work:
                path = Path(work) / "trace.csv"
                path.write_text(data, encoding="utf-8")
                with self.assertRaises(ValueError):
                    list(load_states(path))

    def test_cli_signed_result(self):
        call = subprocess.run(
            [sys.executable, "encoder.py", "examples/reverse-after-pause.csv",
             "--x4-counts", "2000", "--gear", "12"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        self.assertEqual(call.stdout.splitlines(), [
            "Observed edges: 5; unchanged samples: 1; net X4 count: -1",
            "X4 counts per encoder turn: 2000; nominal counts per output turn: 24000",
            "Nominal output step: 0.015000 deg/count; relative angle: -0.015000 deg",
        ])

    def test_cli_rejects_jump_without_angle(self):
        call = subprocess.run(
            [sys.executable, "encoder.py", "examples/two-bit-jump.csv", "--cycles", "500"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(call.returncode, 2)
        self.assertEqual(call.stdout, "")
        self.assertIn("CSV line 3: two-bit jump", call.stderr)


if __name__ == "__main__":
    unittest.main()
