"""Утилиты для загрузки переменных окружения."""
import os
import sys
from pathlib import Path

def load_env():
    """Загружает переменные окружения из .env файла."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value


def safe_print(*args, **kwargs):
    """
    Безопасная замена print() которая не вызывает OSError в FastAPI/uvicorn.
    Полностью отключает вывод в серверном окружении.
    """
    # В FastAPI/uvicorn окружении НЕ выводим ничего
    # Это предотвращает OSError на Windows с кодировкой cp1251
    try:
        # Проверяем, запущены ли мы в uvicorn
        # Если да - молча игнорируем
        if 'uvicorn' in sys.modules or 'fastapi' in sys.modules:
            return

        # Если это обычная консоль - пытаемся вывести
        if sys.stdout and hasattr(sys.stdout, 'write'):
            print(*args, **kwargs)
    except:
        # Любая ошибка - молча игнорируем
        pass

