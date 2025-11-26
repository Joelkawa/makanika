from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    DIAGNOSING = "DIAGNOSING"
    REPAIRING = "REPAIRING"
    WAITING_FOR_PARTS = "WAITING_FOR_PARTS"
    READY = "READY"
    COMPLETED = "COMPLETED"
class JobBase(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_phone: str = Field(..., min_length=1, max_length=20)
    customer_email: Optional[EmailStr] = None
    vehicle_name: str = Field(..., min_length=1, max_length=255)
    motorcycle_numberplate: str = Field(..., min_length=1, max_length=50)
    problem_description: str = Field(..., min_length=1)
    estimated_cost: float = Field(0.0, ge=0)
    priority: int = Field(1, ge=1, le=4)

class JobCreate(JobBase):
    create_customer_account: bool = Field(True, description="Create customer login account")

class JobUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_phone: Optional[str] = Field(None, min_length=1, max_length=20)
    customer_email: Optional[EmailStr] = None
    vehicle_name: Optional[str] = Field(None, min_length=1, max_length=255)
    motorcycle_numberplate: Optional[str] = Field(None, min_length=1, max_length=50)
    problem_description: Optional[str] = Field(None, min_length=1)
    diagnosis_notes: Optional[str] = None
    repair_notes: Optional[str] = None
    estimated_cost: Optional[float] = Field(None, ge=0)
    actual_cost: Optional[float] = Field(None, ge=0)
    status: Optional[JobStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=4)
    assigned_mechanic_id: Optional[int] = None

class JobResponse(JobBase):
    id: int
    job_number: str
    diagnosis_notes: Optional[str]
    repair_notes: Optional[str]
    actual_cost: float
    status: JobStatus
    priority: int
    assigned_mechanic_id: Optional[int]
    assigned_mechanic_name: Optional[str]
    created_by_id: int
    created_by_name: str
    customer_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class JobStatusUpdate(BaseModel):
    status: JobStatus
    notes: Optional[str] = None

class JobCostUpdate(BaseModel):
    actual_cost: float = Field(..., ge=0)
    repair_notes: Optional[str] = None

class JobAssignment(BaseModel):
    assigned_mechanic_id: int

class CustomerCredentials(BaseModel):
    email: str
    password: str
    job_number: str

class JobCreateResponse(BaseModel):
    job: JobResponse
    customer_credentials: Optional[CustomerCredentials] = None
    message: str

class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    size: int
    total_pages: int

class JobStatsResponse(BaseModel):
    total_jobs: int
    diagnosing: int
    repairing: int
    waiting_for_parts: int
    ready: int
    completed: int