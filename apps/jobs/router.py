from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import math

from apps.jobs.schemas import (
    JobCreate, JobUpdate, JobResponse, JobStatusUpdate, JobCostUpdate,
    JobAssignment, JobCreateResponse, JobListResponse, JobStatsResponse
)
from apps.jobs.services import JobService, get_job_service
from apps.jobs.models import JobStatus
from apps.auth.services import get_current_user, get_current_admin, get_current_mechanic
from apps.auth.models import UserModel

router = APIRouter()

@router.post(
    "/",
    response_model=JobCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job",
    description="Create a new repair job. Can automatically create customer portal access."
)
def create_job(
    job: JobCreate,
    service: JobService = Depends(get_job_service),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new job. 
    - Admin and mechanics can create jobs
    - Optionally creates customer portal account
    - Returns customer credentials if account is created
    """
    if current_user.role.name not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and mechanics can create jobs"
        )
    
    return service.create_job(job, current_user)

@router.get(
    "/",
    response_model=JobListResponse,
    summary="Get all jobs",
    description="Retrieve jobs with filtering and pagination. Access controlled by role."
)
def get_jobs(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in customer name, job number, vehicle"),
    customer_phone: Optional[str] = Query(None, description="Filter by customer phone"),
    numberplate: Optional[str] = Query(None, description="Filter by motorcycle numberplate"),
    service: JobService = Depends(get_job_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get jobs with role-based access control"""

    try:
        jobs, total = service.get_jobs(
        skip=skip,
        limit=limit,
        status=status,
        search=search,
        customer_phone=customer_phone,
        numberplate=numberplate,
        user_id=current_user.id,
        user_role=current_user.role.name
        )
    
        total_pages = math.ceil(total / limit) if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1
    
        return JobListResponse(
        items=jobs,
        total=total,
        page=current_page,
        size=limit,
        total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job by ID",
    description="Retrieve a specific job by its ID"
)
@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job by ID",
    description="Retrieve a specific job by its ID"
)
def get_job(
    job_id: int,
    service: JobService = Depends(get_job_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific job by ID with access control"""
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Access control
    if current_user.role.name == "customer" and job.customer_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job"
        )
    
    # UPDATED: Convert to response dict to satisfy Pydantic schema
    return service.job_to_response(job)

@router.get(
    "/number/{job_number}",
    response_model=JobResponse,
    summary="Get job by job number",
    description="Retrieve a specific job by its job number"
)
def get_job_by_number(
    job_number: str,
    service: JobService = Depends(get_job_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific job by job number with access control"""
    job = service.get_job_by_number(job_number)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Access control
    if current_user.role.name == "customer" and job.customer_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job"
        )
    
    # UPDATED: Convert to response dict to satisfy Pydantic schema
    return service.job_to_response(job)

@router.put(
    "/{job_id}",
    response_model=JobResponse,
    summary="Update job details",
    description="Update job information (Admin only)"
)
def update_job(
    job_id: int,
    job_update: JobUpdate,
    service: JobService = Depends(get_job_service),
    admin: UserModel = Depends(get_current_admin)
):
    """Update job details (Admin only)"""
    return service.update_job(job_id, job_update, admin)

@router.patch(
    "/{job_id}/status",
    response_model=JobResponse,
    summary="Update job status",
    description="Update job status (Admin/Mechanic)"
)
def update_job_status(
    job_id: int,
    status_update: JobStatusUpdate,
    service: JobService = Depends(get_job_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Update job status (Admin or Mechanic only)"""
    if current_user.role.name not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and mechanics can update job status"
        )
    
    return service.update_job_status(job_id, status_update, current_user)

@router.patch(
    "/{job_id}/cost",
    response_model=JobResponse,
    summary="Update job cost",
    description="Update actual cost of the job (Admin/Mechanic)"
)
def update_job_cost(
    job_id: int,
    cost_update: JobCostUpdate,
    service: JobService = Depends(get_job_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Update job cost (Admin or Mechanic only)"""
    if current_user.role.name not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and mechanics can update job cost"
        )
    
    return service.update_job_cost(job_id, cost_update, current_user)

@router.patch(
    "/{job_id}/assign",
    response_model=JobResponse,
    summary="Assign mechanic to job",
    description="Assign a mechanic to a job (Admin only)"
)
def assign_mechanic(
    job_id: int,
    assignment: JobAssignment,
    service: JobService = Depends(get_job_service),
    admin: UserModel = Depends(get_current_admin)
):
    """Assign mechanic to job (Admin only)"""
    return service.assign_mechanic(job_id, assignment, admin)

@router.get(
    "/stats/summary",
    response_model=JobStatsResponse,
    summary="Get job statistics",
    description="Get job statistics summary"
)
def get_job_stats(
    service: JobService = Depends(get_job_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get job statistics with role-based filtering"""
    stats = service.get_job_stats(current_user.id, current_user.role.name)
    return JobStatsResponse(**stats)

@router.get(
    "/customer/my-jobs",
    response_model=List[JobResponse],
    summary="Get customer's jobs",
    description="Get all jobs for the current customer"
)
def get_my_jobs(
    service: JobService = Depends(get_job_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Get jobs for the current customer"""
    if current_user.role.name != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for customers only"
        )
    
    jobs, _ = service.get_jobs(user_id=current_user.id, user_role="customer")
    return jobs

@router.get(
    "/search/by-phone",
    response_model=List[JobResponse],
    summary="Search jobs by phone number",
    description="Search jobs by customer phone number (Admin/Mechanic)"
)
def search_jobs_by_phone(
    phone: str = Query(..., min_length=1, description="Customer phone number"),
    service: JobService = Depends(get_job_service),
    current_user: UserModel = Depends(get_current_user)
):
    """Search jobs by customer phone number (Admin/Mechanic only)"""
    if current_user.role.name not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and mechanics can search by phone"
        )
    
    jobs, _ = service.get_jobs(customer_phone=phone, user_id=current_user.id, user_role=current_user.role.name)
    return jobs