"""Unit tests for GitHubService operations."""
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.exceptions import GitHubAPIError, GitHubBranchExistsError, GitHubRateLimitError
from src.services.github_service import GitHubService


class TestGitHubServiceOperations:
    """Test GitHubService GitHub API operations."""

    @pytest.fixture
    def mock_github_client(self):
        """Fixture for mocked GitHubClient."""
        mock_client = AsyncMock()
        mock_client.get_repo = Mock(return_value=Mock())
        return mock_client

    @pytest.fixture
    def github_service(self, mock_github_client):
        """Fixture for GitHubService instance."""
        mock_config = Mock()
        mock_config.GITHUB_TOKEN = "test_token"
        mock_config.GITHUB_REPO = "owner/repo"

        return GitHubService(
            github_client=mock_github_client,
            config=mock_config
        )

    @pytest.mark.asyncio
    async def test_create_branch_success(self, github_service, mock_github_client):
        """Test create_branch() successfully creates a new branch."""
        branch_name = "test-cases/issue-42"
        base_branch = "main"

        # Mock branch creation
        mock_github_client.create_branch = AsyncMock()

        # Execute
        await github_service.create_branch(
            branch_name=branch_name,
            base_branch=base_branch
        )

        # Verify branch created
        mock_github_client.create_branch.assert_called_once_with(
            branch_name=branch_name,
            base_branch=base_branch
        )

    @pytest.mark.asyncio
    async def test_create_branch_already_exists(self, github_service, mock_github_client):
        """Test create_branch() raises GitHubBranchExistsError (E402) if branch exists."""
        branch_name = "test-cases/issue-42"

        # Mock branch exists error
        mock_github_client.create_branch = AsyncMock(
            side_effect=GitHubBranchExistsError(branch_name=branch_name)
        )

        # Should raise E402
        with pytest.raises(GitHubBranchExistsError) as exc_info:
            await github_service.create_branch(branch_name=branch_name)

        assert exc_info.value.error_code == "E402"
        assert branch_name in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_commit_file_success(self, github_service, mock_github_client):
        """Test commit_file() successfully commits file to branch."""
        file_path = "test-cases/issue-42.md"
        content = "# Test Cases\n\nTest content"
        branch_name = "test-cases/issue-42"
        commit_message = "Add test cases for issue #42"

        # Mock file commit
        mock_github_client.create_or_update_file = AsyncMock()

        # Execute
        await github_service.commit_file(
            file_path=file_path,
            content=content,
            branch_name=branch_name,
            commit_message=commit_message
        )

        # Verify file committed
        mock_github_client.create_or_update_file.assert_called_once_with(
            file_path=file_path,
            content=content,
            branch_name=branch_name,
            commit_message=commit_message
        )

    @pytest.mark.asyncio
    async def test_commit_file_update_existing(self, github_service, mock_github_client):
        """Test commit_file() updates existing file."""
        file_path = "test-cases/issue-42.md"
        new_content = "# Updated Test Cases"
        branch_name = "test-cases/issue-42"

        # Mock file update
        mock_github_client.create_or_update_file = AsyncMock()

        # Execute
        await github_service.commit_file(
            file_path=file_path,
            content=new_content,
            branch_name=branch_name,
            commit_message="Update test cases"
        )

        # Verify update called
        mock_github_client.create_or_update_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_pr_success(self, github_service, mock_github_client):
        """Test create_pr() successfully creates pull request."""
        title = "Test Cases: Add Authentication"
        body = "Generated test cases for issue #42.\n\nCloses #42"
        head_branch = "test-cases/issue-42"
        base_branch = "main"

        # Mock PR creation
        mock_pr = {
            "number": 123,
            "html_url": "https://github.com/owner/repo/pull/123",
            "state": "open",
            "created_at": datetime.now().isoformat()
        }
        mock_github_client.create_pull_request = AsyncMock(return_value=mock_pr)

        # Execute
        pr_data = await github_service.create_pr(
            title=title,
            body=body,
            head_branch=head_branch,
            base_branch=base_branch
        )

        # Verify PR created
        mock_github_client.create_pull_request.assert_called_once_with(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch
        )

        # Verify returned data
        assert pr_data["number"] == 123
        assert pr_data["html_url"] == "https://github.com/owner/repo/pull/123"

    @pytest.mark.asyncio
    async def test_create_pr_includes_issue_reference(self, github_service, mock_github_client):
        """Test create_pr() body includes 'Closes #N' reference."""
        issue_number = 42

        mock_github_client.create_pull_request = AsyncMock(
            return_value={"number": 123, "html_url": "https://github.com/owner/repo/pull/123"}
        )

        # Execute
        await github_service.create_pr_for_issue(
            issue_number=issue_number,
            branch_name="test-cases/issue-42",
            title="Test Cases: Feature"
        )

        # Verify body contains "Closes #42"
        call_args = mock_github_client.create_pull_request.call_args
        body = call_args.kwargs.get("body", "")
        assert f"Closes #{issue_number}" in body

    @pytest.mark.asyncio
    async def test_add_comment_success(self, github_service, mock_github_client):
        """Test add_comment() successfully adds comment to issue."""
        issue_number = 42
        comment = "✅ Test cases generated! View PR: https://github.com/owner/repo/pull/123"

        # Mock comment creation
        mock_github_client.add_issue_comment = AsyncMock()

        # Execute
        await github_service.add_comment(
            issue_number=issue_number,
            comment=comment
        )

        # Verify comment added
        mock_github_client.add_issue_comment.assert_called_once_with(
            issue_number=issue_number,
            comment=comment
        )

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, github_service, mock_github_client):
        """Test GitHubRateLimitError (E405) is raised when rate limit exceeded."""
        # Mock rate limit error
        mock_github_client.create_branch = AsyncMock(
            side_effect=GitHubRateLimitError(
                message="API rate limit exceeded",
                details={"reset_at": "2025-01-15T12:00:00Z"}
            )
        )

        # Should raise E405
        with pytest.raises(GitHubRateLimitError) as exc_info:
            await github_service.create_branch(branch_name="test-cases/issue-42")

        assert exc_info.value.error_code == "E405"
        assert "rate limit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_api_error_handling(self, github_service, mock_github_client):
        """Test GitHubAPIError (E406) is raised for generic API errors."""
        # Mock API error
        mock_github_client.create_pull_request = AsyncMock(
            side_effect=GitHubAPIError(
                message="GitHub API request failed",
                details={"status": 500, "error": "Internal Server Error"}
            )
        )

        # Should raise E406
        with pytest.raises(GitHubAPIError) as exc_info:
            await github_service.create_pr(
                title="Test",
                body="Test",
                head_branch="test",
                base_branch="main"
            )

        assert exc_info.value.error_code == "E406"

    @pytest.mark.asyncio
    async def test_branch_name_validation(self, github_service):
        """Test branch name follows pattern 'test-cases/issue-{number}'."""
        issue_number = 42

        # Generate branch name
        branch_name = github_service.generate_branch_name(issue_number)

        # Verify pattern
        assert branch_name == "test-cases/issue-42"
        assert branch_name.startswith("test-cases/issue-")

    @pytest.mark.asyncio
    async def test_pr_body_formatting(self, github_service):
        """Test PR body includes issue reference and generated content."""
        issue_number = 42
        issue_title = "Add authentication"

        # Generate PR body
        pr_body = github_service.generate_pr_body(
            issue_number=issue_number,
            issue_title=issue_title,
            context_sources=[38, 39, 40]
        )

        # Verify formatting
        assert f"Closes #{issue_number}" in pr_body
        assert issue_title in pr_body
        assert "38" in pr_body  # Context sources included

    @pytest.mark.asyncio
    async def test_retry_on_transient_errors(self, github_service, mock_github_client):
        """Test operations retry on transient GitHub API errors."""
        # Mock transient error followed by success
        call_count = 0
        async def mock_create_branch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise GitHubAPIError("Temporary failure", {"status": 502})
            return None

        mock_github_client.create_branch = mock_create_branch

        # Should succeed after retry
        await github_service.create_branch_with_retry(
            branch_name="test-cases/issue-42",
            max_retries=3
        )

        assert call_count == 2  # Failed once, succeeded second time

    @pytest.mark.asyncio
    async def test_get_default_branch(self, github_service, mock_github_client):
        """Test getting repository default branch (main or master)."""
        # Mock repository with default branch
        mock_repo = Mock()
        mock_repo.default_branch = "main"
        mock_github_client.get_repo = Mock(return_value=mock_repo)

        # Get default branch
        default_branch = github_service.get_default_branch()

        assert default_branch == "main"

    @pytest.mark.asyncio
    async def test_validate_permissions(self, github_service, mock_github_client):
        """Test validating GitHub token has required permissions."""
        # Mock permissions check
        mock_repo = Mock()
        mock_repo.permissions.push = True
        mock_repo.permissions.pull = True
        mock_github_client.get_repo = Mock(return_value=mock_repo)

        # Should validate successfully
        has_permissions = github_service.validate_permissions()

        assert has_permissions is True

    @pytest.mark.asyncio
    async def test_file_path_generation(self, github_service):
        """Test generating file path for test case document."""
        issue_number = 42

        # Generate file path
        file_path = github_service.generate_file_path(issue_number)

        # Verify pattern
        assert file_path == f"test-cases/issue-{issue_number}.md"
        assert file_path.endswith(".md")

    @pytest.mark.asyncio
    async def test_commit_message_formatting(self, github_service):
        """Test commit message includes issue reference."""
        issue_number = 42

        # Generate commit message
        commit_message = github_service.generate_commit_message(issue_number)

        # Verify format
        assert f"#{issue_number}" in commit_message
        assert "test case" in commit_message.lower()

    @pytest.mark.asyncio
    async def test_concurrent_pr_creation(self, github_service, mock_github_client):
        """Test service handles concurrent PR creations safely."""
        # Mock multiple PR creations
        mock_github_client.create_pull_request = AsyncMock(
            side_effect=[
                {"number": 123, "html_url": "https://github.com/owner/repo/pull/123"},
                {"number": 124, "html_url": "https://github.com/owner/repo/pull/124"}
            ]
        )

        # Create multiple PRs concurrently
        import asyncio
        pr1_task = github_service.create_pr("Title 1", "Body 1", "branch-1", "main")
        pr2_task = github_service.create_pr("Title 2", "Body 2", "branch-2", "main")

        pr1, pr2 = await asyncio.gather(pr1_task, pr2_task)

        # Verify both created with unique numbers
        assert pr1["number"] == 123
        assert pr2["number"] == 124
        assert pr1["number"] != pr2["number"]
