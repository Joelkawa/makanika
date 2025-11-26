from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    CHECKED_IN = "CHECKED_IN"
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
    estimated_completion: Optional[str] = Field(None, max_length=100)
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
    estimated_completion: Optional[str] = Field(None, max_length=100)
    status: Optional[JobStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=4)
    assigned_mechanic_id: Optional[int] = None

class JobResponse(BaseModel):
    id: int
    job_number: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    vehicle_name: str
    motorcycle_numberplate: str
    problem_description: str
    diagnosis_notes: Optional[str] = None
    repair_notes: Optional[str] = None
    estimated_cost: float
    actual_cost: float
    estimated_completion: Optional[str] = None
    status: JobStatus
    priority: int
    assigned_mechanic_id: Optional[int] = None
    assigned_mechanic_name: Optional[str] = None
    created_by_id: int
    created_by_name: str
    customer_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
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
    checked_in: int = 0
    diagnosing: int = 0
    repairing: int = 0
    waiting_for_parts: int = 0
    ready: int = 0
    completed: int = 0
