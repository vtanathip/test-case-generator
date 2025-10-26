"""Custom exceptions for the test case generation system."""
from typing import Optional


class TestCaseGeneratorException(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str,
        details: Optional[dict] = None
    ):
        """Initialize exception.
        
        Args:
            message: Human-readable error message
            error_code: Error code from error-catalog.md (e.g., E301)
            details: Additional error context
        """
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


# E1xx: Webhook & Input Validation Errors

class InvalidWebhookSignatureError(TestCaseGeneratorException):
    """E101: Webhook signature validation failed."""
    
    def __init__(self, expected: str, received: str):
        super().__init__(
            message=f"Webhook signature validation failed",
            error_code="E101",
            details={"expected": expected[:10] + "...", "received": received[:10] + "..."}
        )


class MissingRequiredTagError(TestCaseGeneratorException):
    """E102: Issue does not contain 'generate-tests' tag."""
    
    def __init__(self, issue_number: int):
        super().__init__(
            message=f"Issue #{issue_number} missing 'generate-tests' tag",
            error_code="E102",
            details={"issue_number": issue_number}
        )


class InsufficientInformationError(TestCaseGeneratorException):
    """E104: Issue lacks sufficient detail for generation."""
    
    def __init__(self, issue_number: int, reason: str):
        super().__init__(
            message=f"Issue #{issue_number} has insufficient information: {reason}",
            error_code="E104",
            details={"issue_number": issue_number, "reason": reason}
        )


class DuplicateWebhookError(TestCaseGeneratorException):
    """E105: Duplicate webhook detected (idempotency)."""
    
    def __init__(self, idempotency_key: str):
        super().__init__(
            message=f"Duplicate webhook detected",
            error_code="E105",
            details={"idempotency_key": idempotency_key}
        )


# E2xx: Vector Database Errors

class VectorDatabaseError(TestCaseGeneratorException):
    """E201: Generic vector database error."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=f"Vector database error: {message}",
            error_code="E201",
            details=details
        )


# E3xx: AI Generation Errors

class AIGenerationError(TestCaseGeneratorException):
    """E301: Generic AI generation error."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=f"AI generation failed: {message}",
            error_code="E301",
            details=details
        )


class AITimeoutError(TestCaseGeneratorException):
    """E302: AI generation timeout."""
    
    def __init__(self, timeout_seconds: int):
        super().__init__(
            message=f"AI generation timed out after {timeout_seconds}s",
            error_code="E302",
            details={"timeout_seconds": timeout_seconds}
        )


class InvalidOutputFormatError(TestCaseGeneratorException):
    """E303: AI output does not match expected format."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"AI output format invalid: {reason}",
            error_code="E303",
            details={"reason": reason}
        )


# E4xx: GitHub API Errors

class GitHubAPIError(TestCaseGeneratorException):
    """E401: Generic GitHub API error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(
            message=f"GitHub API error: {message}",
            error_code="E401",
            details={"status_code": status_code}
        )


class BranchAlreadyExistsError(TestCaseGeneratorException):
    """E402: Branch already exists."""
    
    def __init__(self, branch_name: str):
        super().__init__(
            message=f"Branch '{branch_name}' already exists",
            error_code="E402",
            details={"branch_name": branch_name}
        )


class GitHubRateLimitError(TestCaseGeneratorException):
    """E405: GitHub API rate limit exceeded."""
    
    def __init__(self, reset_at: str):
        super().__init__(
            message=f"GitHub API rate limit exceeded, resets at {reset_at}",
            error_code="E405",
            details={"reset_at": reset_at}
        )


# E5xx: System & Infrastructure Errors

class DatabaseConnectionError(TestCaseGeneratorException):
    """E501: Database connection failed."""
    
    def __init__(self, service: str, reason: str):
        super().__init__(
            message=f"{service} connection failed: {reason}",
            error_code="E501",
            details={"service": service, "reason": reason}
        )


class ConfigurationError(TestCaseGeneratorException):
    """E502: Invalid configuration."""
    
    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Configuration error for '{field}': {reason}",
            error_code="E502",
            details={"field": field, "reason": reason}
        )
