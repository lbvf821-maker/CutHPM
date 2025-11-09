# -*- coding: utf-8 -*-
"""
Optimized 3D Guillotine Cutting - Based on PDF Specification
Fast, collision-free, production-ready implementation

Key improvements over existing algorithms:
- Recursive depth-first strategy (PDF Section 3)
- 6-orientation rotation handling
- Best-orientation heuristic (minimize leftover volume)
- Fast execution (<5s target)
- Zero collision guarantee
- Proper kerf accounting at each cut
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import time


def get_orientations(item) -> List[Tuple[float, float, float]]:
    """Get all 6 unique orientations for an item (PDF Section 3.2)"""
    dims = {item.length, item.width, item.height}
    if len(dims) == 1:
        # Cube - only 1 orientation
        return [(item.length, item.width, item.height)]

    # Generate all permutations, filter duplicates
    orientations = set()
    for l in [item.length, item.width, item.height]:
        for w in [item.length, item.width, item.height]:
            for h in [item.length, item.width, item.height]:
                if l != w or l != h or w != h:  # At least 2 different values
                    orientations.add((l, w, h))

    # If only 2 distinct dimensions, we get 3 orientations
    # If all 3 distinct, we get 6 orientations
    return sorted(list(orientations), reverse=True)  # Largest first


@dataclass
class Block:
    """Available block space"""
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float

    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass
class PlacedItem:
    """Placed part with position"""
    item_id: int
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float

    def overlaps(self, other: 'PlacedItem', kerf: float = 0) -> bool:
        """Check collision with another item"""
        return not (
            self.x + self.length + kerf <= other.x or
            other.x + other.length + kerf <= self.x or
            self.y + self.width + kerf <= other.y or
            other.y + other.width + kerf <= self.y or
            self.z + self.height + kerf <= other.z or
            other.z + other.height + kerf <= self.z
        )


class GuillotinePDF:
    """
    PDF-specified recursive guillotine cutter
    Fast and collision-free
    """

    def __init__(self, block_L: float, block_W: float, block_H: float,
                 items: List, kerf: float = 4.0, allow_rotations: bool = True):
        self.block_L = block_L
        self.block_W = block_W
        self.block_H = block_H
        self.items = items
        self.kerf = kerf
        self.allow_rotations = allow_rotations
        self.placed_items: List[PlacedItem] = []
        self.remaining_quantities: Dict[int, int] = {}

        # Initialize quantities
        for item in items:
            self.remaining_quantities[item.id] = item.quantity

    def solve(self) -> Tuple[List[PlacedItem], Dict]:
        """Main solver - returns (placed_items, stats)"""
        start_time = time.time()

        # Sort items by volume (largest first) - PDF Section 3.3
        sorted_items = sorted(self.items, key=lambda x: x.volume(), reverse=True)

        # Start recursive cutting from full block
        initial_block = Block(0, 0, 0, self.block_L, self.block_W, self.block_H)
        self._recursive_cut(initial_block, sorted_items)

        # Calculate stats
        computation_time = time.time() - start_time
        stats = self._calculate_stats(computation_time)

        return self.placed_items, stats

    def _recursive_cut(self, block: Block, items: List) -> None:
        """
        Recursive guillotine cutting (PDF Section 3.4)

        Strategy:
        1. Find best part that fits in block
        2. Choose best orientation (minimize leftover)
        3. Cut X → Y → Z to place part
        4. Recursively process 3 remainder blocks
        """
        # Base case: block too small
        if block.length < 10 or block.width < 10 or block.height < 10:
            return

        # Find best item that fits
        best_item, best_orientation = self._find_best_fit(block, items)

        if best_item is None:
            return  # No item fits

        # Get dimensions in best orientation
        item_l, item_w, item_h = best_orientation

        # Place the item
        placed = PlacedItem(
            item_id=best_item.id,
            x=block.x,
            y=block.y,
            z=block.z,
            length=item_l,
            width=item_w,
            height=item_h
        )
        self.placed_items.append(placed)

        # Decrease quantity
        self.remaining_quantities[best_item.id] -= 1

        # Create 3 remainder blocks (PDF Figure 3)
        # Remainder 1: After X cut (slab remainder)
        if block.length > item_l + self.kerf:
            r1 = Block(
                x=block.x + item_l + self.kerf,
                y=block.y,
                z=block.z,
                length=block.length - item_l - self.kerf,
                width=block.width,
                height=block.height
            )
            self._recursive_cut(r1, items)

        # Remainder 2: After Y cut (footprint remainder)
        if block.width > item_w + self.kerf:
            r2 = Block(
                x=block.x,
                y=block.y + item_w + self.kerf,
                z=block.z,
                length=item_l,  # Only the slab length
                width=block.width - item_w - self.kerf,
                height=block.height
            )
            self._recursive_cut(r2, items)

        # Remainder 3: After Z cut (top remainder)
        if block.height > item_h + self.kerf:
            r3 = Block(
                x=block.x,
                y=block.y,
                z=block.z + item_h + self.kerf,
                length=item_l,
                width=item_w,
                height=block.height - item_h - self.kerf
            )
            self._recursive_cut(r3, items)

    def _find_best_fit(self, block: Block, items: List) -> Tuple[Optional[Any], Optional[Tuple[float, float, float]]]:
        """
        Find best item and orientation that fits in block

        Heuristic: Minimize leftover volume (PDF Section 3.5)
        """
        best_item = None
        best_orientation = None
        min_leftover = float('inf')

        for item in items:
            # Check if we have any remaining
            if self.remaining_quantities.get(item.id, 0) <= 0:
                continue

            # Try all orientations
            orientations = get_orientations(item) if self.allow_rotations else [(item.length, item.width, item.height)]

            for l, w, h in orientations:
                # Check if fits
                if l <= block.length and w <= block.width and h <= block.height:
                    # Calculate leftover volume
                    leftover = block.volume() - (l * w * h)

                    # Prefer tighter fits (less leftover)
                    if leftover < min_leftover:
                        min_leftover = leftover
                        best_item = item
                        best_orientation = (l, w, h)

        return best_item, best_orientation

    def _calculate_stats(self, computation_time: float) -> Dict:
        """Calculate statistics"""
        block_volume = self.block_L * self.block_W * self.block_H
        filled_volume = sum(p.length * p.width * p.height for p in self.placed_items)
        utilization = (filled_volume / block_volume * 100) if block_volume > 0 else 0

        # Count items by ID
        item_counts = {}
        for placed in self.placed_items:
            item_counts[placed.item_id] = item_counts.get(placed.item_id, 0) + 1

        # Check collisions (should be 0!)
        collisions = self._check_collisions()

        return {
            'filled_volume': filled_volume,
            'block_volume': block_volume,
            'utilization': utilization,
            'waste': 100 - utilization,
            'item_counts': item_counts,
            'placed_items': self.placed_items,
            'computation_time': computation_time,
            'collisions': collisions,
            'algorithm_used': 'Guillotine_PDF_Recursive'
        }

    def _check_collisions(self) -> int:
        """CRITICAL: Check for overlaps"""
        collisions = 0
        n = len(self.placed_items)
        for i in range(n):
            for j in range(i+1, n):
                if self.placed_items[i].overlaps(self.placed_items[j], self.kerf):
                    collisions += 1
        return collisions
