"""GitHub client wrapper using PyGithub."""

import structlog
from github import Auth, Github, GithubException

logger = structlog.get_logger()


class GitHubClient:
    """Wrapper for PyGithub with error handling."""

    def __init__(self, token: str, timeout: int = 30):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token
            timeout: Request timeout in seconds
        """
        auth = Auth.Token(token)
        self.client = Github(auth=auth, timeout=timeout)
        self.repo_cache = {}
        logger.info("github_client_initialized", timeout=timeout)

    def get_repo(self, repo_full_name: str):
        """Get repository object with caching.

        Args:
            repo_full_name: Repository in format owner/repo

        Returns:
            PyGithub Repository object
        """
        if repo_full_name not in self.repo_cache:
            try:
                self.repo_cache[repo_full_name] = self.client.get_repo(
                    repo_full_name)
                logger.info("github_repo_cached", repo=repo_full_name)
            except GithubException as e:
                logger.error("github_repo_error",
                             repo=repo_full_name, error=str(e))
                raise

        return self.repo_cache[repo_full_name]

    def create_branch(self, repo_full_name: str, branch_name: str, base_sha: str) -> bool:
        """Create new branch from base SHA.

        Args:
            repo_full_name: Repository in format owner/repo
            branch_name: New branch name
            base_sha: Base commit SHA

        Returns:
            True if created successfully
        """
        try:
            repo = self.get_repo(repo_full_name)
            ref = f"refs/heads/{branch_name}"
            repo.create_git_ref(ref=ref, sha=base_sha)
            logger.info("github_branch_created",
                        repo=repo_full_name, branch=branch_name)
            return True
        except GithubException as e:
            if e.status == 422:  # Branch already exists
                logger.warning("github_branch_exists", branch=branch_name)
                return False
            logger.error("github_branch_error", error=str(e))
            raise

    def create_or_update_file(
        self,
        repo_full_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str
    ) -> str:
        """Create or update file in repository.

        Args:
            repo_full_name: Repository in format owner/repo
            file_path: File path in repository
            content: File content
            commit_message: Commit message
            branch: Branch name

        Returns:
            Commit SHA
        """
        try:
            repo = self.get_repo(repo_full_name)

            # Try to get existing file
            try:
                existing_file = repo.get_contents(file_path, ref=branch)
                result = repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    sha=existing_file.sha,
                    branch=branch
                )
                logger.info("github_file_updated",
                            file=file_path, branch=branch)
            except GithubException:
                # File doesn't exist, create it
                result = repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    branch=branch
                )
                logger.info("github_file_created",
                            file=file_path, branch=branch)

            return result["commit"].sha

        except GithubException as e:
            logger.error("github_file_error", error=str(e))
            raise

    def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> dict:
        """Create pull request.

        Args:
            repo_full_name: Repository in format owner/repo
            title: PR title
            body: PR description
            head: Head branch name
            base: Base branch name

        Returns:
            Dict with PR number and html_url
        """
        try:
            repo = self.get_repo(repo_full_name)
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base
            )
            logger.info("github_pr_created",
                        repo=repo_full_name, pr_number=pr.number)
            return {"number": pr.number, "html_url": pr.html_url}
        except GithubException as e:
            logger.error("github_pr_error", error=str(e))
            raise

    def add_issue_comment(
        self,
        repo_full_name: str,
        issue_number: int,
        comment: str
    ) -> None:
        """Add comment to issue.

        Args:
            repo_full_name: Repository in format owner/repo
            issue_number: Issue number
            comment: Comment text
        """
        try:
            repo = self.get_repo(repo_full_name)
            issue = repo.get_issue(issue_number)
            issue.create_comment(comment)
            logger.info("github_comment_added", issue=issue_number)
        except GithubException as e:
            logger.error("github_comment_error", error=str(e))
            raise
