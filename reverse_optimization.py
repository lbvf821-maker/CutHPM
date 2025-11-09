"""
Reverse Optimization - Обратная задача
Подбор оптимального размера блока для заданных деталей
"""
from typing import List, Tuple, Dict, Optional
import guillotine3d
from tree_builder import build_cutting_tree
import math


def calculate_theoretical_minimum_block(items: List[guillotine3d.Item]) -> Tuple[float, float, float]:
    """
    Вычислить теоретический минимальный размер блока.

    Это нижняя граница - блок не может быть меньше, чем суммарный объем всех деталей.
    """
    total_volume = sum(item.length * item.width * item.height * item.quantity for item in items)

    # Находим максимальные размеры среди деталей (учитывая вращения)
    max_dim = 0
    for item in items:
        max_dim = max(max_dim, item.length, item.width, item.height)

    # Пробуем кубический блок как начальную точку
    side = math.ceil(total_volume ** (1/3))

    # Убеждаемся что блок не меньше максимальной детали
    side = max(side, max_dim)

    return (side, side, side)


def find_optimal_block_size(
    items: List[guillotine3d.Item],
    kerf: float = 4.0,
    allow_rotations: bool = True,
    target_utilization: float = 8.0,  # Целевая заполняемость (%)
    max_attempts: int = 20
) -> Dict:
    """
    Найти оптимальный размер блока для заданных деталей.

    Алгоритм:
    1. Начинаем с теоретического минимума
    2. Постепенно увеличиваем размеры блока
    3. Для каждого размера запускаем оптимизацию
    4. Ищем наименьший блок с приемлемой заполняемостью

    Args:
        items: Список деталей
        kerf: Ширина пропила
        allow_rotations: Разрешить вращения
        target_utilization: Целевая заполняемость (%)
        max_attempts: Максимум попыток

    Returns:
        Dict с результатами: размеры блока, заполняемость, паттерн и т.д.
    """
    # Вычисляем теоретический минимум
    min_L, min_W, min_H = calculate_theoretical_minimum_block(items)

    # Суммарный объем деталей
    total_items_volume = sum(item.length * item.width * item.height * item.quantity for item in items)

    # Находим максимальные размеры среди деталей
    max_item_L = max(max(item.length, item.width, item.height) for item in items)
    max_item_W = max(max(item.length, item.width, item.height) for item in items)
    max_item_H = max(max(item.length, item.width, item.height) for item in items)

    results = []

    # Пробуем разные пропорции блока
    # Обычно блоки имеют пропорции 2:1.5:1 или 2:2:1
    proportions = [
        (2.0, 1.5, 1.0),  # Стандартная пропорция
        (2.0, 2.0, 1.0),  # Плоский блок
        (2.0, 1.0, 1.0),  # Вытянутый блок
        (1.5, 1.5, 1.0),  # Квадратное основание
        (1.0, 1.0, 1.0),  # Куб
    ]

    for prop_L, prop_W, prop_H in proportions:
        # Нормализуем пропорции
        total_prop = prop_L + prop_W + prop_H
        prop_L, prop_W, prop_H = prop_L/total_prop, prop_W/total_prop, prop_H/total_prop

        # Начинаем с минимального размера
        scale = 1.0

        for attempt in range(max_attempts):
            # Вычисляем размеры блока с учетом пропорций
            base_size = min_L * scale

            L = max(base_size * prop_L / prop_L, max_item_L * 1.1)  # +10% запас
            W = max(base_size * prop_W / prop_L, max_item_W * 1.1)
            H = max(base_size * prop_H / prop_L, max_item_H * 1.1)

            # Округляем до 10 мм
            L = math.ceil(L / 10) * 10
            W = math.ceil(W / 10) * 10
            H = math.ceil(H / 10) * 10

            # Проверяем, не слишком ли большой блок
            block_volume = L * W * H
            if block_volume > total_items_volume * 50:  # Не более чем в 50 раз больше
                break

            # Запускаем оптимизацию
            bin_size = guillotine3d.Bin(length=L, width=W, height=H)
            optimizer = guillotine3d.Guillotine3DCutter(
                bin_size=bin_size,
                items=items,
                kerf=kerf,
                allow_rotations=allow_rotations
            )

            pattern, stats = optimizer.solve()

            if pattern:
                results.append({
                    "block_size": (L, W, H),
                    "volume": block_volume,
                    "utilization": stats['utilization'],
                    "filled_volume": stats['filled_volume'],
                    "waste": stats['waste'],
                    "pattern": pattern,
                    "stats": stats,
                    "proportion": (prop_L, prop_W, prop_H)
                })

                # Если достигли целевой заполняемости, можно остановиться
                if stats['utilization'] >= target_utilization:
                    break

            # Увеличиваем размер блока для следующей попытки
            scale *= 1.15

    if not results:
        return {
            "success": False,
            "message": "Не удалось найти подходящий размер блока"
        }

    # Сортируем результаты по заполняемости (по убыванию) и объему (по возрастанию)
    results.sort(key=lambda r: (-r['utilization'], r['volume']))

    best = results[0]

    # Строим дерево резов для лучшего результата
    cutting_tree = build_cutting_tree(
        pattern=best['pattern'],
        bin_dimensions=best['block_size'],
        kerf=kerf
    )

    return {
        "success": True,
        "best_block_size": best['block_size'],
        "utilization": best['utilization'],
        "filled_volume": best['filled_volume'],
        "waste": best['waste'],
        "block_volume": best['volume'],
        "pattern": best['pattern'],
        "stats": best['stats'],
        "cutting_tree": cutting_tree.to_dict(),
        "all_results": [
            {
                "size": r['block_size'],
                "volume": r['volume'],
                "utilization": r['utilization']
            }
            for r in results[:10]  # Топ 10 результатов
        ]
    }


