# -*- coding: utf-8 -*-
"""
Maximal Spaces Algorithm для 3D упаковки БЕЗ гильотинных ограничений
Этот алгоритм может размещать больше деталей, но НЕ гарантирует гильотинную резку
"""

import guillotine3d
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import time


@dataclass
class Space:
    """Свободное прост

ранство"""
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float

    def volume(self) -> float:
        return self.length * self.width * self.height

    def fits(self, item_l: float, item_w: float, item_h: float) -> bool:
        return item_l <= self.length and item_w <= self.width and item_h <= self.height


@dataclass
class PlacedItem:
    """Размещенная деталь"""
    item_id: int
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float


class MaximalSpacesPacking:
    """
    Maximal Spaces Algorithm

    Алгоритм БЕЗ гильотинных ограничений!
    Размещает детали жадно, отслеживая свободные пространства
    """

    def __init__(self, bin_size: guillotine3d.Bin, items: List[guillotine3d.Item],
                 kerf: float = 4.0, allow_rotations: bool = True):
        self.bin = bin_size
        self.items = items
        self.kerf = kerf
        self.allow_rotations = allow_rotations

        # Результаты
        self.placed_items: List[PlacedItem] = []
        self.spaces: List[Space] = [Space(0, 0, 0, bin_size.length, bin_size.width, bin_size.height)]

    def solve(self) -> Tuple[Optional[guillotine3d.CutPattern], Dict]:
        """
        Решение методом Maximal Spaces
        """
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        start_time = time.time()

        # Создать список всех деталей для размещения
        items_to_place = []
        for item in self.items:
            for _ in range(item.quantity):
                items_to_place.append(item)

        # Сортировать по объему (largest first)
        items_to_place.sort(key=lambda x: x.length * x.width * x.height, reverse=True)

        pass

        # Разместить каждую деталь
        for idx, item in enumerate(items_to_place):
            placed = self._place_item(item)

            if placed:
                if (idx + 1) % 5 == 0:
                    pass
            else:
                pass

        computation_time = time.time() - start_time

        # Статистика
        stats = self._calculate_stats(computation_time)

        pass
        pass
        pass
        pass
        pass
        pass
        pass
        # Преобразовать в CutPattern (хотя это НЕ гильотинный раскрой!)
        # Для совместимости создаем простой pattern
        pattern = None  # Maximal Spaces не создает guillotine pattern

        return pattern, stats

    def _place_item(self, item: guillotine3d.Item) -> bool:
        """
        Разместить деталь в первом подходящем свободном пространстве
        """
        # Попробовать все ориентации
        orientations = self._get_orientations(item)

        for orientation in orientations:
            l, w, h = orientation

            # Найти подходящее пространство
            for space_idx, space in enumerate(self.spaces):
                if space.fits(l, w, h):
                    # Разместить деталь
                    placed = PlacedItem(
                        item_id=item.id,
                        x=space.x,
                        y=space.y,
                        z=space.z,
                        length=l,
                        width=w,
                        height=h
                    )

                    self.placed_items.append(placed)

                    # Удалить использованное пространство
                    self.spaces.pop(space_idx)

                    # Создать новые свободные пространства вокруг размещенной детали
                    self._create_new_spaces(placed, space)

                    return True

        return False

    def _create_new_spaces(self, placed: PlacedItem, original_space: Space):
        """
        Создать новые свободные пространства после размещения детали
        """
        # 3 новых пространства по 3 осям

        # Пространство справа (по X)
        if placed.x + placed.length + self.kerf < original_space.x + original_space.length:
            self.spaces.append(Space(
                x=placed.x + placed.length + self.kerf,
                y=original_space.y,
                z=original_space.z,
                length=original_space.x + original_space.length - (placed.x + placed.length + self.kerf),
                width=original_space.width,
                height=original_space.height
            ))

        # Пространство сзади (по Y)
        if placed.y + placed.width + self.kerf < original_space.y + original_space.width:
            self.spaces.append(Space(
                x=original_space.x,
                y=placed.y + placed.width + self.kerf,
                z=original_space.z,
                length=original_space.length,
                width=original_space.y + original_space.width - (placed.y + placed.width + self.kerf),
                height=original_space.height
            ))

        # Пространство сверху (по Z)
        if placed.z + placed.height + self.kerf < original_space.z + original_space.height:
            self.spaces.append(Space(
                x=original_space.x,
                y=original_space.y,
                z=placed.z + placed.height + self.kerf,
                length=original_space.length,
                width=original_space.width,
                height=original_space.z + original_space.height - (placed.z + placed.height + self.kerf)
            ))

        # Сортировать пространства по объему (largest first)
        self.spaces.sort(key=lambda s: s.volume(), reverse=True)

    def _get_orientations(self, item: guillotine3d.Item) -> List[Tuple[float, float, float]]:
        """Получить все возможные ориентации"""
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

    def _calculate_stats(self, computation_time: float) -> Dict:
        """Вычислить статистику"""
        item_counts = {}
        total_volume = 0

        for placed in self.placed_items:
            item_counts[placed.item_id] = item_counts.get(placed.item_id, 0) + 1
            total_volume += placed.length * placed.width * placed.height

        bin_volume = self.bin.length * self.bin.width * self.bin.height

        return {
            'filled_volume': total_volume,
            'utilization': (total_volume / bin_volume * 100) if bin_volume > 0 else 0,
            'waste': bin_volume - total_volume,
            'item_counts': item_counts,
            'computation_time': computation_time,
            'placed_items': self.placed_items
        }
