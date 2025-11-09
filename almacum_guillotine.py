# -*- coding: utf-8 -*-
"""
Правильный 3D Guillotine алгоритм по принципу AlmaCum
Гарантирует отсутствие пересечений деталей
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import time


@dataclass
class Item3D:
    """Деталь для размещения"""
    id: int
    length: float  # L
    width: float   # W
    height: float  # H
    quantity: int

    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass
class PlacedItem:
    """Размещённая деталь с позицией"""
    item_id: int
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float

    def overlaps(self, other: 'PlacedItem', kerf: float = 0) -> bool:
        """Проверка пересечения с другой деталью с учётом kerf"""
        return not (
            self.x + self.length + kerf <= other.x or
            other.x + other.length + kerf <= self.x or
            self.y + self.width + kerf <= other.y or
            other.y + other.width + kerf <= self.y or
            self.z + self.height + kerf <= other.z or
            other.z + other.height + kerf <= self.z
        )


@dataclass
class CutNode:
    """Узел дерева резов (Cutting Tree)"""
    operation: str  # 'START', 'CUT_Z', 'CUT_Y', 'CUT_X', 'ITEM', 'LOSS'
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float
    cut_position: Optional[float] = None  # Позиция реза
    item_id: Optional[int] = None
    children: List['CutNode'] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


class AlmaCumGuillotine:
    """
    3D Guillotine раскрой по принципу AlmaCum:
    1. Группировка деталей по высоте Z
    2. Создание виртуальных заготовок (sub-blocks)
    3. Гильотинные резы: Z → Y → X
    4. Гарантия отсутствия пересечений
    """

    def __init__(self, block_L: float, block_W: float, block_H: float,
                 items: List[Item3D], kerf: float = 4.0):
        self.block_L = block_L
        self.block_W = block_W
        self.block_H = block_H
        self.items = items
        self.kerf = kerf
        self.placed_items: List[PlacedItem] = []
        self.cutting_tree: Optional[CutNode] = None

    def solve(self) -> Tuple[List[PlacedItem], CutNode, Dict]:
        """Главный метод оптимизации"""
        start_time = time.time()

        # Шаг 1: Группировка деталей по высоте Z
        z_groups = self._group_by_height()

        # Шаг 2: Создание виртуальных заготовок для каждой группы
        sub_blocks = self._create_sub_blocks(z_groups)

        # Шаг 3: Размещение заготовок в материнском блоке с гильотинными резами
        self.cutting_tree = CutNode(
            operation='START',
            x=0, y=0, z=0,
            length=self.block_L,
            width=self.block_W,
            height=self.block_H
        )

        placed_blocks = self._place_sub_blocks_guillotine(sub_blocks)

        # Шаг 4: Размещение деталей внутри каждой заготовки
        for block in placed_blocks:
            self._place_items_in_block(block)

        # Шаг 5: Проверка на пересечения (критично для производства!)
        collisions = self._check_collisions()
        if collisions > 0:
            pass  # Не выводим print, но collisions будет в stats

        # Статистика
        computation_time = time.time() - start_time
        stats = self._calculate_stats(computation_time, collisions)

        return self.placed_items, self.cutting_tree, stats

    def _group_by_height(self) -> Dict[float, List[Item3D]]:
        """
        Группировка деталей по высоте Z (как в AlmaCum)
        Детали с одинаковой высотой группируются в стопки
        """
        groups = {}
        for item in self.items:
            for _ in range(item.quantity):
                if item.height not in groups:
                    groups[item.height] = []
                groups[item.height].append(item)
        return groups

    def _create_sub_blocks(self, z_groups: Dict[float, List[Item3D]]) -> List[Dict]:
        """
        Создание виртуальных заготовок (sub-blocks)
        Каждая заготовка - это компактный прямоугольник с деталями одной высоты
        УЛУЧШЕНО: создаём несколько sub-blocks если детали не влезают в один
        """
        sub_blocks = []

        for z_height, items_list in sorted(z_groups.items(), reverse=True):
            # Группируем детали одинаковой высоты
            # Используем простую эвристику: сортируем по убыванию площади
            sorted_items = sorted(items_list,
                                key=lambda x: x.length * x.width,
                                reverse=True)

            # УЛУЧШЕНИЕ: создаём несколько sub-blocks пока есть неразмещённые детали
            remaining_items = sorted_items[:]
            while remaining_items:
                block = self._pack_2d_items(remaining_items, z_height)
                if not block or not block['items']:
                    # Не удалось разместить ни одной детали - прекращаем
                    break

                sub_blocks.append(block)

                # Удаляем размещённые детали из списка
                for placed_item in block['items']:
                    if placed_item in remaining_items:
                        remaining_items.remove(placed_item)

        return sub_blocks

    def _pack_2d_items(self, items_list: List[Item3D], z_height: float) -> Optional[Dict]:
        """
        2D упаковка деталей одинаковой высоты в прямоугольник
        Возвращает виртуальную заготовку с размещёнными деталями
        Использует улучшенный алгоритм с проверкой влезания
        """
        if not items_list:
            return None

        # Пробуем разместить детали рядами
        rows = []
        current_row = {'items': [], 'width': 0, 'max_length': 0}
        placed_items = []

        for item in items_list:
            # С учётом kerf
            item_l = item.length + self.kerf
            item_w = item.width + self.kerf

            # Проверяем влезет ли деталь вообще в блок
            if item_l > self.block_L or item_w > self.block_W:
                continue  # Деталь слишком большая, пропускаем

            # Проверяем влезет ли в текущий ряд
            if current_row['width'] + item_w <= self.block_W:
                # Проверяем не превысим ли длину блока с этой деталью
                new_length = max(current_row['max_length'], item_l)
                current_length = sum(row['max_length'] for row in rows)

                if current_length + new_length <= self.block_L:
                    current_row['items'].append(item)
                    current_row['width'] += item_w
                    current_row['max_length'] = new_length
                    placed_items.append(item)
                else:
                    # Не влезает по длине - продолжаем со следующим рядом
                    break
            else:
                # Начинаем новый ряд
                if current_row['items']:
                    rows.append(current_row)

                # Проверяем влезет ли новый ряд
                current_length = sum(row['max_length'] for row in rows)
                if current_length + item_l > self.block_L:
                    break  # Не влезает

                current_row = {
                    'items': [item],
                    'width': item_w,
                    'max_length': item_l
                }
                placed_items.append(item)

        if current_row['items']:
            rows.append(current_row)

        # Если ничего не разместили - возвращаем None
        if not rows:
            return None

        # Вычисляем размеры заготовки
        total_length = sum(row['max_length'] for row in rows)
        max_width = max(row['width'] for row in rows)

        return {
            'length': total_length,
            'width': max_width,
            'height': z_height,
            'rows': rows,
            'items': placed_items
        }

    def _place_sub_blocks_guillotine(self, sub_blocks: List[Dict]) -> List[Dict]:
        """
        Размещение виртуальных заготовок с гильотинными резами
        Иерархия: Z → Y → X
        """
        placed_blocks = []
        current_z = 0

        # Сортируем заготовки по высоте (от большей к меньшей)
        sorted_blocks = sorted(sub_blocks, key=lambda b: b['height'], reverse=True)

        for block in sorted_blocks:
            block_h = block['height'] + self.kerf

            # Проверка влезет ли по высоте
            if current_z + block_h > self.block_H:
                break  # Не влезает

            # Размещаем заготовку
            block['position'] = {'x': 0, 'y': 0, 'z': current_z}
            placed_blocks.append(block)

            # Добавляем рез по Z в cutting tree
            cut_node = CutNode(
                operation='CUT_Z',
                x=0, y=0, z=current_z,
                length=self.block_L,
                width=self.block_W,
                height=block_h,
                cut_position=current_z + block_h
            )
            self.cutting_tree.children.append(cut_node)

            current_z += block_h

        # Остаток - это отход
        if current_z < self.block_H:
            loss_node = CutNode(
                operation='LOSS',
                x=0, y=0, z=current_z,
                length=self.block_L,
                width=self.block_W,
                height=self.block_H - current_z
            )
            self.cutting_tree.children.append(loss_node)

        return placed_blocks

    def _place_items_in_block(self, block: Dict):
        """
        Размещение деталей внутри виртуальной заготовки
        """
        pos = block['position']
        current_x = pos['x']

        for row in block['rows']:
            current_y = pos['y']

            for item in row['items']:
                # Размещаем деталь
                placed = PlacedItem(
                    item_id=item.id,
                    x=current_x,
                    y=current_y,
                    z=pos['z'],
                    length=item.length,
                    width=item.width,
                    height=item.height
                )
                self.placed_items.append(placed)

                # Следующая позиция по Y (с учётом kerf)
                current_y += item.width + self.kerf

            # Следующая позиция по X
            current_x += row['max_length']

    def _check_collisions(self) -> int:
        """
        КРИТИЧЕСКАЯ проверка: нет ли пересечений деталей
        Для производства это абсолютно недопустимо!
        """
        collisions = 0
        n = len(self.placed_items)

        for i in range(n):
            for j in range(i+1, n):
                if self.placed_items[i].overlaps(self.placed_items[j], self.kerf):
                    collisions += 1

        return collisions

    def _calculate_stats(self, computation_time: float, collisions: int) -> Dict:
        """Расчёт статистики"""
        block_volume = self.block_L * self.block_W * self.block_H
        filled_volume = sum(p.length * p.width * p.height for p in self.placed_items)

        utilization = (filled_volume / block_volume * 100) if block_volume > 0 else 0
        waste = 100 - utilization

        # Подсчёт деталей по ID
        item_counts = {}
        for placed in self.placed_items:
            item_counts[placed.item_id] = item_counts.get(placed.item_id, 0) + 1

        return {
            'filled_volume': filled_volume,
            'block_volume': block_volume,
            'utilization': utilization,
            'waste': waste,
            'item_counts': item_counts,
            'placed_items': self.placed_items,
            'computation_time': computation_time,
            'collisions': collisions,  # КРИТИЧНО: должно быть 0!
            'algorithm_used': 'AlmaCum_Guillotine'
        }
