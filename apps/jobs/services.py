from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional, Tuple, Dict
from fastapi import HTTPException, status, Depends
import secrets
import string
import logging

from apps.jobs.models import Job, JobStatus
from apps.jobs.schemas import (
    JobCreate, JobUpdate, JobStatusUpdate, JobCostUpdate, 
    JobAssignment, CustomerCredentials, JobCreateResponse
)
from apps.auth.models import UserModel, Role
from apps.auth.services import get_password_hash, get_current_user
from core.database import get_db

logger = logging.getLogger(__name__)

class JobService:
    def __init__(self, db: Session):
        self.db = db

    def generate_job_number(self) -> str:
        """Generate unique job number"""
        prefix = "JOB"
        while True:
            random_suffix = ''.join(secrets.choice(string.digits) for _ in range(6))
            job_number = f"{prefix}-{random_suffix}"
            existing = self.db.query(Job).filter(Job.job_number == job_number).first()
            if not existing:
                return job_number

    def generate_random_password(self, length: int = 8) -> str:
        """Generate random password for customer accounts"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def create_customer_account(self, job: JobCreate, job_number: str) -> Tuple[UserModel, str]:
        """Create customer user account with random password"""
        # Check if customer email already exists
        if job.customer_email:
            existing_user = self.db.query(UserModel).filter(
                UserModel.email == job.customer_email
            ).first()
            if existing_user:
                return existing_user, None

        # Get customer role
        customer_role = self.db.query(Role).filter(Role.name == "customer").first()
        if not customer_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Customer role not found in system"
            )

        # Generate credentials
        password = self.generate_random_password()
        hashed_password = get_password_hash(password)

        # Create user
        customer_user = UserModel(
            name=job.customer_name,
            email=job.customer_email or f"{job_number}@makanika.com",
            hashed_password=hashed_password,
            role=customer_role
        )
        
        self.db.add(customer_user)
        self.db.flush()  # Flush to get ID without committing
        
        return customer_user, password

    def get_job(self, job_id: int) -> Optional[Job]:
        """Get job by ID with related data"""
        return self.db.query(Job).filter(Job.id == job_id).first()

    def get_job_by_number(self, job_number: str) -> Optional[Job]:
        """Get job by job number"""
        return self.db.query(Job).filter(Job.job_number == job_number).first()

    def get_jobs(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[JobStatus] = None,
        search: Optional[str] = None,
        customer_phone: Optional[str] = None,
        numberplate: Optional[str] = None,
        user_id: Optional[int] = None,
        user_role: Optional[str] = None
    ) -> Tuple[List[Dict], int]:
        """Get jobs with filtering and access control"""
        query = self.db.query(Job)
        
        # Apply filters
        if status:
            query = query.filter(Job.status == status)
        
        if search:
            search_filter = or_(
                Job.customer_name.ilike(f"%{search}%"),
                Job.job_number.ilike(f"%{search}%"),
                Job.vehicle_name.ilike(f"%{search}%"),
                Job.problem_description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        if customer_phone:
            query = query.filter(Job.customer_phone.ilike(f"%{customer_phone}%"))
        
        if numberplate:
            query = query.filter(Job.motorcycle_numberplate.ilike(f"%{numberplate}%"))
        
        # Access control based on user role
        if user_role == "customer" and user_id:
            query = query.filter(Job.customer_user_id == user_id)
        elif user_role == "mechanic" and user_id:
            query = query.filter(
                or_(
                    Job.assigned_mechanic_id == user_id,
                    Job.assigned_mechanic_id.is_(None)
                )
            )
        # Admin can see all jobs
        
        # Order by creation date (newest first)
        query = query.order_by(Job.created_at.desc())
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        raw_jobs = query.offset(skip).limit(limit).all()
        # UPDATED: Calling the renamed public method
        jobs = [self.job_to_response(job) for job in raw_jobs]
        
        return jobs, total

    def create_job(self, job_data: JobCreate, created_by: UserModel) -> JobCreateResponse:
        """Create a new job"""
        # Generate job number
        job_number = self.generate_job_number()
        
        customer_user = None
        customer_password = None
        
        # Create customer account if requested
        if job_data.create_customer_account and job_data.customer_email:
            try:
                customer_user, customer_password = self.create_customer_account(job_data, job_number)
            except Exception as e:
                logger.warning(f"Failed to create customer account: {e}")
                # Continue without customer account
        
        # Create job
        job_dict = job_data.model_dump(exclude={'create_customer_account'})
        db_job = Job(
            **job_dict,
            job_number=job_number,
            created_by_id=created_by.id,
            customer_user_id=customer_user.id if customer_user else None
        )
        
        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)
        
        logger.info(f"Created job: {job_number} for customer: {job_data.customer_name}")
        
        # UPDATED: Calling the renamed public method
        job_response = self.job_to_response(db_job)
        credentials = None
        
        if customer_user and customer_password:
            credentials = CustomerCredentials(
                email=customer_user.email,
                password=customer_password,
                job_number=job_number
            )
        
        return JobCreateResponse(
            job=job_response,
            customer_credentials=credentials,
            message="Job created successfully" + (" with customer portal access" if credentials else "")
        )
        
    def update_job(self, job_id: int, job_update: JobUpdate, updated_by: UserModel) -> Job:
        """Update job details"""
        db_job = self.get_job(job_id)
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        update_data = job_update.model_dump(exclude_unset=True)
        
        # Update status timestamp if status is changing to completed
        if 'status' in update_data and update_data['status'] == JobStatus.COMPLETED:
            update_data['completed_at'] = func.now()
        
        for field, value in update_data.items():
            setattr(db_job, field, value)
        
        self.db.commit()
        self.db.refresh(db_job)
        
        logger.info(f"Updated job {db_job.job_number} by user {updated_by.email}")
        return db_job

    def update_job_status(self, job_id: int, status_update: JobStatusUpdate, updated_by: UserModel) -> Job:
        """Update job status with notes"""
        db_job = self.get_job(job_id)
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Update status and notes based on the new status
        if status_update.status == JobStatus.DIAGNOSING and status_update.notes:
            db_job.diagnosis_notes = status_update.notes
        elif status_update.status == JobStatus.REPAIRING and status_update.notes:
            db_job.repair_notes = status_update.notes
        
        db_job.status = status_update.status
        
        # Set completed timestamp if job is marked as completed
        if status_update.status == JobStatus.COMPLETED:
            db_job.completed_at = func.now()
        
        self.db.commit()
        self.db.refresh(db_job)
        
        logger.info(f"Updated job {db_job.job_number} status to {status_update.status}")
        return db_job

    def update_job_cost(self, job_id: int, cost_update: JobCostUpdate, updated_by: UserModel) -> Job:
        """Update job actual cost"""
        db_job = self.get_job(job_id)
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        db_job.actual_cost = cost_update.actual_cost
        if cost_update.repair_notes:
            db_job.repair_notes = cost_update.repair_notes
        
        self.db.commit()
        self.db.refresh(db_job)
        
        logger.info(f"Updated job {db_job.job_number} cost to {cost_update.actual_cost}")
        return db_job

    def assign_mechanic(self, job_id: int, assignment: JobAssignment, assigned_by: UserModel) -> Job:
        """Assign mechanic to job"""
        db_job = self.get_job(job_id)
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Verify the assigned user is a mechanic
        mechanic = self.db.query(UserModel).filter(
            UserModel.id == assignment.assigned_mechanic_id,
            UserModel.role.has(Role.name == "mechanic")
        ).first()
        
        if not mechanic:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not a mechanic"
            )
        
        db_job.assigned_mechanic_id = assignment.assigned_mechanic_id
        self.db.commit()
        self.db.refresh(db_job)
        
        logger.info(f"Assigned mechanic {mechanic.name} to job {db_job.job_number}")
        return db_job

    def get_job_stats(self, user_id: Optional[int] = None, user_role: Optional[str] = None) -> Dict:
        """Get job statistics"""
        query = self.db.query(Job.status, func.count(Job.id))
        
        # Apply access control
        if user_role == "customer" and user_id:
            query = query.filter(Job.customer_user_id == user_id)
        elif user_role == "mechanic" and user_id:
            query = query.filter(Job.assigned_mechanic_id == user_id)
        
        stats = query.group_by(Job.status).all()
        
        total = sum(count for status, count in stats)
        stats_dict = {
            'total_jobs': total,
            'diagnosing': 0,
            'repairing': 0,
            'waiting_for_parts': 0,
            'ready': 0,
            'completed': 0
        }
        
        for status, count in stats:
            stats_dict[status.value] = count
        
        return stats_dict

    def job_to_response(self, job: Job) -> Dict:
        """Convert Job model to response dictionary"""
        return {
            "id": job.id,
            "job_number": job.job_number,
            "customer_name": job.customer_name,
            "customer_phone": job.customer_phone,
            "customer_email": job.customer_email,
            "vehicle_name": job.vehicle_name,
            "motorcycle_numberplate": job.motorcycle_numberplate,
            "problem_description": job.problem_description,
            "diagnosis_notes": job.diagnosis_notes,
            "repair_notes": job.repair_notes,
            "estimated_cost": job.estimated_cost,
            "actual_cost": job.actual_cost,
            "status": job.status,
            "priority": job.priority,
            "assigned_mechanic_id": job.assigned_mechanic_id,
            "assigned_mechanic_name": job.assigned_mechanic.name if job.assigned_mechanic else None,
            "created_by_id": job.created_by_id,
            "created_by_name": job.created_by.name,
            "customer_user_id": job.customer_user_id,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "completed_at": job.completed_at
        }


    def get_jobs_public(
        self,
        customer_phone: str,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Dict], int]:
        """Get jobs by phone number - PUBLIC (no auth required)
        Used for customer tracking without login
        """
        query = self.db.query(Job)
        
        # Clean phone number - remove spaces, dashes, etc.
        clean_phone = ''.join(filter(str.isdigit, customer_phone))
        
        # Search by phone number (flexible matching)
        query = query.filter(
            or_(
                Job.customer_phone.ilike(f"%{customer_phone}%"),
                Job.customer_phone.ilike(f"%{clean_phone}%")
            )
        )
        
        # Order by creation date (newest first)
        query = query.order_by(Job.created_at.desc())
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        raw_jobs = query.offset(skip).limit(limit).all()
        jobs = [self.job_to_response(job) for job in raw_jobs]
        
        return jobs, total

# Dependency injection
def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db)
