# Validator Module

## Purpose

The Validator Module ensures that generated test code is syntactically correct, semantically valid, and follows best practices. It performs static analysis and validation before tests are written to files.

## Features

- Syntax validation for generated code
- Test completeness verification
- Code quality checks (linting)
- Framework-specific validation
- Test coverage verification
- Best practice compliance checking

## API

### Main Interface

```typescript
interface Validator {
  /**
   * Validate generated test code
   * @param test - Generated test to validate
   * @returns Validation result with errors/warnings
   */
  validateTest(test: GeneratedTest): ValidationResult;

  /**
   * Validate entire test file
   * @param testFile - Complete test file to validate
   * @returns Comprehensive validation report
   */
  validateTestFile(testFile: TestFile): FileValidationResult;

  /**
   * Check test completeness
   * @param tests - Generated tests
   * @param scenarios - Original test scenarios
   * @returns Completeness check result
   */
  checkCompleteness(tests: GeneratedTest[], scenarios: TestScenario[]): CompletenessReport;

  /**
   * Validate against best practices
   * @param test - Test to check
   * @returns Best practice compliance report
   */
  validateBestPractices(test: GeneratedTest): BestPracticeReport;
}
```

### Data Models

```typescript
interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  suggestions: string[];
}

interface ValidationError {
  line: number;
  column: number;
  message: string;
  severity: 'error' | 'warning';
  code: string;
}

interface CompletenessReport {
  complete: boolean;
  missingScenarios: TestScenario[];
  unimplementedTests: string[];
  coverageGaps: string[];
}

interface BestPracticeReport {
  score: number;
  violations: BestPracticeViolation[];
  recommendations: string[];
}
```

## Usage Examples

### Example 1: Validate Generated Test

```typescript
import { Validator } from './validator';

const validator = new Validator({ framework: 'jest' });
const result = validator.validateTest(generatedTest);

if (!result.valid) {
  console.error('Validation failed:');
  result.errors.forEach(err => {
    console.error(`  Line ${err.line}: ${err.message}`);
  });
}
```

### Example 2: Validate Complete Test File

```typescript
import { Validator } from './validator';

const validator = new Validator();
const fileResult = validator.validateTestFile(testFile);

console.log(`Validation: ${fileResult.valid ? 'PASS' : 'FAIL'}`);
console.log(`Errors: ${fileResult.errors.length}`);
console.log(`Warnings: ${fileResult.warnings.length}`);
```

### Example 3: Check Test Completeness

```typescript
import { Validator } from './validator';

const validator = new Validator();
const completeness = validator.checkCompleteness(generatedTests, originalScenarios);

if (!completeness.complete) {
  console.log('Missing test scenarios:');
  completeness.missingScenarios.forEach(scenario => {
    console.log(`  - ${scenario.description}`);
  });
}
```

### Example 4: Validate Best Practices

```typescript
import { Validator } from './validator';

const validator = new Validator();
const practices = validator.validateBestPractices(test);

console.log(`Best Practices Score: ${practices.score}/100`);
if (practices.violations.length > 0) {
  console.log('Violations:');
  practices.violations.forEach(v => {
    console.log(`  - ${v.rule}: ${v.message}`);
  });
}
```

## Validation Rules

### Syntax Validation

- Valid language syntax
- Correct framework API usage
- Proper imports and dependencies
- Valid assertion syntax

### Semantic Validation

- Tests are executable
- Mocks match dependencies
- Test data types match function signatures
- Assertions match expected output types

### Best Practices

- **Naming**: Descriptive test names
- **Structure**: AAA pattern (Arrange, Act, Assert)
- **Isolation**: No test interdependencies
- **Focus**: One assertion per test (when appropriate)
- **Setup/Teardown**: Proper resource management

### Quality Metrics

- Test complexity
- Code duplication
- Test maintainability
- Documentation completeness

## Validation Levels

### Level 1: Critical (Must Fix)

- Syntax errors
- Missing imports
- Invalid framework usage
- Type mismatches

### Level 2: Warning (Should Fix)

- Best practice violations
- Code smells
- Redundant code
- Missing documentation

### Level 3: Suggestion (Nice to Have)

- Optimization opportunities
- Alternative approaches
- Enhanced clarity

## Testing

### Unit Tests

```bash
npm test src/validator/tests/unit
```

Test coverage:

- Validation rule accuracy
- Error detection correctness
- Warning appropriateness
- Suggestion relevance

### Integration Tests

```bash
npm test src/validator/tests/integration
```

## Configuration

```typescript
interface ValidatorOptions {
  framework: string;              // Target framework for specific rules
  strictMode?: boolean;           // Fail on warnings
  customRules?: ValidationRule[]; // User-defined rules
  ignoreWarnings?: string[];      // Warning codes to suppress
  bestPracticesLevel?: 'strict' | 'moderate' | 'relaxed';
}
```

## Custom Validation Rules

Extend the validator with custom rules:

```typescript
import { Validator, ValidationRule } from './validator';

const customRule: ValidationRule = {
  name: 'no-hardcoded-values',
  check: (test) => {
    // Rule implementation
    return {
      valid: !containsHardcodedValues(test),
      message: 'Avoid hardcoded values in tests'
    };
  }
};

const validator = new Validator({
  customRules: [customRule]
});
```

## Dependencies

- **Language Parsers**: For syntax validation
- **Linters**: ESLint, Pylint, etc.
- **Framework Validators**: Framework-specific checkers

## Error Recovery

The validator provides fix suggestions:

```typescript
interface ValidationError {
  message: string;
  fixSuggestion?: {
    description: string;
    fixedCode: string;
    autoFixable: boolean;
  };
}
```

## Contributing

When adding validation rules:

1. Add rule in `./rules/`
2. Implement the `ValidationRule` interface
3. Add comprehensive tests
4. Document the rule
5. Update this README

## Future Enhancements

- [ ] Auto-fix capability for common issues
- [ ] IDE integration for real-time validation
- [ ] Machine learning for better suggestions
- [ ] Test smell detection
- [ ] Performance regression detection

---

**Module Status**: Planning Phase
**Last Updated**: 2025-10-25
