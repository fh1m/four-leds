import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rig"))

from main_v2 import error_line, v1_direction  # noqa: E402


def test_error_is_signed_proportional_and_clamped():
    assert error_line((330, 240), (320, 240), 640) == "E 6 0\n"       # 10 px of a 160 px "far"
    assert error_line((160, 400), (320, 240), 640) == "E -100 100\n"  # far on both axes, clamped
    assert error_line((320, 240), (320, 240), 640) == "E 0 0\n"


def test_v1_direction_with_the_parentheses_it_was_missing():
    assert v1_direction((100, 400), (320, 240)) == "left,down"
    assert v1_direction((500, 100), (320, 240)) == "right,up"
    assert v1_direction((320, 400), (320, 240)) == "down"


def test_the_original_bug_really_was_a_bug():
    center, ideal, direction = (100, 400), (320, 240), "left"
    # origin/main.py, verbatim operator precedence:
    direction += ("" if direction == "" else ",") + "up" if center[1] < ideal[1] else "down"
    assert direction == "leftdown"
