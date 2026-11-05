"""Audit a sampled A/B trace offline; this module does not read hardware."""
import argparse
import csv
from fractions import Fraction
from pathlib import Path

PHASE = {"00": 0, "10": 1, "11": 2, "01": 3}


def trace_steps(states):
    """Count signed observed X4 transitions, rejecting ambiguous two-bit jumps."""
    net = edges = repeats = 0
    previous = None
    for row, state in enumerate(states, start=2):
        if state not in PHASE:
            raise ValueError(f"CSV line {row}: expected A and B bits (0 or 1)")
        current = PHASE[state]
        if previous is not None:
            delta = (current - previous) % 4
            if delta == 2:
                raise ValueError(
                    f"CSV line {row}: two-bit jump; direction is ambiguous, "
                    "inspect sampling or signals before using this trace"
                )
            if delta == 0:
                repeats += 1
            else:
                net += 1 if delta == 1 else -1
                edges += 1
        previous = current
    if previous is None:
        raise ValueError("trace needs at least one A/B sample")
    return net, edges, repeats


def load_states(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = csv.reader(file, strict=True)
        if next(rows, None) != ["A", "B"]:
            raise ValueError("expected exact CSV header A,B")
        for number, row in enumerate(rows, start=2):
            if len(row) != 2 or any(bit not in {"0", "1"} for bit in row):
                raise ValueError(f"CSV line {number}: expected exactly two 0 or 1 fields")
            yield "".join(row)


def audit(states, *, cycles=None, x4_counts=None, gear=Fraction(1)):
    """gear is encoder shaft turns per output turn; result is relative to row one."""
    if (cycles is None) == (x4_counts is None):
        raise ValueError("specify exactly one of cycles or X4 counts per encoder turn")
    resolution = cycles if cycles is not None else x4_counts
    if type(resolution) is not int or resolution <= 0:
        raise ValueError("encoder resolution must be a positive integer")
    ratio = Fraction(gear)
    if ratio <= 0:
        raise ValueError("gear ratio must be positive")
    counts_per_encoder_rev = 4 * cycles if cycles is not None else x4_counts
    count, edges, repeats = trace_steps(states)
    counts_per_output_rev = counts_per_encoder_rev * ratio
    step = 360 / counts_per_output_rev
    return count, edges, repeats, counts_per_encoder_rev, counts_per_output_rev, step, count * step


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cycles", type=int, help="A cycles per encoder revolution")
    group.add_argument("--x4-counts", type=int, help="already decoded X4 counts per encoder revolution")
    parser.add_argument("--gear", default="1", help="encoder turns per output turn, e.g. 12 or 3/2")
    args = parser.parse_args(argv)
    try:
        net, edges, repeats, shaft, output, step, angle = audit(
            load_states(args.trace), cycles=args.cycles, x4_counts=args.x4_counts, gear=args.gear
        )
        # Preserve exact fractions in the API and in the count ratio; decimal angles are display only.
        step_text, angle_text = f"{float(step):.6f}", f"{float(angle):+.6f}"
    except (OSError, UnicodeError, csv.Error, ValueError, ArithmeticError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"Observed edges: {edges}; unchanged samples: {repeats}; net X4 count: {net:+d}")
    print(f"X4 counts per encoder turn: {shaft}; nominal counts per output turn: {output}")
    print(f"Nominal output step: {step_text} deg/count; relative angle: {angle_text} deg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
