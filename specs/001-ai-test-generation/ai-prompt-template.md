# AI Prompt Template: Test Case Generation

**Purpose**: LangGraph prompt engineering template for generating test cases from GitHub issues  
**Model**: Llama 3.2  
**Max Context Window**: 8192 tokens  
**Temperature**: 0.3 (low for consistent, factual output)

---

## Prompt Structure

### System Prompt (Always Included)

```text
You are an expert QA engineer and test case designer. Your task is to generate comprehensive, 
well-structured test cases in Markdown format based on GitHub issue descriptions.

CRITICAL REQUIREMENTS:
- Generate EXACTLY 5 test scenarios (mix of happy path, alternate flows, error cases)
- Generate EXACTLY 3 edge cases minimum
- Use Given-When-Then format for all scenarios
- Prioritize scenarios (High/Medium/Low)
- Include test data examples where applicable
- Consider security, performance, and accessibility concerns
- Base recommendations on similar historical test cases when provided

OUTPUT FORMAT: Strictly follow the Markdown template structure provided.
```

---

## User Prompt Template (Dynamic Content)

```text
# TASK: Generate Test Cases

## ISSUE INFORMATION

**Issue Number**: {issue_number}
**Issue Title**: {issue_title}
**Issue Body**:
{issue_body}

**Labels**: {labels_list}
**Created By**: {author}

---

## SIMILAR TEST CASES (Historical Context)

{context_from_vector_db}

The following are {num_similar} similar test cases from previous issues that you should 
use as reference for patterns, structure, and quality expectations:

### Similar Test Case 1 (Similarity: {similarity_score_1})
```markdown
{historical_test_case_1}
```

### Similar Test Case 2 (Similarity: {similarity_score_2})
```markdown
{historical_test_case_2}
```

### Similar Test Case 3 (Similarity: {similarity_score_3})
```markdown
{historical_test_case_3}
```

---

## GENERATION INSTRUCTIONS

1. Analyze the issue description carefully to understand:
   - Core functionality being described
   - User intent and expected behavior
   - Technical constraints or requirements mentioned
   - Implicit edge cases or error scenarios

2. Review the similar test cases for:
   - Common patterns in this domain
   - Typical edge cases that should be covered
   - Test data structures and examples
   - Quality standards and level of detail

3. Generate comprehensive test cases following the template structure:
   - Start with primary happy path scenarios (High priority)
   - Include alternate flows and error handling (Medium priority)
   - Cover boundary conditions and edge cases
   - Add performance, security, or accessibility requirements if relevant

4. Ensure test cases are:
   - Specific and unambiguous
   - Independently executable
   - Traceable to the issue requirements
   - Realistic and implementable

5. Quality checks before output:
   - ✓ Minimum 5 test scenarios present
   - ✓ Minimum 3 edge cases defined
   - ✓ All scenarios use Given-When-Then format
   - ✓ Priorities assigned (High/Medium/Low)
   - ✓ Test data examples provided where needed
   - ✓ Markdown formatting is valid

---

## OUTPUT

Generate the test cases now using the template structure. Start with the title:

# Test Cases: {issue_title}
```

---

## Fallback Prompts (Error Handling)

### Insufficient Information Prompt

```text
ANALYSIS: The provided issue description lacks sufficient detail to generate comprehensive test cases.

MISSING INFORMATION:
{list_of_missing_elements}

RECOMMENDATION: Post the following comment template to the issue requesting clarification:

---

Hi @{issue_author}! 👋

I attempted to generate test cases for this issue, but I need more information to create 
comprehensive test scenarios. Could you please provide:

{bulleted_list_of_needed_info}

Once you add these details, I'll generate the test cases automatically.

**Tip**: The more specific you are about expected behavior, edge cases, and acceptance 
criteria, the better the test cases will be!

---

ACTION: Mark this job as SKIPPED with reason "insufficient_information"
```

### Quality Validation Prompt (Post-Generation)

```text
You generated test cases. Now validate they meet quality standards:

CHECKLIST:
- [ ] Contains exactly 5 or more test scenarios
- [ ] Contains exactly 3 or more edge cases
- [ ] All scenarios follow Given-When-Then format
- [ ] Priorities are assigned (High/Medium/Low)
- [ ] Test data examples provided where applicable
- [ ] No placeholder text like {example} or TODO remains
- [ ] Markdown syntax is valid (proper headers, code blocks)
- [ ] Scenarios are traceable to issue requirements

If ANY item is unchecked, regenerate the test cases with corrections.
If ALL items are checked, proceed with PR creation.
```

---

## Token Management Strategy

**Context Window**: 8192 tokens (Llama 3.2)

**Allocation**:
- System prompt: ~300 tokens
- Issue information: ~500 tokens (truncated if > 5000 chars)
- Similar test cases (3 × ~800 tokens): ~2400 tokens
- Instructions: ~400 tokens
- **Reserved for output**: ~4592 tokens

**Truncation Rules**:
1. If issue body > 5000 characters, truncate and add warning
2. If similar test cases > 2400 tokens total, reduce to 2 cases
3. Prioritize most recent/relevant similar cases by similarity score

---

## LangGraph Integration

```python
# Node: prepare_prompt
def prepare_prompt(state: AgentState) -> dict:
    """Prepare the prompt with issue data and context."""
    
    system_prompt = load_template("ai-prompt-template.md", section="system")
    
    user_prompt = render_template(
        template="ai-prompt-template.md",
        section="user",
        variables={
            "issue_number": state.issue_number,
            "issue_title": state.issue_title,
            "issue_body": truncate(state.issue_body, max_chars=5000),
            "labels_list": ", ".join(state.labels),
            "author": state.author,
            "num_similar": len(state.similar_cases),
            "context_from_vector_db": format_context(state.similar_cases),
            "similarity_score_1": state.similar_cases[0].score,
            "historical_test_case_1": state.similar_cases[0].content,
            # ... repeat for other similar cases
        }
    )
    
    return {
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
    }

# Node: generate_test_cases
def generate_test_cases(state: AgentState) -> dict:
    """Call Llama 3.2 to generate test cases."""
    
    response = llm.invoke(
        state.messages,
        temperature=0.3,
        max_tokens=4592,
        stop=["---END---"]
    )
    
    generated_content = response.content
    
    # Validate quality
    if not validate_output(generated_content):
        # Retry with quality validation prompt
        pass
    
    return {"generated_test_cases": generated_content}
```

---

## Example Filled Prompt

```text
# TASK: Generate Test Cases

## ISSUE INFORMATION

**Issue Number**: 123
**Issue Title**: Add user authentication to API endpoints
**Issue Body**:
We need to add JWT-based authentication to all API endpoints except /health and /status.
Users should get a 401 if token is missing or invalid. Tokens expire after 24 hours.

**Labels**: feature, security, api
**Created By**: developer123

---

## SIMILAR TEST CASES (Historical Context)

The following are 3 similar test cases from previous issues...

[Historical context would be inserted here]

---

## OUTPUT

Generate the test cases now using the template structure...
```

---

**Template Version**: 1.0  
**Last Updated**: 2025-10-26  
**Compatibility**: Llama 3.2, LangGraph 0.2.x
