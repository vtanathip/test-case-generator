"""TestCaseDocument pydantic model."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class TestCaseDocument(BaseModel):
    """Represents a generated test case document ready for PR creation."""
    
    model_config = ConfigDict(frozen=True)  # Immutable model
    
    # 12 attributes
    document_id: str = Field(..., description="Unique document identifier (UUID)")
    issue_number: int = Field(..., gt=0, description="GitHub issue number")
    title: str = Field(..., description="Document title (e.g., 'Test Cases: Feature X')")
    content: str = Field(..., description="Markdown-formatted test case content")
    metadata: dict[str, Any] = Field(..., description="Metadata with issue, generated_at, ai_model, context_sources")
    branch_name: str = Field(..., description="Git branch name in format 'test-cases/issue-{N}'")
    pr_number: Optional[int] = Field(default=None, gt=0, description="GitHub PR number (if created)")
    pr_url: Optional[str] = Field(default=None, description="GitHub PR URL (if created)")
    generated_at: datetime = Field(..., description="Timestamp when document was generated")
    ai_model: str = Field(..., description="AI model used for generation (e.g., 'llama-3.2-11b')")
    context_sources: list[int] = Field(default_factory=list, description="List of similar issue numbers (context)")
    correlation_id: str = Field(..., description="Correlation ID for tracking (UUID)")
    
    @field_validator("content")
    @classmethod
    def validate_content_is_markdown(cls, v: str) -> str:
        """Validate content is valid Markdown format (contains Markdown headings)."""
        if not v.strip():
            raise ValueError("content cannot be empty")
        
        # Basic Markdown validation: Must contain at least one heading
        if not re.search(r'^#{1,6}\s+.+', v, re.MULTILINE):
            raise ValueError("content must contain at least one Markdown heading (# Title)")
        
        return v
    
    @field_validator("metadata")
    @classmethod
    def validate_metadata_required_fields(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate metadata contains required fields: issue, generated_at, ai_model, context_sources."""
        required_fields = ["issue", "generated_at", "ai_model", "context_sources"]
        
        missing_fields = [field for field in required_fields if field not in v]
        if missing_fields:
            raise ValueError(f"metadata missing required fields: {', '.join(missing_fields)}")
        
        return v
    
    @field_validator("branch_name")
    @classmethod
    def validate_branch_name_pattern(cls, v: str) -> str:
        """Validate branch_name matches pattern 'test-cases/issue-{issue_number}'."""
        pattern = r'^test-cases/issue-\d+$'
        if not re.match(pattern, v):
            raise ValueError(
                "branch_name must match pattern 'test-cases/issue-{issue_number}' "
                f"(e.g., 'test-cases/issue-42'), got: {v}"
            )
        return v
    
    @field_validator("pr_url")
    @classmethod
    def validate_pr_url_format(cls, v: Optional[str], info) -> Optional[str]:
        """Validate pr_url is a valid GitHub URL if not None."""
        if v is None:
            return v
        
        # GitHub PR URL pattern: https://github.com/{owner}/{repo}/pull/{number}
        github_pr_pattern = r'^https://github\.com/[\w-]+/[\w.-]+/pull/\d+$'
        if not re.match(github_pr_pattern, v):
            raise ValueError(
                f"pr_url must be a valid GitHub PR URL (https://github.com/owner/repo/pull/123), got: {v}"
            )
        
        return v
    
    @field_validator("pr_url")
    @classmethod
    def validate_pr_consistency(cls, v: Optional[str], info) -> Optional[str]:
        """Validate pr_number and pr_url are consistent (both None or both set)."""
        pr_number = info.data.get("pr_number")
        
        # Check consistency
        if (pr_number is None and v is not None) or (pr_number is not None and v is None):
            raise ValueError(
                "pr_number and pr_url must be consistent: both None (before PR) or both set (after PR)"
            )
        
        return v
