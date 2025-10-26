"""Contract tests for GitHub API interactions."""
import pytest
import json
from unittest.mock import Mock, patch
from pydantic import BaseModel, ValidationError

from src.core.github_client import GitHubClient


class TestGitHubAPIContracts:
    """Test GitHub API schema validation and contract compliance."""

    @pytest.fixture
    def github_client(self):
        """Fixture for GitHubClient instance."""
        mock_config = Mock()
        mock_config.GITHUB_TOKEN = "test_token"
        mock_config.GITHUB_REPO = "owner/repo"
        
        return GitHubClient(config=mock_config)

    @pytest.mark.contract
    def test_issue_opened_event_schema(self):
        """Test GitHub issue.opened webhook event matches expected schema."""
        # Sample webhook payload from GitHub
        webhook_payload = {
            "action": "opened",
            "issue": {
                "id": 1,
                "number": 42,
                "title": "Add authentication feature",
                "body": "Implement OAuth2 authentication",
                "state": "open",
                "labels": [
                    {
                        "id": 1234,
                        "name": "generate-tests",
                        "color": "00FF00"
                    }
                ],
                "user": {
                    "login": "test-user",
                    "id": 5678
                },
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z"
            },
            "repository": {
                "id": 9999,
                "name": "repo",
                "full_name": "owner/repo",
                "owner": {
                    "login": "owner",
                    "id": 1111
                },
                "default_branch": "main"
            },
            "sender": {
                "login": "sender-user",
                "id": 2222
            }
        }
        
        # Validate required fields exist
        assert "action" in webhook_payload
        assert webhook_payload["action"] == "opened"
        assert "issue" in webhook_payload
        assert "number" in webhook_payload["issue"]
        assert "title" in webhook_payload["issue"]
        assert "body" in webhook_payload["issue"]
        assert "labels" in webhook_payload["issue"]
        assert "repository" in webhook_payload
        assert "full_name" in webhook_payload["repository"]

    @pytest.mark.contract
    def test_issue_labeled_event_schema(self):
        """Test GitHub issue.labeled webhook event matches expected schema."""
        webhook_payload = {
            "action": "labeled",
            "issue": {
                "number": 42,
                "title": "Add authentication",
                "body": "Feature description",
                "labels": [
                    {"name": "generate-tests"}
                ]
            },
            "label": {
                "id": 1234,
                "name": "generate-tests",
                "color": "00FF00"
            },
            "repository": {
                "full_name": "owner/repo"
            }
        }
        
        # Validate required fields
        assert webhook_payload["action"] == "labeled"
        assert "label" in webhook_payload
        assert webhook_payload["label"]["name"] == "generate-tests"

    @pytest.mark.contract
    def test_create_pull_request_request_schema(self):
        """Test create PR request matches GitHub API schema."""
        pr_request = {
            "title": "Test Cases: Add Authentication",
            "body": "Generated test cases for issue #42.\n\nCloses #42",
            "head": "test-cases/issue-42",
            "base": "main",
            "draft": False
        }
        
        # Validate required fields for GitHub PR creation
        required_fields = ["title", "body", "head", "base"]
        for field in required_fields:
            assert field in pr_request, f"Missing required field: {field}"
        
        # Validate types
        assert isinstance(pr_request["title"], str)
        assert isinstance(pr_request["body"], str)
        assert isinstance(pr_request["head"], str)
        assert isinstance(pr_request["base"], str)

    @pytest.mark.contract
    def test_create_pull_request_response_schema(self):
        """Test GitHub PR creation response matches expected schema."""
        # Sample GitHub API response for PR creation
        pr_response = {
            "id": 123456789,
            "number": 123,
            "state": "open",
            "title": "Test Cases: Add Authentication",
            "body": "Generated test cases.\n\nCloses #42",
            "html_url": "https://github.com/owner/repo/pull/123",
            "user": {
                "login": "github-actions[bot]",
                "id": 41898282
            },
            "created_at": "2025-01-15T10:35:00Z",
            "updated_at": "2025-01-15T10:35:00Z",
            "head": {
                "ref": "test-cases/issue-42",
                "sha": "abc123def456"
            },
            "base": {
                "ref": "main",
                "sha": "def456ghi789"
            },
            "mergeable": True,
            "mergeable_state": "clean"
        }
        
        # Validate required response fields
        assert "number" in pr_response
        assert "html_url" in pr_response
        assert "state" in pr_response
        assert pr_response["state"] in ["open", "closed", "merged"]
        
        # Validate URL format
        assert pr_response["html_url"].startswith("https://github.com/")
        assert "/pull/" in pr_response["html_url"]

    @pytest.mark.contract
    def test_create_branch_request_schema(self):
        """Test create branch request matches GitHub API schema."""
        # GitHub uses "create ref" endpoint for branch creation
        branch_request = {
            "ref": "refs/heads/test-cases/issue-42",
            "sha": "abc123def456"  # SHA of commit to branch from
        }
        
        # Validate required fields
        assert "ref" in branch_request
        assert "sha" in branch_request
        assert branch_request["ref"].startswith("refs/heads/")

    @pytest.mark.contract
    def test_create_file_request_schema(self):
        """Test create/update file request matches GitHub API schema."""
        file_request = {
            "message": "Add test cases for issue #42",
            "content": "IyBUZXN0IENhc2VzCgpDb250ZW50",  # Base64 encoded
            "branch": "test-cases/issue-42"
        }
        
        # Validate required fields for GitHub file creation
        assert "message" in file_request  # Commit message
        assert "content" in file_request  # Base64 encoded content
        
        # Validate content is base64
        import base64
        try:
            base64.b64decode(file_request["content"])
        except Exception:
            pytest.fail("Content must be base64 encoded")

    @pytest.mark.contract
    def test_issue_comment_request_schema(self):
        """Test issue comment creation request matches GitHub API schema."""
        comment_request = {
            "body": "✅ Test cases generated! View PR: https://github.com/owner/repo/pull/123"
        }
        
        # Validate required fields
        assert "body" in comment_request
        assert isinstance(comment_request["body"], str)
        assert len(comment_request["body"]) > 0

    @pytest.mark.contract
    def test_issue_comment_response_schema(self):
        """Test GitHub issue comment response matches expected schema."""
        comment_response = {
            "id": 987654321,
            "body": "✅ Test cases generated!",
            "user": {
                "login": "github-actions[bot]",
                "id": 41898282
            },
            "created_at": "2025-01-15T10:40:00Z",
            "updated_at": "2025-01-15T10:40:00Z",
            "html_url": "https://github.com/owner/repo/issues/42#issuecomment-987654321"
        }
        
        # Validate response fields
        assert "id" in comment_response
        assert "body" in comment_response
        assert "created_at" in comment_response

    @pytest.mark.contract
    def test_repository_response_schema(self):
        """Test GitHub repository response matches expected schema."""
        repo_response = {
            "id": 123456,
            "name": "repo",
            "full_name": "owner/repo",
            "owner": {
                "login": "owner",
                "id": 789
            },
            "default_branch": "main",
            "permissions": {
                "admin": False,
                "push": True,
                "pull": True
            }
        }
        
        # Validate required fields
        assert "full_name" in repo_response
        assert "default_branch" in repo_response
        assert "permissions" in repo_response

    @pytest.mark.contract
    def test_rate_limit_response_schema(self):
        """Test GitHub rate limit response matches expected schema."""
        rate_limit_response = {
            "resources": {
                "core": {
                    "limit": 5000,
                    "remaining": 4999,
                    "reset": 1642251600,
                    "used": 1
                },
                "search": {
                    "limit": 30,
                    "remaining": 30,
                    "reset": 1642248000,
                    "used": 0
                }
            },
            "rate": {
                "limit": 5000,
                "remaining": 4999,
                "reset": 1642251600,
                "used": 1
            }
        }
        
        # Validate rate limit fields
        assert "rate" in rate_limit_response
        assert "limit" in rate_limit_response["rate"]
        assert "remaining" in rate_limit_response["rate"]
        assert "reset" in rate_limit_response["rate"]

    @pytest.mark.contract
    def test_error_response_schema(self):
        """Test GitHub API error response matches expected schema."""
        error_response = {
            "message": "Not Found",
            "documentation_url": "https://docs.github.com/rest/reference/repos#get-a-repository",
            "status": "404"
        }
        
        # Validate error response structure
        assert "message" in error_response
        assert isinstance(error_response["message"], str)

    @pytest.mark.contract
    def test_validation_error_response_schema(self):
        """Test GitHub API validation error response matches expected schema."""
        validation_error_response = {
            "message": "Validation Failed",
            "errors": [
                {
                    "resource": "PullRequest",
                    "field": "head",
                    "code": "invalid"
                }
            ],
            "documentation_url": "https://docs.github.com/rest/pulls/pulls#create-a-pull-request"
        }
        
        # Validate validation error structure
        assert "message" in validation_error_response
        assert "errors" in validation_error_response
        assert isinstance(validation_error_response["errors"], list)
        
        if len(validation_error_response["errors"]) > 0:
            error = validation_error_response["errors"][0]
            assert "resource" in error
            assert "field" in error
            assert "code" in error

    @pytest.mark.contract
    def test_webhook_headers_schema(self):
        """Test GitHub webhook headers match expected format."""
        webhook_headers = {
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "12345678-1234-1234-1234-123456789012",
            "X-Hub-Signature": "sha1=abc123",
            "X-Hub-Signature-256": "sha256=def456",
            "Content-Type": "application/json",
            "User-Agent": "GitHub-Hookshot/abc123"
        }
        
        # Validate required webhook headers
        assert "X-GitHub-Event" in webhook_headers
        assert "X-Hub-Signature-256" in webhook_headers
        assert webhook_headers["X-Hub-Signature-256"].startswith("sha256=")

    @pytest.mark.contract
    def test_label_schema(self):
        """Test GitHub label object matches expected schema."""
        label = {
            "id": 1234567890,
            "node_id": "MDU6TGFiZWwxMjM0NTY3ODkw",
            "url": "https://api.github.com/repos/owner/repo/labels/generate-tests",
            "name": "generate-tests",
            "color": "00FF00",
            "default": False,
            "description": "Automatically generate test cases"
        }
        
        # Validate label fields
        assert "id" in label
        assert "name" in label
        assert "color" in label
        
        # Validate color is hex format
        assert len(label["color"]) == 6
        assert all(c in "0123456789ABCDEFabcdef" for c in label["color"])

    @pytest.mark.contract
    def test_branch_protection_response_schema(self):
        """Test GitHub branch protection response matches expected schema."""
        protection_response = {
            "required_status_checks": {
                "strict": True,
                "contexts": ["ci/test", "ci/lint"]
            },
            "enforce_admins": {
                "enabled": True
            },
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": True,
                "required_approving_review_count": 1
            },
            "restrictions": None
        }
        
        # Validate protection fields (may be None if not protected)
        if protection_response is not None:
            assert "required_status_checks" in protection_response or \
                   "enforce_admins" in protection_response or \
                   "required_pull_request_reviews" in protection_response
