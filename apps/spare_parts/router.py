from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from apps.spare_parts.schemas import (
    SparePartCreate,
    SparePartUpdate,
    SparePartResponse,
    SparePartStockUpdate,
    SparePartListResponse,
    LowStockAlert
)
from apps.spare_parts.services import SparePartService, get_spare_part_service
from apps.auth.services import get_current_user, get_current_admin, get_current_mechanic
from apps.auth.models import UserModel
import math

router = APIRouter()

@router.post(
    "/", 
    response_model=SparePartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new spare part",
    description="Create a new spare part in the inventory (Admin only)"
)
def create_spare_part(
    spare_part: SparePartCreate,
    service: SparePartService = Depends(get_spare_part_service),
    admin: UserModel = Depends(get_current_admin)
):
    """Create a new spare part (Admin only)"""
    return service.create_spare_part(spare_part)

@router.get(
    "/", 
    response_model=SparePartListResponse,
    summary="Get all spare parts",
    description="Retrieve spare parts with filtering and pagination"
)
def get_spare_parts(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    search: Optional[str] = Query(None, description="Search in name, description, or SKU"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    low_stock_only: bool = Query(False, description="Show only low stock items"),
    service: SparePartService = Depends(get_spare_part_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get spare parts with filtering and pagination"""
    spare_parts, total = service.get_spare_parts(
        skip=skip,
        limit=limit,
        search=search,
        category=category,
        min_price=min_price,
        max_price=max_price,
        low_stock_only=low_stock_only
    )
    
    total_pages = math.ceil(total / limit) if limit > 0 else 1
    current_page = (skip // limit) + 1 if limit > 0 else 1
    
    return SparePartListResponse(
        items=spare_parts,
        total=total,
        page=current_page,
        size=limit,
        total_pages=total_pages
    )

@router.get(
    "/{spare_part_id}",
    response_model=SparePartResponse,
    summary="Get spare part by ID",
    description="Retrieve a specific spare part by its ID"
)
def get_spare_part(
    spare_part_id: int,
    service: SparePartService = Depends(get_spare_part_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific spare part by ID"""
    spare_part = service.get_spare_part(spare_part_id)
    if not spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found"
        )
    return spare_part

@router.get(
    "/sku/{sku}",
    response_model=SparePartResponse,
    summary="Get spare part by SKU",
    description="Retrieve a specific spare part by its SKU"
)
def get_spare_part_by_sku(
    sku: str,
    service: SparePartService = Depends(get_spare_part_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific spare part by SKU"""
    spare_part = service.get_spare_part_by_sku(sku)
    if not spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spare part not found"
        )
    return spare_part

@router.put(
    "/{spare_part_id}",
    response_model=SparePartResponse,
    summary="Update spare part",
    description="Update an existing spare part (Admin only)"
)
def update_spare_part(
    spare_part_id: int,
    spare_part_update: SparePartUpdate,
    service: SparePartService = Depends(get_spare_part_service),
    admin: UserModel = Depends(get_current_admin)
):
    """Update a spare part (Admin only)"""
    return service.update_spare_part(spare_part_id, spare_part_update)

@router.delete(
    "/{spare_part_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete spare part",
    description="Delete a spare part (soft delete - Admin only)"
)
def delete_spare_part(
    spare_part_id: int,
    service: SparePartService = Depends(get_spare_part_service),
    admin: UserModel = Depends(get_current_admin)
):
    """Delete a spare part (Admin only)"""
    success = service.delete_spare_part(spare_part_id)
    return {"message": "Spare part deleted successfully"}

@router.patch(
    "/{spare_part_id}/stock",
    response_model=SparePartResponse,
    summary="Update stock quantity",
    description="Update stock quantity for a spare part (Admin/Mechanic)"
)
def update_stock(
    spare_part_id: int,
    stock_update: SparePartStockUpdate,
    service: SparePartService = Depends(get_spare_part_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Update stock quantity (Admin or Mechanic only)"""
    # Check if user has permission (Admin or Mechanic)
    if current_user.role.name not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update stock"
        )
    
    return service.update_stock(spare_part_id, stock_update)

@router.get(
    "/alerts/low-stock",
    response_model=List[LowStockAlert],
    summary="Get low stock alerts",
    description="Get all spare parts with stock below minimum level (Admin/Mechanic)"
)
def get_low_stock_alerts(
    service: SparePartService = Depends(get_spare_part_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get low stock alerts (Admin or Mechanic only)"""
    if current_user.role.name not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view stock alerts"
        )
    
    return service.get_low_stock_items()

@router.get(
    "/categories/all",
    response_model=List[str],
    summary="Get all categories",
    description="Get all unique spare part categories"
)
def get_categories(
    service: SparePartService = Depends(get_spare_part_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get all unique categories"""
    return service.get_categories()

@router.get(
    "/search/quick",
    response_model=List[SparePartResponse],
    summary="Quick search",
    description="Quick search for spare parts by name or SKU"
)
def quick_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    service: SparePartService = Depends(get_spare_part_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Quick search for spare parts"""
    spare_parts, _ = service.get_spare_parts(
        skip=0,
        limit=limit,
        search=q,
        active_only=True
    )
    return spare_parts