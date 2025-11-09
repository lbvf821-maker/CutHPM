#!/usr/bin/env python
"""Запуск сервера."""
import uvicorn
from api import app
from utils import load_env

if __name__ == "__main__":
    import os
    load_env()  # Загружаем переменные из .env
    PORT = int(os.getenv("PORT", "3000"))  # Используем порт 3000 по умолчанию
    print("=" * 60)
    print("AlmaCut3D Server")
    print("=" * 60)
    print(f"Open: http://localhost:{PORT}")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=PORT, reload=False)

