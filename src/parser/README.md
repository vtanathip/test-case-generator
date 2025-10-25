# Parser Module

## Purpose

The Parser Module is responsible for extracting and parsing source code, specifications, and design documents into structured data models that can be consumed by other components of the test case generator.

## Features

- Source code parsing for multiple programming languages
- Specification document parsing (Markdown, YAML, JSON)
- Design artifact extraction (contracts, data models, API definitions)
- Abstract Syntax Tree (AST) generation
- Metadata extraction (functions, classes, parameters, return types)

## API

### Main Interface

```typescript
interface Parser {
  /**
   * Parse source code and return structured representation
   * @param input - Source code or file path to parse
   * @param options - Parser configuration options
   * @returns Parsed code structure with metadata
   */
  parseCode(input: string | FilePath, options?: ParserOptions): ParsedCode;

  /**
   * Parse specification documents into structured format
   * @param specPath - Path to specification document
   * @returns Structured specification data
   */
  parseSpecification(specPath: FilePath): Specification;

  /**
   * Extract function signatures and metadata
   * @param code - Parsed code structure
   * @returns Array of function metadata
   */
  extractFunctions(code: ParsedCode): FunctionMetadata[];
}
```

### Data Models

```typescript
interface ParsedCode {
  language: string;
  ast: ASTNode;
  functions: FunctionMetadata[];
  classes: ClassMetadata[];
  imports: ImportStatement[];
  exports: ExportStatement[];
}

interface FunctionMetadata {
  name: string;
  parameters: Parameter[];
  returnType: Type;
  isAsync: boolean;
  isPublic: boolean;
  documentation?: string;
}
```

## Usage Examples

### Example 1: Parse JavaScript Source Code

```typescript
import { Parser } from './parser';

const parser = new Parser({ language: 'javascript' });
const code = `
  function calculateSum(a, b) {
    return a + b;
  }
`;

const parsed = parser.parseCode(code);
console.log(parsed.functions);
// Output: [{ name: 'calculateSum', parameters: [...], returnType: 'number' }]
```

### Example 2: Parse Specification Document

```typescript
import { Parser } from './parser';

const parser = new Parser();
const spec = parser.parseSpecification('./specs/feature-001/spec.md');

console.log(spec.userStories);
// Output: [{ id: 'US1', title: '...', priority: 'P1', ... }]
```

### Example 3: Extract Function Metadata

```typescript
import { Parser } from './parser';

const parser = new Parser({ language: 'typescript' });
const parsed = parser.parseCode(sourceFile);
const functions = parser.extractFunctions(parsed);

functions.forEach(fn => {
  console.log(`Function: ${fn.name}`);
  console.log(`  Parameters: ${fn.parameters.map(p => p.name).join(', ')}`);
  console.log(`  Returns: ${fn.returnType}`);
});
```

## Dependencies

- **Language Parsers**: Language-specific parsing libraries (e.g., Babel, TypeScript Compiler API)
- **Markdown Parser**: For specification document parsing
- **YAML/JSON Parser**: For structured configuration files

## Testing

### Unit Tests

Run unit tests to verify parser functionality:

```bash
npm test src/parser/tests/unit
```

Key test scenarios:
- Parse valid source code in supported languages
- Handle syntax errors gracefully
- Extract correct function signatures
- Parse complex nested structures
- Handle edge cases (empty files, malformed input)

### Integration Tests

Run integration tests to verify parser with real files:

```bash
npm test src/parser/tests/integration
```

## Configuration

The parser can be configured with:

```typescript
interface ParserOptions {
  language?: string;           // Target language (auto-detect if not specified)
  strictMode?: boolean;        // Fail on warnings
  extractComments?: boolean;   // Include code comments in output
  includeTypes?: boolean;      // Extract type information (TypeScript, etc.)
}
```

## Error Handling

The parser throws specific error types:

- `SyntaxError`: Invalid code syntax
- `UnsupportedLanguageError`: Language not supported
- `FileNotFoundError`: Input file doesn't exist
- `ParseError`: General parsing failure

## Contributing

When adding new parsing capabilities:

1. Add parser for new language in `./languages/`
2. Implement the `LanguageParser` interface
3. Add comprehensive unit tests
4. Update this README with examples
5. Update main Parser to register new language

## Future Enhancements

- [ ] Support for additional programming languages (Python, Java, Go)
- [ ] Incremental parsing for large files
- [ ] Caching mechanism for repeated parses
- [ ] Better error recovery and suggestions
- [ ] Support for parsing test files to avoid duplication

---

**Module Status**: Planning Phase
**Last Updated**: 2025-10-25
