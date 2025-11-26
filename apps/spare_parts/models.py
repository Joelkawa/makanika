from core.database import Base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime

class SparePart(Base):
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    quantity_in_stock = Column(Integer, default=0)
    sku = Column(String(100), unique=True, index=True, nullable=True)  # Stock Keeping Unit
    category = Column(String(100), index=True, nullable=True)
    minimum_stock_level = Column(Integer, default=0)  # Alert when stock falls below this
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)