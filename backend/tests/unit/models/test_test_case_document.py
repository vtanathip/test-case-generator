"""Unit tests for TestCaseDocument model."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.test_case_document import TestCaseDocument


class TestTestCaseDocumentValidation:
    """Test TestCaseDocument model validation rules."""

    def test_create_valid_test_case_document(self):
        """Test creating a valid test case document."""
        metadata = {
            "issue": 42,
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": [38, 39, 40]
        }
        
        doc = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Add OAuth2 Authentication",
            content="# Test Cases: Add OAuth2 Authentication\n\n## Overview\n\nTest authentication flow.",
            metadata=metadata,
            branch_name="test-cases/issue-42",
            pr_number=None,
            pr_url=None,
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[38, 39, 40],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        
        assert doc.document_id == "880e8400-e29b-41d4-a716-446655440000"
        assert doc.issue_number == 42
        assert doc.branch_name == "test-cases/issue-42"
        assert doc.ai_model == "llama-3.2-11b"
        assert len(doc.context_sources) == 3

    def test_content_is_valid_markdown(self):
        """Test content must be valid Markdown format."""
        metadata = {
            "issue": 42,
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": [38, 39]
        }
        
        # Valid Markdown with headings, lists, code blocks
        valid_markdown = """# Test Cases: Feature X

## Overview

Test the authentication feature.

## Test Scenarios

### Scenario 1: Login Success

**Given**:
- User has valid credentials

**When**:
- User submits login form

**Then**:
- User is redirected to dashboard

