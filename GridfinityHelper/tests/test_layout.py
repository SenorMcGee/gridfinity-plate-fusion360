import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.layout import compute_layout, PAD, PARTIAL, START, END, CENTER


def test_exact_fit():
    l = compute_layout(210, 126)
    assert (l.cols, l.rows) == (5, 3)
    assert l.pad_x == (0, 0) and not any(c.partial for c in l.cells)


def test_center_pad():
    l = compute_layout(200, 130, mode=PAD)
    assert (l.cols, l.rows) == (4, 3)
    assert abs(l.pad_x[0] - 16) < 1e-6 and abs(l.pad_x[1] - 16) < 1e-6
    assert abs(l.pad_y[0] - 2) < 1e-6


def test_start_end_pad():
    l = compute_layout(200, 126, mode=PAD, align_x=START)
    assert l.pad_x == (0, 32)
    l = compute_layout(200, 126, mode=PAD, align_x=END)
    assert l.pad_x == (32, 0)


def test_partial_center():
    l = compute_layout(200, 126, mode=PARTIAL)
    assert l.cols == 6 and l.rows == 3
    widths = sorted({round(c.w, 6) for c in l.cells})
    assert widths == [16, 42]
    assert sum(c.w for c in l.cells[:6]) == 200


def test_partial_start_end():
    l = compute_layout(200, 126, mode=PARTIAL, align_x=START)
    assert l.cells[4].w == 32 and l.cells[4].partial
    l = compute_layout(200, 126, mode=PARTIAL, align_x=END)
    assert l.cells[0].w == 32 and l.cells[0].nominal_x == -10


def test_min_partial_becomes_padding():
    l = compute_layout(214, 126, mode=PARTIAL, align_x=START, min_partial=5)
    assert l.cols == 5 and l.pad_x == (0, 4)
    l = compute_layout(214, 126, mode=PARTIAL, align_x=CENTER, min_partial=5)
    assert l.cols == 5 and l.pad_x == (2, 2)


def test_smaller_than_pitch():
    l = compute_layout(30, 30, mode=PARTIAL, align_x=START, align_y=START)
    assert len(l.cells) == 1 and l.cells[0].w == 30
    l = compute_layout(30, 30, mode=PAD)
    assert len(l.cells) == 0


def test_split_400x400_on_256_bed():
    # 400x400 with 42mm pitch -> 9x9 cells (378mm) + 11mm pad on each side.
    # On a 256x256 bed, 9 cells should split into 5 + 4 cells:
    # Tile 1: 11 + 5*42 = 221 mm (<= 256)
    # Tile 2: 4*42 + 11 = 179 mm (<= 256)
    l = compute_layout(400, 400, mode=PAD, max_length=256, max_width=256)
    assert (l.tiles_x, l.tiles_y) == (2, 2)
    assert len(l.tiles) == 4
    widths = sorted({round(t.width, 4) for t in l.tiles})
    assert widths == [179.0, 221.0]
    assert all(t.width <= 256 and t.height <= 256 for t in l.tiles)


