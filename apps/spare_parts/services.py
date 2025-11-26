from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional, Tuple
from fastapi import HTTPException, status, Depends
from apps.spare_parts.models import SparePart
from apps.spare_parts.schemas import (
    SparePartCreate, 
    SparePartUpdate, 
    SparePartStockUpdate,
    LowStockAlert
)
from core.database import get_db
from apps.auth.services import get_current_user, get_current_admin
from apps.auth.models import UserModel
import logging

logger = logging.getLogger(__name__)

class SparePartService:
    def __init__(self, db: Session):
        self.db = db

    def get_spare_part(self, spare_part_id: int) -> Optional[SparePart]:
        """Get spare part by ID"""
        return self.db.query(SparePart).filter(SparePart.id == spare_part_id).first()

    def get_spare_part_by_sku(self, sku: str) -> Optional[SparePart]:
        """Get spare part by SKU"""
        return self.db.query(SparePart).filter(SparePart.sku == sku.upper()).first()

    def get_spare_parts(
        self, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        low_stock_only: bool = False,
        active_only: bool = True
    ) -> Tuple[List[SparePart], int]:
        """Get spare parts with filtering and pagination"""
        query = self.db.query(SparePart)
        
        # Apply filters
        if active_only:
            query = query.filter(SparePart.is_active == 1)
        
        if search:
            search_filter = or_(
                SparePart.name.ilike(f"%{search}%"),
                SparePart.description.ilike(f"%{search}%"),
                SparePart.sku.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        if category:
            query = query.filter(SparePart.category == category)
        
        if min_price is not None:
            query = query.filter(SparePart.price >= min_price)
        
        if max_price is not None:
            query = query.filter(SparePart.price <= max_price)
        
        if low_stock_only:
            query = query.filter(
                SparePart.quantity_in_stock <= SparePart.minimum_stock_level
            )
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        spare_parts = query.offset(skip).limit(limit).all()
        
        return spare_parts, total

    def create_spare_part(self, spare_part: SparePartCreate) -> SparePart:
        """Create a new spare part"""
        # Check if SKU already exists
        if spare_part.sku:
            existing = self.get_spare_part_by_sku(spare_part.sku)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Spare part with SKU '{spare_part.sku}' already exists"
                )
        
        db_spare_part = SparePart(**spare_part.model_dump())
        self.db.add(db_spare_part)
        self.db.commit()
        self.db.refresh(db_spare_part)
        
        logger.info(f"Created spare part: {db_spare_part.name} (ID: {db_spare_part.id})")
        return db_spare_part

    def update_spare_part(
        self, 
        spare_part_id: int, 
        spare_part_update: SparePartUpdate
    ) -> SparePart:
        """Update an existing spare part"""
        db_spare_part = self.get_spare_part(spare_part_id)
        if not db_spare_part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Spare part not found"
            )
        
        update_data = spare_part_update.model_dump(exclude_unset=True)
        
        # Check SKU uniqueness if provided
        if 'sku' in update_data and update_data['sku']:
            existing = self.get_spare_part_by_sku(update_data['sku'])
            if existing and existing.id != spare_part_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Spare part with SKU '{update_data['sku']}' already exists"
                )
        
        for field, value in update_data.items():
            setattr(db_spare_part, field, value)
        
        self.db.commit()
        self.db.refresh(db_spare_part)
        
        logger.info(f"Updated spare part: {db_spare_part.name} (ID: {db_spare_part.id})")
        return db_spare_part

    def delete_spare_part(self, spare_part_id: int) -> bool:
        """Delete a spare part (soft delete by setting is_active to 0)"""
        db_spare_part = self.get_spare_part(spare_part_id)
        if not db_spare_part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Spare part not found"
            )
        
        db_spare_part.is_active = 0
        self.db.commit()
        
        logger.info(f"Deleted spare part: {db_spare_part.name} (ID: {db_spare_part.id})")
        return True

    def update_stock(
        self, 
        spare_part_id: int, 
        stock_update: SparePartStockUpdate
    ) -> SparePart:
        """Update spare part stock quantity"""
        db_spare_part = self.get_spare_part(spare_part_id)
        if not db_spare_part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Spare part not found"
            )
        
        new_quantity = db_spare_part.quantity_in_stock + stock_update.quantity_change
        
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Current: {db_spare_part.quantity_in_stock}, "
                       f"Requested reduction: {abs(stock_update.quantity_change)}"
            )
        
        db_spare_part.quantity_in_stock = new_quantity
        self.db.commit()
        self.db.refresh(db_spare_part)
        
        logger.info(
            f"Updated stock for {db_spare_part.name}: "
            f"{stock_update.quantity_change} (Reason: {stock_update.reason})"
        )
        return db_spare_part

    def get_low_stock_items(self) -> List[LowStockAlert]:
        """Get items with stock below minimum level"""
        low_stock_items = self.db.query(SparePart).filter(
            and_(
                SparePart.quantity_in_stock <= SparePart.minimum_stock_level,
                SparePart.is_active == 1
            )
        ).all()
        
        alerts = []
        for item in low_stock_items:
            alerts.append(LowStockAlert(
                spare_part=item,
                current_stock=item.quantity_in_stock,
                minimum_level=item.minimum_stock_level,
                needs_reorder=item.quantity_in_stock == 0
            ))
        
        return alerts

    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = self.db.query(SparePart.category).filter(
            SparePart.category.isnot(None),
            SparePart.is_active == 1
        ).distinct().all()
        
        return [cat[0] for cat in categories if cat[0]]

# Dependency injection
def get_spare_part_service(db: Session = Depends(get_db)) -> SparePartService:
    return SparePartService(db)