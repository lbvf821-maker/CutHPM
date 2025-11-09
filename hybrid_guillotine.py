# -*- coding: utf-8 -*-
"""
Hybrid Algorithm: Maximal Spaces для определения групп + Guillotine для резки

Идея:
1. Использовать Maximal Spaces чтобы понять какие детали могут быть размещены вместе
2. Группировать размещенные детали в "зоны" (sub-blocks)
3. Для каждой зоны создать гильотинный раскрой
4. Объединить зоны в общий раскрой основного блока
"""

import guillotine3d
from maximal_spaces import MaximalSpacesPacking, PlacedItem
from typing import List, Tuple, Dict, Optional
import time


class HybridGuillotinePacking:
    """
    Гибридный алгоритм

    Шаг 1: Maximal Spaces дает нам размещение всех деталей
    Шаг 2: Анализируем размещение и создаем sub-blocks
    Шаг 3: Для каждого sub-block создаем гильотинный раскрой
    Шаг 4: Размещаем sub-blocks в основном блоке с гильотинными разрезами
    """

    def __init__(self, bin_size: guillotine3d.Bin, items: List[guillotine3d.Item],
                 kerf: float = 4.0, allow_rotations: bool = True):
        self.bin = bin_size
        self.items = items
        self.kerf = kerf
        self.allow_rotations = allow_rotations

    def solve(self) -> Tuple[Optional[guillotine3d.CutPattern], Dict]:
        """
        Решение гибридным методом
        """
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        start_time = time.time()

        # ШАГ 1: Использовать Maximal Spaces для размещения
        pass
        ms_packer = MaximalSpacesPacking(self.bin, self.items, self.kerf, self.allow_rotations)
        _, ms_stats = ms_packer.solve()

        placed_items = ms_stats.get('placed_items', [])

        if len(placed_items) < sum(item.quantity for item in self.items):
            pass

        # ШАГ 2: Группировать детали в sub-blocks по координатам
        pass
        sub_blocks = self._group_into_sub_blocks(placed_items)

        pass

        # ШАГ 3: Создать гильотинный раскрой для основного блока
        pass
        pattern = self._create_guillotine_pattern(sub_blocks)

        computation_time = time.time() - start_time

        # Статистика
        stats = {
            'filled_volume': ms_stats['filled_volume'],
            'utilization': ms_stats['utilization'],
            'waste': ms_stats['waste'],
            'item_counts': ms_stats['item_counts'],
            'computation_time': computation_time,
            'sub_blocks_count': len(sub_blocks),
            'placed_items': ms_stats.get('placed_items', [])  # Передать позиции деталей
        }

        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        return pattern, stats

    def _group_into_sub_blocks(self, placed_items: List[PlacedItem]) -> List[Dict]:
        """
        Группировать размещенные детали в sub-blocks

        Простая эвристика: группируем по слоям (по оси Z)
        """
        if not placed_items:
            return []

        # Сортировать по Z-координате
        sorted_items = sorted(placed_items, key=lambda p: p.z)

        # Группировать детали которые находятся на одном уровне Z
        sub_blocks = []
        current_block_items = []
        current_z_level = sorted_items[0].z

        for item in sorted_items:
            # Если деталь на том же уровне (допуск 10mm)
            if abs(item.z - current_z_level) < 10:
                current_block_items.append(item)
            else:
                # Создать sub-block из текущих деталей
                if current_block_items:
                    sub_blocks.append(self._create_sub_block(current_block_items))

                # Начать новый sub-block
                current_block_items = [item]
                current_z_level = item.z

        # Добавить последний sub-block
        if current_block_items:
            sub_blocks.append(self._create_sub_block(current_block_items))

        return sub_blocks

    def _create_sub_block(self, items: List[PlacedItem]) -> Dict:
        """
        Создать sub-block из списка деталей

        Вычислить bounding box
        """
        if not items:
            return None

        min_x = min(item.x for item in items)
        min_y = min(item.y for item in items)
        min_z = min(item.z for item in items)

        max_x = max(item.x + item.length for item in items)
        max_y = max(item.y + item.width for item in items)
        max_z = max(item.z + item.height for item in items)

        return {
            'x': min_x,
            'y': min_y,
            'z': min_z,
            'length': max_x - min_x,
            'width': max_y - min_y,
            'height': max_z - min_z,
            'items': items
        }

    def _create_guillotine_pattern(self, sub_blocks: List[Dict]) -> Optional[guillotine3d.CutPattern]:
        """
        Создать гильотинный раскрой для размещения sub-blocks

        Упрощенная версия: просто создаем вертикальные разрезы по Z
        """
        if not sub_blocks:
            return None

        # Сортировать sub-blocks по Z
        sub_blocks.sort(key=lambda sb: sb['z'])

        # Создать рекурсивный pattern
        return self._create_recursive_pattern(sub_blocks, 0, self.bin.length, self.bin.width, self.bin.height)

    def _create_recursive_pattern(self, sub_blocks: List[Dict], start_z: float,
                                   L: float, W: float, H: float) -> Optional[guillotine3d.CutPattern]:
        """
        Рекурсивно создать pattern для sub-blocks
        """
        if not sub_blocks:
            return None

        if len(sub_blocks) == 1:
            # Один sub-block - создать лист
            sb = sub_blocks[0]
            return guillotine3d.CutPattern(
                length=L,
                width=W,
                height=sb['height'],
                value=sum(item.length * item.width * item.height for item in sb['items']),
                cut_dir=guillotine3d.CutDirection.NONE,
                cut_pos=None,
                item_id=None,  # Множество деталей
                left_pattern=None,
                right_pattern=None
            )

        # Разделить по первому sub-block
        first_sb = sub_blocks[0]
        cut_height = first_sb['height'] + self.kerf

        # Левый pattern - первый sub-block
        left = guillotine3d.CutPattern(
            length=L,
            width=W,
            height=first_sb['height'],
            value=sum(item.length * item.width * item.height for item in first_sb['items']),
            cut_dir=guillotine3d.CutDirection.NONE,
            cut_pos=None,
            item_id=None,
            left_pattern=None,
            right_pattern=None
        )

        # Правый pattern - остальные sub-blocks
        right = self._create_recursive_pattern(
            sub_blocks[1:],
            start_z + cut_height,
            L, W, H - cut_height
        )

        # Объединить
        total_value = first_sb.get('value', 0)
        if right:
            total_value += right.value

        return guillotine3d.CutPattern(
            length=L,
            width=W,
            height=H,
            value=total_value,
            cut_dir=guillotine3d.CutDirection.H,
            cut_pos=cut_height,
            item_id=None,
            left_pattern=left,
            right_pattern=right
        )