**Test Data**:
```json
{
  "username": "test@example.com",
  "password": "SecurePass123"
}
```
"""
        
        doc = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature X",
            content=valid_markdown,
            metadata=metadata,
            branch_name="test-cases/issue-42",
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[38, 39],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        
        assert "# Test Cases:" in doc.content
        assert "## Overview" in doc.content
        assert "### Scenario 1:" in doc.content

    def test_metadata_required_fields(self):
        """Test metadata must include: issue, generated_at, ai_model, context_sources."""
        # Valid metadata with all required fields
        valid_metadata = {
            "issue": 42,
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": [38, 39, 40]
        }
        
        doc = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature",
            content="# Test Cases\n\nContent here.",
            metadata=valid_metadata,
            branch_name="test-cases/issue-42",
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[38, 39, 40],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        
        assert "issue" in doc.metadata
        assert "generated_at" in doc.metadata
        assert "ai_model" in doc.metadata
        assert "context_sources" in doc.metadata
        
        # Invalid: Missing required metadata field (issue)
        invalid_metadata = {
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": [38]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TestCaseDocument(
                document_id="880e8400-e29b-41d4-a716-446655440000",
                issue_number=42,
                title="Test Cases: Feature",
                content="# Test Cases\n\nContent here.",
                metadata=invalid_metadata,
                branch_name="test-cases/issue-42",
                generated_at=datetime.now(),
                ai_model="llama-3.2-11b",
                context_sources=[38],
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
        assert "metadata" in str(exc_info.value)

    def test_branch_name_pattern(self):
        """Test branch_name must match pattern 'test-cases/issue-{issue_number}'."""
        metadata = {
            "issue": 42,
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": []
        }
        
        # Valid branch name
        doc = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature",
            content="# Test Cases",
            metadata=metadata,
            branch_name="test-cases/issue-42",
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert doc.branch_name == "test-cases/issue-42"
        
        # Invalid branch name patterns
        invalid_branches = [
            "issue-42",
            "test-cases-issue-42",
            "test-cases/42",
            "test/issue-42",
            "test-cases/issue-abc"
        ]
        
        for invalid_branch in invalid_branches:
            with pytest.raises(ValidationError) as exc_info:
                TestCaseDocument(
                    document_id="880e8400-e29b-41d4-a716-446655440000",
                    issue_number=42,
                    title="Test Cases: Feature",
                    content="# Test Cases",
                    metadata=metadata,
                    branch_name=invalid_branch,
                    generated_at=datetime.now(),
                    ai_model="llama-3.2-11b",
                    context_sources=[],
                    correlation_id="660e8400-e29b-41d4-a716-446655440001"
                )
            assert "branch_name" in str(exc_info.value)

    def test_pr_url_validation(self):
        """Test pr_url must be valid GitHub URL if not null."""
        metadata = {
            "issue": 42,
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": []
        }
        
        # Valid: pr_url is None (before PR created)
        doc_no_pr = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature",
            content="# Test Cases",
            metadata=metadata,
            branch_name="test-cases/issue-42",
            pr_number=None,
            pr_url=None,
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert doc_no_pr.pr_url is None
        
        # Valid: pr_url is valid GitHub URL
        valid_pr_url = "https://github.com/owner/repo/pull/123"
        doc_with_pr = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature",
            content="# Test Cases",
            metadata=metadata,
            branch_name="test-cases/issue-42",
            pr_number=123,
            pr_url=valid_pr_url,
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert doc_with_pr.pr_url == valid_pr_url
        
        # Invalid: pr_url is not a valid GitHub URL
        invalid_urls = [
            "https://example.com/pull/123",
            "github.com/owner/repo/pull/123",
            "https://github.com/pull/123",
            "not-a-url"
        ]
        
        for invalid_url in invalid_urls:
            with pytest.raises(ValidationError) as exc_info:
                TestCaseDocument(
                    document_id="880e8400-e29b-41d4-a716-446655440000",
                    issue_number=42,
                    title="Test Cases: Feature",
                    content="# Test Cases",
                    metadata=metadata,
                    branch_name="test-cases/issue-42",
                    pr_number=123,
                    pr_url=invalid_url,
                    generated_at=datetime.now(),
                    ai_model="llama-3.2-11b",
                    context_sources=[],
                    correlation_id="660e8400-e29b-41d4-a716-446655440001"
                )
            assert "pr_url" in str(exc_info.value)

    def test_ai_model_values(self):
        """Test ai_model accepts valid model names (llama-3.2-11b, llama-3.2-90b)."""
        metadata = {
            "issue": 42,
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": []
        }
        
        valid_models = [
            "llama-3.2-11b",
            "llama-3.2-90b",
            "llama-3.2-1b"
        ]
        
        for model in valid_models:
            doc = TestCaseDocument(
                document_id="880e8400-e29b-41d4-a716-446655440000",
                issue_number=42,
                title="Test Cases: Feature",
                content="# Test Cases",
                metadata={**metadata, "ai_model": model},
                branch_name="test-cases/issue-42",
                generated_at=datetime.now(),
                ai_model=model,
                context_sources=[],
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
            assert doc.ai_model == model

    def test_context_sources_list(self):
        """Test context_sources is a list of issue numbers."""
        metadata = {
            "issue": 42,
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": [38, 39, 40, 41, 37]
        }
        
        # Valid: List of up to 5 issue numbers (top 5 similar from vector DB)
        doc = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature",
            content="# Test Cases",
            metadata=metadata,
            branch_name="test-cases/issue-42",
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[38, 39, 40, 41, 37],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        
        assert len(doc.context_sources) == 5
        assert all(isinstance(issue, int) for issue in doc.context_sources)
        
        # Valid: Empty list (no similar context found)
        doc_no_context = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature",
            content="# Test Cases",
            metadata={**metadata, "context_sources": []},
            branch_name="test-cases/issue-42",
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert len(doc_no_context.context_sources) == 0

    def test_pr_number_consistency(self):
        """Test pr_number and pr_url must be consistent (both null or both set)."""
        metadata = {
            "issue": 42,
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": []
        }
        
        # Valid: Both None (before PR created)
        doc_both_none = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature",
            content="# Test Cases",
            metadata=metadata,
            branch_name="test-cases/issue-42",
            pr_number=None,
            pr_url=None,
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert doc_both_none.pr_number is None and doc_both_none.pr_url is None
        
        # Valid: Both set (after PR created)
        doc_both_set = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature",
            content="# Test Cases",
            metadata=metadata,
            branch_name="test-cases/issue-42",
            pr_number=123,
            pr_url="https://github.com/owner/repo/pull/123",
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert doc_both_set.pr_number == 123 and doc_both_set.pr_url is not None
        
        # Invalid: pr_number set but pr_url None (inconsistent state)
        with pytest.raises(ValidationError) as exc_info:
            TestCaseDocument(
                document_id="880e8400-e29b-41d4-a716-446655440000",
                issue_number=42,
                title="Test Cases: Feature",
                content="# Test Cases",
                metadata=metadata,
                branch_name="test-cases/issue-42",
                pr_number=123,
                pr_url=None,
                generated_at=datetime.now(),
                ai_model="llama-3.2-11b",
                context_sources=[],
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
        # Validation should catch inconsistency

    def test_test_case_document_immutability(self):
        """Test TestCaseDocument is immutable once created (frozen model)."""
        metadata = {
            "issue": 42,
            "generated_at": "2025-01-15T10:30:00Z",
            "ai_model": "llama-3.2-11b",
            "context_sources": []
        }
        
        doc = TestCaseDocument(
            document_id="880e8400-e29b-41d4-a716-446655440000",
            issue_number=42,
            title="Test Cases: Feature",
            content="# Test Cases",
            metadata=metadata,
            branch_name="test-cases/issue-42",
            generated_at=datetime.now(),
            ai_model="llama-3.2-11b",
            context_sources=[],
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        
        # Attempt to modify content should fail
        with pytest.raises(ValidationError):
            doc.content = "# Modified Test Cases"
