"""
GitHub Integration - Fetch PRs, diffs, and post review comments
"""
from github import Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository
from typing import Dict, Any, List, Optional
import requests


class GitHubClient:
    """Client for interacting with GitHub API"""
    
    def __init__(self, token: str):
        if not token:
            raise ValueError("GitHub token is required")
        
        self.token = token
        self.github = Github(token)
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def get_repository(self, owner: str, repo_name: str) -> Repository:
        """Get a repository by owner and name"""
        try:
            return self.github.get_repo(f"{owner}/{repo_name}")
        except GithubException as e:
            raise Exception(f"Failed to get repository {owner}/{repo_name}: {e}")
    
    def get_pull_request(self, owner: str, repo_name: str, pr_number: int) -> PullRequest:
        """Get a pull request by number"""
        try:
            repo = self.get_repository(owner, repo_name)
            return repo.get_pull(pr_number)
        except GithubException as e:
            raise Exception(f"Failed to get PR #{pr_number}: {e}")
    
    def get_pr_info(self, owner: str, repo_name: str, pr_number: int) -> Dict[str, Any]:
        """Get detailed PR information"""
        pr = self.get_pull_request(owner, repo_name, pr_number)
        
        return {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "state": pr.state,
            "author": pr.user.login if pr.user else "unknown",
            "url": pr.html_url,
            "head_sha": pr.head.sha,
            "base_sha": pr.base.sha,
            "head_branch": pr.head.ref,
            "base_branch": pr.base.ref,
            "created_at": pr.created_at.isoformat() if pr.created_at else None,
            "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "mergeable": pr.mergeable,
            "merged": pr.merged
        }
    
    def get_pr_diff(self, owner: str, repo_name: str, pr_number: int) -> str:
        """Get the raw diff content of a PR"""
        url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls/{pr_number}"
        headers = {
            **self.headers,
            "Accept": "application/vnd.github.v3.diff"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Failed to get PR diff: {response.status_code} - {response.text}")
    
    def get_pr_files(self, owner: str, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get list of files changed in a PR"""
        pr = self.get_pull_request(owner, repo_name, pr_number)
        files = pr.get_files()
        
        return [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
                "patch": f.patch if hasattr(f, 'patch') and f.patch else "",
                "blob_url": f.blob_url,
                "raw_url": f.raw_url
            }
            for f in files
        ]
    
    def get_file_content(self, owner: str, repo_name: str, file_path: str, ref: str) -> str:
        """Get content of a file at a specific ref"""
        try:
            repo = self.get_repository(owner, repo_name)
            content = repo.get_contents(file_path, ref=ref)
            return content.decoded_content.decode('utf-8')
        except GithubException as e:
            raise Exception(f"Failed to get file content: {e}")
    
    def create_pr_review(
        self,
        owner: str,
        repo_name: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a PR review with optional inline comments
        
        Args:
            owner: Repository owner
            repo_name: Repository name
            pr_number: PR number
            body: Review body text
            event: Review event (COMMENT, APPROVE, REQUEST_CHANGES)
            comments: List of inline comments with path, position, and body
        """
        pr = self.get_pull_request(owner, repo_name, pr_number)
        
        try:
            if comments:
                # Create review with inline comments
                review = pr.create_review(
                    body=body,
                    event=event,
                    comments=comments
                )
            else:
                # Create review without inline comments
                review = pr.create_review(
                    body=body,
                    event=event
                )
            
            return {
                "id": review.id,
                "state": review.state,
                "body": review.body,
                "html_url": review.html_url
            }
        except GithubException as e:
            raise Exception(f"Failed to create review: {e}")
    
    def create_pr_comment(
        self,
        owner: str,
        repo_name: str,
        pr_number: int,
        body: str
    ) -> Dict[str, Any]:
        """Create a general comment on a PR"""
        pr = self.get_pull_request(owner, repo_name, pr_number)
        
        try:
            comment = pr.create_issue_comment(body)
            return {
                "id": comment.id,
                "body": comment.body,
                "html_url": comment.html_url
            }
        except GithubException as e:
            raise Exception(f"Failed to create comment: {e}")
    
    def create_review_comment(
        self,
        owner: str,
        repo_name: str,
        pr_number: int,
        body: str,
        commit_sha: str,
        path: str,
        line: int
    ) -> Dict[str, Any]:
        """Create an inline review comment on a specific line"""
        pr = self.get_pull_request(owner, repo_name, pr_number)
        
        try:
            comment = pr.create_review_comment(
                body=body,
                commit=pr.head.sha if not commit_sha else commit_sha,
                path=path,
                line=line
            )
            return {
                "id": comment.id,
                "body": comment.body,
                "path": comment.path,
                "line": comment.line,
                "html_url": comment.html_url
            }
        except GithubException as e:
            raise Exception(f"Failed to create review comment: {e}")
    
    def validate_token(self) -> bool:
        """Validate that the GitHub token is working"""
        try:
            user = self.github.get_user()
            _ = user.login
            return True
        except GithubException:
            return False
    
    def get_rate_limit(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        try:
            rate_limit = self.github.get_rate_limit()
            core = rate_limit.core
            search = rate_limit.search
            return {
                "core": {
                    "limit": core.limit,
                    "remaining": core.remaining,
                    "reset": core.reset.isoformat() if core.reset else None
                },
                "search": {
                    "limit": search.limit,
                    "remaining": search.remaining,
                    "reset": search.reset.isoformat() if search.reset else None
                }
            }
        except Exception:
            # Fallback for different PyGithub versions
            return {"core": {"limit": 5000, "remaining": 5000, "reset": None}, "search": {"limit": 30, "remaining": 30, "reset": None}}


def get_github_client(token: str) -> GitHubClient:
    """Factory function to create GitHub client"""
    return GitHubClient(token)
