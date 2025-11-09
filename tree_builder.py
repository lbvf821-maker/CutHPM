"""
Cutting Tree Builder - построение иерархического дерева резов с последовательностью и проверкой конфликтов

ВАЖНО: Эта часть реализует требования пользователя:
1. Очередность резов с учетом конфликтов
2. Промежуточные заготовки (sub-blocks)
3. Иерархическая структура: Блок → Заготовка → Деталь
"""
from typing import List, Dict, Optional, Tuple
import guillotine3d
from guillotine3d import CutPattern, CutDirection


class CutNode:
    """Узел дерева резов"""

    def __init__(
        self,
        node_id: int,
        seq: int,
        node_type: str,  # "block", "sub-block", "cut", "item"
        cut_dir: Optional[str] = None,
        cut_pos: Optional[float] = None,
        dimensions: Tuple[float, float, float] = (0, 0, 0),
        origin: Tuple[float, float, float] = (0, 0, 0),
        item_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        depth: int = 0
    ):
        self.node_id = node_id
        self.seq = seq
        self.node_type = node_type
        self.cut_dir = cut_dir
        self.cut_pos = cut_pos
        self.dimensions = dimensions  # (L, W, H)
        self.origin = origin  # (x, y, z)
        self.item_id = item_id
        self.parent_id = parent_id
        self.depth = depth
        self.children: List[CutNode] = []

    def volume(self):
        """Объем узла"""
        return self.dimensions[0] * self.dimensions[1] * self.dimensions[2]

    def to_dict(self):
        """Конвертировать в словарь для JSON"""
        return {
            "node_id": self.node_id,
            "seq": self.seq,
            "type": self.node_type,
            "cut_dir": self.cut_dir,
            "cut_pos": self.cut_pos,
            "dimensions": {
                "L": self.dimensions[0],
                "W": self.dimensions[1],
                "H": self.dimensions[2]
            },
            "origin": {
                "x": self.origin[0],
                "y": self.origin[1],
                "z": self.origin[2]
            },
            "volume": self.volume(),
            "item_id": self.item_id,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "children": [child.to_dict() for child in self.children]
        }


