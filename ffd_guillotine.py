# -*- coding: utf-8 -*-
"""
First-Fit Decreasing (FFD) Heuristic for 3D Guillotine Cutting
This is a greedy heuristic that should place more items than basic DP3UK
"""

import guillotine3d
from typing import List, Tuple, Dict, Optional
import time


class FFDGuillotine:
    """
    First-Fit Decreasing heuristic with guillotine constraints

    Algorithm:
    1. Sort items by volume (largest first)
    2. Greedily place items using guillotine cuts
    3. Try all 6 orientations for each item
    4. Recursively subdivide remaining space
    """

    def __init__(self, bin_size: guillotine3d.Bin, items: List[guillotine3d.Item],
                 kerf: float = 4.0, allow_rotations: bool = True):
        self.bin = bin_size
        self.items = items
        self.kerf = kerf
        self.allow_rotations = allow_rotations
        self.min_part_size = 15.0

        # Track placed items
        self.placed_items = []
        self.item_counts = {}

        # Remaining quantities for each item
        self.remaining = {item.id: item.quantity for item in items}

    def solve(self) -> Tuple[guillotine3d.CutPattern, Dict]:
        """
        Solve using FFD heuristic

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

        # Sort items by volume (largest first)
        sorted_items = sorted(self.items, key=lambda x: x.length * x.width * x.height, reverse=True)

        # Create list of all items to place (expanded by quantity)
        items_to_place = []
        for item in sorted_items:
            for _ in range(item.quantity):
                items_to_place.append(item)

        safe_print(f"\nPlacing {len(items_to_place)} items using FFD...")

        # Try to place all items
        pattern = self._pack_items(
            self.bin.length,
            self.bin.width,
            self.bin.height,
            items_to_place,
            0,  # Start from index 0
            "Root"
        )

        computation_time = time.time() - start_time

        # Calculate statistics
        stats = self._calculate_stats(pattern, computation_time)

        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        for item_id, count in sorted(stats['item_counts'].items()):
            original_qty = next((item.quantity for item in self.items if item.id == item_id), 0)
            safe_print(f"  Item {item_id}: {count}/{original_qty} pcs ({count/original_qty*100:.1f}%)")
        pass
        return pattern, stats

    def _pack_items(self, L: float, W: float, H: float, items: List[guillotine3d.Item],
                    start_idx: int, label: str) -> Optional[guillotine3d.CutPattern]:
        """
        Recursively pack items into a block using FFD

        Args:
            L, W, H: Block dimensions
            items: List of items to place
            start_idx: Index to start searching from
            label: Debug label

        Returns:
            CutPattern or None
        """
        if L < self.min_part_size or W < self.min_part_size or H < self.min_part_size:
            return None

        if start_idx >= len(items):
            return None

        # Try to place each remaining item
        for idx in range(start_idx, len(items)):
            item = items[idx]

            # Try all orientations
            orientations = self._get_orientations(item)

            for (l, w, h) in orientations:
                # Check if item fits
                if l <= L and w <= W and h <= H:
                    # Item fits! Place it
                    value = l * w * h

                    # Create new list without this item
                    remaining_items = items[:idx] + items[idx+1:]

                    # Update item count
                    self.item_counts[item.id] = self.item_counts.get(item.id, 0) + 1

                    # Try to place remaining items in the leftover space
                    # We have 3 possible guillotine cuts after placing the item

                    best_pattern = guillotine3d.CutPattern(
                        L, W, H, value,
                        guillotine3d.CutDirection.NONE, None, None, None, item.id
                    )
                    best_total_value = value

                    # Try guillotine cut along length
                    if l + self.kerf < L:
                        remaining_L = L - l - self.kerf
                        if remaining_L >= self.min_part_size:
                            right_pattern = self._pack_items(remaining_L, W, H, remaining_items, 0, f"{label}.R")
                            if right_pattern:
                                total_value = value + right_pattern.value
                                if total_value > best_total_value:
                                    best_pattern = guillotine3d.CutPattern(
                                        L, W, H, total_value,
                                        guillotine3d.CutDirection.V, l,
                                        guillotine3d.CutPattern(l, W, H, value, guillotine3d.CutDirection.NONE, None, None, None, item.id),
                                        right_pattern,
                                        None
                                    )
                                    best_total_value = total_value

                    # Try guillotine cut along width
                    if w + self.kerf < W:
                        remaining_W = W - w - self.kerf
                        if remaining_W >= self.min_part_size:
                            right_pattern = self._pack_items(L, remaining_W, H, remaining_items, 0, f"{label}.D")
                            if right_pattern:
                                total_value = value + right_pattern.value
                                if total_value > best_total_value:
                                    best_pattern = guillotine3d.CutPattern(
                                        L, W, H, total_value,
                                        guillotine3d.CutDirection.D, w,
                                        guillotine3d.CutPattern(L, w, H, value, guillotine3d.CutDirection.NONE, None, None, None, item.id),
                                        right_pattern,
                                        None
                                    )
                                    best_total_value = total_value

                    # Try guillotine cut along height
                    if h + self.kerf < H:
                        remaining_H = H - h - self.kerf
                        if remaining_H >= self.min_part_size:
                            right_pattern = self._pack_items(L, W, remaining_H, remaining_items, 0, f"{label}.H")
                            if right_pattern:
                                total_value = value + right_pattern.value
                                if total_value > best_total_value:
                                    best_pattern = guillotine3d.CutPattern(
                                        L, W, H, total_value,
                                        guillotine3d.CutDirection.H, h,
                                        guillotine3d.CutPattern(L, W, h, value, guillotine3d.CutDirection.NONE, None, None, None, item.id),
                                        right_pattern,
                                        None
                                    )
                                    best_total_value = total_value

                    return best_pattern

        # No item fits
        return None

    def _get_orientations(self, item: guillotine3d.Item) -> List[Tuple[float, float, float]]:
        """Get all possible orientations for an item"""
        if self.allow_rotations:
            return list(set([
                (item.length, item.width, item.height),
                (item.length, item.height, item.width),
                (item.width, item.length, item.height),
                (item.width, item.height, item.length),
                (item.height, item.length, item.width),
                (item.height, item.width, item.length),
            ]))
        else:
            return [(item.length, item.width, item.height)]

    def _calculate_stats(self, pattern: Optional[guillotine3d.CutPattern], computation_time: float) -> Dict:
        """Calculate statistics"""
        if not pattern:
            return {
                'filled_volume': 0,
                'utilization': 0,
                'waste': self.bin.length * self.bin.width * self.bin.height,
                'item_counts': {},
                'computation_time': computation_time
            }

        total_volume = self.bin.length * self.bin.width * self.bin.height
        filled_volume = pattern.value

        return {
            'filled_volume': filled_volume,
            'utilization': (filled_volume / total_volume * 100) if total_volume > 0 else 0,
            'waste': total_volume - filled_volume,
            'item_counts': self.item_counts.copy(),
            'computation_time': computation_time
        }
