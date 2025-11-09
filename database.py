"""
Database operations for AlmaCut3D
"""
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Block, OptimizationHistory
from typing import List, Optional, Dict
import json


# Database setup
DATABASE_URL = "sqlite:///almacut3d.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Создать все таблицы в базе данных"""
    Base.metadata.create_all(bind=engine)
    pass
def get_db() -> Session:
    """Получить сессию БД"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Не закрываем здесь, закроем после использования


# ============================================================================
# CRUD операции для Blocks
# ============================================================================

def create_block(
    material: str,
    length: float,
    width: float,
    height: float,
    quantity: int = 1,
    grade: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None
) -> Block:
    """Создать новый блок"""
    db = get_db()
    try:
        block = Block(
            material=material,
            grade=grade,
            length=length,
            width=width,
            height=height,
            quantity=quantity,
            location=location,
            notes=notes
        )
        db.add(block)
        db.commit()
        db.refresh(block)
        return block
    finally:
        db.close()


def get_all_blocks(active_only: bool = True) -> List[Block]:
    """Получить все блоки"""
    db = get_db()
    try:
        query = db.query(Block)
        if active_only:
            query = query.filter(Block.is_active == True)
        return query.all()
    finally:
        db.close()


def get_block_by_id(block_id: int) -> Optional[Block]:
    """Получить блок по ID"""
    db = get_db()
    try:
        return db.query(Block).filter(Block.id == block_id).first()
    finally:
        db.close()


def get_blocks_by_material(material: str, active_only: bool = True) -> List[Block]:
    """Получить блоки определенного материала"""
    db = get_db()
    try:
        query = db.query(Block).filter(Block.material == material)
        if active_only:
            query = query.filter(Block.is_active == True)
        return query.all()
    finally:
        db.close()


def update_block(block_id: int, **kwargs) -> Optional[Block]:
    """Обновить блок"""
    db = get_db()
    try:
        block = db.query(Block).filter(Block.id == block_id).first()
        if not block:
            return None

        for key, value in kwargs.items():
            if hasattr(block, key):
                setattr(block, key, value)

        db.commit()
        db.refresh(block)
        return block
    finally:
        db.close()


def delete_block(block_id: int, soft_delete: bool = True) -> bool:
    """Удалить блок (мягкое или жесткое удаление)"""
    db = get_db()
    try:
        block = db.query(Block).filter(Block.id == block_id).first()
        if not block:
            return False

        if soft_delete:
            block.is_active = False
            db.commit()
        else:
            db.delete(block)
            db.commit()

        return True
    finally:
        db.close()


def decrease_block_quantity(block_id: int, amount: int = 1) -> Optional[Block]:
    """Уменьшить количество блоков (после использования)"""
    db = get_db()
    try:
        block = db.query(Block).filter(Block.id == block_id).first()
        if not block:
            return None

        block.quantity -= amount
        if block.quantity <= 0:
            block.quantity = 0
            block.is_active = False  # Автоматически деактивировать

        db.commit()
        db.refresh(block)
        return block
    finally:
        db.close()


# ============================================================================
# CRUD операции для OptimizationHistory
# ============================================================================

def save_optimization(
    items: List[Dict],
    block_id: Optional[int] = None,
    kerf: float = 4.0,
    iterations: int = 1,
    utilization: Optional[float] = None,
    filled_volume: Optional[float] = None,
    waste_volume: Optional[float] = None,
    execution_time: Optional[float] = None,
    pattern_json: Optional[str] = None,
    user_id: Optional[str] = None
) -> OptimizationHistory:
    """Сохранить историю оптимизации"""
    db = get_db()
    try:
        history = OptimizationHistory(
            block_id=block_id,
            items_json=json.dumps(items),
            kerf=kerf,
            iterations=iterations,
            utilization=utilization,
            filled_volume=filled_volume,
            waste_volume=waste_volume,
            execution_time=execution_time,
            pattern_json=pattern_json,
            user_id=user_id
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        return history
    finally:
        db.close()


def get_optimization_history(limit: int = 50) -> List[OptimizationHistory]:
    """Получить последние оптимизации"""
    db = get_db()
    try:
        return db.query(OptimizationHistory).order_by(desc(OptimizationHistory.created_at)).limit(limit).all()
    finally:
        db.close()


def get_history_by_user(user_id: str, limit: int = 20) -> List[OptimizationHistory]:
    """Получить историю пользователя"""
    db = get_db()
    try:
        return db.query(OptimizationHistory).filter(
            OptimizationHistory.user_id == user_id
        ).order_by(desc(OptimizationHistory.created_at)).limit(limit).all()
    finally:
        db.close()


# ============================================================================
# Вспомогательные функции
# ============================================================================

def populate_sample_data():
    """Заполнить БД тестовыми данными"""
    # Стальные блоки
    create_block(
        material="Сталь",
        grade="45",
        length=2000,
        width=1200,
        height=800,
        quantity=5,
        location="Стеллаж A-1",
        notes="Основной размер для крупных деталей"
    )

    create_block(
        material="Сталь",
        grade="45",
        length=1000,
        width=600,
        height=400,
        quantity=10,
        location="Стеллаж A-2",
        notes="Средний размер"
    )

    create_block(
        material="Сталь",
        grade="40Х",
        length=1500,
        width=800,
        height=600,
        quantity=3,
        location="Стеллаж A-3",
        notes="Легированная сталь"
    )

    # Алюминиевые блоки
    create_block(
        material="Алюминий",
        grade="Д16Т",
        length=2000,
        width=1000,
        height=500,
        quantity=8,
        location="Стеллаж B-1",
        notes="Дюралюминий для авиации"
    )

    create_block(
        material="Алюминий",
        grade="АМг6",
        length=1200,
        width=800,
        height=400,
        quantity=12,
        location="Стеллаж B-2",
        notes="Алюминиево-магниевый сплав"
    )

    pass
if __name__ == "__main__":
    # Инициализация БД
    init_db()

    # Заполнение тестовыми данными
    populate_sample_data()

    # Тест: вывести все блоки
    blocks = get_all_blocks()
    safe_print(f"\n[INFO] Всего блоков на складе: {len(blocks)}")
    for block in blocks:
        pass