"""GitHubService for GitHub API operations."""
import asyncio
from typing import Optional, Dict, Any, List

import structlog

from src.core.exceptions import (
    GitHubAPIError,
    GitHubBranchExistsError,
    GitHubRateLimitError
)

# Initialize structured logger
logger = structlog.get_logger(__name__)


class GitHubService:
    """Service for GitHub API operations: branches, commits, PRs, comments."""
    
    def __init__(self, github_client, config):
        """Initialize GitHubService.
        
        Args:
            github_client: GitHub client for API operations
            config: Configuration object with GitHub settings
        """
        self.github_client = github_client
        self.config = config
        self.repo_name = getattr(config, 'GITHUB_REPO', 'owner/repo')
        
    async def create_branch(
        self,
        branch_name: str,
        base_branch: str = "main"
    ) -> None:
        """Create a new branch in the repository.
        
        Args:
            branch_name: Name of the branch to create
            base_branch: Base branch to branch from (default: main)
            
        Raises:
            GitHubBranchExistsError: If branch already exists (E402)
            GitHubAPIError: If API request fails (E406)
            GitHubRateLimitError: If rate limit exceeded (E405)
        """
        log = logger.bind(
            operation="create_branch",
            branch_name=branch_name,
            base_branch=base_branch,
            repository=self.repo_name
        )
        
        log.info("github_create_branch_started")
        
        try:
            await self.github_client.create_branch(
                branch_name=branch_name,
                base_branch=base_branch
            )
            
            log.info("github_create_branch_completed")
            
        except GitHubBranchExistsError as e:
            log.warning("github_create_branch_exists")
            raise
        except GitHubRateLimitError as e:
            log.error("github_create_branch_rate_limit")
            raise
        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(
                message=f"Failed to create branch: {str(e)}",
                details={"branch": branch_name, "error": str(e)}
            )
    
    async def commit_file(
        self,
        file_path: str,
        content: str,
        branch_name: str,
        commit_message: str
    ) -> None:
        """Commit a file to a branch.
        
        Args:
            file_path: Path to the file in the repository
            content: File content to commit
            branch_name: Branch to commit to
            commit_message: Commit message
            
        Raises:
            GitHubAPIError: If API request fails (E406)
        """
        try:
            await self.github_client.create_or_update_file(
                file_path=file_path,
                content=content,
                branch_name=branch_name,
                commit_message=commit_message
            )
        except Exception as e:
            raise GitHubAPIError(
                message=f"Failed to commit file: {str(e)}",
                details={"file_path": file_path, "branch": branch_name, "error": str(e)}
            )
    
    async def create_pr(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        """Create a pull request.
        
        Args:
            title: PR title
            body: PR body/description
            head_branch: Source branch
            base_branch: Target branch (default: main)
            
        Returns:
            PR data dict with number, html_url, state, etc.
            
        Raises:
            GitHubAPIError: If API request fails (E406)
        """
        log = logger.bind(
            operation="create_pr",
            head_branch=head_branch,
            base_branch=base_branch,
            repository=self.repo_name
        )
        
        log.info(
            "github_create_pr_started",
            title=title
        )
        
        try:
            pr_data = await self.github_client.create_pull_request(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            log.info(
                "github_create_pr_completed",
                pr_number=pr_data.get("number"),
                pr_url=pr_data.get("html_url")
            )
            
            return pr_data
            
        except Exception as e:
            log.error(
                "github_create_pr_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise GitHubAPIError(
                message=f"Failed to create pull request: {str(e)}",
                details={"title": title, "head": head_branch, "error": str(e)}
            )
    
    async def create_pr_for_issue(
        self,
        issue_number: int,
        branch_name: str,
        title: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a pull request that closes an issue.
        
        Args:
            issue_number: Issue number to close
            branch_name: Source branch
            title: PR title
            additional_context: Optional additional context to include in body
            
        Returns:
            PR data dict with number, html_url, etc.
        """
        body = f"Automated test case generation for issue #{issue_number}.\n\n"
        if additional_context:
            body += f"{additional_context}\n\n"
        body += f"Closes #{issue_number}"
        
        return await self.create_pr(
            title=title,
            body=body,
            head_branch=branch_name,
            base_branch=self.get_default_branch()
        )
    
    async def add_comment(
        self,
        issue_number: int,
        comment: str
    ) -> None:
        """Add a comment to an issue.
        
        Args:
            issue_number: Issue number to comment on
            comment: Comment text
            
        Raises:
            GitHubAPIError: If API request fails (E406)
        """
        log = logger.bind(
            operation="add_comment",
            issue_number=issue_number,
            repository=self.repo_name
        )
        
        log.info(
            "github_add_comment_started",
            comment_length=len(comment)
        )
        
        try:
            await self.github_client.add_issue_comment(
                issue_number=issue_number,
                comment=comment
            )
            
            log.info("github_add_comment_completed")
            
        except Exception as e:
            log.error(
                "github_add_comment_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise GitHubAPIError(
                message=f"Failed to add comment: {str(e)}",
                details={"issue_number": issue_number, "error": str(e)}
            )
    
    async def create_branch_with_retry(
        self,
        branch_name: str,
        base_branch: str = "main",
        max_retries: int = 3
    ) -> None:
        """Create a branch with retry logic for transient errors.
        
        Args:
            branch_name: Name of the branch to create
            base_branch: Base branch to branch from
            max_retries: Maximum number of retry attempts
            
        Raises:
            GitHubBranchExistsError: If branch already exists (no retry)
            GitHubAPIError: If all retries exhausted
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                await self.create_branch(branch_name, base_branch)
                return
            except GitHubBranchExistsError:
                # Don't retry if branch exists
                raise
            except GitHubRateLimitError:
                # Don't retry rate limit errors
                raise
            except GitHubAPIError as e:
                last_error = e
                # Check if it's a transient error (5xx)
                status = e.details.get("status", 0)
                if status >= 500 and attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
        
        if last_error:
            raise last_error
    
    def generate_branch_name(self, issue_number: int) -> str:
        """Generate branch name for an issue.
        
        Args:
            issue_number: Issue number
            
        Returns:
            Branch name in format 'test-cases/issue-{number}'
        """
        return f"test-cases/issue-{issue_number}"
    
    def generate_file_path(self, issue_number: int) -> str:
        """Generate file path for test case document.
        
        Args:
            issue_number: Issue number
            
        Returns:
            File path in format 'test-cases/issue-{number}.md'
        """
        return f"test-cases/issue-{issue_number}.md"
    
    def generate_commit_message(self, issue_number: int) -> str:
        """Generate commit message for test case commit.
        
        Args:
            issue_number: Issue number
            
        Returns:
            Commit message
        """
        return f"Add test cases for issue #{issue_number}"
    
    def generate_pr_body(
        self,
        issue_number: int,
        issue_title: str,
        context_sources: Optional[List[int]] = None
    ) -> str:
        """Generate PR body with issue reference and context.
        
        Args:
            issue_number: Issue number to close
            issue_title: Issue title
            context_sources: List of issue numbers used as context
            
        Returns:
            Formatted PR body
        """
        body = f"Automated test case generation for: **{issue_title}**\n\n"
        
        if context_sources:
            body += "### Context Sources\n"
            body += "Generated using similar test cases from:\n"
            for source in context_sources:
                body += f"- Issue #{source}\n"
            body += "\n"
        
        body += f"Closes #{issue_number}"
        
        return body
    
    def get_default_branch(self) -> str:
        """Get the repository's default branch.
        
        Returns:
            Default branch name (usually 'main' or 'master')
        """
        try:
            repo = self.github_client.get_repo()
            return repo.default_branch
        except:
            # Fallback to 'main' if we can't get repo info
            return "main"
    
    def validate_permissions(self) -> bool:
        """Validate GitHub token has required permissions.
        
        Returns:
            True if token has push and pull permissions
        """
        try:
            repo = self.github_client.get_repo()
            return repo.permissions.push and repo.permissions.pull
        except:
            return False