class CuttingTree:
    """
    Дерево резов с проверкой конфликтов и отслеживанием последовательности.

    Основные возможности:
    - Построение иерархического дерева из CutPattern
    - Нумерация резов по порядку выполнения
    - Отслеживание промежуточных заготовок (sub-blocks)
    - Проверка конфликтов между резами
    """

    def __init__(self, pattern: CutPattern, bin_dimensions: Tuple[float, float, float], kerf: float = 4.0):
        self.pattern = pattern
        self.bin_dimensions = bin_dimensions
        self.kerf = kerf
        self.root: Optional[CutNode] = None
        self.nodes: List[CutNode] = []
        self.sequence_counter = 0
        self.node_id_counter = 0

        # Построить дерево
        self._build_tree()

    def _get_next_seq(self) -> int:
        """Получить следующий номер последовательности"""
        self.sequence_counter += 1
        return self.sequence_counter

    def _get_next_node_id(self) -> int:
        """Получить следующий ID узла"""
        self.node_id_counter += 1
        return self.node_id_counter

    def _build_tree(self):
        """Построить дерево резов из паттерна"""
        if not self.pattern:
            return

        # Корневой узел - весь блок
        self.root = CutNode(
            node_id=self._get_next_node_id(),
            seq=self._get_next_seq(),
            node_type="block",
            dimensions=self.bin_dimensions,
            origin=(0, 0, 0),
            depth=0
        )
        self.nodes.append(self.root)

        # Рекурсивно обходим дерево паттернов
        self._traverse_pattern(
            pattern=self.pattern,
            parent_node=self.root,
            origin=(0, 0, 0),
            depth=1
        )

    def _traverse_pattern(
        self,
        pattern: CutPattern,
        parent_node: CutNode,
        origin: Tuple[float, float, float],
        depth: int
    ):
        """
        Рекурсивный обход дерева паттернов.

        Логика:
        - Если узел - деталь (NONE cut) → создать item node
        - Если узел - рез → создать cut node + 2 sub-block nodes для левой/правой части
        """
        if pattern.cut_dir == CutDirection.NONE:
            # Это деталь (конечный узел)
            item_node = CutNode(
                node_id=self._get_next_node_id(),
                seq=self._get_next_seq(),
                node_type="item",
                dimensions=(pattern.length, pattern.width, pattern.height),
                origin=origin,
                item_id=pattern.item_id,
                parent_id=parent_node.node_id,
                depth=depth
            )
            parent_node.children.append(item_node)
            self.nodes.append(item_node)
            return

        # Это рез - создаем узел реза
        cut_node = CutNode(
            node_id=self._get_next_node_id(),
            seq=self._get_next_seq(),
            node_type="cut",
            cut_dir=pattern.cut_dir.name,
            cut_pos=pattern.cut_pos,
            dimensions=(pattern.length, pattern.width, pattern.height),
            origin=origin,
            parent_id=parent_node.node_id,
            depth=depth
        )
        parent_node.children.append(cut_node)
        self.nodes.append(cut_node)

        # Создаем sub-blocks для левой и правой части реза
        if pattern.left_pattern:
            # Вычисляем размеры и origin для левой части
            left_dims, left_origin = self._calculate_subblock_geometry(
                pattern, pattern.left_pattern, "left", origin
            )

            left_subblock = CutNode(
                node_id=self._get_next_node_id(),
                seq=self._get_next_seq(),
                node_type="sub-block",
                dimensions=left_dims,
                origin=left_origin,
                parent_id=cut_node.node_id,
                depth=depth + 1
            )
            cut_node.children.append(left_subblock)
            self.nodes.append(left_subblock)

            # Рекурсивно обрабатываем левую часть
            self._traverse_pattern(pattern.left_pattern, left_subblock, left_origin, depth + 2)

        if pattern.right_pattern:
            # Вычисляем размеры и origin для правой части
            right_dims, right_origin = self._calculate_subblock_geometry(
                pattern, pattern.right_pattern, "right", origin
            )

            right_subblock = CutNode(
                node_id=self._get_next_node_id(),
                seq=self._get_next_seq(),
                node_type="sub-block",
                dimensions=right_dims,
                origin=right_origin,
                parent_id=cut_node.node_id,
                depth=depth + 1
            )
            cut_node.children.append(right_subblock)
            self.nodes.append(right_subblock)

            # Рекурсивно обрабатываем правую часть
            self._traverse_pattern(pattern.right_pattern, right_subblock, right_origin, depth + 2)

    def _calculate_subblock_geometry(
        self,
        parent_pattern: CutPattern,
        child_pattern: CutPattern,
        side: str,  # "left" or "right"
        parent_origin: Tuple[float, float, float]
    ) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Вычислить геометрию sub-block после реза.

        Возвращает: (dimensions, origin)
        """
        L, W, H = parent_pattern.length, parent_pattern.width, parent_pattern.height
        x0, y0, z0 = parent_origin
        cut_pos = parent_pattern.cut_pos
        cut_dir = parent_pattern.cut_dir

        # Размеры child паттерна
        child_L = child_pattern.length
        child_W = child_pattern.width
        child_H = child_pattern.height

        if side == "left":
            # Левая часть (до реза)
            if cut_dir == CutDirection.V:  # Vertical - по длине (X)
                origin = (x0, y0, z0)
            elif cut_dir == CutDirection.D:  # Depth - по ширине (Y)
                origin = (x0, y0, z0)
            elif cut_dir == CutDirection.H:  # Horizontal - по высоте (Z)
                origin = (x0, y0, z0)
            else:
                origin = parent_origin
        else:  # right
            # Правая часть (после реза)
            if cut_dir == CutDirection.V:  # Vertical - по длине (X)
                origin = (x0 + cut_pos + self.kerf, y0, z0)
            elif cut_dir == CutDirection.D:  # Depth - по ширине (Y)
                origin = (x0, y0 + cut_pos + self.kerf, z0)
            elif cut_dir == CutDirection.H:  # Horizontal - по высоте (Z)
                origin = (x0, y0, z0 + cut_pos + self.kerf)
            else:
                origin = parent_origin

        return (child_L, child_W, child_H), origin

    def check_conflicts(self) -> List[Dict]:
        """
        Проверка конфликтов между резами.

        Конфликт = когда два реза на разных уровнях пересекаются в пространстве.

        Возвращает список конфликтов.
        """
        conflicts = []

        # Получаем все узлы резов
        cut_nodes = [node for node in self.nodes if node.node_type == "cut"]

        # Проверяем каждую пару резов
        for i, cut1 in enumerate(cut_nodes):
            for cut2 in cut_nodes[i + 1:]:
                if self._cuts_intersect(cut1, cut2):
                    conflicts.append({
                        "cut1_id": cut1.node_id,
                        "cut1_seq": cut1.seq,
                        "cut2_id": cut2.node_id,
                        "cut2_seq": cut2.seq,
                        "description": f"Рез #{cut1.seq} ({cut1.cut_dir}) пересекается с резом #{cut2.seq} ({cut2.cut_dir})"
                    })

        return conflicts

    def _cuts_intersect(self, cut1: CutNode, cut2: CutNode) -> bool:
        """
        Проверить, пересекаются ли два реза.

        Два реза НЕ пересекаются если:
        - Один является потомком другого (это нормально)
        - Их bounding boxes не пересекаются

        Примечание: Это упрощенная проверка. В реальной гильотинной резке
        конфликты возникают редко, т.к. каждый рез делит блок на непересекающиеся части.
        """
        # Проверяем родство
        if self._is_ancestor(cut1, cut2) or self._is_ancestor(cut2, cut1):
            return False

        # Проверяем пересечение bounding boxes
        x1_min, y1_min, z1_min = cut1.origin
        x1_max = x1_min + cut1.dimensions[0]
        y1_max = y1_min + cut1.dimensions[1]
        z1_max = z1_min + cut1.dimensions[2]

        x2_min, y2_min, z2_min = cut2.origin
        x2_max = x2_min + cut2.dimensions[0]
        y2_max = y2_min + cut2.dimensions[1]
        z2_max = z2_min + cut2.dimensions[2]

        # Проверка непересечения по каждой оси
        if x1_max <= x2_min or x2_max <= x1_min:
            return False
        if y1_max <= y2_min or y2_max <= y1_min:
            return False
        if z1_max <= z2_min or z2_max <= z1_min:
            return False

        # Если bounding boxes пересекаются, это потенциальный конфликт
        return True

    def _is_ancestor(self, potential_ancestor: CutNode, node: CutNode) -> bool:
        """Проверить, является ли potential_ancestor предком node"""
        current = node
        while current.parent_id is not None:
            if current.parent_id == potential_ancestor.node_id:
                return True
            # Найти родителя
            parent = next((n for n in self.nodes if n.node_id == current.parent_id), None)
            if not parent:
                break
            current = parent
        return False

    def get_cutting_sequence(self) -> List[Dict]:
        """
        Получить последовательность резов в порядке выполнения.

        Возвращает список операций (резы + промежуточные заготовки).
        """
        # Сортируем узлы по seq
        sorted_nodes = sorted(self.nodes, key=lambda n: n.seq)

        sequence = []
        for node in sorted_nodes:
            if node.node_type == "block":
                sequence.append({
                    "seq": node.seq,
                    "operation": "START",
                    "description": f"Исходный блок: {node.dimensions[0]}×{node.dimensions[1]}×{node.dimensions[2]} мм",
                    "node": node.to_dict()
                })
            elif node.node_type == "cut":
                sequence.append({
                    "seq": node.seq,
                    "operation": "CUT",
                    "description": f"Рез {node.cut_dir} на позиции {node.cut_pos:.1f} мм",
                    "node": node.to_dict()
                })
            elif node.node_type == "sub-block":
                sequence.append({
                    "seq": node.seq,
                    "operation": "SUB-BLOCK",
                    "description": f"Заготовка: {node.dimensions[0]:.0f}×{node.dimensions[1]:.0f}×{node.dimensions[2]:.0f} мм",
                    "node": node.to_dict()
                })
            elif node.node_type == "item":
                sequence.append({
                    "seq": node.seq,
                    "operation": "ITEM",
                    "description": f"Деталь #{node.item_id}: {node.dimensions[0]:.0f}×{node.dimensions[1]:.0f}×{node.dimensions[2]:.0f} мм",
                    "node": node.to_dict()
                })

        return sequence

    def to_dict(self) -> Dict:
        """Полное представление дерева в виде словаря"""
        return {
            "root": self.root.to_dict() if self.root else None,
            "total_nodes": len(self.nodes),
            "total_cuts": len([n for n in self.nodes if n.node_type == "cut"]),
            "total_items": len([n for n in self.nodes if n.node_type == "item"]),
            "total_subblocks": len([n for n in self.nodes if n.node_type == "sub-block"]),
            "max_depth": max([n.depth for n in self.nodes]) if self.nodes else 0,
            "sequence": self.get_cutting_sequence(),
            "conflicts": self.check_conflicts()
        }


def build_cutting_tree(
    pattern: CutPattern,
    bin_dimensions: Tuple[float, float, float],
    kerf: float = 4.0
) -> CuttingTree:
    """
    Построить дерево резов из паттерна.

    Args:
        pattern: Результат оптимизации (CutPattern)
        bin_dimensions: Размеры блока (L, W, H)
        kerf: Ширина пропила

    Returns:
        CuttingTree с полной информацией о последовательности и конфликтах
    """
    return CuttingTree(pattern, bin_dimensions, kerf)