def suggest_standard_blocks(
    items: List[guillotine3d.Item],
    kerf: float = 4.0,
    allow_rotations: bool = True
) -> List[Dict]:
    """
    Предложить стандартные размеры блоков из типового ряда.

    Типовые размеры металлопроката:
    - 2000×1000×500
    - 1500×800×600
    - 1200×600×400
    - 1000×500×300
    - 3000×1500×800
    и т.д.
    """
    # Стандартные размеры блоков (мм)
    standard_sizes = [
        (3000, 1500, 800),
        (2500, 1200, 600),
        (2000, 1200, 800),
        (2000, 1000, 500),
        (1500, 800, 600),
        (1200, 800, 400),
        (1200, 600, 400),
        (1000, 600, 400),
        (1000, 500, 300),
        (800, 400, 300),
    ]

    results = []

    for L, W, H in standard_sizes:
        bin_size = guillotine3d.Bin(length=L, width=W, height=H)
        optimizer = guillotine3d.Guillotine3DCutter(
            bin_size=bin_size,
            items=items,
            kerf=kerf,
            allow_rotations=allow_rotations
        )

        pattern, stats = optimizer.solve()

        if pattern and stats['utilization'] > 0:
            results.append({
                "block_size": (L, W, H),
                "volume": L * W * H,
                "utilization": stats['utilization'],
                "filled_volume": stats['filled_volume'],
                "waste": stats['waste'],
                "stats": stats,
                "is_standard": True
            })

    # Сортируем по заполняемости
    results.sort(key=lambda r: -r['utilization'])

    return results


if __name__ == "__main__":
    # Тест обратной оптимизации
    items = [
        guillotine3d.Item(id=1, length=200, width=300, height=400, quantity=5),
        guillotine3d.Item(id=2, length=150, width=250, height=300, quantity=8),
        guillotine3d.Item(id=3, length=100, width=200, height=250, quantity=10),
    ]

    pass
    pass
    pass
    result = find_optimal_block_size(items, target_utilization=6.0)

    if result['success']:
        L, W, H = result['best_block_size']
        pass
        pass
        pass
        pass
        pass
        pass
        for i, alt in enumerate(result['all_results'][:5], 1):
            L, W, H = alt['size']
            pass
    else:
        pass
    pass
    pass
    pass
    standard = suggest_standard_blocks(items)

    if standard:
        pass
        for i, block in enumerate(standard[:5], 1):
            L, W, H = block['block_size']
            pass