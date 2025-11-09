# -*- coding: utf-8 -*-
"""
Simple Tight Packing Algorithm
Вместо перебора размеров, вычисляем минимальный размер блока для всех деталей
"""

import guillotine3d
from typing import List, Tuple, Dict
import time


class SimpleTightPacking:
    """
    Простой алгоритм плотной упаковки

    Стратегия:
    1. Вычислить минимальные размеры блока для размещения всех деталей
    2. Использовать эти размеры как базу
    3. Постепенно увеличивать размеры пока не поместятся все детали
    """

    def __init__(self, bin_size: guillotine3d.Bin, items: List[guillotine3d.Item],
                 kerf: float = 4.0, allow_rotations: bool = True):
        self.bin = bin_size
        self.items = items
        self.kerf = kerf
        self.allow_rotations = allow_rotations

    def solve(self) -> Tuple[guillotine3d.CutPattern, Dict]:
        """
        Решение методом постепенного увеличения блока
        """
        pass
        pass
        pass
        pass
        safe_print(f"Items: {len(self.items)} types, {sum(item.quantity for item in self.items)} total")
        pass
        pass
        start_time = time.time()

        # Вычислить минимальный объем всех деталей
        total_volume = sum(item.length * item.width * item.height * item.quantity
                          for item in self.items)

        pass
        pass
        # Попробуем разные размеры блока, начиная с малых
        best_pattern = None
        best_stats = None
        best_item_count = 0

        # Стратегия: пробуем блоки увеличивающихся размеров
        # Начинаем с 1/4, 1/3, 1/2, 2/3, 3/4, 1/1 от основного блока
        size_fractions = [
            (0.25, 0.25, 0.5),
            (0.33, 0.33, 0.5),
            (0.5, 0.5, 0.5),
            (0.5, 0.5, 0.67),
            (0.5, 0.5, 1.0),
            (0.67, 0.67, 0.67),
            (0.67, 0.67, 1.0),
            (0.75, 0.75, 0.75),
            (0.75, 0.75, 1.0),
            (1.0, 0.5, 0.5),
            (1.0, 0.67, 0.67),
            (1.0, 0.75, 0.75),
            (1.0, 1.0, 0.5),
            (1.0, 1.0, 0.67),
            (1.0, 1.0, 1.0),
        ]

        for i, (l_frac, w_frac, h_frac) in enumerate(size_fractions):
            block_l = self.bin.length * l_frac
            block_w = self.bin.width * w_frac
            block_h = self.bin.height * h_frac

            safe_print(f"\n[{i+1}/{len(size_fractions)}] Trying {block_l:.0f}x{block_w:.0f}x{block_h:.0f}...")

            test_bin = guillotine3d.Bin(length=block_l, width=block_w, height=block_h)

            optimizer = guillotine3d.Guillotine3DCutter(
                bin_size=test_bin,
                items=self.items,
                kerf=self.kerf,
                allow_rotations=self.allow_rotations
            )

            pattern, stats = optimizer.solve()

            item_count = sum(stats['item_counts'].values())
            pass
            if item_count > best_item_count:
                best_item_count = item_count
                best_pattern = pattern
                best_stats = stats
                pass
            # Если разместили все детали - успех!
            total_requested = sum(item.quantity for item in self.items)
            if item_count == total_requested:
                pass
                break

        computation_time = time.time() - start_time

        if best_stats:
            best_stats['computation_time'] = computation_time

        pass
        pass
        pass
        pass
        if best_stats:
            pass
            pass
        pass
        return best_pattern, best_stats if best_stats else {}
