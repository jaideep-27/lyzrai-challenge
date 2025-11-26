"""
Pydantic schemas for API request/response models
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ReviewStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class IssueSeverityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategoryEnum(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    CODE_QUALITY = "code_quality"
    BEST_PRACTICE = "best_practice"
    DOCUMENTATION = "documentation"


# Request schemas
class PRReviewRequest(BaseModel):
    """Request to review a GitHub PR"""
    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    pr_number: int = Field(..., description="Pull request number")
    github_token: Optional[str] = Field(None, description="Optional GitHub token override")


class ManualDiffReviewRequest(BaseModel):
    """Request to review a manually provided diff"""
    diff_content: str = Field(..., description="The diff content to review")
    file_name: Optional[str] = Field("unknown", description="Optional filename for context")
    language: Optional[str] = Field(None, description="Programming language hint")


# Response schemas
class ReviewCommentSchema(BaseModel):
    """Schema for a single review comment"""
    id: Optional[int] = None
    file_path: str
    line_number: Optional[int] = None
    line_range_start: Optional[int] = None
    line_range_end: Optional[int] = None
    category: IssueCategoryEnum
    severity: IssueSeverityEnum
    title: str
    description: str
    original_code: Optional[str] = None
    suggested_code: Optional[str] = None
    agent_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class PRReviewResponse(BaseModel):
    """Response for a PR review"""
    id: int
    repo_owner: str
    repo_name: str
    pr_number: int
    pr_title: Optional[str] = None
    pr_author: Optional[str] = None
    pr_url: Optional[str] = None
    status: ReviewStatusEnum
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_files_changed: int
    total_additions: int
    total_deletions: int
    overall_summary: Optional[str] = None
    comments: List[ReviewCommentSchema] = []
    
    class Config:
        from_attributes = True


class ReviewSummary(BaseModel):
    """Summary of a code review"""
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    security_issues: int
    performance_issues: int
    logic_issues: int
    code_quality_issues: int
    summary_text: str


class AgentOutput(BaseModel):
    """Output from a single agent"""
    agent_name: str
    findings: List[ReviewCommentSchema]
    execution_time_seconds: float
    error: Optional[str] = None


class ParsedDiff(BaseModel):
    """Parsed diff information"""
    file_path: str
    language: Optional[str] = None
    additions: int
    deletions: int
    hunks: List[dict]
    changed_lines: List[dict]


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    database_connected: bool
    github_configured: bool
    llm_configured: bool
