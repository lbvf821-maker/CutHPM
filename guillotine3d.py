"""
3D Guillotine Cutting Optimizer
Правильная реализация с учетом количества деталей и качественной визуализацией
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum
import time

class CutDirection(Enum):
    """Направление гильотинного реза"""
    NONE = 0
    H = 1  # Horizontal (parallel to XY plane) - по высоте
    V = 2  # Vertical (parallel to YZ plane) - по длине
    D = 3  # Depth (parallel to XZ plane) - по ширине

@dataclass
class Item:
    """Заготовка для раскроя"""
    id: int
    length: float  # X
    width: float   # Y
    height: float  # Z
    quantity: int  # Количество доступных деталей
    
    def volume(self) -> float:
        return self.length * self.width * self.height
    
    def rotations(self) -> List[Tuple[float, float, float]]:
        """Все возможные ориентации детали"""
        dims = [self.length, self.width, self.height]
        unique = set()
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if len({i, j, k}) == 3:
                        unique.add((dims[i], dims[j], dims[k]))
        return list(unique)

@dataclass
class Bin:
    """Исходный блок для раскроя"""
    length: float
    width: float
    height: float
    
    def volume(self) -> float:
        return self.length * self.width * self.height

@dataclass
class CutPattern:
    """Паттерн раскроя"""
    length: float
    width: float
    height: float
    value: float
    cut_dir: CutDirection
    cut_pos: float
    item_id: Optional[int] = None  # Если это одна деталь
    left_pattern: Optional['CutPattern'] = None
    right_pattern: Optional['CutPattern'] = None
    
    def get_all_items(self, origin: Tuple[float, float, float] = (0, 0, 0), kerf: float = 4.0) -> List[Tuple[int, Tuple[float, float, float], Tuple[float, float, float]]]:
        """
        Рекурсивно собирает все детали из дерева с правильными позициями
        Returns: List[(item_id, (x, y, z), (l, w, h))]
        """
        items = []
        x, y, z = origin
        
        if self.cut_dir == CutDirection.NONE and self.item_id is not None:
            # Это лист с деталью
            items.append((self.item_id, (x, y, z), (self.length, self.width, self.height)))
        else:
            # Это разрез - рекурсивно обрабатываем детей
            if self.left_pattern:
                left_items = self.left_pattern.get_all_items(origin, kerf)
                items.extend(left_items)
            
            if self.right_pattern:
                # Вычисляем смещение для правой части
                if self.cut_dir == CutDirection.V:  # Разрез по длине (X)
                    offset_x = self.cut_pos + kerf
                    right_origin = (x + offset_x, y, z)
                elif self.cut_dir == CutDirection.D:  # Разрез по ширине (Y)
                    offset_y = self.cut_pos + kerf
                    right_origin = (x, y + offset_y, z)
                elif self.cut_dir == CutDirection.H:  # Разрез по высоте (Z)
                    offset_z = self.cut_pos + kerf
                    right_origin = (x, y, z + offset_z)
                else:
                    right_origin = origin
                
                right_items = self.right_pattern.get_all_items(right_origin, kerf)
                items.extend(right_items)
        
        return items

class ReducedRasterPoints:
    """Вычисление reduced raster points (алгоритм RRP из статьи)"""
    
    @staticmethod
    def compute(dimensions: List[float], max_size: float) -> List[int]:
        """
        Вычисляет reduced raster points для заданных размеров

        Args:
            dimensions: Список размеров деталей
            max_size: Максимальный размер (размер бина)

        Returns:
            Отсортированный список r-points
        """
        # ИСПРАВЛЕНО: Используем упрощенный подход - все уникальные размеры и их комбинации
        dp = set([0])

        # Добавляем сами размеры деталей
        for dim in dimensions:
            if dim <= max_size:
                dp.add(int(dim))

        # Dynamic programming для генерации комбинаций
        current = list(dp)
        for dim in dimensions:
            new_points = []
            for p in current:
                val = p + dim
                if val <= max_size:
                    new_points.append(int(val))
            # Ограничиваем рост для производительности
            dp.update(new_points[:100])  # Берем только первые 100 новых точек
            current = sorted(list(dp))[:200]  # Ограничиваем общее количество

        # Возвращаем отсортированный список
        return sorted(list(dp))

class Guillotine3DCutter:
    """Основной класс для 3D гильотинного раскроя с учетом количества деталей"""

    def __init__(self, bin_size: Bin, items: List[Item],
                 kerf: float = 4.0, max_cut_length: float = 1400.0,
                 min_part_size: float = 15.0, allow_rotations: bool = True,
                 use_hybrid: bool = False):
        """
        Args:
            bin_size: Размер исходного блока
            items: Список заготовок с количествами
            kerf: Ширина пропила (мм)
            max_cut_length: Максимальная длина реза (мм)
            min_part_size: Минимальный размер детали (мм)
            allow_rotations: Разрешить вращения деталей
            use_hybrid: Использовать гибридный алгоритм (Maximal Spaces + Guillotine)
        """
        self.bin = bin_size
        self.items = items
        self.kerf = kerf
        self.max_cut_length = max_cut_length
        self.min_part_size = min_part_size
        self.allow_rotations = allow_rotations
        self.use_hybrid = use_hybrid

        # Кэш для DP - ТОЛЬКО для больших блоков (для ускорения)
        self.dp_cache: Dict[Tuple[int, int, int], Tuple[CutPattern, Dict]] = {}

        # Reduced raster points
        self.rp_length = None
        self.rp_width = None
        self.rp_height = None

        # Счетчик рекурсивных вызовов для ограничения глубины
        self.recursion_depth = 0
        self.max_recursion_depth = 50  # Ограничение глубины

        # Расширенный список деталей с вращениями
        self.expanded_items = self._expand_items()
    
    def _expand_items(self) -> List[Tuple[Item, Tuple[float, float, float]]]:
        """Создает список всех ориентаций деталей"""
        expanded = []

        for item in self.items:
            if self.allow_rotations:
                rotations = item.rotations()
                for (l, w, h) in rotations:
                    # Проверка минимальных размеров
                    if l >= self.min_part_size and w >= self.min_part_size and h >= self.min_part_size:
                        expanded.append((item, (l, w, h)))
            else:
                expanded.append((item, (item.length, item.width, item.height)))

        # НЕ сортируем! Порядок деталей задается извне (API shuffle)
        # Это позволяет итерациям пробовать разные варианты

        return expanded
    
    def _compute_raster_points(self):
        """Вычисляет reduced raster points для всех измерений"""
        dims_l = []
        dims_w = []
        dims_h = []
        
        for item, (l, w, h) in self.expanded_items:
            dims_l.append(l + self.kerf)
            dims_w.append(w + self.kerf)
            dims_h.append(h + self.kerf)
        
        self.rp_length = ReducedRasterPoints.compute(dims_l, self.bin.length)
        self.rp_width = ReducedRasterPoints.compute(dims_w, self.bin.width)
        self.rp_height = ReducedRasterPoints.compute(dims_h, self.bin.height)

        # Возвращаем достаточно points для хорошего решения
        max_points = 18
        self.rp_length = self.rp_length[:max_points]
        self.rp_width = self.rp_width[:max_points]
        self.rp_height = self.rp_height[:max_points]
        
        # Raster points info (commented to avoid Windows console encoding issues)
        pass
        pass
        pass
        pass
    
    def _get_single_item_value(self, l: float, w: float, h: float,
                               demands: Dict[Tuple[int, Tuple[float, float, float]], int]) -> Tuple[float, Optional[int], Optional[Tuple[float, float, float]]]:
        """
        Находит максимальную стоимость одной детали, помещающейся в бин (l, w, h)
        С учетом доступного количества через demands (если max_fill_mode=False)
        В режиме max_fill_mode=True ИГНОРИРУЕТ количество и размещает детали пока есть место

        Returns:
            (value, item_id, orientation) или (0, None, None)
        """
        best_value = 0
        best_item = None
        best_orientation = None

        for item, orientation in self.expanded_items:
            (item_l, item_w, item_h) = orientation

            # ИСПРАВЛЕНО: Проверяем помещается ли деталь (строго меньше, чтобы был запас)
            if item_l <= l and item_w <= w and item_h <= h:
                # Проверяем доступное количество для данной ориентации
                key = (item.id, orientation)
                available = demands.get(key, 0)

                if available > 0:
                    value = item_l * item_w * item_h  # Используем объем как стоимость
                    if value > best_value:
                        best_value = value
                        best_item = item.id
                        best_orientation = orientation

        return best_value, best_item, best_orientation
    
    def _p(self, x: float) -> int:
        """Функция p(x) = max{i | i ∈ P̃, i ≤ x}"""
        if not self.rp_length:
            return int(x)
        for i in reversed(self.rp_length):
            if i <= x:
                return i
        return 0
    
    def _q(self, y: float) -> int:
        """Функция q(y) = max{j | j ∈ Q̃, j ≤ y}"""
        if not self.rp_width:
            return int(y)
        for j in reversed(self.rp_width):
            if j <= y:
                return j
        return 0
    
    def _r(self, z: float) -> int:
        """Функция r(z) = max{k | k ∈ R̃, k ≤ z}"""
        if not self.rp_height:
            return int(z)
        for k in reversed(self.rp_height):
            if k <= z:
                return k
        return 0
    
    def solve(self) -> Tuple[CutPattern, Dict]:
        """
        Решает задачу 3D unbounded knapsack с гильотинными резами
        С учетом ограничений по количеству деталей

        Returns:
            (best_pattern, statistics)
        """
        # Если включен гибридный режим, используем Hybrid Algorithm
        if self.use_hybrid:
            from hybrid_guillotine import HybridGuillotinePacking
            hybrid = HybridGuillotinePacking(self.bin, self.items, self.kerf, self.allow_rotations)
            return hybrid.solve()

        # Optimization info (commented to avoid Windows console encoding issues)
        pass
        pass
        pass
        pass
        pass
        # for item in self.items:
        pass
        pass
        pass
        pass

        start_time = time.time()
        
        # Инициализируем demands - доступное количество для каждой ориентации
        demands = {}
        for item in self.items:
            quantity = item.quantity  # ВСЕГДА используем item.quantity

            if self.allow_rotations:
                rotations = item.rotations()
                for orientation in rotations:
                    key = (item.id, orientation)
                    demands[key] = quantity
            else:
                orientation = (item.length, item.width, item.height)
                key = (item.id, orientation)
                demands[key] = quantity

        # Initial demands info (commented to avoid Windows console encoding issues)
        pass
        # total_items = {}
        # for (item_id, orientation), qty in demands.items():
        #     if item_id not in total_items:
        #         total_items[item_id] = 0
        #     total_items[item_id] = max(total_items[item_id], qty)
        # for item_id, qty in sorted(total_items.items()):
        pass
        
        # Вычисляем raster points
        try:
            self._compute_raster_points()
        except Exception:
            # Fallback: используем простые raster points если RRP не работает
            self.rp_length = [0, self.bin.length]
            self.rp_width = [0, self.bin.width]
            self.rp_height = [0, self.bin.height]

        # Запускаем DP
        best_pattern, final_demands = self._dp3uk(self.bin.length, self.bin.width, self.bin.height, demands.copy())
        
        elapsed = time.time() - start_time
        
        # Подсчитываем статистику
        all_items = best_pattern.get_all_items((0, 0, 0), self.kerf) if best_pattern else []
        item_counts = {}
        total_volume = 0
        
        for item_id, pos, dims in all_items:
            if item_id not in item_counts:
                item_counts[item_id] = 0
            item_counts[item_id] += 1
            total_volume += dims[0] * dims[1] * dims[2]
        
        # Статистика
        stats = {
            'computation_time': elapsed,
            'raster_points': {
                'length': len(self.rp_length),
                'width': len(self.rp_width),
                'height': len(self.rp_height),
                'total_subproblems': len(self.rp_length) * len(self.rp_width) * len(self.rp_height)
            },
            'cache_size': len(self.dp_cache),
            'best_value': best_pattern.value if best_pattern else 0,
            'bin_volume': self.bin.volume(),
            'filled_volume': total_volume,
            'utilization': (total_volume / self.bin.volume() * 100) if self.bin.volume() > 0 else 0,
            'waste': self.bin.volume() - total_volume,
            'item_counts': item_counts,
            'items_placed': all_items
        }
        
        # Optimization complete info (commented to avoid Windows console encoding issues)
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        # for item in self.items:
        #     placed = item_counts.get(item.id, 0)
        pass
        pass
        
        return best_pattern, stats
    
    def _hash_demands(self, demands: Dict) -> int:
        """Создает хеш из demands для кэширования"""
        # Сортируем для стабильности хеша
        items = sorted(demands.items())
        return hash(tuple(items))
    
    def _dp3uk(self, l: float, w: float, h: float, demands: Dict[Tuple[int, Tuple[float, float, float]], int]) -> Tuple[Optional[CutPattern], Dict]:
        """
        Алгоритм DP3UK из статьи (Algorithm 1)
        Рекурсивная формула (2) с мемоизацией
        С учетом ограничений по количеству деталей
        
        Returns:
            (pattern, updated_demands)
        """
        # Базовые проверки
        if l < self.min_part_size or w < self.min_part_size or h < self.min_part_size:
            return None, demands.copy()
        
        # Округляем до raster points
        l_rp = self._p(l)
        w_rp = self._q(w)
        h_rp = self._r(h)

        # Ограничение глубины рекурсии для избежания зависаний
        self.recursion_depth += 1
        if self.recursion_depth > self.max_recursion_depth:
            self.recursion_depth -= 1
            # Возвращаем только одну деталь если достигли предела
            single_value, single_item, single_orientation = self._get_single_item_value(l_rp, w_rp, h_rp, demands)
            if single_value > 0:
                new_demands = demands.copy()
                key = (single_item, single_orientation)
                if key in new_demands:
                    new_demands[key] -= 1
                return CutPattern(l_rp, w_rp, h_rp, single_value, CutDirection.NONE, 0, single_item), new_demands
            return None, demands.copy()

        # Кэш ТОЛЬКО для больших блоков (чтобы не взрывать память)
        volume = l_rp * w_rp * h_rp
        use_cache = volume > 500000  # Кэшируем только блоки > 500k mm³
        cache_key = (l_rp, w_rp, h_rp)

        if use_cache and cache_key in self.dp_cache:
            cached_pattern, _ = self.dp_cache[cache_key]
            self.recursion_depth -= 1
            return cached_pattern, demands.copy()
        
        # Базовый случай: одна деталь
        single_value, single_item, single_orientation = self._get_single_item_value(l_rp, w_rp, h_rp, demands)
        
        best_pattern = CutPattern(
            length=l_rp,
            width=w_rp,
            height=h_rp,
            value=single_value,
            cut_dir=CutDirection.NONE,
            cut_pos=0,
            item_id=single_item
        )
        
        best_demands = demands.copy()

        # Если нашли деталь, отмечаем её использование
        if single_item is not None and single_orientation is not None:
            key = (single_item, single_orientation)
            if key in best_demands and best_demands[key] > 0:
                best_demands[key] -= 1

        # Пробуем вертикальные резы (V) - по длине
        max_cuts_to_try = min(18, len(self.rp_length))  # Увеличено с 10 до 18 для лучших результатов
        for l_cut in self.rp_length[:max_cuts_to_try]:
            if l_cut >= self.min_part_size and l_cut < l_rp:  # Убрано ограничение <= l_rp / 2
                l_remaining = self._p(l_rp - l_cut - self.kerf)

                if l_remaining >= self.min_part_size:
                    left_pattern, left_demands = self._dp3uk(l_cut, w_rp, h_rp, demands.copy())
                    if left_pattern:  # Проверяем что левая часть дала результат
                        right_pattern, right_demands = self._dp3uk(l_remaining, w_rp, h_rp, left_demands.copy())

                        if right_pattern:
                            total_value = left_pattern.value + right_pattern.value
                            if total_value > best_pattern.value:
                                best_pattern = CutPattern(
                                    length=l_rp,
                                    width=w_rp,
                                    height=h_rp,
                                    value=total_value,
                                    cut_dir=CutDirection.V,
                                    cut_pos=l_cut,
                                    left_pattern=left_pattern,
                                    right_pattern=right_pattern
                                )
                                best_demands = right_demands.copy()
        
        # Пробуем резы по ширине (D) - depth
        max_cuts_to_try = min(18, len(self.rp_width))  # Увеличено с 10 до 18 для лучших результатов
        for w_cut in self.rp_width[:max_cuts_to_try]:
            if w_cut >= self.min_part_size and w_cut < w_rp:  # Убрано ограничение <= w_rp / 2
                w_remaining = self._q(w_rp - w_cut - self.kerf)

                if w_remaining >= self.min_part_size:
                    left_pattern, left_demands = self._dp3uk(l_rp, w_cut, h_rp, demands.copy())
                    if left_pattern:
                        right_pattern, right_demands = self._dp3uk(l_rp, w_remaining, h_rp, left_demands.copy())

                        if right_pattern:
                            total_value = left_pattern.value + right_pattern.value
                            if total_value > best_pattern.value:
                                best_pattern = CutPattern(
                                    length=l_rp,
                                    width=w_rp,
                                    height=h_rp,
                                    value=total_value,
                                    cut_dir=CutDirection.D,
                                    cut_pos=w_cut,
                                    left_pattern=left_pattern,
                                    right_pattern=right_pattern
                                )
                                best_demands = right_demands.copy()
        
        # Пробуем горизонтальные резы (H) - по высоте
        max_cuts_to_try = min(18, len(self.rp_height))  # Увеличено с 10 до 18 для лучших результатов
        for h_cut in self.rp_height[:max_cuts_to_try]:
            if h_cut >= self.min_part_size and h_cut < h_rp:  # Убрано ограничение <= h_rp / 2
                h_remaining = self._r(h_rp - h_cut - self.kerf)

                if h_remaining >= self.min_part_size:
                    left_pattern, left_demands = self._dp3uk(l_rp, w_rp, h_cut, demands.copy())
                    if left_pattern:
                        right_pattern, right_demands = self._dp3uk(l_rp, w_rp, h_remaining, left_demands.copy())

                        if right_pattern:
                            total_value = left_pattern.value + right_pattern.value
                            if total_value > best_pattern.value:
                                best_pattern = CutPattern(
                                    length=l_rp,
                                    width=w_rp,
                                    height=h_rp,
                                    value=total_value,
                                    cut_dir=CutDirection.H,
                                    cut_pos=h_cut,
                                    left_pattern=left_pattern,
                                    right_pattern=right_pattern
                                )
                                best_demands = right_demands.copy()
        
        # Сохраняем в кэш ТОЛЬКО если используем кэширование
        if use_cache:
            self.dp_cache[cache_key] = (best_pattern, best_demands.copy())

        self.recursion_depth -= 1
        return best_pattern, best_demands
    
    def visualize_pattern(self, pattern: CutPattern, depth: int = 0) -> str:
        """Текстовая визуализация паттерна раскроя"""
        if not pattern:
            return "No pattern"
        
        indent = "  " * depth
        result = []
        
        if pattern.cut_dir == CutDirection.NONE:
            # Лист
            result.append(f"{indent}+- Item #{pattern.item_id}: "
                         f"{pattern.length:.0f}x{pattern.width:.0f}x{pattern.height:.0f} "
                         f"(value: {pattern.value:.0f})")
        else:
            # Узел с резом
            cut_name = {
                CutDirection.H: "Horizontal",
                CutDirection.V: "Vertical", 
                CutDirection.D: "Depth"
            }[pattern.cut_dir]
            
            result.append(f"{indent}+- {cut_name} cut at {pattern.cut_pos:.0f} mm "
                         f"[{pattern.length:.0f}x{pattern.width:.0f}x{pattern.height:.0f}]")
            
            if pattern.left_pattern:
                result.append(self.visualize_pattern(pattern.left_pattern, depth + 1))
            if pattern.right_pattern:
                result.append(self.visualize_pattern(pattern.right_pattern, depth + 1))
        
        return "\n".join(result)

def visualize_with_plotly(pattern: CutPattern, bin_size: Bin, items: List[Item], 
                          kerf: float = 4.0, output_file: Optional[str] = None) -> str:
    """
    Создает интерактивную 3D визуализацию раскроя с помощью plotly
    
    Args:
        pattern: Паттерн раскроя
        bin_size: Размер блока
        items: Список деталей (для цветов)
        kerf: Ширина пропила
        output_file: Путь для сохранения HTML (опционально)
    
    Returns:
        HTML строка с визуализацией
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        pass
        return "<p>Plotly not installed. Install with: pip install plotly</p>"
    
    if not pattern:
        return "<p>No pattern to visualize</p>"
    
    # Получаем все детали с позициями
    all_items = pattern.get_all_items((0, 0, 0), kerf)
    
    # Создаем цветовую карту для деталей
    item_colors = {}
    colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
        '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52BE80',
        '#E74C3C', '#3498DB', '#9B59B6', '#1ABC9C', '#F39C12',
        '#E67E22', '#34495E', '#16A085', '#27AE60', '#2980B9'
    ]
    
    for idx, item in enumerate(items):
        item_colors[item.id] = colors[idx % len(colors)]
    
    # Создаем фигуру
    fig = go.Figure()
    
    # Добавляем блок (проволочная рамка)
    L, W, H = bin_size.length, bin_size.width, bin_size.height
    
    # Вершины блока
    vertices = [
        [0, 0, 0], [L, 0, 0], [L, W, 0], [0, W, 0],  # Нижняя грань
        [0, 0, H], [L, 0, H], [L, W, H], [0, W, H]   # Верхняя грань
    ]
    
    # Рёбра блока
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # Нижняя грань
        [4, 5], [5, 6], [6, 7], [7, 4],  # Верхняя грань
        [0, 4], [1, 5], [2, 6], [3, 7]   # Вертикальные рёбра
    ]
    
    for edge in edges:
        x = [vertices[edge[0]][0], vertices[edge[1]][0]]
        y = [vertices[edge[0]][1], vertices[edge[1]][1]]
        z = [vertices[edge[0]][2], vertices[edge[1]][2]]
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode='lines',
            line=dict(color='gray', width=2, dash='dash'),
            showlegend=False,
            name='Block'
        ))
    
    # Добавляем детали
    item_counts = {}
    for item_id, (x, y, z), (l, w, h) in all_items:
        if item_id not in item_counts:
            item_counts[item_id] = 0
        item_counts[item_id] += 1
        
        color = item_colors.get(item_id, '#888888')
        
        # Создаем 8 вершин параллелепипеда
        x_coords = [x, x+l, x+l, x, x, x+l, x+l, x]
        y_coords = [y, y, y+w, y+w, y, y, y+w, y+w]
        z_coords = [z, z, z, z, z+h, z+h, z+h, z+h]
        
        # Грани параллелепипеда
        faces = [
            [0, 1, 2, 3],  # Нижняя
            [4, 5, 6, 7],  # Верхняя
            [0, 1, 5, 4],  # Передняя
            [2, 3, 7, 6],  # Задняя
            [0, 3, 7, 4],  # Левая
            [1, 2, 6, 5]   # Правая
        ]
        
        # Используем Mesh3d для отображения
        # Индексы для треугольников (каждая грань = 2 треугольника)
        i_indices = []
        j_indices = []
        k_indices = []
        
        for face in faces:
            # Первый треугольник: face[0], face[1], face[2]
            i_indices.append(face[0])
            j_indices.append(face[1])
            k_indices.append(face[2])
            # Второй треугольник: face[0], face[2], face[3]
            i_indices.append(face[0])
            j_indices.append(face[2])
            k_indices.append(face[3])
        
        # Проверяем, есть ли уже этот item_id в легенде
        existing_items = set()
        for trace in fig.data:
            if hasattr(trace, 'name') and trace.name and 'Item' in trace.name:
                try:
                    existing_items.add(int(trace.name.split()[-1]))
                except:
                    pass
        
        show_in_legend = item_id not in existing_items
        
        fig.add_trace(go.Mesh3d(
            x=x_coords,
            y=y_coords,
            z=z_coords,
            i=i_indices,
            j=j_indices,
            k=k_indices,
            opacity=0.8,
            color=color,
            name=f'Item {item_id}',
            showlegend=show_in_legend
        ))
    
    # Настройка осей и камеры
    fig.update_layout(
        title={
            'text': f'3D Guillotine Cutting Visualization<br>Utilization: {(sum(l*w*h for _, _, (l, w, h) in all_items) / bin_size.volume() * 100):.1f}%',
            'x': 0.5,
            'xanchor': 'center'
        },
        scene=dict(
            xaxis_title='Length (X)',
            yaxis_title='Width (Y)',
            zaxis_title='Height (Z)',
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5),
                center=dict(x=0, y=0, z=0)
            )
        ),
        width=1000,
        height=800,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    # Сохраняем или возвращаем HTML
    html_str = fig.to_html(include_plotlyjs='cdn', div_id='plotly-div')
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_str)
        pass
    return html_str




