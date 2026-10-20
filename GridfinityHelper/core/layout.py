"""Pure-Python Gridfinity layout math (no Fusion dependency). All units are mm."""
import math
from dataclasses import dataclass, field
from typing import List, Tuple

PAD = 'pad'          # center/align full cells only, pad the leftover
PARTIAL = 'partial'  # fill leftover with clipped partial cells

START = 'start'
CENTER = 'center'
END = 'end'

_EPS = 1e-6


@dataclass
class Segment:
    """One cell along a single axis."""
    start: float          # clipped start position inside the plate
    size: float           # clipped size (== pitch for full cells)
    nominal_start: float  # where the full (unclipped) cell would begin


@dataclass
class Cell:
    x: float
    y: float
    w: float
    h: float
    nominal_x: float
    nominal_y: float
    partial: bool


@dataclass
class Tile:
    tx: int
    ty: int
    x0: float
    x1: float
    y0: float
    y1: float
    col_start: int
    col_end: int
    row_start: int
    row_end: int

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def cols(self) -> int:
        return self.col_end - self.col_start

    @property
    def rows(self) -> int:
        return self.row_end - self.row_start


@dataclass
class Layout:
    cells: List[Cell]
    cols: int
    rows: int
    pad_x: Tuple[float, float]  # (start side, end side) unused plate on X
    pad_y: Tuple[float, float]
    split_x: List[float] = field(default_factory=list)  # internal split X coordinates
    split_y: List[float] = field(default_factory=list)  # internal split Y coordinates
    tiles: List[Tile] = field(default_factory=list)

    @property
    def tiles_x(self) -> int:
        return len(self.split_x) + 1

    @property
    def tiles_y(self) -> int:
        return len(self.split_y) + 1


def axis_segments(length: float, pitch: float, mode: str, align: str,
                  min_partial: float):
    """Return (segments, pad_start, pad_end) for one axis."""
    if length <= 0 or pitch <= 0:
        raise ValueError('length and pitch must be positive')
    n = int(math.floor(length / pitch + _EPS))
    slack = length - n * pitch
    if slack < _EPS:
        slack = 0.0

    # Decide what the leftover becomes: partial cell(s) or padding.
    use_partial = False
    if mode == PARTIAL and slack > 0:
        per_side = slack / 2 if align == CENTER else slack
        use_partial = per_side >= min_partial

    segs: List[Tuple[float, float, float]] = []  # start, size, nominal_start

    if use_partial:
        if align == START:
            offset = 0.0
            tail = [(n * pitch, slack, n * pitch)]
            head = []
        elif align == END:
            offset = slack
            head = [(0.0, slack, slack - pitch)]
            tail = []
        else:
            half = slack / 2
            offset = half
            head = [(0.0, half, half - pitch)]
            tail = [(half + n * pitch, half, half + n * pitch)]
        segs += head
        segs += [(offset + i * pitch, pitch, offset + i * pitch) for i in range(n)]
        segs += tail
        return segs, 0.0, 0.0

    offset = {START: 0.0, END: slack, CENTER: slack / 2}[align]
    segs = [(offset + i * pitch, pitch, offset + i * pitch) for i in range(n)]
    return segs, offset, slack - offset


def split_axis(length: float, segs: List[Tuple[float, float, float]],
               max_size: float) -> Tuple[List[float], List[Tuple[float, float, int, int]]]:
    """Compute balanced split positions along cell boundaries so each tile <= max_size.

    Returns (internal_splits, [(x0, x1, idx_start, idx_end), ...]).
    If max_size <= 0 or length <= max_size, returns no splits and a single span.
    """
    n = len(segs)
    if max_size <= _EPS or length <= max_size + _EPS or n <= 1:
        return [], [(0.0, length, 0, n)]

    # Physical extent of each segment i when it is at the start/interior/end of the plate:
    # Seam between segment i-1 and segment i is at segs[i][0].
    # So a tile covering segments [a .. b) spans from:
    #   x0 = 0.0 if a == 0 else segs[a][0]
    #   x1 = length if b == n else segs[b][0]
    def span_bounds(a: int, b: int) -> Tuple[float, float]:
        x0 = 0.0 if a == 0 else segs[a][0]
        x1 = length if b == n else segs[b][0]
        return x0, x1

    # Find minimum number of tiles K such that a valid partition of [0..n] into K parts exists
    # where every part has width <= max_size (or if a single cell + pad > max_size, allow 1-cell tile).
    # Furthermore, among valid partitions of size K, minimize the difference between max and min tile width.
    for k in range(2, n + 1):
        best_cost = None
        best_cuts: List[int] = []

        # DP / recursion over cut indices 0 < c_1 < c_2 < ... < c_{k-1} < n
        def search(start_idx: int, cuts_left: int, current_cuts: List[int],
                   widths: List[float]):
            nonlocal best_cost, best_cuts
            if cuts_left == 0:
                x0, x1 = span_bounds(start_idx, n)
                w = x1 - x0
                if w > max_size + _EPS and (n - start_idx) > 1:
                    return
                all_w = widths + [w]
                # Prefer all <= max_size; score by variance from ideal length/k
                over = sum(max(0.0, ww - max_size) for ww in all_w)
                ideal = length / k
                cost = (round(over, 4), sum((ww - ideal) ** 2 for ww in all_w))
                if best_cost is None or cost < best_cost:
                    best_cost = cost
                    best_cuts = list(current_cuts)
                return

            for nxt in range(start_idx + 1, n - cuts_left + 1):
                x0, x1 = span_bounds(start_idx, nxt)
                w = x1 - x0
                if w > max_size + _EPS and (nxt - start_idx) > 1:
                    break
                current_cuts.append(nxt)
                widths.append(w)
                search(nxt, cuts_left - 1, current_cuts, widths)
                widths.pop()
                current_cuts.pop()

        search(0, k - 1, [], [])
        if best_cost is not None and best_cost[0] == 0.0:
            idxs = [0] + best_cuts + [n]
            splits = [segs[c][0] for c in best_cuts]
            spans = [(*span_bounds(idxs[i], idxs[i + 1]), idxs[i], idxs[i + 1])
                     for i in range(k)]
            return splits, spans

    # Fallback: split at every cell boundary
    idxs = list(range(n + 1))
    splits = [segs[c][0] for c in range(1, n)]
    spans = [(*span_bounds(i, i + 1), i, i + 1) for i in range(n)]
    return splits, spans


def compute_layout(length: float, width: float, pitch: float = 42.0,
                   mode: str = PAD, align_x: str = CENTER,
                   align_y: str = CENTER, min_partial: float = 5.0,
                   max_length: float = 0.0, max_width: float = 0.0) -> Layout:
    xs, pxs, pxe = axis_segments(length, pitch, mode, align_x, min_partial)
    ys, pys, pye = axis_segments(width, pitch, mode, align_y, min_partial)
    cells = []
    for (y, h, ny) in ys:
        for (x, w, nx) in xs:
            partial = w < pitch - _EPS or h < pitch - _EPS
            cells.append(Cell(x, y, w, h, nx, ny, partial))

    split_x, spans_x = split_axis(length, xs, max_length)
    split_y, spans_y = split_axis(width, ys, max_width)
    tiles = []
    for ty, (y0, y1, r0, r1) in enumerate(spans_y):
        for tx, (x0, x1, c0, c1) in enumerate(spans_x):
            tiles.append(Tile(tx, ty, x0, x1, y0, y1, c0, c1, r0, r1))

    return Layout(cells, len(xs), len(ys), (pxs, pxe), (pys, pye),
                  split_x, split_y, tiles)
