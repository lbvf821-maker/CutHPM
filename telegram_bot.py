"""
Telegram Bot для AlmaCut3D
Позволяет пользователям запрашивать оптимизацию через Telegram
"""
import os
import asyncio
from typing import Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import guillotine3d
from tree_builder import build_cutting_tree
import database

# Токен бота (нужно установить в .env файле)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветственное сообщение"""
    welcome_text = """
🤖 Добро пожаловать в AlmaCut3D Bot!

Я помогу вам оптимизировать раскрой 3D блоков.

📋 Доступные команды:
/optimize - Запустить оптимизацию раскроя
/blocks - Показать доступные блоки на складе
/help - Помощь

💡 Пример использования:
Отправьте команду /optimize и следуйте инструкциям.
    """
    await message.answer(welcome_text)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь"""
    help_text = """
📖 Справка по командам:

/optimize - Оптимизация раскроя
Формат: отправьте детали построчно:
id,длина,ширина,высота,количество

Пример:
1,200,300,400,5
2,150,250,300,8
3,100,200,250,10

/blocks - Список блоков на складе
Показывает все доступные материнские блоки

/find_best - Найти лучший блок
Автоматически подбирает оптимальный блок из базы данных
    """
    await message.answer(help_text)


@dp.message(Command("blocks"))
async def cmd_blocks(message: Message):
    """Показать доступные блоки"""
    try:
        blocks = database.get_all_blocks(active_only=True)

        if not blocks:
            await message.answer("📦 На складе нет доступных блоков")
            return

        response = f"📦 Доступные блоки на складе ({len(blocks)} шт.):\n\n"

        for block in blocks[:20]:  # Ограничиваем 20 блоками
            response += f"🔹 ID {block.id}: {block.material}"
            if block.grade:
                response += f" ({block.grade})"
            response += f"\n"
            response += f"   Размеры: {block.length}×{block.width}×{block.height} мм\n"
            response += f"   Количество: {block.quantity} шт.\n"
            if block.location:
                response += f"   Расположение: {block.location}\n"
            response += "\n"

        await message.answer(response)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("optimize"))
async def cmd_optimize(message: Message):
    """Запрос оптимизации"""
    instruction = """
📝 Отправьте детали для раскроя в формате:

id,длина,ширина,высота,количество

Каждая деталь на новой строке.

Пример:
1,200,300,400,5
2,150,250,300,8
3,100,200,250,10

После этого я подберу оптимальный блок из базы данных.
    """
    await message.answer(instruction)


@dp.message(Command("find_best"))
async def cmd_find_best(message: Message):
    """Информация о поиске лучшего блока"""
    info = """
🔍 Автоматический подбор блока

Отправьте список деталей, и я автоматически:
1. Перебрать все доступные блоки на складе
2. Для каждого блока запустить оптимизацию
3. Выбрать блок с максимальным заполнением
4. Показать программу раскроя

Формат такой же как для /optimize:
id,длина,ширина,высота,количество
    """
    await message.answer(info)


@dp.message()
async def handle_items(message: Message):
    """Обработка списка деталей"""
    try:
        # Парсим детали
        lines = message.text.strip().split('\n')
        items = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('/'):
                continue

            parts = line.split(',')
            if len(parts) < 5:
                await message.answer(f"❌ Неверный формат строки: {line}\nОжидается: id,l,w,h,qty")
                return

            try:
                item = guillotine3d.Item(
                    id=int(parts[0].strip()),
                    length=float(parts[1].strip()),
                    width=float(parts[2].strip()),
                    height=float(parts[3].strip()),
                    quantity=int(parts[4].strip())
                )
                items.append(item)
            except ValueError as e:
                await message.answer(f"❌ Ошибка парсинга: {line}\n{str(e)}")
                return

        if not items:
            await message.answer("❌ Не найдено ни одной детали. Используйте /help для справки.")
            return

        # Уведомляем о начале обработки
        processing_msg = await message.answer("🔄 Ищу оптимальный блок...")

        # Получаем блоки
        blocks = database.get_all_blocks(active_only=True)
        if not blocks:
            await processing_msg.edit_text("❌ На складе нет доступных блоков")
            return

        # Перебираем блоки
        best_result = None
        best_utilization = 0
        best_block = None

        for block in blocks:
            if block.quantity <= 0:
                continue

            bin_size = guillotine3d.Bin(
                length=block.length,
                width=block.width,
                height=block.height
            )

            optimizer = guillotine3d.Guillotine3DCutter(
                bin_size=bin_size,
                items=items,
                kerf=4.0,
                allow_rotations=True
            )

            pattern, stats = optimizer.solve()

            if pattern and stats['utilization'] > best_utilization:
                best_utilization = stats['utilization']
                best_result = {"pattern": pattern, "stats": stats}
                best_block = block

        if not best_result:
            await processing_msg.edit_text("❌ Не удалось найти решение ни для одного блока")
            return

        # Строим дерево резов
        cutting_tree = build_cutting_tree(
            pattern=best_result["pattern"],
            bin_dimensions=(best_block.length, best_block.width, best_block.height),
            kerf=4.0
        )

        stats = best_result["stats"]

        # Формируем отчет
        report = f"""
