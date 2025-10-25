# Generator Module

## Purpose

The Generator Module takes analyzed test scenarios and generates actual test code in the target testing framework's syntax. It produces runnable, well-structured, and maintainable test files.

## Features

- Multi-framework test generation (Jest, Mocha, PyTest, JUnit, etc.)
- Test file structuring and organization
- Mock/stub generation for dependencies
- Assertion generation based on expected outcomes
- Test data fixture creation
- Documentation comment generation

## API

### Main Interface

```typescript
interface Generator {
  /**
   * Generate test code from scenarios
   * @param scenarios - Test scenarios from Analyzer
   * @param options - Generator configuration
   * @returns Generated test code
   */
  generateTests(scenarios: TestScenario[], options: GeneratorOptions): GeneratedTest[];

  /**
   * Generate test file with proper structure
   * @param tests - Individual test cases
   * @param filePath - Target file path for test
   * @returns Complete test file content
   */
  generateTestFile(tests: GeneratedTest[], filePath: string): TestFile;

  /**
   * Generate mock objects for dependencies
   * @param dependencies - Dependencies to mock
   * @returns Mock implementation code
   */
  generateMocks(dependencies: Dependency[]): MockCode;

  /**
   * Generate test fixtures and data
   * @param scenario - Test scenario requiring fixtures
   * @returns Fixture data and setup code
   */
  generateFixtures(scenario: TestScenario): Fixture[];
}
```

### Data Models

```typescript
interface GeneratedTest {
  id: string;
  name: string;
  description: string;
  code: string;
  framework: string;
  imports: string[];
  fixtures: Fixture[];
}

interface TestFile {
  path: string;
  content: string;
  language: string;
  framework: string;
  metadata: {
    generatedAt: Date;
    targetModule: string;
    testCount: number;
  };
}

interface MockCode {
  target: string;
  implementation: string;
  dependencies: string[];
}
```

## Usage Examples

### Example 1: Generate Jest Tests

```typescript
import { Generator } from './generator';

const generator = new Generator({
  framework: 'jest',
  language: 'typescript'
});

const scenarios = [
  {
    id: 'T001',
    type: 'unit',
    targetFunction: 'calculateSum',
    description: 'Should add two positive numbers',
    inputs: [{ name: 'a', value: 5 }, { name: 'b', value: 3 }],
    expectedOutput: 8
  }
];

const tests = generator.generateTests(scenarios);
console.log(tests[0].code);
// Output:
// describe('calculateSum', () => {
//   it('should add two positive numbers', () => {
//     expect(calculateSum(5, 3)).toBe(8);
//   });
// });
```

### Example 2: Generate Complete Test File

```typescript
import { Generator } from './generator';

const generator = new Generator({ framework: 'jest' });
const tests = generator.generateTests(scenarios);
const testFile = generator.generateTestFile(tests, './tests/unit/math.test.ts');

// Write to file system
fs.writeFileSync(testFile.path, testFile.content);
```

### Example 3: Generate Mocks

```typescript
import { Generator } from './generator';

const generator = new Generator({ framework: 'jest' });
const mocks = generator.generateMocks([
  { name: 'DatabaseService', type: 'class' },
  { name: 'LoggerService', type: 'class' }
]);

console.log(mocks[0].implementation);
// Output:
// const mockDatabaseService = {
//   query: jest.fn(),
//   connect: jest.fn()
// };
```

## Supported Frameworks

### JavaScript/TypeScript

- **Jest**: Full support with mocking
- **Mocha + Chai**: Assertion library integration
- **Vitest**: Modern test runner

### Python

- **PyTest**: Fixture generation
- **unittest**: Built-in framework
- **nose2**: Extended features

### Java

- **JUnit 5**: Modern annotations
- **TestNG**: Data-driven tests

### Other

- **Go**: testing package
- **Rust**: cargo test
- **C#**: xUnit, NUnit

## Testing

### Unit Tests

```bash
npm test src/generator/tests/unit
```

Test coverage:

- Correct test syntax generation
- Proper assertion formatting
- Mock generation accuracy
- Fixture creation

### Integration Tests

```bash
npm test src/generator/tests/integration
```

Verify:

- Generated tests are syntactically valid
- Generated tests can be executed
- Generated tests pass/fail correctly

## Configuration

```typescript
interface GeneratorOptions {
  framework: string;              // Target testing framework
  language: string;               // Target language
  includeComments?: boolean;      // Add documentation comments
  mockStyle?: 'manual' | 'auto'; // Mock generation strategy
  assertionStyle?: 'expect' | 'assert' | 'should';
  fileNaming?: 'snake' | 'kebab' | 'camel';
}
```

## Code Templates

The generator uses templates for consistency:

```typescript
// Template example
const testTemplate = `
describe('{{moduleName}}', () => {
  {{#each tests}}
  it('{{description}}', () => {
    {{#if setup}}
    {{setup}}
    {{/if}}
    
    const result = {{targetFunction}}({{inputs}});
    
    {{assertion}}
  });
  {{/each}}
});
`;
```

## Best Practices

Generated tests follow these principles:

1. **AAA Pattern**: Arrange, Act, Assert
2. **Descriptive Names**: Clear test descriptions
3. **Single Assertion**: One concept per test
4. **DRY**: Shared setup in beforeEach
5. **Isolation**: Independent, order-agnostic tests

## Dependencies

- **Template Engine**: For code generation
- **Code Formatter**: Prettier, Black, etc.
- **AST Builder**: For complex code generation

## Contributing

When adding framework support:

1. Create framework adapter in `./frameworks/`
2. Implement the `FrameworkAdapter` interface
3. Add syntax templates
4. Add comprehensive tests
5. Update this README

## Future Enhancements

- [ ] AI-assisted assertion inference
- [ ] Property-based test generation
- [ ] Visual test generation for UI components
- [ ] Performance test generation
- [ ] Contract test generation for APIs

---

**Module Status**: Planning Phase
**Last Updated**: 2025-10-25
