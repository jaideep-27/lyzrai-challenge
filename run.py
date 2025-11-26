#!/usr/bin/env python
"""
Run the PR Review Agent server
"""
import uvicorn
from app.main import app

# Export app for Vercel
app = app


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
