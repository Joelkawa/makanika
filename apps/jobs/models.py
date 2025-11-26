from core.database import Base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class JobStatus(str,enum.Enum):
    DIAGNOSING = "DIAGNOSING"
    REPAIRING = "REPAIRING"
    WAITING_FOR_PARTS = "WAITING_FOR_PARTS"
    READY = "READY"
    COMPLETED = "COMPLETED"
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_number = Column(String(50), unique=True, index=True, nullable=False)
    
    # Customer information
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(255), nullable=True)
    
    # Vehicle information
    vehicle_name = Column(String(255), nullable=False)
    motorcycle_numberplate = Column(String(50), nullable=False)
    
    # Job details
    problem_description = Column(Text, nullable=False)
    diagnosis_notes = Column(Text, nullable=True)
    repair_notes = Column(Text, nullable=True)
    
    # Financial information
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    
    # Status and tracking
    status = Column(SQLEnum(JobStatus), default=JobStatus.DIAGNOSING)
    priority = Column(Integer, default=1)  # 1=Low, 2=Medium, 3=High, 4=Urgent
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    assigned_mechanic_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_mechanic = relationship("UserModel", foreign_keys=[assigned_mechanic_id])
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = relationship("UserModel", foreign_keys=[created_by_id])
    
    # Customer user account reference (if created)
    customer_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    customer_user = relationship("UserModel", foreign_keys=[customer_user_id])