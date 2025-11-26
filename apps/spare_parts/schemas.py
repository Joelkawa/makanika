from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class SparePartBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Spare part name")
    description: Optional[str] = Field(None, description="Detailed description")
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    quantity_in_stock: int = Field(0, ge=0, description="Quantity cannot be negative")
    sku: Optional[str] = Field(None, max_length=100, description="Stock Keeping Unit")
    category: Optional[str] = Field(None, max_length=100, description="Category")
    minimum_stock_level: int = Field(0, ge=0, description="Minimum stock level for alerts")
    is_active: bool = Field(True, description="Active status")

class SparePartCreate(SparePartBase):
    pass

class SparePartUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    quantity_in_stock: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    minimum_stock_level: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @validator('sku')
    def sku_uppercase(cls, v):
        if v is not None:
            return v.upper()
        return v

class SparePartResponse(SparePartBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SparePartStockUpdate(BaseModel):
    quantity_change: int = Field(..., description="Positive to add stock, negative to remove")
    reason: Optional[str] = Field(None, description="Reason for stock change")

class SparePartListResponse(BaseModel):
    items: List[SparePartResponse]
    total: int
    page: int
    size: int
    total_pages: int

class LowStockAlert(BaseModel):
    spare_part: SparePartResponse
    current_stock: int
    minimum_level: int
    needs_reorder: bool