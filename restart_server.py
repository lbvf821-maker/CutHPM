# -*- coding: utf-8 -*-
"""
Скрипт для перезапуска сервера с очисткой кэша
"""
import subprocess
import sys
import time
import os
import shutil

print("="*80)
print("ПЕРЕЗАПУСК СЕРВЕРА С ОЧИСТКОЙ КЭША")
print("="*80)

# 1. Убить все процессы Python
print("\n1. Остановка всех процессов Python...")
subprocess.run(["taskkill", "/F", "/IM", "python.exe"],
               stdout=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL)
time.sleep(2)

# 2. Очистить __pycache__
print("2. Очистка Python cache...")
for root, dirs, files in os.walk("."):
    if '__pycache__' in dirs:
        pycache_path = os.path.join(root, '__pycache__')
        print(f"   Удаление {pycache_path}")
        shutil.rmtree(pycache_path, ignore_errors=True)

# 3. Запустить сервер с флагом -B (без кэша)
print("\n3. Запуск сервера (без кэша bytecode)...")
print("   Порт: 8000")
print("   URL: http://127.0.0.1:8000")
print("\nСервер запущен! Нажмите Ctrl+C для остановки.\n")
print("="*80)

# Запуск с выводом в консоль
subprocess.run([
    sys.executable, "-B", "-m", "uvicorn",
    "api:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--reload"  # Автоматическая перезагрузка при изменении файлов
])
