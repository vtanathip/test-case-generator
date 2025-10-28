"""Unit tests for AIService with LangGraph workflow."""
from datetime import datetime
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from src.core.exceptions import AIGenerationError, AITimeoutError, VectorDBQueryError
from src.models.processing_job import JobStatus, ProcessingJob
from src.services.ai_service import AIService, WorkflowStage


class TestAIServiceWorkflow:
    """Test AIService 6-stage LangGraph workflow."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture for AIService dependencies."""
        return {
            'llm_client': AsyncMock(),
            'vector_db': AsyncMock(),
            'embedding_service': Mock(),
            'github_client': AsyncMock(),
            'redis_client': AsyncMock(),
            'config': Mock()
        }

    @pytest.fixture
    def ai_service(self, mock_dependencies):
        """Fixture for AIService instance."""
        mock_dependencies['config'].LLAMA_TIMEOUT = 120
        mock_dependencies['config'].LLAMA_MODEL = "llama-3.2-11b"
        mock_dependencies['config'].MAX_RETRIES = 3
        mock_dependencies['config'].RETRY_DELAYS = [5, 15, 45]

        return AIService(**mock_dependencies)

    @pytest.fixture
    def sample_processing_job(self):
        """Fixture for sample ProcessingJob."""
        return ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.PENDING,
            started_at=datetime.now(),
            idempotency_key="abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
            current_stage=WorkflowStage.RECEIVE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )

    @pytest.mark.asyncio
    async def test_stage_1_receive_webhook(self, ai_service, sample_processing_job):
        """Test RECEIVE stage: Validate webhook and initialize job."""
        # Mock webhook event
        mock_webhook_event = Mock()
        mock_webhook_event.issue_number = 42
        mock_webhook_event.issue_title = "Add authentication"
        mock_webhook_event.issue_body = "Implement OAuth2"
        mock_webhook_event.repository = "owner/repo"

        # Execute RECEIVE stage
        result = await ai_service.receive_webhook(
            job=sample_processing_job,
            webhook_event=mock_webhook_event
        )

        assert result.current_stage == WorkflowStage.RETRIEVE
        assert result.status == JobStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_stage_2_retrieve_context(self, ai_service, sample_processing_job):
        """Test RETRIEVE stage: Query vector DB for top 5 similar test cases (FR-004)."""
        # Mock webhook event
        mock_webhook_event = Mock()
        mock_webhook_event.issue_body = "Implement OAuth2 authentication"

        # Mock vector DB to return 5 similar documents
        mock_similar_docs = [
            {"issue_number": 38, "similarity": 0.85},
            {"issue_number": 39, "similarity": 0.82},
            {"issue_number": 40, "similarity": 0.78},
            {"issue_number": 41, "similarity": 0.75},
            {"issue_number": 37, "similarity": 0.72}
        ]
        ai_service.vector_db.query_similar = AsyncMock(return_value=mock_similar_docs)

        # Execute RETRIEVE stage
        context = await ai_service.retrieve_context(
            job=sample_processing_job,
            webhook_event=mock_webhook_event
        )

        # Verify top 5 results retrieved
        assert len(context) == 5
        assert context[0]["issue_number"] == 38
        assert context[0]["similarity"] >= 0.7  # SC-006 threshold

        # Verify vector DB query was called
        ai_service.vector_db.query_similar.assert_called_once()

    @pytest.mark.asyncio
    async def test_stage_2_retrieve_no_context(self, ai_service, sample_processing_job):
        """Test RETRIEVE stage handles case with no similar context."""
        mock_webhook_event = Mock()
        mock_webhook_event.issue_body = "Completely new feature"

        # Mock vector DB to return empty results
        ai_service.vector_db.query_similar = AsyncMock(return_value=[])

        # Should still proceed with empty context
        context = await ai_service.retrieve_context(
            job=sample_processing_job,
            webhook_event=mock_webhook_event
        )

        assert len(context) == 0

    @pytest.mark.asyncio
    async def test_stage_3_generate_test_cases(self, ai_service, sample_processing_job):
        """Test GENERATE stage: AI generates test cases using LLM."""
        mock_webhook_event = Mock()
        mock_webhook_event.issue_number = 42
        mock_webhook_event.issue_title = "Add authentication"
        mock_webhook_event.issue_body = "Implement OAuth2"

        mock_context = [
            {"issue_number": 38, "content": "Similar test case"}
        ]

        # Mock LLM response
        mock_llm_response = "# Test Cases: Add Authentication\n\n## Scenario 1: Login Success"
        ai_service.llm_client.generate = AsyncMock(return_value=mock_llm_response)

        # Execute GENERATE stage
        test_document = await ai_service.generate_test_cases(
            job=sample_processing_job,
            webhook_event=mock_webhook_event,
            context=mock_context
        )

        assert test_document.issue_number == 42
        assert "# Test Cases:" in test_document.content
        assert test_document.ai_model == "llama-3.2-11b"

        # Verify LLM was called with prompt
        ai_service.llm_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_stage_3_generate_timeout(self, ai_service, sample_processing_job):
        """Test GENERATE stage handles AI timeout (120s per FR-009)."""
        import asyncio

        mock_webhook_event = Mock()
        mock_webhook_event.issue_number = 42
        mock_webhook_event.issue_title = "Add authentication"
        mock_webhook_event.issue_body = "Implement OAuth2"

        # Mock LLM to timeout
        async def mock_timeout(*args, **kwargs):
            await asyncio.sleep(121)  # Exceed 120s timeout

        ai_service.llm_client.generate = mock_timeout

        # Should raise AITimeoutError (E302)
        with pytest.raises(AITimeoutError) as exc_info:
            await ai_service.generate_test_cases(
                job=sample_processing_job,
                webhook_event=mock_webhook_event,
                context=[]
            )

        assert exc_info.value.error_code == "E302"

    @pytest.mark.asyncio
    async def test_stage_4_commit_to_branch(self, ai_service, sample_processing_job):
        """Test COMMIT stage: Create branch and commit test document."""
        mock_test_document = Mock()
        mock_test_document.branch_name = "test-cases/issue-42"
        mock_test_document.content = "# Test Cases"
        mock_test_document.issue_number = 42

        # Mock GitHub operations
        ai_service.github_client.create_branch = AsyncMock()
        ai_service.github_client.create_or_update_file = AsyncMock()

        # Execute COMMIT stage
        result = await ai_service.commit_test_cases(
            job=sample_processing_job,
            test_document=mock_test_document
        )

        # Verify branch created
        ai_service.github_client.create_branch.assert_called_once_with(
            branch_name="test-cases/issue-42"
        )

        # Verify file committed
        ai_service.github_client.create_or_update_file.assert_called_once()
        assert result.current_stage == WorkflowStage.CREATE_PR

    @pytest.mark.asyncio
    async def test_stage_5_create_pull_request(self, ai_service, sample_processing_job):
        """Test CREATE_PR stage: Open GitHub pull request."""
        mock_test_document = Mock()
        mock_test_document.branch_name = "test-cases/issue-42"
        mock_test_document.title = "Test Cases: Add Authentication"
        mock_test_document.issue_number = 42

        # Mock PR creation
        mock_pr = {"number": 123, "html_url": "https://github.com/owner/repo/pull/123"}
        ai_service.github_client.create_pull_request = AsyncMock(return_value=mock_pr)

        # Execute CREATE_PR stage
        updated_document = await ai_service.create_pull_request(
            job=sample_processing_job,
            test_document=mock_test_document
        )

        # Verify PR created with correct params
        ai_service.github_client.create_pull_request.assert_called_once()
        call_args = ai_service.github_client.create_pull_request.call_args
        body = call_args.kwargs.get("body", "")
        assert "Closes #42" in body

        # Verify document updated with PR info
        assert updated_document.pr_number == 123
        assert updated_document.pr_url == "https://github.com/owner/repo/pull/123"

    @pytest.mark.asyncio
    async def test_stage_6_finalize_job(self, ai_service, sample_processing_job):
        """Test FINALIZE stage: Add comment to issue and complete job."""
        mock_test_document = Mock()
        mock_test_document.issue_number = 42
        mock_test_document.pr_url = "https://github.com/owner/repo/pull/123"

        # Mock issue comment
        ai_service.github_client.add_issue_comment = AsyncMock()

        # Execute FINALIZE stage
        completed_job = await ai_service.finalize_job(
            job=sample_processing_job,
            test_document=mock_test_document
        )

        # Verify comment added to issue
        ai_service.github_client.add_issue_comment.assert_called_once_with(
            issue_number=42,
            comment=ANY  # Comment contains PR link
        )

        # Verify job marked as COMPLETED
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.current_stage == WorkflowStage.FINALIZE
        assert completed_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_full_workflow_end_to_end(self, ai_service, sample_processing_job):
        """Test complete 6-stage workflow: RECEIVE → RETRIEVE → GENERATE → COMMIT → CREATE_PR → FINALIZE."""
        mock_webhook_event = Mock()
        mock_webhook_event.issue_number = 42
        mock_webhook_event.issue_title = "Add authentication"
        mock_webhook_event.issue_body = "Implement OAuth2"
        mock_webhook_event.repository = "owner/repo"

        # Mock all dependencies
        ai_service.vector_db.query_similar = AsyncMock(return_value=[])
        ai_service.llm_client.generate = AsyncMock(return_value="# Test Cases")
        ai_service.github_client.create_branch = AsyncMock()
        ai_service.github_client.create_or_update_file = AsyncMock()
        ai_service.github_client.create_pull_request = AsyncMock(
            return_value={"number": 123, "html_url": "https://github.com/owner/repo/pull/123"}
        )
        ai_service.github_client.add_issue_comment = AsyncMock()

        # Execute full workflow
        final_job = await ai_service.execute_workflow(
            job=sample_processing_job,
            webhook_event=mock_webhook_event
        )

        # Verify all stages completed
        assert final_job.status == JobStatus.COMPLETED
        assert final_job.current_stage == WorkflowStage.FINALIZE

    @pytest.mark.asyncio
    async def test_retry_logic_exponential_backoff(self, ai_service, sample_processing_job):
        """Test retry logic with exponential backoff (5s, 15s, 45s per FR-011)."""
        mock_webhook_event = Mock()
        mock_webhook_event.issue_number = 42
        mock_webhook_event.issue_body = "Test"

        # Mock LLM to fail first 2 attempts, succeed on 3rd
        call_count = 0
        async def mock_generate_with_retries(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AIGenerationError("Temporary failure", "E301")
            return "# Test Cases"

        ai_service.llm_client.generate = mock_generate_with_retries

        # Execute with retries
        test_document = await ai_service.generate_with_retries(
            job=sample_processing_job,
            webhook_event=mock_webhook_event,
            context=[]
        )

        # Verify retry count and delays
        assert sample_processing_job.retry_count <= 3
        assert call_count == 3  # Failed twice, succeeded third time

    @pytest.mark.asyncio
    async def test_retry_exhausted_fails_job(self, ai_service, sample_processing_job):
        """Test job fails after 3 retry attempts."""
        mock_webhook_event = Mock()
        mock_webhook_event.issue_number = 42
        mock_webhook_event.issue_body = "Test"

        # Mock LLM to always fail
        ai_service.llm_client.generate = AsyncMock(
            side_effect=AIGenerationError("Persistent failure", "E301")
        )

        # Should fail after max retries
        with pytest.raises(AIGenerationError):
            await ai_service.generate_with_retries(
                job=sample_processing_job,
                webhook_event=mock_webhook_event,
                context=[],
                max_retries=3
            )

        # Verify generate was called 3 times (3 retry attempts)
        assert ai_service.llm_client.generate.call_count == 3

    @pytest.mark.asyncio
    async def test_prompt_template_rendering(self, ai_service):
        """Test prompt template is rendered correctly with issue and context."""
        issue_data = {
            "number": 42,
            "title": "Add authentication",
            "body": "Implement OAuth2 with Google provider"
        }

        context_data = [
            {"issue_number": 38, "content": "Test case for login"},
            {"issue_number": 39, "content": "Test case for logout"}
        ]

        # Render prompt
        prompt = ai_service.render_prompt(
            issue=issue_data,
            context=context_data
        )

        # Verify prompt contains issue details
        assert "42" in prompt
        assert "Add authentication" in prompt
        assert "OAuth2" in prompt

        # Verify context is included
        assert "38" in prompt or "login" in prompt
        assert "39" in prompt or "logout" in prompt

    @pytest.mark.asyncio
    async def test_vector_db_failure_handling(self, ai_service, sample_processing_job):
        """Test workflow handles vector DB failures gracefully."""
        mock_webhook_event = Mock()
        mock_webhook_event.issue_body = "Test"

        # Mock vector DB to fail
        ai_service.vector_db.query_similar = AsyncMock(
            side_effect=VectorDBQueryError("Connection failed", "E201")
        )

        # Should raise VectorDBQueryError
        with pytest.raises(VectorDBQueryError) as exc_info:
            await ai_service.retrieve_context(
                job=sample_processing_job,
                webhook_event=mock_webhook_event
            )

        assert exc_info.value.error_code == "E201"
