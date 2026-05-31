# SoroScan SDK Code Generation

This directory contains tools for auto-generating type-safe SDK types from the GraphQL schema.

## Overview

The code generation pipeline ensures SDK types always match the backend GraphQL schema without manual synchronization:

- **TypeScript SDK**: Auto-generates TypeScript types from GraphQL schema
- **Python SDK**: Auto-generates Pydantic models from GraphQL schema
- **Documentation**: Includes docstrings from schema descriptions
- **Version Control**: Generated files are committed to the repository
- **CI Integration**: Codegen runs automatically on schema changes

## Usage

### Generate All SDK Types

```bash
# From the sdk/codegen directory
npm install
npm run generate
```

### Generate TypeScript Only

```bash
npm run generate:typescript
```

### Generate Python Only

```bash
npm run generate:python
```

### Watch Mode (Development)

```bash
npm run generate:watch
```

## How It Works

1. **Schema Introspection**: Fetches the GraphQL schema from the Django backend
2. **Type Generation**: Uses GraphQL Code Generator to create TypeScript types
3. **Python Conversion**: Converts GraphQL types to Pydantic models with proper Python typing
4. **Documentation**: Preserves schema descriptions as docstrings
5. **Validation**: Runs SDK tests to verify generated types

## Configuration

- `codegen.yml` - GraphQL Code Generator configuration
- `scripts/generate-python-types.ts` - Python type generation script
- `templates/` - Custom templates for type generation

## CI Integration

The `.github/workflows/sdk-codegen.yml` workflow:
- Triggers on changes to `django-backend/soroscan/ingest/schema.py`
- Runs code generation
- Commits updated types if changes detected
- Fails if generated types don't match committed versions

## Generated Files

### TypeScript SDK
- `sdk/typescript/src/generated/types.ts` - All GraphQL types
- `sdk/typescript/src/generated/operations.ts` - Query/Mutation types

### Python SDK
- `sdk/python/soroscan/generated/types.py` - Pydantic models
- `sdk/python/soroscan/generated/__init__.py` - Public exports

## Development

When modifying the GraphQL schema:

1. Update `django-backend/soroscan/ingest/schema.py`
2. Run `npm run generate` from `sdk/codegen/`
3. Review generated types
4. Run SDK tests: `cd sdk/typescript && npm test` and `cd sdk/python && pytest`
5. Commit both schema and generated types

## Troubleshooting

### Schema Introspection Fails

Ensure the Django backend is running:
```bash
cd django-backend
python manage.py runserver
```

### Type Mismatches

If SDK tests fail after generation:
1. Check for breaking schema changes
2. Update SDK client code to match new types
3. Update SDK version following semver

### Python Type Errors

The Python generator handles:
- GraphQL scalars → Python types (String → str, Int → int, etc.)
- Custom scalars (JSON, DateTime) → appropriate Python types
- Nullable fields → Optional[T]
- Lists → list[T]
- Enums → Python Enum classes
