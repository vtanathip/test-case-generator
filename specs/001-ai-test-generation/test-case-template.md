# Test Cases: {Feature Name}

**Source Issue**: #{issue_number} - {issue_title}  
**Generated**: {timestamp}  
**AI Model**: Llama 3.2  
**Context Sources**: {number} similar test cases retrieved

---

## Overview

{Brief summary of what is being tested based on issue description}

---

## Test Scenarios

### Scenario 1: {Primary Happy Path Scenario Name}

**Priority**: High  
**Type**: Functional

**Given**:
- {Precondition 1}
- {Precondition 2}

**When**:
- {User action or system trigger}

**Then**:
- {Expected outcome 1}
- {Expected outcome 2}

**Test Data**:
```
{Example input data if applicable}
```

---

### Scenario 2: {Alternate Flow Scenario Name}

**Priority**: Medium  
**Type**: Functional

**Given**:
- {Precondition}

**When**:
- {Alternative action}

**Then**:
- {Expected outcome}

---

### Scenario 3: {Another Primary Scenario}

**Priority**: High  
**Type**: Functional

**Given**:
- {Precondition}

**When**:
- {Action}

**Then**:
- {Expected outcome}

---

### Scenario 4: {Additional Scenario}

**Priority**: Medium  
**Type**: {Functional/Integration/Performance}

**Given**:
- {Precondition}

**When**:
- {Action}

**Then**:
- {Expected outcome}

---

### Scenario 5: {Fifth Scenario}

**Priority**: Low  
**Type**: {Type}

**Given**:
- {Precondition}

**When**:
- {Action}

**Then**:
- {Expected outcome}

---

## Edge Cases

### Edge Case 1: {Boundary Condition}

**Scenario**: {Description of edge case}

**Expected Behavior**:
- {How system should handle this case}
- {Specific outcomes or error handling}

---

### Edge Case 2: {Error Condition}

**Scenario**: {Description of error scenario}

**Expected Behavior**:
- {Error handling approach}
- {User feedback or system response}

---

### Edge Case 3: {Invalid Input}

**Scenario**: {Description of invalid input case}

**Expected Behavior**:
- {Validation behavior}
- {Error message or rejection}

---

## Non-Functional Requirements

### Performance
- {Performance expectation, e.g., "Response time < 2 seconds"}
- {Scalability requirement if applicable}

### Security
- {Security consideration if applicable}
- {Authentication/authorization requirements}

### Accessibility
- {Accessibility requirements if applicable}

---

## Test Data Requirements

```yaml
# Example test data structure
test_data:
  valid_input:
    field1: "value1"
    field2: "value2"
  
  invalid_input:
    field1: null
    field2: "invalid"
  
  edge_cases:
    - scenario: "boundary"
      value: 5000
```

---

## Dependencies

- {External service or API dependency}
- {Database or state requirements}
- {Environment configuration needed}

---

## Notes

- {Any additional context from similar issues}
- {Known limitations or assumptions}
- {Related test cases or issues}

---

**Template Version**: 1.0  
**Minimum Scenarios Required**: 5  
**Minimum Edge Cases Required**: 3
