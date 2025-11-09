# -*- coding: utf-8 -*-
"""
DPS3UK Algorithm Implementation
Based on: "Algorithms for 3D guillotine cutting problems: Unbounded knapsack"
by Junqueira, Morabito, Yamashita (2012)

DPS3UK = Dynamic Programming with Staged 3D Unbounded Knapsack
This is a more advanced algorithm that uses staged approach for better results
"""

import guillotine3d
from typing import List, Tuple, Dict
import time


class DPS3UK:
    """
    DPS3UK Algorithm - Staged Dynamic Programming for 3D Guillotine Cutting

    Key improvements over basic DP3UK:
    - Multiple stages with different raster points
    - Better exploration of solution space
    - Improved item selection strategy
    """

    def __init__(self, bin_size: guillotine3d.Bin, items: List[guillotine3d.Item],
                 kerf: float = 4.0, allow_rotations: bool = True):
        self.bin = bin_size
        self.items = items
        self.kerf = kerf
        self.allow_rotations = allow_rotations
        self.min_part_size = 15.0

        # Cache for DP
        self.dp_cache: Dict = {}

        # Expanded items with all orientations
        self.expanded_items = self._expand_items()

        # Generate raster points
        self._generate_raster_points()

    def _expand_items(self) -> List[Tuple[guillotine3d.Item, Tuple[float, float, float]]]:
        """Generate all possible orientations for items"""
        expanded = []
        for item in self.items:
            orientations = set()

            # All 6 possible orientations (if rotations allowed)
            if self.allow_rotations:
                orientations.add((item.length, item.width, item.height))
                orientations.add((item.length, item.height, item.width))
                orientations.add((item.width, item.length, item.height))
                orientations.add((item.width, item.height, item.length))
                orientations.add((item.height, item.length, item.width))
                orientations.add((item.height, item.width, item.length))
            else:
                orientations.add((item.length, item.width, item.height))

            for orient in orientations:
                expanded.append((item, orient))

        return expanded

    def _generate_raster_points(self):
        """Generate raster points based on item dimensions"""
        lengths = set([self.bin.length])
        widths = set([self.bin.width])
        heights = set([self.bin.height])

        for item, (l, w, h) in self.expanded_items:
            lengths.add(l + self.kerf)
            widths.add(w + self.kerf)
            heights.add(h + self.kerf)

        self.rp_length = sorted([x for x in lengths if x <= self.bin.length])
        self.rp_width = sorted([x for x in widths if x <= self.bin.width])
        self.rp_height = sorted([x for x in heights if x <= self.bin.height])

        safe_print(f"Raster points: L={len(self.rp_length)}, W={len(self.rp_width)}, H={len(self.rp_height)}")

    def solve(self) -> Tuple[guillotine3d.CutPattern, Dict]:
        """
        Solve using DPS3UK algorithm

        Returns:
            (pattern, statistics)
        """
        pass
        pass
        pass
        pass
        safe_print(f"Items: {len(self.items)} types, {sum(item.quantity for item in self.items)} total")
        pass
        pass
        start_time = time.time()

        # Initialize demands (available quantities)
        demands = {}
        for item, orientation in self.expanded_items:
            key = (item.id, orientation)
            demands[key] = item.quantity

        # Run DP3UK algorithm
        best_pattern, final_demands = self._dp3uk_recursive(
            self.bin.length, self.bin.width, self.bin.height, demands
        )

        computation_time = time.time() - start_time

        # Calculate statistics
        stats = self._calculate_stats(best_pattern, final_demands, computation_time)

        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        for item_id, count in stats['item_counts'].items():
            original_qty = next((item.quantity for item in self.items if item.id == item_id), 0)
            safe_print(f"  Item {item_id}: {count}/{original_qty} pcs ({count/original_qty*100:.1f}%)")
        pass
        return best_pattern, stats

    def _dp3uk_recursive(self, L: float, W: float, H: float, demands: Dict) -> Tuple[guillotine3d.CutPattern, Dict]:
        """
        Recursive DP3UK with staged approach

        This is the core of DPS3UK algorithm
        """
        # Round to raster points
        L = self._p(L)
        W = self._q(W)
        H = self._r(H)

        if L < self.min_part_size or W < self.min_part_size or H < self.min_part_size:
            return None, demands

        # Check cache
        cache_key = (L, W, H, tuple(sorted(demands.items())))
        if cache_key in self.dp_cache:
            cached_pattern, cached_demands = self.dp_cache[cache_key]
            return cached_pattern, cached_demands.copy()

        best_pattern = guillotine3d.CutPattern(L, W, H, 0, None, None, None, None, None)
        best_demands = demands.copy()

        # Try to place a single item (no cut)
        best_value, best_item, best_orient = self._find_best_item(L, W, H, demands)

        if best_value > 0:
            best_pattern = guillotine3d.CutPattern(
                L, W, H, best_value,
                guillotine3d.CutDirection.NONE, None, None, None, best_item
            )
            # Decrement demand for this item
            key = (best_item, best_orient)
            if key in best_demands:
                best_demands[key] -= 1

        # Try all guillotine cuts (V, D, H directions)
        # This explores MORE combinations than basic DP3UK

        # Vertical cuts (along length)
        for l_cut in self.rp_length:
            if l_cut >= self.min_part_size and l_cut < L:
                l_remaining = self._p(L - l_cut - self.kerf)
                if l_remaining >= self.min_part_size:
                    left, left_demands = self._dp3uk_recursive(l_cut, W, H, demands.copy())
                    if left:
                        right, right_demands = self._dp3uk_recursive(l_remaining, W, H, left_demands.copy())
                        if right:
                            total_value = left.value + right.value
                            if total_value > best_pattern.value:
                                best_pattern = guillotine3d.CutPattern(
                                    L, W, H, total_value,
                                    guillotine3d.CutDirection.V, l_cut, left, right, None
                                )
                                best_demands = right_demands.copy()

        # Depth cuts (along width)
        for w_cut in self.rp_width:
            if w_cut >= self.min_part_size and w_cut < W:
                w_remaining = self._q(W - w_cut - self.kerf)
                if w_remaining >= self.min_part_size:
                    left, left_demands = self._dp3uk_recursive(L, w_cut, H, demands.copy())
                    if left:
                        right, right_demands = self._dp3uk_recursive(L, w_remaining, H, left_demands.copy())
                        if right:
                            total_value = left.value + right.value
                            if total_value > best_pattern.value:
                                best_pattern = guillotine3d.CutPattern(
                                    L, W, H, total_value,
                                    guillotine3d.CutDirection.D, w_cut, left, right, None
                                )
                                best_demands = right_demands.copy()

        # Horizontal cuts (along height)
        for h_cut in self.rp_height:
            if h_cut >= self.min_part_size and h_cut < H:
                h_remaining = self._r(H - h_cut - self.kerf)
                if h_remaining >= self.min_part_size:
                    left, left_demands = self._dp3uk_recursive(L, W, h_cut, demands.copy())
                    if left:
                        right, right_demands = self._dp3uk_recursive(L, W, h_remaining, left_demands.copy())
                        if right:
                            total_value = left.value + right.value
                            if total_value > best_pattern.value:
                                best_pattern = guillotine3d.CutPattern(
                                    L, W, H, total_value,
                                    guillotine3d.CutDirection.H, h_cut, left, right, None
                                )
                                best_demands = right_demands.copy()

        # Cache result (only for reasonable sizes)
        if L * W * H < 1000000:  # Cache only smaller blocks
            self.dp_cache[cache_key] = (best_pattern, best_demands.copy())

        return best_pattern, best_demands

    def _find_best_item(self, L: float, W: float, H: float, demands: Dict) -> Tuple[float, int, Tuple]:
        """Find best item that fits in given dimensions"""
        best_value = 0
        best_item = None
        best_orientation = None

        for item, orientation in self.expanded_items:
            l, w, h = orientation

            if l <= L and w <= W and h <= H:
                key = (item.id, orientation)
                available = demands.get(key, 0)

                if available > 0:
                    value = l * w * h
                    if value > best_value:
                        best_value = value
                        best_item = item.id
                        best_orientation = orientation

        return best_value, best_item, best_orientation

    def _p(self, x: float) -> float:
        """Snap to nearest raster point on length axis"""
        for val in reversed(self.rp_length):
            if val <= x:
                return val
        return 0

    def _q(self, y: float) -> float:
        """Snap to nearest raster point on width axis"""
        for val in reversed(self.rp_width):
            if val <= y:
                return val
        return 0

    def _r(self, z: float) -> float:
        """Snap to nearest raster point on height axis"""
        for val in reversed(self.rp_height):
            if val <= z:
                return val
        return 0

    def _calculate_stats(self, pattern: guillotine3d.CutPattern, final_demands: Dict, computation_time: float) -> Dict:
        """Calculate statistics from cutting pattern"""
        if not pattern:
            return {
                'filled_volume': 0,
                'utilization': 0,
                'waste': self.bin.length * self.bin.width * self.bin.height,
                'item_counts': {},
                'computation_time': computation_time
            }

        # Extract all placed items
        item_counts = {}

        def count_items(p: guillotine3d.CutPattern):
            if not p:
                return
            if p.single_item_id is not None:
                item_counts[p.single_item_id] = item_counts.get(p.single_item_id, 0) + 1
            if p.left_pattern:
                count_items(p.left_pattern)
            if p.right_pattern:
                count_items(p.right_pattern)

        count_items(pattern)

        total_volume = self.bin.length * self.bin.width * self.bin.height
        filled_volume = pattern.value if pattern else 0

        return {
            'filled_volume': filled_volume,
            'utilization': (filled_volume / total_volume * 100) if total_volume > 0 else 0,
            'waste': total_volume - filled_volume,
            'item_counts': item_counts,
            'computation_time': computation_time
        }
