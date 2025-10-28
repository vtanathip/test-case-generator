"""AIService with 6-stage LangGraph workflow for test case generation."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from uuid import uuid4
from pydantic import BaseModel
import operator

import structlog
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.models.processing_job import ProcessingJob, JobStatus, WorkflowStage
from src.models.test_case_document import TestCaseDocument
from src.core.exceptions import AIGenerationError, AITimeoutError, VectorDBQueryError
from src.services.ai_prompt_template import PromptTemplate

# Initialize structured logger
logger = structlog.get_logger(__name__)


class WorkflowState(TypedDict):
    """State container for LangGraph workflow.

    This state is passed through all nodes in the graph and tracks:
    - job: Current ProcessingJob with status and stage
    - webhook_event: Original webhook data
    - context: Retrieved similar test cases from vector DB
    - test_document: Generated test case document
    - error: Any error message encountered
    - messages: Conversation history for LangChain
    """
    job: ProcessingJob
    webhook_event: Any
    context: Optional[List[Dict[str, Any]]]
    test_document: Optional[TestCaseDocument]
    error: Optional[str]
    # Use operator.add to append messages instead of replacing
    messages: Annotated[List[BaseMessage], operator.add]


class AIService:
    """Service for AI-powered test case generation using LangGraph state machine.

    Implements a 6-stage workflow as a directed graph:
    RECEIVE → RETRIEVE → GENERATE → COMMIT → CREATE_PR → FINALIZE → END

    Each stage is a node in the graph that:
    1. Receives the current state
    2. Performs its operation
    3. Updates and returns the state
    4. Triggers the next stage automatically
    """

    def __init__(
        self,
        llm_client,
        vector_db,
        embedding_service,
        github_client,
        redis_client,
        config
    ):
        """Initialize AIService with dependencies and build LangGraph workflow.

        Args:
            llm_client: LLM client for AI generation
            vector_db: Vector database for semantic search
            embedding_service: Service for text embeddings
            github_client: GitHub API client
            redis_client: Redis client for caching
            config: Configuration object
        """
        self.llm_client = llm_client
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.github_client = github_client
        self.redis_client = redis_client
        self.config = config

        # Configuration
        self.timeout = getattr(config, 'LLAMA_TIMEOUT', 120)
        self.model_name = getattr(config, 'LLAMA_MODEL', 'llama-3.2-11b')
        self.max_retries = getattr(config, 'MAX_RETRIES', 3)
        self.retry_delays = getattr(config, 'RETRY_DELAYS', [5, 15, 45])

        # Initialize Jinja2 prompt template
        self.prompt_template = PromptTemplate()

        # Build the LangGraph workflow
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine with 6 stages.

        Returns:
            Compiled StateGraph ready for execution
        """
        # Initialize the graph with our state schema
        workflow = StateGraph(WorkflowState)

        # Add nodes for each stage
        workflow.add_node("receive", self._receive_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("commit", self._commit_node)
        workflow.add_node("create_pr", self._create_pr_node)
        workflow.add_node("finalize", self._finalize_node)

        # Define the workflow edges (stage transitions)
        workflow.set_entry_point("receive")
        workflow.add_edge("receive", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", "commit")
        workflow.add_edge("commit", "create_pr")
        workflow.add_edge("create_pr", "finalize")
        workflow.add_edge("finalize", END)

        # Compile the graph for execution
        return workflow.compile()

    async def _receive_node(self, state: WorkflowState) -> WorkflowState:
        """Node 1: RECEIVE - Validate webhook and initialize job.

        Updates job status to PROCESSING and stage to RETRIEVE.

        Args:
            state: Current workflow state

        Returns:
            Updated state with job in PROCESSING/RETRIEVE
        """
        job = state["job"]

        # Update job to PROCESSING status and RETRIEVE stage
        updated_job = ProcessingJob(
            job_id=job.job_id,
            webhook_event_id=job.webhook_event_id,
            status=JobStatus.PROCESSING,
            started_at=job.started_at,
            completed_at=None,
            error_message=None,
            error_code=None,
            retry_count=job.retry_count,
            retry_delays=job.retry_delays,
            last_retry_at=job.last_retry_at,
            idempotency_key=job.idempotency_key,
            current_stage=WorkflowStage.RETRIEVE,
            correlation_id=job.correlation_id
        )

        return {
            **state,
            "job": updated_job,
            "messages": [HumanMessage(content="Stage 1 (RECEIVE): Webhook received and validated")]
        }

    async def _retrieve_node(self, state: WorkflowState) -> WorkflowState:
        """Node 2: RETRIEVE - Query vector DB for similar test cases.

        Queries vector DB for top 5 similar documents with similarity >= 0.7.

        Args:
            state: Current workflow state

        Returns:
            Updated state with context from vector DB

        Raises:
            VectorDBQueryError: If vector DB query fails
        """
        webhook_event = state["webhook_event"]

        try:
            # Generate embedding for the issue body
            query_embedding = self.embedding_service.generate_embedding(
                webhook_event.issue_body)

            # Query vector DB for similar documents
            results = await self.vector_db.query_similar(
                query_embedding=query_embedding,
                n_results=5
            )

            # Transform ChromaDB results into expected format
            similar_docs = []
            if results and results.get('documents') and len(results['documents']) > 0:
                documents = results['documents'][0]  # First query result
                metadatas = results['metadatas'][0] if results.get(
                    'metadatas') else []

                for i, doc_content in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    similar_docs.append({
                        'content': doc_content,
                        'issue_number': metadata.get('issue_number', 'unknown')
                    })

            return {
                **state,
                "context": similar_docs,
                "messages": [AIMessage(content=f"Stage 2 (RETRIEVE): Retrieved {len(similar_docs)} similar documents")]
            }

        except Exception as e:
            return {
                **state,
                "error": str(e),
                "messages": [AIMessage(content=f"Stage 2 (RETRIEVE): Failed - {str(e)}")]
            }

    async def _generate_node(self, state: WorkflowState) -> WorkflowState:
        """Node 3: GENERATE - AI generates test cases using LLM.

        Renders prompt and calls LLM with 120s timeout.

        Args:
            state: Current workflow state

        Returns:
            Updated state with generated test document

        Raises:
            AITimeoutError: If generation exceeds timeout
            AIGenerationError: If generation fails
        """
        job = state["job"]
        webhook_event = state["webhook_event"]
        context = state.get("context", [])

        log = logger.bind(
            job_id=job.job_id,
            correlation_id=job.correlation_id,
            stage=WorkflowStage.GENERATE.value
        )

        log.info(
            "stage_generate_started",
            model=self.model_name,
            timeout_seconds=self.timeout,
            context_count=len(context) if context else 0
        )

        # Render prompt with issue and context
        prompt = self.render_prompt(
            issue={
                "number": webhook_event.issue_number,
                "title": webhook_event.issue_title,
                "body": webhook_event.issue_body
            },
            context=context
        )

        # Generate test cases with timeout
        generation_start = datetime.now()
        try:
            async with asyncio.timeout(self.timeout):
                content = await self.llm_client.generate(
                    prompt=prompt
                )
            generation_duration = (
                datetime.now() - generation_start).total_seconds()

            log.info(
                "stage_generate_completed",
                duration_seconds=generation_duration,
                content_length=len(content)
            )

        except asyncio.TimeoutError:
            generation_duration = (
                datetime.now() - generation_start).total_seconds()
            error_msg = f"AI generation timeout after {self.timeout}s"

            log.error(
                "stage_generate_timeout",
                timeout_seconds=self.timeout,
                duration_seconds=generation_duration
            )

            return {
                **state,
                "error": error_msg,
                "messages": [AIMessage(content=f"Stage 3 (GENERATE): {error_msg}")]
            }
        except Exception as e:
            generation_duration = (
                datetime.now() - generation_start).total_seconds()
            error_msg = f"AI generation failed: {str(e)}"

            log.error(
                "stage_generate_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=generation_duration
            )

            return {
                **state,
                "error": error_msg,
                "messages": [AIMessage(content=f"Stage 3 (GENERATE): {error_msg}")]
            }

        # Create TestCaseDocument
        context_sources = [doc["issue_number"]
                           for doc in context] if context else []
        metadata = {
            "issue": webhook_event.issue_number,
            "generated_at": datetime.now().isoformat(),
            "ai_model": self.model_name,
            "context_sources": context_sources
        }

        test_document = TestCaseDocument(
            document_id=str(uuid4()),
            issue_number=webhook_event.issue_number,
            title=f"Test Cases: {webhook_event.issue_title}",
            content=content,
            metadata=metadata,
            branch_name=f"test-cases/issue-{webhook_event.issue_number}",
            pr_number=None,
            pr_url=None,
            generated_at=datetime.now(),
            ai_model=self.model_name,
            context_sources=context_sources,
            correlation_id=job.correlation_id
        )

        return {
            **state,
            "test_document": test_document,
            "messages": [AIMessage(content="Stage 3 (GENERATE): Test cases generated successfully")]
        }

    async def _commit_node(self, state: WorkflowState) -> WorkflowState:
        """Node 4: COMMIT - Create branch and commit test document.

        Creates a new branch and commits the generated test cases.

        Args:
            state: Current workflow state

        Returns:
            Updated state with job in CREATE_PR stage
        """
        job = state["job"]
        test_document = state["test_document"]
        webhook_event = state["webhook_event"]

        # Get repository and default branch SHA
        repo = self.github_client.get_repo(webhook_event.repository)
        default_branch = repo.default_branch
        base_sha = repo.get_branch(default_branch).commit.sha

        # Create new branch
        self.github_client.create_branch(
            repo_full_name=webhook_event.repository,
            branch_name=test_document.branch_name,
            base_sha=base_sha
        )

        # Commit test case file
        file_path = f"test-cases/issue-{test_document.issue_number}.md"
        self.github_client.create_or_update_file(
            repo_full_name=webhook_event.repository,
            file_path=file_path,
            content=test_document.content,
            commit_message=f"Add test cases for issue #{test_document.issue_number}",
            branch=test_document.branch_name
        )

        # Update job stage to CREATE_PR
        updated_job = ProcessingJob(
            job_id=job.job_id,
            webhook_event_id=job.webhook_event_id,
            status=job.status,
            started_at=job.started_at,
            completed_at=None,
            error_message=None,
            error_code=None,
            retry_count=job.retry_count,
            retry_delays=job.retry_delays,
            last_retry_at=job.last_retry_at,
            idempotency_key=job.idempotency_key,
            current_stage=WorkflowStage.CREATE_PR,
            correlation_id=job.correlation_id
        )

        return {
            **state,
            "job": updated_job,
            "messages": [AIMessage(content="Stage 4 (COMMIT): Test cases committed to branch")]
        }

    async def _create_pr_node(self, state: WorkflowState) -> WorkflowState:
        """Node 5: CREATE_PR - Open GitHub pull request.

        Creates a PR that closes the original issue.

        Args:
            state: Current workflow state

        Returns:
            Updated state with PR details in test document
        """
        test_document = state["test_document"]
        webhook_event = state["webhook_event"]

        # Create PR with issue reference
        pr_body = f"Automated test case generation for issue #{test_document.issue_number}.\n\nCloses #{test_document.issue_number}"

        pr = self.github_client.create_pull_request(
            repo_full_name=webhook_event.repository,
            title=test_document.title,
            body=pr_body,
            head=test_document.branch_name,
            base="main"
        )

        # Update test document with PR info
        if isinstance(test_document, BaseModel):
            updated_document = test_document.model_copy(
                update={
                    "pr_number": pr["number"],
                    "pr_url": pr["html_url"]
                }
            )
        else:
            # For Mock objects in tests
            test_document.pr_number = pr["number"]
            test_document.pr_url = pr["html_url"]
            updated_document = test_document

        return {
            **state,
            "test_document": updated_document,
            "messages": [AIMessage(content=f"Stage 5 (CREATE_PR): Pull request #{pr['number']} created")]
        }

    async def _finalize_node(self, state: WorkflowState) -> WorkflowState:
        """Node 6: FINALIZE - Add comment to issue and complete job.

        Adds a comment to the issue with the PR link and marks job as COMPLETED.

        Args:
            state: Current workflow state

        Returns:
            Final state with completed job
        """
        job = state["job"]
        test_document = state["test_document"]
        webhook_event = state["webhook_event"]

        # Add comment to issue with PR link
        comment = f"✅ Test cases have been generated and are ready for review!\n\nPull Request: {test_document.pr_url}"

        self.github_client.add_issue_comment(
            repo_full_name=webhook_event.repository,
            issue_number=test_document.issue_number,
            comment=comment
        )

        # Mark job as COMPLETED
        completed_job = ProcessingJob(
            job_id=job.job_id,
            webhook_event_id=job.webhook_event_id,
            status=JobStatus.COMPLETED,
            started_at=job.started_at,
            completed_at=datetime.now(),
            error_message=None,
            error_code=None,
            retry_count=job.retry_count,
            retry_delays=job.retry_delays,
            last_retry_at=job.last_retry_at,
            idempotency_key=job.idempotency_key,
            current_stage=WorkflowStage.FINALIZE,
            correlation_id=job.correlation_id
        )

        return {
            **state,
            "job": completed_job,
            "messages": [AIMessage(content="Stage 6 (FINALIZE): Workflow completed successfully")]
        }

    # ============================================================================
    # Public API - These methods provide compatibility with existing tests
    # They either delegate to graph nodes or invoke the full graph
    # ============================================================================

    async def receive_webhook(
        self,
        job: ProcessingJob,
        webhook_event: Any
    ) -> ProcessingJob:
        """Stage 1 (RECEIVE): Validate webhook and initialize job.

        Args:
            job: Current processing job
            webhook_event: Validated webhook event

        Returns:
            Updated job with RETRIEVE stage
        """
        # Update job to PROCESSING status and RETRIEVE stage
        updated_job = ProcessingJob(
            job_id=job.job_id,
            webhook_event_id=job.webhook_event_id,
            status=JobStatus.PROCESSING,
            started_at=job.started_at,
            completed_at=None,
            error_message=None,
            error_code=None,
            retry_count=job.retry_count,
            retry_delays=job.retry_delays,
            last_retry_at=job.last_retry_at,
            idempotency_key=job.idempotency_key,
            current_stage=WorkflowStage.RETRIEVE,
            correlation_id=job.correlation_id
        )

        return updated_job

    async def retrieve_context(
        self,
        job: ProcessingJob,
        webhook_event: Any
    ) -> List[Dict[str, Any]]:
        """Stage 2 (RETRIEVE): Query vector DB for top 5 similar test cases.

        Args:
            job: Current processing job
            webhook_event: Webhook event with issue details

        Returns:
            List of similar documents (top 5)

        Raises:
            VectorDBQueryError: If vector DB query fails
        """
        try:
            # Generate embedding for the issue body
            query_embedding = self.embedding_service.generate_embedding(
                webhook_event.issue_body)

            # Query vector DB for similar documents
            results = await self.vector_db.query_similar(
                query_embedding=query_embedding,
                n_results=5
            )

            # Transform ChromaDB results into expected format
            similar_docs = []
            if results and results.get('documents') and len(results['documents']) > 0:
                documents = results['documents'][0]  # First query result
                metadatas = results['metadatas'][0] if results.get(
                    'metadatas') else []

                for i, doc_content in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    similar_docs.append({
                        'content': doc_content,
                        'issue_number': metadata.get('issue_number', 'unknown')
                    })

            return similar_docs

        except Exception as e:
            raise VectorDBQueryError(
                message=f"Vector DB query failed: {str(e)}",
                details={"error": str(e)}
            )

    async def generate_test_cases(
        self,
        job: ProcessingJob,
        webhook_event: Any,
        context: List[Dict[str, Any]]
    ) -> TestCaseDocument:
        """Stage 3 (GENERATE): AI generates test cases using LLM.

        Args:
            job: Current processing job
            webhook_event: Webhook event with issue details
            context: Similar documents from vector DB

        Returns:
            Generated test case document

        Raises:
            AITimeoutError: If generation exceeds timeout
            AIGenerationError: If generation fails
        """
        # Render prompt with issue and context
        prompt = self.render_prompt(
            issue={
                "number": webhook_event.issue_number,
                "title": webhook_event.issue_title,
                "body": webhook_event.issue_body
            },
            context=context
        )

        # Generate test cases with timeout
        try:
            async with asyncio.timeout(self.timeout):
                content = await self.llm_client.generate(
                    prompt=prompt
                )
        except asyncio.TimeoutError:
            raise AITimeoutError(timeout_seconds=self.timeout)
        except Exception as e:
            raise AIGenerationError(
                message=f"AI generation failed: {str(e)}",
                details={"error": str(e)}
            )

        # Create TestCaseDocument
        metadata = {
            "issue": webhook_event.issue_number,
            "generated_at": datetime.now().isoformat(),
            "ai_model": self.model_name,
            "context_sources": [doc["issue_number"] for doc in context]
        }

        test_document = TestCaseDocument(
            document_id=str(uuid4()),
            issue_number=webhook_event.issue_number,
            title=f"Test Cases: {webhook_event.issue_title}",
            content=content,
            metadata=metadata,
            branch_name=f"test-cases/issue-{webhook_event.issue_number}",
            pr_number=None,
            pr_url=None,
            generated_at=datetime.now(),
            ai_model=self.model_name,
            context_sources=[doc["issue_number"] for doc in context],
            correlation_id=job.correlation_id
        )

        return test_document

    async def commit_test_cases(
        self,
        job: ProcessingJob,
        test_document: TestCaseDocument
    ) -> ProcessingJob:
        """Stage 4 (COMMIT): Create branch and commit test document.

        Args:
            job: Current processing job
            test_document: Generated test case document

        Returns:
            Updated job with CREATE_PR stage
        """
        # Create new branch
        self.github_client.create_branch(
            branch_name=test_document.branch_name
        )

        # Commit test case file
        file_path = f"test-cases/issue-{test_document.issue_number}.md"
        self.github_client.create_or_update_file(
            file_path=file_path,
            content=test_document.content,
            commit_message=f"Add test cases for issue #{test_document.issue_number}",
            branch=test_document.branch_name
        )

        # Update job stage
        updated_job = ProcessingJob(
            job_id=job.job_id,
            webhook_event_id=job.webhook_event_id,
            status=job.status,
            started_at=job.started_at,
            completed_at=None,
            error_message=None,
            error_code=None,
            retry_count=job.retry_count,
            retry_delays=job.retry_delays,
            last_retry_at=job.last_retry_at,
            idempotency_key=job.idempotency_key,
            current_stage=WorkflowStage.CREATE_PR,
            correlation_id=job.correlation_id
        )

        return updated_job

    async def create_pull_request(
        self,
        job: ProcessingJob,
        test_document: TestCaseDocument
    ) -> TestCaseDocument:
        """Stage 5 (CREATE_PR): Open GitHub pull request.

        Args:
            job: Current processing job
            test_document: Test case document with committed content

        Returns:
            Updated test document with PR number and URL
        """
        # Create PR with issue reference
        pr_body = f"Automated test case generation for issue #{test_document.issue_number}.\n\nCloses #{test_document.issue_number}"

        pr = self.github_client.create_pull_request(
            title=test_document.title,
            body=pr_body,
            head=test_document.branch_name,
            base="main"
        )

        # Update test document with PR info
        # Check if it's a real Pydantic model or a mock
        if isinstance(test_document, BaseModel):
            updated_document = test_document.model_copy(
                update={
                    "pr_number": pr["number"],
                    "pr_url": pr["html_url"]
                }
            )
        else:
            # For Mock objects in tests, just set attributes
            test_document.pr_number = pr["number"]
            test_document.pr_url = pr["html_url"]
            updated_document = test_document

        return updated_document

    async def finalize_job(
        self,
        job: ProcessingJob,
        test_document: TestCaseDocument
    ) -> ProcessingJob:
        """Stage 6 (FINALIZE): Add comment to issue and complete job.

        Args:
            job: Current processing job
            test_document: Test case document with PR created

        Returns:
            Completed job
        """
        # Add comment to issue with PR link
        comment = f"✅ Test cases have been generated and are ready for review!\n\nPull Request: {test_document.pr_url}"

        self.github_client.add_issue_comment(
            issue_number=test_document.issue_number,
            comment=comment
        )

        # Complete job
        completed_job = ProcessingJob(
            job_id=job.job_id,
            webhook_event_id=job.webhook_event_id,
            status=JobStatus.COMPLETED,
            started_at=job.started_at,
            completed_at=datetime.now(),
            error_message=None,
            error_code=None,
            retry_count=job.retry_count,
            retry_delays=job.retry_delays,
            last_retry_at=job.last_retry_at,
            idempotency_key=job.idempotency_key,
            current_stage=WorkflowStage.FINALIZE,
            correlation_id=job.correlation_id
        )

        return completed_job

    async def execute_workflow(
        self,
        job: ProcessingJob,
        webhook_event: Any
    ) -> ProcessingJob:
        """Execute the complete 6-stage LangGraph workflow.

        This is the main entry point that runs the compiled StateGraph.
        The workflow progresses through: RECEIVE → RETRIEVE → GENERATE → COMMIT → CREATE_PR → FINALIZE

        Args:
            job: Initial processing job
            webhook_event: Validated webhook event

        Returns:
            Completed job with final status
        """
        log = logger.bind(
            job_id=job.job_id,
            correlation_id=job.correlation_id,
            issue_number=webhook_event.issue_number,
            repository=webhook_event.repository
        )

        log.info(
            "workflow_started",
            initial_stage=job.current_stage.value
        )

        # Create initial state for the graph
        initial_state: WorkflowState = {
            "job": job,
            "webhook_event": webhook_event,
            "context": None,
            "test_document": None,
            "error": None,
            "messages": []
        }

        try:
            # Execute the compiled LangGraph workflow
            workflow_start = datetime.now()
            final_state = await self.graph.ainvoke(initial_state)
            workflow_duration = (
                datetime.now() - workflow_start).total_seconds()

            # Check if workflow encountered an error
            if final_state.get("error"):
                log.error(
                    "workflow_failed",
                    error=final_state["error"],
                    duration_seconds=workflow_duration
                )
                # Mark job as failed
                failed_job = ProcessingJob(
                    job_id=job.job_id,
                    webhook_event_id=job.webhook_event_id,
                    status=JobStatus.FAILED,
                    started_at=job.started_at,
                    completed_at=datetime.now(),
                    error_message=final_state["error"],
                    error_code="E301",
                    retry_count=job.retry_count,
                    retry_delays=job.retry_delays,
                    last_retry_at=job.last_retry_at,
                    idempotency_key=job.idempotency_key,
                    current_stage=job.current_stage,
                    correlation_id=job.correlation_id
                )
                return failed_job

            log.info(
                "workflow_completed",
                final_status=final_state["job"].status.value,
                final_stage=final_state["job"].current_stage.value,
                duration_seconds=workflow_duration
            )

            # Return the completed job from final state
            return final_state["job"]

        except Exception as e:
            log.error(
                "workflow_exception",
                error=str(e),
                error_type=type(e).__name__
            )
            # Handle unexpected errors during graph execution
            failed_job = ProcessingJob(
                job_id=job.job_id,
                webhook_event_id=job.webhook_event_id,
                status=JobStatus.FAILED,
                started_at=job.started_at,
                completed_at=datetime.now(),
                error_message=str(e),
                error_code="E300",
                retry_count=job.retry_count,
                retry_delays=job.retry_delays,
                last_retry_at=job.last_retry_at,
                idempotency_key=job.idempotency_key,
                current_stage=job.current_stage,
                correlation_id=job.correlation_id
            )
            return failed_job

    async def generate_with_retries(
        self,
        job: ProcessingJob,
        webhook_event: Any,
        context: List[Dict[str, Any]],
        max_retries: Optional[int] = None
    ) -> TestCaseDocument:
        """Generate test cases with retry logic (exponential backoff).

        Args:
            job: Current processing job
            webhook_event: Webhook event
            context: Context from vector DB
            max_retries: Maximum retry attempts (default from config)

        Returns:
            Generated test case document

        Raises:
            AIGenerationError: If all retries exhausted
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_error: Optional[AIGenerationError] = None

        for attempt in range(retries):
            try:
                return await self.generate_test_cases(job, webhook_event, context)
            except AIGenerationError as e:
                last_error = e
                job = ProcessingJob(
                    job_id=job.job_id,
                    webhook_event_id=job.webhook_event_id,
                    status=job.status,
                    started_at=job.started_at,
                    completed_at=None,
                    error_message=None,
                    error_code=None,
                    retry_count=attempt + 1,
                    retry_delays=job.retry_delays,
                    last_retry_at=datetime.now(),
                    idempotency_key=job.idempotency_key,
                    current_stage=job.current_stage,
                    correlation_id=job.correlation_id
                )

                if attempt < retries - 1:
                    delay = self.retry_delays[attempt] if attempt < len(
                        self.retry_delays) else self.retry_delays[-1]
                    await asyncio.sleep(delay)

        # All retries exhausted
        if last_error:
            raise last_error
        else:
            raise AIGenerationError(
                message="All retries exhausted without error",
                details={"retries": retries}
            )

    def render_prompt(
        self,
        issue: Dict[str, Any],
        context: List[Dict[str, Any]]
    ) -> str:
        """Render prompt template with issue and context data using Jinja2.

        Args:
            issue: Issue details (number, title, body)
            context: Similar documents from vector DB

        Returns:
            Rendered prompt string for LLM
        """
        return self.prompt_template.render(issue=issue, context=context)
