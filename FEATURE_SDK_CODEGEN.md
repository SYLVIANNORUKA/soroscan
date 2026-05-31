# Feature: Auto-Generate SDK Types from GraphQL Schema

**Status**: ✅ Complete  
**Issue**: feat: auto-generate TypeScript and Python type definitions from GraphQL schema  
**Labels**: enhancement, sdk, tooling  
**Complexity**: medium

## Summary

Implemented automatic code generation for SoroScan SDKs that produces type-safe TypeScript and Python types directly from the GraphQL schema. This eliminates manual type synchronization and ensures SDKs always match the backend API.

## Implementation

### What Was Built

1. **Code Generation Tools** (`sdk/codegen/`)
   - GraphQL Code Generator setup for TypeScript
   - Custom Python Pydantic model generator
   - Schema introspection and caching
   - Watch mode for development
   - Makefile for convenient commands

2. **Generated Type Directories**
   - `sdk/typescript/src/generated/` - TypeScript types, operations, resolvers
   - `sdk/python/soroscan/generated/` - Pydantic models with full validation

3. **CI/CD Integration**
   - Automatic generation on schema changes
   - Validation that types match schema
   - Auto-commit on main/develop branches
   - PR checks to ensure types are in sync

4. **Testing**
   - TypeScript SDK tests for generated types
   - Python SDK tests for Pydantic models
   - Backward compatibility checks
   - CI validation

5. **Documentation**
   - Comprehensive developer guide (`sdk/CODEGEN_GUIDE.md`)
   - Public documentation (`docs/sdk-codegen.md`)
   - Quick start guide (`sdk/codegen/QUICK_START.md`)
   - Implementation summary (`sdk/codegen/IMPLEMENTATION_SUMMARY.md`)

### Key Features

✅ **TypeScript types auto-generated from GraphQL schema**
- Uses GraphQL Code Generator
- Generates types, operations, and resolvers
- Proper handling of nullable, list, and nested types
- JSDoc comments from schema descriptions

✅ **Python types generated using Pydantic**
- Custom script converts GraphQL to Pydantic models
- Full type hints (Optional, list, dict, etc.)
- Enum classes for GraphQL enums
- Docstrings from schema descriptions
- JSON serialization support

✅ **Types include docstrings from schema descriptions**
- TypeScript: JSDoc comments
- Python: Class and field docstrings
- Preserves all schema documentation

✅ **Generated files are version-controlled (committed)**
- Files committed to repository
- Reviewed in PRs
- Tracked in version control

✅ **Codegen runs in CI on schema changes**
- GitHub Actions workflow
- Triggers on `schema.py` changes
- Runs tests after generation
- Auto-commits on main/develop

✅ **SDK tests verify generated types**
- TypeScript: `test/generated-types.test.ts`
- Python: `tests/test_generated_types.py`
- Both run in CI pipeline

## Usage

### Generate Types Locally

```bash
cd sdk/codegen
npm install
npm run generate
```

### Development Workflow

1. Edit GraphQL schema in `django-backend/soroscan/ingest/schema.py`
2. Run `cd sdk/codegen && npm run generate`
3. Review generated types
4. Update SDK clients if needed
5. Run SDK tests
6. Commit schema + generated types together

### Using Generated Types

#### TypeScript

```typescript
import type { ContractType, EventType, EventConnection } from './generated/types';

class SoroScanClient {
  async getContract(contractId: string): Promise<ContractType> {
    // Fully type-safe
  }
}
```

#### Python

```python
from soroscan.generated.types import ContractType, EventType, EventConnection

class SoroScanClient:
    def get_contract(self, contract_id: str) -> ContractType:
        """Type-safe with Pydantic validation."""
        response = self._query(...)
        return ContractType(**response)
```

## File Structure

```
sdk/
├── codegen/                          # Code generation tools
│   ├── scripts/
│   │   ├── generate-python-types.ts  # Python type generator
│   │   ├── introspect-schema.ts      # Schema introspection
│   │   └── check-backend.sh          # Backend health check
│   ├── package.json                  # Dependencies and scripts
│   ├── codegen.yml                   # GraphQL codegen config
│   ├── Makefile                      # Convenient commands
│   ├── README.md                     # Usage documentation
│   ├── QUICK_START.md                # Quick start guide
│   ├── CHANGELOG.md                  # Version history
│   └── IMPLEMENTATION_SUMMARY.md     # Technical details
│
├── typescript/src/generated/         # Auto-generated TypeScript
│   ├── types.ts                      # GraphQL types
│   ├── operations.ts                 # Query/Mutation types
│   └── resolvers.ts                  # Resolver types
│
├── python/soroscan/generated/        # Auto-generated Python
│   ├── types.py                      # Pydantic models
│   └── __init__.py                   # Public exports
│
├── CODEGEN_GUIDE.md                  # Comprehensive guide
└── README.md                         # SDK overview

.github/workflows/
├── sdk-codegen.yml                   # Main codegen workflow
└── sdk-codegen-check.yml             # PR check workflow

docs/
└── sdk-codegen.md                    # Public documentation
```

## Type Mappings

### GraphQL → TypeScript

