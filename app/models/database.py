"""
Database models for PR Review Agent
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

Base = declarative_base()


class ReviewStatus(str, enum.Enum):
    """Status of a PR review"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class IssueSeverity(str, enum.Enum):
    """Severity levels for identified issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, enum.Enum):
    """Categories of code issues"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    CODE_QUALITY = "code_quality"
    BEST_PRACTICE = "best_practice"
    DOCUMENTATION = "documentation"


class PullRequestReview(Base):
    """Model for storing PR review sessions"""
    __tablename__ = "pull_request_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # GitHub PR details
    repo_owner = Column(String(255), nullable=False)
    repo_name = Column(String(255), nullable=False)
    pr_number = Column(Integer, nullable=False)
    pr_title = Column(String(500))
    pr_author = Column(String(255))
    pr_url = Column(String(500))
    
    # Review metadata
    status = Column(String(50), default=ReviewStatus.PENDING.value)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Summary
    total_files_changed = Column(Integer, default=0)
    total_additions = Column(Integer, default=0)
    total_deletions = Column(Integer, default=0)
    overall_summary = Column(Text, nullable=True)
    
    # Raw data
    diff_content = Column(Text, nullable=True)
    
    # Relationships
    comments = relationship("ReviewComment", back_populates="review", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PullRequestReview {self.repo_owner}/{self.repo_name}#{self.pr_number}>"


class ReviewComment(Base):
    """Model for individual review comments"""
    __tablename__ = "review_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("pull_request_reviews.id"), nullable=False)
    
    # Location
    file_path = Column(String(500), nullable=False)
    line_number = Column(Integer, nullable=True)
    line_range_start = Column(Integer, nullable=True)
    line_range_end = Column(Integer, nullable=True)
    
    # Issue details
    category = Column(String(50), default=IssueCategory.CODE_QUALITY.value)
    severity = Column(String(50), default=IssueSeverity.MEDIUM.value)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    
    # Code context
    original_code = Column(Text, nullable=True)
    suggested_code = Column(Text, nullable=True)
    
    # Agent that found the issue
    agent_name = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    review = relationship("PullRequestReview", back_populates="comments")
    
    def __repr__(self):
        return f"<ReviewComment {self.file_path}:{self.line_number} - {self.title}>"


class AgentExecution(Base):
    """Model for tracking agent executions"""
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("pull_request_reviews.id"), nullable=False)
    
    agent_name = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Execution details
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    status = Column(String(50), default="pending")


# Database setup functions
def get_engine(database_url: str):
    """Create database engine"""
    return create_engine(
        database_url,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
    )


def create_session(engine):
    """Create session factory"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def init_db(database_url: str):
    """Initialize database tables"""
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine


def get_db_session(engine):
    """Get database session context manager"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
