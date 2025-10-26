"""Prompt template for test case generation using Jinja2.

This module provides the prompt template used by the AIService to generate
test cases from GitHub issues. The template includes:
- Issue context (title, body, number)
- Similar historical test cases for reference
- Structured Markdown output format
- Few-shot examples for better quality
"""
from typing import Dict, List, Any
from jinja2 import Template


# Main prompt template for test case generation
TEST_CASE_GENERATION_TEMPLATE = """You are an expert software testing engineer. Your task is to generate comprehensive test cases based on a GitHub issue.

## GitHub Issue

**Issue #{{ issue.number }}: {{ issue.title }}**

{{ issue.body }}

{% if context and context|length > 0 %}
## Similar Test Cases for Reference

The following test cases were previously generated for similar issues. Use them as inspiration for structure, coverage, and best practices:

{% for doc in context %}
### Reference {{ loop.index }}: Issue #{{ doc.issue_number }}
{{ doc.content[:500] }}...

{% endfor %}
{% endif %}

## Your Task

Generate comprehensive test cases in Markdown format following this structure:

# Test Cases: {{ issue.title }}

## Overview
Brief description of what is being tested (2-3 sentences).

## Prerequisites
List any setup requirements, test data, or environment configuration needed.

## Test Scenarios

### Scenario 1: [Happy Path - Normal Flow]
**Given**: Initial conditions and setup
**When**: User action or system event
**Then**: Expected outcome with specific assertions

**Test Steps**:
1. Step-by-step instructions
2. Include specific data values
3. Verify expected results

---

### Scenario 2: [Edge Case - Boundary Conditions]
**Given**: Edge case setup
**When**: Action at boundary
**Then**: Expected handling

**Test Steps**:
1. Detailed steps
2. Edge case values
3. Expected behavior

---

### Scenario 3: [Error Handling - Invalid Input]
**Given**: Invalid or missing input
**When**: Error condition triggered
**Then**: Appropriate error response

**Test Steps**:
1. Trigger error condition
2. Verify error message
3. Check system remains stable

---

### Scenario 4: [Performance/Load]
**Given**: Performance baseline
**When**: High load or stress condition
**Then**: Performance within acceptable limits

**Test Steps**:
1. Define performance criteria
2. Execute under load
3. Measure and verify

---

## Test Data

Provide sample test data needed for the scenarios:
```json
{
  "example_input": "value",
  "expected_output": "value"
}
```

## Acceptance Criteria

- [ ] All happy path scenarios pass
- [ ] Edge cases handled correctly
- [ ] Error messages are clear and actionable
- [ ] Performance meets requirements
- [ ] Security considerations addressed

## Notes

Any additional context, assumptions, or considerations for testers.

---

**Important Guidelines**:
1. **Be Specific**: Include exact values, not placeholders
2. **Be Comprehensive**: Cover happy path, edge cases, errors, and performance
3. **Be Practical**: Tests should be executable by a QA engineer
4. **Be Clear**: Use clear language and structured format
5. **Reference Context**: If similar test cases exist, incorporate their patterns and best practices

Now generate the test cases:
"""


class PromptTemplate:
    """Wrapper class for test case generation prompt template."""
    
    def __init__(self):
        """Initialize the Jinja2 template."""
        self.template = Template(TEST_CASE_GENERATION_TEMPLATE)
    
    def render(
        self,
        issue: Dict[str, Any],
        context: List[Dict[str, Any]] = None
    ) -> str:
        """Render the prompt template with issue and context data.
        
        Args:
            issue: Dictionary containing issue details
                - number: Issue number
                - title: Issue title
                - body: Issue body/description
            context: Optional list of similar test case documents
                - Each dict should contain: issue_number, content
        
        Returns:
            Rendered prompt string ready for LLM
        
        Example:
            >>> template = PromptTemplate()
            >>> issue = {
            ...     "number": 42,
            ...     "title": "Add OAuth2 authentication",
            ...     "body": "Implement OAuth2 with Google provider..."
            ... }
            >>> context = [
            ...     {
            ...         "issue_number": 38,
            ...         "content": "# Test Cases: Login Feature\\n..."
            ...     }
            ... ]
            >>> prompt = template.render(issue, context)
        """
        if context is None:
            context = []
        
        return self.template.render(
            issue=issue,
            context=context
        )
    
    def render_with_metadata(
        self,
        issue: Dict[str, Any],
        context: List[Dict[str, Any]] = None,
        repository: str = None,
        labels: List[str] = None
    ) -> Dict[str, Any]:
        """Render prompt and return with metadata.
        
        Args:
            issue: Issue details dictionary
            context: Similar test cases
            repository: Repository name (owner/repo)
            labels: Issue labels
        
        Returns:
            Dictionary with 'prompt' and 'metadata' keys
        """
        prompt = self.render(issue, context)
        
        metadata = {
            "issue_number": issue.get("number"),
            "repository": repository,
            "labels": labels or [],
            "context_count": len(context) if context else 0,
            "context_sources": [doc.get("issue_number") for doc in (context or [])]
        }
        
        return {
            "prompt": prompt,
            "metadata": metadata
        }


# Example few-shot prompt for better quality (alternative approach)
FEW_SHOT_EXAMPLES = """
# Example 1: Authentication Feature

## Overview
Testing OAuth2 authentication flow with Google and GitHub providers.

## Test Scenarios

### Scenario 1: Successful Google OAuth Login
**Given**: User is on the login page and Google OAuth is configured
**When**: User clicks "Sign in with Google" and completes OAuth flow
**Then**: User is redirected to dashboard with valid session token

**Test Steps**:
1. Navigate to `/login`
2. Click "Sign in with Google" button
3. Complete Google consent screen
4. Verify redirect to `/dashboard`
5. Verify session cookie is set
6. Verify user profile is loaded

---

# Example 2: API Endpoint

## Overview
Testing RESTful API endpoint for user profile retrieval.

## Test Scenarios

### Scenario 1: Get User Profile - Authenticated
**Given**: User is authenticated with valid JWT token
**When**: GET request to `/api/users/{id}`
**Then**: Returns 200 OK with user profile data

**Test Steps**:
1. Authenticate and obtain JWT token
2. Send GET `/api/users/123` with Authorization header
3. Verify response status is 200
4. Verify response body contains: id, name, email, created_at
5. Verify email is not null

### Scenario 2: Get User Profile - Unauthenticated
**Given**: No authentication token provided
**When**: GET request to `/api/users/{id}` without Authorization header
**Then**: Returns 401 Unauthorized

**Test Steps**:
1. Send GET `/api/users/123` without Authorization header
2. Verify response status is 401
3. Verify error message: "Authentication required"

---
"""


def get_default_template() -> PromptTemplate:
    """Get the default prompt template instance.
    
    Returns:
        PromptTemplate instance ready to use
    """
    return PromptTemplate()
