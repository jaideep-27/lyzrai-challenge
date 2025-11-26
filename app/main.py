"""
FastAPI Application - Main entry point
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from typing import Optional, List
from datetime import datetime
import os
from pathlib import Path

from app.config import settings
from app.models.schemas import (
    PRReviewRequest,
    ManualDiffReviewRequest,
    PRReviewResponse,
    ReviewCommentSchema,
    HealthCheckResponse,
    ReviewSummary
)
from app.orchestrator import create_orchestrator

# Check if we're in serverless environment (Vercel)
IS_SERVERLESS = os.environ.get('VERCEL', False) or os.environ.get('AWS_LAMBDA_FUNCTION_NAME', False)

# Only import database if not serverless
if not IS_SERVERLESS:
    from app.models.database import init_db, get_engine, create_session, PullRequestReview, ReviewComment, ReviewStatus

# Initialize FastAPI app
app = FastAPI(
    title="PR Review Agent",
    description="Automated GitHub Pull Request Review Agent with Multi-Agent Architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
engine = None
SessionLocal = None


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    global engine, SessionLocal
    if not IS_SERVERLESS:
        engine = init_db(settings.database_url)
        SessionLocal = create_session(engine)


def get_db():
    """Database session dependency"""
    if IS_SERVERLESS or SessionLocal is None:
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse, tags=["System"])
async def health_check():
    """Check system health status"""
    db_connected = False
    
    if not IS_SERVERLESS and SessionLocal:
        try:
            from sqlalchemy import text
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db_connected = True
            db.close()
        except:
            pass
    
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        database_connected=db_connected,
        github_configured=bool(settings.github_token),
        llm_configured=bool(settings.google_api_key)
    )


# Review GitHub PR
@app.post("/api/review/github", tags=["Review"])
async def review_github_pr(
    request: PRReviewRequest,
    background_tasks: BackgroundTasks,
    post_to_github: bool = Query(False, description="Post review comments to GitHub"),
    db=Depends(get_db)
):
    """
    Trigger a review of a GitHub Pull Request.
    
    This endpoint:
    1. Fetches the PR diff from GitHub
    2. Parses the changes
    3. Runs multi-agent analysis (Security, Performance, Logic, Code Quality, Documentation)
    4. Returns structured review comments
    5. Optionally posts comments back to GitHub
    """
    github_token = request.github_token or settings.github_token
    
    if not github_token:
        raise HTTPException(
            status_code=400,
            detail="GitHub token is required. Provide it in the request or set GITHUB_TOKEN environment variable."
        )
    
    if not settings.google_api_key:
        raise HTTPException(
            status_code=500,
            detail="LLM API key not configured. Set GOOGLE_API_KEY environment variable."
        )
    
    try:
        # Create orchestrator
        orchestrator = create_orchestrator(
            llm_api_key=settings.google_api_key,
            github_token=github_token
        )
        
        review_record = None
        review_id = None
        
        # Create DB record only if database is available
        if db and not IS_SERVERLESS:
            from app.models.database import PullRequestReview, ReviewComment, ReviewStatus
            review_record = PullRequestReview(
                repo_owner=request.repo_owner,
                repo_name=request.repo_name,
                pr_number=request.pr_number,
                status=ReviewStatus.IN_PROGRESS.value
            )
            db.add(review_record)
            db.commit()
            db.refresh(review_record)
            review_id = review_record.id
        
        # Run the review
        result = orchestrator.review_github_pr(
            owner=request.repo_owner,
            repo_name=request.repo_name,
            pr_number=request.pr_number,
            post_comments=post_to_github
        )
        
        # Update DB record with PR info if available
        if review_record and db:
            from app.models.database import ReviewComment, ReviewStatus
            pr_info = result.get("pr_info", {})
            review_record.pr_title = pr_info.get("title")
            review_record.pr_author = pr_info.get("author")
            review_record.pr_url = pr_info.get("url")
            review_record.total_files_changed = result.get("files_reviewed", 0)
            review_record.total_additions = result.get("total_additions", 0)
            review_record.total_deletions = result.get("total_deletions", 0)
            review_record.status = ReviewStatus.COMPLETED.value
            review_record.completed_at = datetime.utcnow()
            
            # Save summary
            summary = result.get("summary", {})
            review_record.overall_summary = f"Found {summary.get('total_issues', 0)} issues. Rating: {summary.get('overall_rating', 'unknown')}"
            
            # Save comments
            for finding in result.get("findings", []):
                comment = ReviewComment(
                    review_id=review_record.id,
                    file_path=finding.get("file_path", "unknown"),
                    line_number=finding.get("line_number"),
                    line_range_start=finding.get("line_range_start"),
                    line_range_end=finding.get("line_range_end"),
                    category=finding.get("category", "code_quality"),
                    severity=finding.get("severity", "medium"),
                    title=finding.get("title", "Issue"),
                    description=finding.get("description", ""),
                    original_code=finding.get("original_code"),
                    suggested_code=finding.get("suggested_code"),
                    agent_name=finding.get("agent_name")
                )
                db.add(comment)
            
            db.commit()
        
        pr_info = result.get("pr_info", {})
        summary = result.get("summary", {})
        
        return {
            "success": True,
            "review_id": review_id,
            "pr_info": pr_info,
            "files_reviewed": result.get("files_reviewed", 0),
            "summary": summary,
            "findings": result.get("findings", []),
            "execution_time_seconds": result.get("execution_time_seconds", 0),
            "github_comment_posted": post_to_github and "github_comment" in result
        }
        
    except Exception as e:
        # Update status to failed
        if review_record and db:
            from app.models.database import ReviewStatus
            review_record.status = ReviewStatus.FAILED.value
            db.commit()
        
        raise HTTPException(status_code=500, detail=str(e))


# Review raw diff
@app.post("/api/review/diff", tags=["Review"])
async def review_diff(
    request: ManualDiffReviewRequest,
    db=Depends(get_db)
):
    """
    Review a manually provided diff string.
    
    Useful for:
    - Testing the review system without GitHub integration
    - Reviewing local changes before pushing
    - CI/CD pipeline integration
    """
    if not settings.google_api_key:
        raise HTTPException(
            status_code=500,
            detail="LLM API key not configured. Set GOOGLE_API_KEY environment variable."
        )
    
    try:
        # Create orchestrator without GitHub client
        orchestrator = create_orchestrator(
            llm_api_key=settings.google_api_key,
            github_token=None
        )
        
        review_record = None
        review_id = None
        
        # Create DB record only if database is available
        if db and not IS_SERVERLESS:
            from app.models.database import PullRequestReview, ReviewComment, ReviewStatus
            review_record = PullRequestReview(
                repo_owner="manual",
                repo_name="diff",
                pr_number=0,
                status=ReviewStatus.IN_PROGRESS.value,
                diff_content=request.diff_content
            )
            db.add(review_record)
            db.commit()
            db.refresh(review_record)
            review_id = review_record.id
        
        # Run the review
        result = orchestrator.review_diff(request.diff_content)
        
        # Update DB record if available
        if review_record and db:
            from app.models.database import ReviewComment, ReviewStatus
            review_record.total_files_changed = result.get("files_reviewed", 0)
            review_record.total_additions = result.get("total_additions", 0)
            review_record.total_deletions = result.get("total_deletions", 0)
            review_record.status = ReviewStatus.COMPLETED.value
            review_record.completed_at = datetime.utcnow()
            
            # Save summary
            summary = result.get("summary", {})
            review_record.overall_summary = f"Found {summary.get('total_issues', 0)} issues. Rating: {summary.get('overall_rating', 'unknown')}"
            
            # Save comments
            for finding in result.get("findings", []):
                comment = ReviewComment(
                    review_id=review_record.id,
                    file_path=finding.get("file_path", "unknown"),
                    line_number=finding.get("line_number"),
                    line_range_start=finding.get("line_range_start"),
                    line_range_end=finding.get("line_range_end"),
                    category=finding.get("category", "code_quality"),
                    severity=finding.get("severity", "medium"),
                    title=finding.get("title", "Issue"),
                    description=finding.get("description", ""),
                    original_code=finding.get("original_code"),
                    suggested_code=finding.get("suggested_code"),
                    agent_name=finding.get("agent_name")
                )
                db.add(comment)
            
            db.commit()
        
        summary = result.get("summary", {})
        
        return {
            "success": True,
            "review_id": review_id,
            "files_reviewed": result.get("files_reviewed", 0),
            "summary": summary,
            "findings": result.get("findings", []),
            "execution_time_seconds": result.get("execution_time_seconds", 0)
        }
        
    except Exception as e:
        if review_record and db:
            from app.models.database import ReviewStatus
            review_record.status = ReviewStatus.FAILED.value
            db.commit()
        
        raise HTTPException(status_code=500, detail=str(e))


# Get review by ID
@app.get("/api/review/{review_id}", tags=["Review"])
async def get_review(review_id: int, db=Depends(get_db)):
    """Get a specific review by ID"""
    if IS_SERVERLESS or not db:
        raise HTTPException(status_code=501, detail="Database not available in serverless mode")
    
    from app.models.database import PullRequestReview, ReviewComment
    review = db.query(PullRequestReview).filter(PullRequestReview.id == review_id).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    comments = db.query(ReviewComment).filter(ReviewComment.review_id == review_id).all()
    
    return {
        "id": review.id,
        "repo_owner": review.repo_owner,
        "repo_name": review.repo_name,
        "pr_number": review.pr_number,
        "pr_title": review.pr_title,
        "pr_author": review.pr_author,
        "pr_url": review.pr_url,
        "status": review.status,
        "started_at": review.started_at,
        "completed_at": review.completed_at,
        "total_files_changed": review.total_files_changed,
        "total_additions": review.total_additions,
        "total_deletions": review.total_deletions,
        "overall_summary": review.overall_summary,
        "comments": [
            {
                "id": c.id,
                "file_path": c.file_path,
                "line_number": c.line_number,
                "category": c.category,
                "severity": c.severity,
                "title": c.title,
                "description": c.description,
                "original_code": c.original_code,
                "suggested_code": c.suggested_code,
                "agent_name": c.agent_name
            }
            for c in comments
        ]
    }


# List all reviews
@app.get("/api/reviews", tags=["Review"])
async def list_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db)
):
    """List all reviews with pagination"""
    if IS_SERVERLESS or not db:
        return {"total": 0, "skip": skip, "limit": limit, "reviews": [], "message": "History not available in serverless mode"}
    
    from app.models.database import PullRequestReview
    total = db.query(PullRequestReview).count()
    reviews = db.query(PullRequestReview).order_by(
        PullRequestReview.started_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "reviews": [
            {
                "id": r.id,
                "repo_owner": r.repo_owner,
                "repo_name": r.repo_name,
                "pr_number": r.pr_number,
                "pr_title": r.pr_title,
                "status": r.status,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "overall_summary": r.overall_summary
            }
            for r in reviews
        ]
    }


# Delete review
@app.delete("/api/review/{review_id}", tags=["Review"])
async def delete_review(review_id: int, db=Depends(get_db)):
    """Delete a review by ID"""
    if IS_SERVERLESS or not db:
        raise HTTPException(status_code=501, detail="Database not available in serverless mode")
    
    from app.models.database import PullRequestReview
    review = db.query(PullRequestReview).filter(PullRequestReview.id == review_id).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db.delete(review)
    db.commit()
    
    return {"success": True, "message": f"Review {review_id} deleted"}


# Test LLM connection
@app.get("/api/test/llm", tags=["System"])
async def test_llm():
    """Test the LLM connection"""
    if not settings.google_api_key:
        raise HTTPException(status_code=500, detail="LLM API key not configured")
    
    try:
        from app.services.llm_provider import get_llm
        llm = get_llm(api_key=settings.google_api_key)
        response = llm.generate("Say 'Hello, I am working!' in exactly those words.")
        return {"success": True, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Test GitHub connection
@app.get("/api/test/github", tags=["System"])
async def test_github():
    """Test the GitHub API connection"""
    if not settings.github_token:
        raise HTTPException(status_code=500, detail="GitHub token not configured")
    
    try:
        from app.services.github_client import get_github_client
        client = get_github_client(settings.github_token)
        
        if client.validate_token():
            rate_limit = client.get_rate_limit()
            return {"success": True, "rate_limit": rate_limit}
        else:
            raise HTTPException(status_code=401, detail="Invalid GitHub token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve static UI
@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def serve_ui():
    """Serve the web UI"""
    static_path = Path(__file__).parent.parent / "static" / "index.html"
    if static_path.exists():
        return FileResponse(static_path)
    return HTMLResponse("<h1>UI not found. Please access /docs for API documentation.</h1>")