✅ Оптимизация завершена!

📦 Лучший блок:
   ID: {best_block.id}
   Материал: {best_block.material} {best_block.grade or ''}
   Размеры: {best_block.length}×{best_block.width}×{best_block.height} мм
   Расположение: {best_block.location or 'Не указано'}

📊 Результаты:
   Заполнение: {stats['utilization']:.2f}%
   Отход: {100 - stats['utilization']:.2f}%
   Объем использован: {stats['filled_volume']:,.0f} мм³
   Объем отхода: {stats['waste']:,.0f} мм³
   Время расчета: {stats['computation_time']:.2f} сек

📋 Размещено деталей:
"""

        for item_id, count in stats['item_counts'].items():
            requested = next((item.quantity for item in items if item.id == item_id), 0)
            report += f"   Item {item_id}: {count}/{requested} шт. ({count/requested*100:.1f}%)\n"

        report += f"\n✂️ Всего операций: {cutting_tree.total_nodes}"
        report += f"\n   Резов: {cutting_tree.total_cuts}"
        report += f"\n   Деталей: {cutting_tree.total_items}"
        report += f"\n   Промежуточных заготовок: {cutting_tree.total_subblocks}"

        # Проверка конфликтов
        conflicts = cutting_tree.check_conflicts()
        if conflicts:
            report += f"\n\n⚠️ Обнаружены конфликты резов: {len(conflicts)}"
        else:
            report += f"\n\n✓ Конфликтов резов не обнаружено"

        await processing_msg.edit_text(report)

        # Отправляем программу раскроя
        if cutting_tree.sequence:
            program = "📋 Программа раскроя:\n\n"
            for step in cutting_tree.sequence[:15]:  # Первые 15 операций
                program += f"{step['seq']}. {step['operation']}: {step['description']}\n"

            if len(cutting_tree.sequence) > 15:
                program += f"\n... и еще {len(cutting_tree.sequence) - 15} операций"

            await message.answer(program)

        # Сохраняем в историю
        database.save_optimization(
            items=[{"id": item.id, "l": item.length, "w": item.width, "h": item.height, "qty": item.quantity} for item in items],
            block_id=best_block.id,
            kerf=4.0,
            iterations=1,
            utilization=stats['utilization'],
            filled_volume=stats['filled_volume'],
            waste_volume=stats['waste'],
            execution_time=stats['computation_time'],
            user_id=str(message.from_user.id)
        )

    except Exception as e:
        import traceback
        error_msg = f"❌ Ошибка: {str(e)}\n\n{traceback.format_exc()}"
        await message.answer(error_msg[:4000])  # Telegram limit


async def main():
    """Запуск бота"""
    # Инициализация БД
    database.init_db()
    print("✅ База данных инициализирована")

    # Проверяем блоки
    blocks = database.get_all_blocks(active_only=False)
    if len(blocks) == 0:
        print("📦 Добавляем тестовые блоки...")
        database.populate_sample_data()

    print(f"🤖 Telegram бот запущен (токен: {BOT_TOKEN[:10]}...)")
    print("📦 Доступных блоков на складе:", len(database.get_all_blocks(active_only=True)))

    # Запуск polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
