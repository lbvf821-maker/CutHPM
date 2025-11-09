"""
Database models for AlmaCut3D
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Block(Base):
    """
    Материнский блок на складе
    """
    __tablename__ = 'blocks'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Материал
    material = Column(String(50), nullable=False)  # Сталь, Алюминий, и т.д.
    grade = Column(String(50), nullable=True)  # Марка стали (например, "45", "40Х")

    # Размеры (мм)
    length = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)

    # Количество
    quantity = Column(Integer, nullable=False, default=1)

    # Местоположение на складе
    location = Column(String(100), nullable=True)  # Например, "Стеллаж А-5"

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)  # Доступен ли блок

    # Дополнительные параметры
    notes = Column(String(500), nullable=True)  # Примечания

    def volume(self):
        """Объем блока в мм³"""
        return self.length * self.width * self.height

    def __repr__(self):
        return f"<Block(id={self.id}, material={self.material}, {self.length}x{self.width}x{self.height}, qty={self.quantity})>"


class OptimizationHistory(Base):
    """
    История оптимизаций для аналитики
    """
    __tablename__ = 'optimization_history'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Использованный блок
    block_id = Column(Integer, nullable=True)  # NULL если обратная задача

    # Параметры задачи
    items_json = Column(String, nullable=False)  # JSON с деталями
    kerf = Column(Float, default=4.0)
    iterations = Column(Integer, default=1)

    # Результаты
    utilization = Column(Float, nullable=True)  # Процент заполнения
    filled_volume = Column(Float, nullable=True)  # Использованный объем
    waste_volume = Column(Float, nullable=True)  # Отход
    execution_time = Column(Float, nullable=True)  # Время расчета (сек)

    # Результат раскроя
    pattern_json = Column(String, nullable=True)  # JSON дерева резов

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(100), nullable=True)  # Telegram user_id или IP

    def __repr__(self):
        return f"<OptimizationHistory(id={self.id}, block_id={self.block_id}, util={self.utilization}%)>"