| GraphQL | TypeScript |
|---------|------------|
| `String` | `string` |
| `Int` | `number` |
| `Boolean` | `boolean` |
| `DateTime` | `string` (ISO-8601) |
| `JSON` | `Record<string, any>` |
| `[Type]` | `Type[]` |
| `Type!` | `Type` (non-null) |
| `Type` | `Type \| null` |

### GraphQL → Python

| GraphQL | Python |
|---------|--------|
| `String` | `str` |
| `Int` | `int` |
| `Boolean` | `bool` |
| `DateTime` | `datetime` |
| `JSON` | `dict[str, Any]` |
| `[Type]` | `list[Type]` |
| `Type!` | `Type` |
| `Type` | `Optional[Type]` |

## CI/CD Workflows

### Main Workflow (`.github/workflows/sdk-codegen.yml`)

**Triggers:**
- Push to main/develop with schema changes
- Pull requests with schema changes
- Manual workflow dispatch

**Steps:**
1. Start Django backend with PostgreSQL and Redis
2. Install codegen dependencies
3. Generate TypeScript and Python types
4. Run SDK tests to verify types
5. Check for changes
6. **On PR**: Fail if types are out of sync
7. **On main/develop**: Auto-commit updated types

### Check Workflow (`.github/workflows/sdk-codegen-check.yml`)

**Triggers:**
- Pull requests affecting schema or generated types

**Steps:**
1. Check if generated directories exist
2. Verify auto-generated warnings present
3. Provide helpful error messages

## Testing

### TypeScript SDK Tests

```bash
cd sdk/typescript
npm test
```

Tests verify:
- Generated types can be imported
- Expected types are exported
- Type safety and compilation
- Backward compatibility

### Python SDK Tests

```bash
cd sdk/python
pytest tests/test_generated_types.py
```

Tests verify:
- Generated module exists
- Pydantic model inheritance
- Enum types work correctly
- Type annotations are correct
- JSON serialization works
- Backward compatibility

## Documentation

### For Developers
- **[CODEGEN_GUIDE.md](sdk/CODEGEN_GUIDE.md)**: Comprehensive guide with architecture, workflows, and troubleshooting
- **[sdk/codegen/README.md](sdk/codegen/README.md)**: Tool-specific documentation
- **[sdk/codegen/QUICK_START.md](sdk/codegen/QUICK_START.md)**: Get started in 3 steps
- **[sdk/codegen/IMPLEMENTATION_SUMMARY.md](sdk/codegen/IMPLEMENTATION_SUMMARY.md)**: Technical implementation details

### For Users
- **[docs/sdk-codegen.md](docs/sdk-codegen.md)**: Public documentation
- **[sdk/README.md](sdk/README.md)**: SDK overview with codegen info

## Benefits

1. **Type Safety**: SDKs are always type-safe and match the backend
2. **No Manual Sync**: Types update automatically when schema changes
3. **Documentation**: Schema descriptions become code comments
4. **CI Integration**: Types validated and regenerated automatically
5. **Developer Experience**: Simple commands, helpful errors, comprehensive docs
6. **Maintainability**: Single source of truth (GraphQL schema)
7. **Quality**: Tests verify generated types work correctly

## Future Enhancements

Potential improvements:
- Custom scalar type mappings
- GraphQL fragment generation
- SDK method generation from operations
- Automatic changelog generation for type changes
- Performance optimizations for large schemas
- Schema validation before generation
- API documentation generation

## Acceptance Criteria

All acceptance criteria met:

✅ TypeScript types auto-generated from GraphQL schema  
✅ Python types generated using Pydantic or dataclasses  
✅ Types include docstrings from schema descriptions  
✅ Generated files are version-controlled (committed)  
✅ Codegen runs in CI on schema changes  
✅ SDK tests verify generated types  

## Commands Reference

```bash
# Generate all types
cd sdk/codegen && npm run generate

# Generate TypeScript only
npm run generate:typescript

# Generate Python only
npm run generate:python

# Watch mode (auto-regenerate)
npm run generate:watch

# Save schema locally
npm run introspect

# Run all SDK tests
npm run test:sdks

# Using Makefile
make install          # Install dependencies
make generate         # Generate all types
make validate         # Generate and test
make watch            # Watch mode
make clean            # Clean generated files
```

## Troubleshooting

### Backend Not Running

```bash
cd django-backend
python manage.py runserver
```

### Types Out of Sync

```bash
cd sdk/codegen
npm run generate
git add ../typescript/src/generated/ ../python/soroscan/generated/
git commit -m "chore: regenerate SDK types"
```

### CI Failures

Check that:
1. Django backend starts successfully
2. GraphQL schema is valid
3. Generated types are committed
4. SDK tests pass locally

## Support

- **Documentation**: See guides in `sdk/` directory
- **Issues**: [GitHub Issues](https://github.com/soroscan/soroscan/issues)
- **Discussions**: [GitHub Discussions](https://github.com/soroscan/soroscan/discussions)
- **Email**: team@soroscan.io

## License

MIT License - Same as SoroScan project

---

**Implementation Date**: May 31, 2026  
**Implemented By**: Kiro AI Assistant  
**Status**: ✅ Complete and Ready for Use
