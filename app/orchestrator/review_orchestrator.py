"""
Review Orchestrator - Coordinates multi-agent code review
"""
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

from app.agents import (
    SecurityAgent,
    PerformanceAgent,
    CodeQualityAgent,
    LogicAgent,
    DocumentationAgent
)
from app.services.diff_parser import DiffParser, FileDiff
from app.services.llm_provider import get_llm
from app.services.github_client import GitHubClient


class ReviewOrchestrator:
    """
    Orchestrates the multi-agent code review process.
    Coordinates multiple specialized agents to analyze code changes.
    """
    
    def __init__(
        self,
        llm_api_key: str,
        github_client: Optional[GitHubClient] = None,
        enable_security: bool = True,
        enable_performance: bool = True,
        enable_code_quality: bool = True,
        enable_logic: bool = True,
        enable_documentation: bool = True
    ):
        self.llm = get_llm(api_key=llm_api_key)
        self.github_client = github_client
        self.diff_parser = DiffParser()
        
        # Initialize agents based on configuration
        self.agents = []
        
        if enable_security:
            self.agents.append(SecurityAgent(self.llm))
        if enable_performance:
            self.agents.append(PerformanceAgent(self.llm))
        if enable_code_quality:
            self.agents.append(CodeQualityAgent(self.llm))
        if enable_logic:
            self.agents.append(LogicAgent(self.llm))
        if enable_documentation:
            self.agents.append(DocumentationAgent(self.llm))
    
    def _prepare_code_context(self, file_diff: FileDiff) -> Dict[str, Any]:
        """Prepare code context for agent analysis"""
        # Get all additions
        additions = []
        for hunk in file_diff.hunks:
            for line in hunk.lines:
                if line.change_type == 'addition':
                    additions.append({
                        "line_number": line.line_number,
                        "content": line.content
                    })
        
        # Build diff content string
        diff_lines = []
        for hunk in file_diff.hunks:
            diff_lines.append(f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@ {hunk.header}")
            for line in hunk.lines:
                prefix = {
                    'addition': '+',
                    'deletion': '-',
                    'context': ' '
                }.get(line.change_type, ' ')
                diff_lines.append(f"{prefix}{line.content}")
        
        return {
            "file_path": file_diff.file_path,
            "language": file_diff.language,
            "is_new_file": file_diff.is_new_file,
            "is_deleted_file": file_diff.is_deleted_file,
            "additions": additions,
            "diff_content": "\n".join(diff_lines)
        }
    
    def _run_agent(self, agent, code_context: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single agent on code context"""
        try:
            return agent.run(code_context)
        except Exception as e:
            return {
                "agent_name": agent.name,
                "findings": [],
                "execution_time_seconds": 0,
                "error": str(e)
            }
    
    def review_diff(self, diff_content: str, parallel: bool = True) -> Dict[str, Any]:
        """
        Review a diff string using all enabled agents.
        
        Args:
            diff_content: The raw diff string
            parallel: Whether to run agents in parallel
            
        Returns:
            Dictionary containing all findings and metadata
        """
        start_time = time.time()
        
        # Parse the diff
        file_diffs = self.diff_parser.parse(diff_content)
        
        if not file_diffs:
            return {
                "success": True,
                "message": "No changes to review",
                "files_reviewed": 0,
                "findings": [],
                "execution_time_seconds": time.time() - start_time
            }
        
        all_findings = []
        agent_results = []
        
        # Process each file
        for file_diff in file_diffs:
            # Skip deleted files and non-code files
            if file_diff.is_deleted_file:
                continue
            
            code_context = self._prepare_code_context(file_diff)
            
            # Skip files with no additions
            if not code_context["additions"]:
                continue
            
            if parallel:
                # Run agents in parallel for each file
                with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
                    futures = {
                        executor.submit(self._run_agent, agent, code_context): agent
                        for agent in self.agents
                    }
                    
                    for future in as_completed(futures):
                        result = future.result()
                        agent_results.append(result)
                        all_findings.extend(result.get("findings", []))
            else:
                # Run agents sequentially
                for agent in self.agents:
                    result = self._run_agent(agent, code_context)
                    agent_results.append(result)
                    all_findings.extend(result.get("findings", []))
        
        # Sort findings by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        all_findings.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 4))
        
        # Generate summary
        summary = self._generate_summary(all_findings)
        
        total_time = time.time() - start_time
        
        return {
            "success": True,
            "files_reviewed": len([f for f in file_diffs if not f.is_deleted_file]),
            "total_additions": sum(f.additions for f in file_diffs),
            "total_deletions": sum(f.deletions for f in file_diffs),
            "findings": all_findings,
            "agent_results": agent_results,
            "summary": summary,
            "execution_time_seconds": total_time
        }
    
    def review_github_pr(
        self,
        owner: str,
        repo_name: str,
        pr_number: int,
        post_comments: bool = False
    ) -> Dict[str, Any]:
        """
        Review a GitHub PR using all enabled agents.
        
        Args:
            owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number
            post_comments: Whether to post comments back to GitHub
            
        Returns:
            Dictionary containing all findings and metadata
        """
        if not self.github_client:
            raise ValueError("GitHub client not configured")
        
        start_time = time.time()
        
        # Get PR info
        pr_info = self.github_client.get_pr_info(owner, repo_name, pr_number)
        
        # Get PR diff
        diff_content = self.github_client.get_pr_diff(owner, repo_name, pr_number)
        
        # Run the review
        review_result = self.review_diff(diff_content, parallel=True)
        
        # Add PR metadata
        review_result["pr_info"] = pr_info
        
        # Post comments if requested
        if post_comments and review_result["findings"]:
            try:
                comment_body = self._format_review_comment(review_result)
                comment_result = self.github_client.create_pr_comment(
                    owner, repo_name, pr_number, comment_body
                )
                review_result["github_comment"] = comment_result
            except Exception as e:
                review_result["github_comment_error"] = str(e)
        
        review_result["execution_time_seconds"] = time.time() - start_time
        
        return review_result
    
    def _generate_summary(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from findings"""
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        category_counts = {
            "security": 0,
            "performance": 0,
            "logic": 0,
            "code_quality": 0,
            "documentation": 0
        }
        
        for finding in findings:
            severity = finding.get("severity", "info")
            category = finding.get("category", "code_quality")
            
            if severity in severity_counts:
                severity_counts[severity] += 1
            if category in category_counts:
                category_counts[category] += 1
        
        # Determine overall rating
        if severity_counts["critical"] > 0:
            overall = "needs_work"
        elif severity_counts["high"] > 2:
            overall = "needs_work"
        elif severity_counts["high"] > 0 or severity_counts["medium"] > 5:
            overall = "changes_requested"
        elif severity_counts["medium"] > 0:
            overall = "comment"
        else:
            overall = "approve"
        
        return {
            "total_issues": len(findings),
            "severity_counts": severity_counts,
            "category_counts": category_counts,
            "overall_rating": overall
        }
    
    def _format_review_comment(self, review_result: Dict[str, Any]) -> str:
        """Format review results as a GitHub comment"""
        findings = review_result.get("findings", [])
        summary = review_result.get("summary", {})
        
        # Build the comment
        lines = [
            "## 🤖 Automated Code Review",
            "",
            f"**Files Reviewed:** {review_result.get('files_reviewed', 0)}",
            f"**Total Issues Found:** {summary.get('total_issues', 0)}",
            ""
        ]
        
        # Add severity breakdown
        severity_counts = summary.get("severity_counts", {})
        lines.append("### Issue Summary")
        lines.append("")
        lines.append(f"- 🔴 Critical: {severity_counts.get('critical', 0)}")
        lines.append(f"- 🟠 High: {severity_counts.get('high', 0)}")
        lines.append(f"- 🟡 Medium: {severity_counts.get('medium', 0)}")
        lines.append(f"- 🔵 Low: {severity_counts.get('low', 0)}")
        lines.append(f"- ℹ️ Info: {severity_counts.get('info', 0)}")
        lines.append("")
        
        # Add findings by category
        if findings:
            lines.append("### Detailed Findings")
            lines.append("")
            
            # Group findings by file
            files_findings = {}
            for finding in findings:
                file_path = finding.get("file_path", "unknown")
                if file_path not in files_findings:
                    files_findings[file_path] = []
                files_findings[file_path].append(finding)
            
            for file_path, file_findings in files_findings.items():
                lines.append(f"#### 📄 `{file_path}`")
                lines.append("")
                
                for finding in file_findings:
                    severity_emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🔵",
                        "info": "ℹ️"
                    }.get(finding.get("severity", "info"), "ℹ️")
                    
                    category = finding.get("category", "").replace("_", " ").title()
                    line_num = finding.get("line_number", "")
                    line_str = f" (Line {line_num})" if line_num else ""
                    
                    lines.append(f"{severity_emoji} **{finding.get('title', 'Issue')}**{line_str}")
                    lines.append(f"   - *Category:* {category}")
                    lines.append(f"   - {finding.get('description', '')}")
                    
                    if finding.get("suggested_code"):
                        lines.append(f"   - *Suggestion:* `{finding.get('suggested_code')}`")
                    
                    lines.append("")
        
        # Add footer
        lines.append("---")
        lines.append("*Generated by PR Review Agent 🤖*")
        
        return "\n".join(lines)


def create_orchestrator(
    llm_api_key: str,
    github_token: Optional[str] = None,
    **kwargs
) -> ReviewOrchestrator:
    """Factory function to create a review orchestrator"""
    github_client = None
    if github_token:
        from app.services.github_client import get_github_client
        github_client = get_github_client(github_token)
    
    return ReviewOrchestrator(
        llm_api_key=llm_api_key,
        github_client=github_client,
        **kwargs
    )
