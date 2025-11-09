# -*- coding: utf-8 -*-
"""
AlmaCam Two-Level Optimization Algorithm
Reverse-engineered from AlmaCam PDF screenshots

Two-level approach:
1. Level 1: Group items and calculate optimal sub-blocks (заготовки)
2. Level 2: Place sub-blocks in main block using guillotine cuts

This solves the problem where DP3UK only places 7/23 items by creating
intermediate sub-blocks that pack items efficiently.
"""

import guillotine3d
from typing import List, Tuple, Dict, Optional
import time
from dataclasses import dataclass


@dataclass
class SubBlock:
    """Represents a sub-block (заготовка) containing items"""
    length: float
    width: float
    height: float
    items: List[Tuple[guillotine3d.Item, Tuple[float, float, float]]]  # (item, orientation)
    value: float
    pattern: Optional[guillotine3d.CutPattern] = None


class AlmaCamTwoLevel:
    """
    Two-Level Guillotine Optimization (AlmaCam approach)

    Algorithm:
    1. Group items by size similarity
    2. For each group, find optimal sub-block dimensions
    3. Pack items into sub-blocks using DP
    4. Pack sub-blocks into main block using guillotine cuts
    """

    def __init__(self, bin_size: guillotine3d.Bin, items: List[guillotine3d.Item],
                 kerf: float = 4.0, allow_rotations: bool = True):
        self.bin = bin_size
        self.items = items
        self.kerf = kerf
        self.allow_rotations = allow_rotations
        self.min_part_size = 15.0

        # Results
        self.sub_blocks: List[SubBlock] = []
        self.final_pattern: Optional[guillotine3d.CutPattern] = None

    def solve(self) -> Tuple[guillotine3d.CutPattern, Dict]:
        """
        Solve using two-level optimization

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

        # LEVEL 1: Create optimal sub-blocks from items
        pass
        self.sub_blocks = self._create_sub_blocks()

        safe_print(f"\nCreated {len(self.sub_blocks)} sub-blocks:")
        for i, sb in enumerate(self.sub_blocks):
            item_count = len(sb.items)
            # Count items by ID
            sb_item_counts = {}
            for item, _ in sb.items:
                sb_item_counts[item.id] = sb_item_counts.get(item.id, 0) + 1
            items_str = ", ".join([f"{iid}:{cnt}" for iid, cnt in sorted(sb_item_counts.items())])
            safe_print(f"  Sub-block {i+1}: {sb.length:.0f}x{sb.width:.0f}x{sb.height:.0f} with {item_count} items ({items_str}), value={sb.value:.0f}")

        # LEVEL 2: Pack sub-blocks into main block
        safe_print(f"\n[LEVEL 2] Packing {len(self.sub_blocks)} sub-blocks into main block...")
        self.final_pattern = self._pack_sub_blocks_into_block()

        computation_time = time.time() - start_time

        # Calculate statistics
        stats = self._calculate_stats(self.final_pattern, computation_time)

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
        return self.final_pattern, stats

    def _create_sub_blocks(self) -> List[SubBlock]:
        """
        LEVEL 1: Create optimal sub-blocks from items

        NEW Strategy (similar to AlmaCam):
        - Don't pre-group items - let DP create sub-blocks naturally
        - Create ONE large sub-block that fits all items (or as many as possible)
        - If items don't all fit, create multiple sub-blocks iteratively
        """
        sub_blocks = []

        # Convert items to list with quantities
        remaining_items = self._convert_to_unique_items(self.items)

        iteration = 1
        while remaining_items and any(item.quantity > 0 for item in remaining_items):
            pass
            # Calculate total volume needed
            total_volume = sum(item.length * item.width * item.height * item.quantity
                             for item in remaining_items)

            # Try to create a sub-block that fits into main bin
            # Start with dimensions that utilize bin efficiently
            sub_block = self._create_smart_sub_block(remaining_items)

            if sub_block and sub_block.items:
                sub_blocks.append(sub_block)

                # Update remaining quantities
                packed_counts = {}
                for packed_item, _ in sub_block.items:
                    packed_counts[packed_item.id] = packed_counts.get(packed_item.id, 0) + 1

                # Decrease quantities
                for item in remaining_items:
                    if item.id in packed_counts:
                        item.quantity -= packed_counts[item.id]

                # Remove items with quantity = 0
                remaining_items = [item for item in remaining_items if item.quantity > 0]

                safe_print(f"    -> Packed {len(sub_block.items)} items, {sum(item.quantity for item in remaining_items)} remaining")
                iteration += 1
            else:
                # Can't create more sub-blocks
                pass
                break

            # Safety: max 10 sub-blocks (temp: limit to 1 for testing)
            if iteration > 1:
                break

        return sub_blocks

    def _create_smart_sub_block(self, items: List[guillotine3d.Item]) -> Optional[SubBlock]:
        """
        Create a smart sub-block that fits maximum items

        Strategy:
        1. Try different sub-block dimensions based on bin size
        2. Use fractions of bin dimensions (1/1, 1/2, 1/3, etc.)
        3. Choose the one that packs most items efficiently
        """
        best_sub_block = None
        best_item_count = 0

        # Try different fractions of bin dimensions
        for l_frac in [1.0, 0.5, 0.33, 0.67]:
            for w_frac in [1.0, 0.5, 0.33, 0.67]:
                for h_frac in [1.0, 0.5, 0.33, 0.67]:
                    sb_length = self.bin.length * l_frac
                    sb_width = self.bin.width * w_frac
                    sb_height = self.bin.height * h_frac

                    if sb_length < self.min_part_size or sb_width < self.min_part_size or sb_height < self.min_part_size:
                        continue

                    # Try to pack items
                    sub_bin = guillotine3d.Bin(length=sb_length, width=sb_width, height=sb_height)

                    optimizer = guillotine3d.Guillotine3DCutter(
                        bin_size=sub_bin,
                        items=items,
                        kerf=self.kerf,
                        allow_rotations=self.allow_rotations
                    )

                    pattern, stats = optimizer.solve()

                    if pattern:
                        item_count = sum(stats['item_counts'].values())

                        if item_count > best_item_count:
                            best_item_count = item_count

                            # Extract packed items
                            packed_items = []
                            source_items = []
                            for item in items:
                                for _ in range(item.quantity):
                                    source_items.append(item)

                            self._extract_items_from_pattern(pattern, source_items, packed_items)

                            best_sub_block = SubBlock(
                                length=sb_length,
                                width=sb_width,
                                height=sb_height,
                                items=packed_items,
                                value=pattern.value,
                                pattern=pattern
                            )

        return best_sub_block

    def _create_sub_block_for_items(self, items: List[guillotine3d.Item]) -> Optional[SubBlock]:
        """
        Create a sub-block that efficiently packs given items

        Strategy:
        1. Start with largest item dimensions
        2. Try to pack as many items as possible
        3. Find minimal bounding box
        """
        if not items:
            return None

        # Start with largest item as seed
        seed = items[0]
        seed_vol = seed.length * seed.width * seed.height

        # Try different sub-block sizes based on seed item
        # We'll test multiples of the seed dimensions
        best_sub_block = None
        best_efficiency = 0

        for l_mult in [1, 2, 3]:
            for w_mult in [1, 2, 3]:
                for h_mult in [1, 2]:
                    # Calculate sub-block dimensions
                    sb_length = min(seed.length * l_mult + self.kerf * (l_mult - 1), self.bin.length)
                    sb_width = min(seed.width * w_mult + self.kerf * (w_mult - 1), self.bin.width)
                    sb_height = min(seed.height * h_mult + self.kerf * (h_mult - 1), self.bin.height)

                    # Try to pack items into this sub-block using DP
                    sub_bin = guillotine3d.Bin(length=sb_length, width=sb_width, height=sb_height)

                    # Convert items to unique items for DP
                    unique_items = self._convert_to_unique_items(items[:20])  # Limit to first 20 items for speed

                    optimizer = guillotine3d.Guillotine3DCutter(
                        bin_size=sub_bin,
                        items=unique_items,
                        kerf=self.kerf,
                        allow_rotations=self.allow_rotations
                    )

                    pattern, stats = optimizer.solve()

                    if pattern and stats['utilization'] > best_efficiency:
                        best_efficiency = stats['utilization']

                        # Extract packed items
                        packed_items = []
                        self._extract_items_from_pattern(pattern, items, packed_items)

                        best_sub_block = SubBlock(
                            length=sb_length,
                            width=sb_width,
                            height=sb_height,
                            items=packed_items,
                            value=pattern.value,
                            pattern=pattern
                        )

        return best_sub_block

    def _convert_to_unique_items(self, items: List[guillotine3d.Item]) -> List[guillotine3d.Item]:
        """Convert list of items to unique items with quantities - just return a copy"""
        unique_items = []
        for item in items:
            unique_items.append(
                guillotine3d.Item(
                    id=item.id,
                    length=item.length,
                    width=item.width,
                    height=item.height,
                    quantity=item.quantity
                )
            )
        return unique_items

    def _extract_items_from_pattern(self, pattern: guillotine3d.CutPattern,
                                     source_items: List[guillotine3d.Item],
                                     result: List[Tuple[guillotine3d.Item, Tuple[float, float, float]]]):
        """Recursively extract all items from cutting pattern"""
        if not pattern:
            return

        if pattern.item_id is not None:
            # Find corresponding item
            for item in source_items:
                if item.id == pattern.item_id:
                    result.append((item, (pattern.length, pattern.width, pattern.height)))
                    break

        if pattern.left_pattern:
            self._extract_items_from_pattern(pattern.left_pattern, source_items, result)
        if pattern.right_pattern:
            self._extract_items_from_pattern(pattern.right_pattern, source_items, result)

    def _pack_sub_blocks_into_block(self) -> Optional[guillotine3d.CutPattern]:
        """
        LEVEL 2: Pack sub-blocks into main block using guillotine cuts

        Treat sub-blocks as large "items" and use DP to pack them
        """
        if not self.sub_blocks:
            return None

        # Convert sub-blocks to items
        sub_block_items = []
        for i, sb in enumerate(self.sub_blocks):
            sub_block_items.append(
                guillotine3d.Item(
                    id=1000 + i,  # Use high IDs to distinguish from regular items
                    length=sb.length,
                    width=sb.width,
                    height=sb.height,
                    quantity=1
                )
            )

        # Use DP to pack sub-blocks
        optimizer = guillotine3d.Guillotine3DCutter(
            bin_size=self.bin,
            items=sub_block_items,
            kerf=self.kerf,
            allow_rotations=False  # Sub-blocks already optimized
        )

        pattern, stats = optimizer.solve()

        # Replace sub-block IDs with actual item patterns
        # This creates the hierarchical structure like AlmaCam
        final_pattern = self._merge_sub_block_patterns(pattern)

        return final_pattern

    def _merge_sub_block_patterns(self, pattern: Optional[guillotine3d.CutPattern]) -> Optional[guillotine3d.CutPattern]:
        """
        Merge sub-block patterns into main pattern
        Creates hierarchical structure: Block -> Sub-blocks -> Items
        """
        if not pattern:
            return None

        # If this is a sub-block item, replace with actual sub-block pattern
        if pattern.item_id is not None and pattern.item_id >= 1000:
            sub_block_idx = pattern.item_id - 1000
            if sub_block_idx < len(self.sub_blocks):
                return self.sub_blocks[sub_block_idx].pattern

        # Recursively merge children
        left = self._merge_sub_block_patterns(pattern.left_pattern) if pattern.left_pattern else None
        right = self._merge_sub_block_patterns(pattern.right_pattern) if pattern.right_pattern else None

        return guillotine3d.CutPattern(
            length=pattern.length,
            width=pattern.width,
            height=pattern.height,
            value=pattern.value,
            cut_dir=pattern.cut_dir,
            cut_pos=pattern.cut_pos,
            item_id=pattern.item_id,
            left_pattern=left,
            right_pattern=right
        )

    def _calculate_stats(self, pattern: Optional[guillotine3d.CutPattern], computation_time: float) -> Dict:
        """Calculate statistics from cutting pattern"""
        if not pattern:
            return {
                'filled_volume': 0,
                'utilization': 0,
                'waste': self.bin.length * self.bin.width * self.bin.height,
                'item_counts': {},
                'computation_time': computation_time
            }

        # Count items from sub-blocks
        item_counts = {}
        for sb in self.sub_blocks:
            for item, _ in sb.items:
                item_counts[item.id] = item_counts.get(item.id, 0) + 1

        total_volume = self.bin.length * self.bin.width * self.bin.height
        filled_volume = sum(sb.value for sb in self.sub_blocks)

        return {
            'filled_volume': filled_volume,
            'utilization': (filled_volume / total_volume * 100) if total_volume > 0 else 0,
            'waste': total_volume - filled_volume,
            'item_counts': item_counts,
            'computation_time': computation_time,
            'sub_blocks_count': len(self.sub_blocks)
        }
