# -*- coding: utf-8 -*-
"""
3D k-staged guillotine cutting (DP + Reduced Raster Points)
Adapted for production use with collision detection

Based on: DPS3UK, Scheithauer-Terno RRP, de Queiroz k-staged patterns
Adapted by: Claude for AlmaCum-style production cutting
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Iterable, Literal
import math
import time


Axis = Literal["X", "Y", "Z"]


@dataclass(frozen=True)
class Item:
    """Item type with dimensions in mm"""
    id: str
    x: int
    y: int
    z: int
    quantity: int = 1
    value: float = 0.0
    allow_rotation: bool = True

    def orientations(self) -> Iterable[Tuple[int, int, int]]:
        """All allowed orientations without duplicates"""
        base = (self.x, self.y, self.z)
        if not self.allow_rotation:
            yield base
            return

        perms = [
            (base[0], base[1], base[2]),
            (base[0], base[2], base[1]),
            (base[1], base[0], base[2]),
            (base[1], base[2], base[0]),
            (base[2], base[0], base[1]),
            (base[2], base[1], base[0]),
        ]
        seen = set()
        for a, b, c in perms:
            if (a, b, c) not in seen:
                seen.add((a, b, c))
                yield (a, b, c)

    @property
    def vol_value(self) -> float:
        return self.value if self.value > 0 else float(self.x * self.y * self.z)


@dataclass(frozen=True)
class Stock:
    """Mother block (mm) and tech parameters"""
    Lx: int
    Ly: int
    Lz: int
    kerf: int = 4
    min_slice: int = 10
    stage_order: Tuple[Axis, ...] = ("Z", "X", "Y")


def _nx(L: int, a: int, kerf: int) -> int:
    """How many pieces of size a fit along length L with kerf"""
    # n*a + (n-1)*kerf <= L  =>  n <= floor((L + kerf) / (a + kerf))
    return max(0, (L + kerf) // (a + kerf))


def _gcd_list(vals: List[int]) -> int:
    vals = [v for v in vals if v > 0]
    if not vals:
        return 1
    g = vals[0]
    for v in vals[1:]:
        g = math.gcd(g, v)
    return max(1, g)


def rrp_points(L: int, sizes: List[int], kerf: int, min_slice: int) -> List[int]:
    """
    Reduced Raster Points (RRP):
    - Multiples of gcd(sizes) and kerf
    - Partial sums of typical sizes
    - Filter points too close to edges
    - Keep only up to half length (symmetry)
    """
    cand = set()

    # 1) Multiples of GCD and kerf
    base = max(_gcd_list(sizes), kerf)
    for t in range(base, L, base):
        cand.add(t)

    # 2) Partial sums of characteristic sizes
    uniq = sorted(set(sizes))
    uniq = [u for u in uniq if u + min_slice <= L]
    prefix = [0]
    limit = min(12, len(uniq))
    for u in uniq[:limit]:
        prefix += [p + u for p in prefix]
    for p in prefix:
        if min_slice <= p <= L - min_slice:
            cand.add(p)

    pts = sorted(cand)
    # Remove points too close to edge and merging (< kerf)
    filtered = []
    last = -10**9
    for p in pts:
        if p < min_slice or L - p < min_slice:
            continue
        if p - last >= kerf:
            filtered.append(p)
            last = p

    # Keep only up to half (symmetric cuts)
    half = [p for p in filtered if p <= L // 2]
    return half or filtered


@dataclass
class PlanNode:
    """
    Slicing tree node.
    type: 'cut' | 'grid' | 'empty'
    """
    type: str
    size: Tuple[int, int, int]
    axis: Optional[Axis] = None
    at: Optional[int] = None
    kerf: Optional[int] = None
    left: Optional["PlanNode"] = None
    right: Optional["PlanNode"] = None
    item_id: Optional[str] = None
    item_size: Optional[Tuple[int, int, int]] = None
    counts: Optional[Tuple[int, int, int]] = None
    value: float = 0.0


@dataclass
class Plan:
    root: PlanNode
    counts_by_item: Dict[str, int]
    packed_value: float
    utilization: float


class DPGuillotineSolver:
    """DP + RRP guillotine solver with production safety"""

    def __init__(self, stock: Stock, items: List[Item]) -> None:
        self.stock = stock

        # Expand all orientations
        self.item_variants: List[Tuple[str, Tuple[int, int, int], float]] = []
        for it in items:
            base_val = it.vol_value
            for (a, b, c) in it.orientations():
                self.item_variants.append((it.id, (a, b, c), base_val))

        # Size lists per axis for RRP
        self.sizes_x = [sz[0] for _, sz, _ in self.item_variants]
        self.sizes_y = [sz[1] for _, sz, _ in self.item_variants]
        self.sizes_z = [sz[2] for _, sz, _ in self.item_variants]

        self._cache: Dict[Tuple[int, int, int, int], Tuple[float, PlanNode]] = {}

    def _grid_best(self, Lx: int, Ly: int, Lz: int) -> Tuple[float, Optional[PlanNode]]:
        """Grid macro-action: fill node with uniform 3D grid"""
        best_val = 0.0
        best_node: Optional[PlanNode] = None
        k = self.stock.kerf

        for item_id, (a, b, c), val in self.item_variants:
            nx = _nx(Lx, a, k)
            ny = _nx(Ly, b, k)
            nz = _nx(Lz, c, k)
            if nx == 0 or ny == 0 or nz == 0:
                continue

            total = nx * ny * nz
            grid_val = total * val
            if grid_val > best_val:
                best_val = grid_val
                best_node = PlanNode(
                    type="grid",
                    size=(Lx, Ly, Lz),
                    item_id=item_id,
                    item_size=(a, b, c),
                    counts=(nx, ny, nz),
                    kerf=k,
                    value=grid_val,
                )
        return best_val, best_node

    def _dp(self, Lx: int, Ly: int, Lz: int, stage_idx: int) -> Tuple[float, PlanNode]:
        """DP core: returns (best value, node)"""
        if Lx <= 0 or Ly <= 0 or Lz <= 0:
            return 0.0, PlanNode(type="empty", size=(max(0, Lx), max(0, Ly), max(0, Lz)))

        key = (Lx, Ly, Lz, stage_idx % len(self.stock.stage_order))
        if key in self._cache:
            return self._cache[key]

        axis: Axis = self.stock.stage_order[stage_idx % len(self.stock.stage_order)]
        k = self.stock.kerf
        m = self.stock.min_slice

        # 1) Grid macro-action
        best_val, best_node = self._grid_best(Lx, Ly, Lz)

        # 2) Cut along allowed axis (sum of children)
        if axis == "X":
            points = rrp_points(Lx, self.sizes_x, k, m)
            for x in points:
                L1 = x
                L2 = Lx - x - k
                if L1 < m or L2 < m:
                    continue
                v1, n1 = self._dp(L1, Ly, Lz, stage_idx + 1)
                v2, n2 = self._dp(L2, Ly, Lz, stage_idx + 1)
                if v1 + v2 > best_val:
                    best_val = v1 + v2
                    best_node = PlanNode(
                        type="cut",
                        size=(Lx, Ly, Lz),
                        axis="X",
                        at=x,
                        kerf=k,
                        left=n1,
                        right=n2,
                        value=best_val,
                    )

        elif axis == "Y":
            points = rrp_points(Ly, self.sizes_y, k, m)
            for y in points:
                L1 = y
                L2 = Ly - y - k
                if L1 < m or L2 < m:
                    continue
                v1, n1 = self._dp(Lx, L1, Lz, stage_idx + 1)
                v2, n2 = self._dp(Lx, L2, Lz, stage_idx + 1)
                if v1 + v2 > best_val:
                    best_val = v1 + v2
                    best_node = PlanNode(
                        type="cut",
                        size=(Lx, Ly, Lz),
                        axis="Y",
                        at=y,
                        kerf=k,
                        left=n1,
                        right=n2,
                        value=best_val,
                    )

        else:  # axis == "Z"
            points = rrp_points(Lz, self.sizes_z, k, m)
            for z in points:
                L1 = z
                L2 = Lz - z - k
                if L1 < m or L2 < m:
                    continue
                v1, n1 = self._dp(Lx, Ly, L1, stage_idx + 1)
                v2, n2 = self._dp(Lx, Ly, L2, stage_idx + 1)
                if v1 + v2 > best_val:
                    best_val = v1 + v2
                    best_node = PlanNode(
                        type="cut",
                        size=(Lx, Ly, Lz),
                        axis="Z",
                        at=z,
                        kerf=k,
                        left=n1,
                        right=n2,
                        value=best_val,
                    )

        if best_node is None:
            best_node = PlanNode(type="empty", size=(Lx, Ly, Lz), value=0.0)

        self._cache[key] = (best_val, best_node)
        return best_val, best_node

    def _count_items(self, node: PlanNode, agg: Dict[str, int]) -> None:
        if node.type == "grid" and node.item_id and node.counts:
            nx, ny, nz = node.counts
            agg[node.item_id] = agg.get(node.item_id, 0) + nx * ny * nz
        if node.left:
            self._count_items(node.left, agg)
        if node.right:
            self._count_items(node.right, agg)

    def solve(self) -> Plan:
        v, root = self._dp(self.stock.Lx, self.stock.Ly, self.stock.Lz, 0)
        counts: Dict[str, int] = {}
        self._count_items(root, counts)

        total_vol = float(self.stock.Lx * self.stock.Ly * self.stock.Lz)
        util = min(1.0, v / total_vol) if total_vol > 0 else 0.0
        return Plan(root=root, counts_by_item=counts, packed_value=v, utilization=util)


# ============================================================================
# Adapter for existing API: converts Plan to placed items with positions
# ============================================================================

@dataclass
class PlacedItem:
    """Placed item with collision detection"""
    item_id: str
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float

    def overlaps(self, other: 'PlacedItem', kerf: float = 0) -> bool:
        """Check overlap with another item accounting for kerf"""
        return not (
            self.x + self.length + kerf <= other.x or
            other.x + other.length + kerf <= self.x or
            self.y + self.width + kerf <= other.y or
            other.y + other.width + kerf <= self.y or
            self.z + self.height + kerf <= other.z or
            other.z + other.height + kerf <= self.z
        )


def expand_plan_to_items(plan: Plan, kerf: float) -> List[PlacedItem]:
    """
    Convert Plan tree to flat list of PlacedItem with absolute positions.
    CRITICAL: Grid nodes expand to n_x × n_y × n_z individual items.
    """
    items = []

    def rec(node: PlanNode, ox: float, oy: float, oz: float) -> None:
        """Recursive traversal with offset tracking"""
        if node.type == "grid" and node.item_id and node.item_size and node.counts:
            ax, ay, az = node.item_size
            nx, ny, nz = node.counts

            # Generate grid of items
            for iz in range(nz):
                for ix in range(nx):
                    for iy in range(ny):
                        x = ox + ix * (ax + kerf)
                        y = oy + iy * (ay + kerf)
                        z = oz + iz * (az + kerf)
                        items.append(PlacedItem(
                            item_id=node.item_id,
                            x=x, y=y, z=z,
                            length=ax, width=ay, height=az
                        ))

        elif node.type == "cut":
            if node.axis == "X" and node.at is not None:
                if node.left:
                    rec(node.left, ox, oy, oz)
                if node.right:
                    rec(node.right, ox + node.at + kerf, oy, oz)
            elif node.axis == "Y" and node.at is not None:
                if node.left:
                    rec(node.left, ox, oy, oz)
                if node.right:
                    rec(node.right, ox, oy + node.at + kerf, oz)
            elif node.axis == "Z" and node.at is not None:
                if node.left:
                    rec(node.left, ox, oy, oz)
                if node.right:
                    rec(node.right, ox, oy, oz + node.at + kerf)

    rec(plan.root, 0, 0, 0)
    return items


def check_collisions(items: List[PlacedItem], kerf: float) -> int:
    """CRITICAL production safety check"""
    collisions = 0
    n = len(items)
    for i in range(n):
        for j in range(i+1, n):
            if items[i].overlaps(items[j], kerf):
                collisions += 1
    return collisions
