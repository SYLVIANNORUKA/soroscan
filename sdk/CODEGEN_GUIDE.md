# SDK Code Generation Guide

This guide explains how SoroScan automatically generates type-safe SDK types from the GraphQL schema.

## Overview

SoroScan uses GraphQL Code Generator to automatically create TypeScript and Python type definitions that match the backend GraphQL schema. This ensures:

- **Type Safety**: SDKs are always type-safe and match the backend API
- **No Manual Sync**: Types update automatically when the schema changes
- **Documentation**: Schema descriptions become code comments/docstrings
- **CI Integration**: Types are validated and regenerated in CI/CD

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Django Backend                            │
│  ┌────────────────────────────────────────────────────┐     │
│  │  soroscan/ingest/schema.py (Strawberry GraphQL)    │     │
│  │  - Query, Mutation, Subscription types             │     │
│  │  - ContractType, EventType, etc.                   │     │
│  └────────────────────────────────────────────────────┘     │
│                          │                                   │
│                          │ GraphQL Introspection             │
│                          ▼                                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
         ▼                                   ▼
┌──────────────────────┐          ┌──────────────────────┐
│  TypeScript SDK      │          │  Python SDK          │
│  ┌────────────────┐  │          │  ┌────────────────┐  │
│  │ Generated:     │  │          │  │ Generated:     │  │
│  │ - types.ts     │  │          │  │ - types.py     │  │
│  │ - operations.ts│  │          │  │ - __init__.py  │  │
│  │ - resolvers.ts │  │          │  └────────────────┘  │
│  └────────────────┘  │          │                      │
│  ┌────────────────┐  │          │  ┌────────────────┐  │
│  │ Manual:        │  │          │  │ Manual:        │  │
│  │ - client.ts    │  │          │  │ - client.py    │  │
│  │ - index.ts     │  │          │  │ - builder.py   │  │
│  └────────────────┘  │          │  └────────────────┘  │
└──────────────────────┘          └──────────────────────┘
```

## Generated Files

### TypeScript SDK (`sdk/typescript/src/generated/`)

- **`types.ts`**: All GraphQL types (objects, inputs, enums, scalars)
- **`operations.ts`**: Query and Mutation operation types
- **`resolvers.ts`**: Resolver types (for reference)

### Python SDK (`sdk/python/soroscan/generated/`)

- **`types.py`**: Pydantic models for all GraphQL types
- **`__init__.py`**: Public exports

## Type Mappings

### GraphQL → TypeScript

| GraphQL Type | TypeScript Type |
|--------------|-----------------|
| `String` | `string` |
| `Int` | `number` |
| `Float` | `number` |
| `Boolean` | `boolean` |
| `ID` | `string` |
| `DateTime` | `string` (ISO-8601) |
| `JSON` | `Record<string, any>` |
| `[Type]` | `Type[]` |
| `Type!` | `Type` (non-nullable) |
| `Type` | `Type \| null` |

### GraphQL → Python

| GraphQL Type | Python Type |
|--------------|-------------|
| `String` | `str` |
| `Int` | `int` |
| `Float` | `float` |
| `Boolean` | `bool` |
| `ID` | `str` |
| `DateTime` | `datetime` |
| `JSON` | `dict[str, Any]` |
| `[Type]` | `list[Type]` |
| `Type!` | `Type` |
| `Type` | `Optional[Type]` |

## Usage

### 1. Generate Types Locally

```bash
# From the repository root
cd sdk/codegen

# Install dependencies (first time only)
npm install

# Generate all SDK types
npm run generate

# Or generate individually
npm run generate:typescript
npm run generate:python

# Watch mode for development
npm run generate:watch
```

### 2. Using Generated Types in TypeScript

```typescript
// Import generated types
import type { 
  ContractType, 
  EventType, 
  EventConnection,
  Query,
  Mutation 
} from './generated/types';

// Use in your SDK client
class SoroScanClient {
  async getContract(contractId: string): Promise<ContractType> {
    // Type-safe implementation
  }
  
  async getEvents(params: EventQueryParams): Promise<EventConnection> {
    // Type-safe implementation
  }
}
```

### 3. Using Generated Types in Python

```python
# Import generated types
from soroscan.generated.types import (
    ContractType,
    EventType,
    EventConnection,
    TimelineBucketSize,
)

# Use in your SDK client
class SoroScanClient:
    def get_contract(self, contract_id: str) -> ContractType:
        """Type-safe method with Pydantic validation."""
        response = self._query(...)
        return ContractType(**response)
    
    def get_events(self, **params) -> EventConnection:
        """Type-safe method with Pydantic validation."""
        response = self._query(...)
        return EventConnection(**response)
```

## Development Workflow

### When Modifying the GraphQL Schema

1. **Edit the schema** in `django-backend/soroscan/ingest/schema.py`

2. **Start Django backend** (if not running):
   ```bash
   cd django-backend
   python manage.py runserver
   ```

3. **Generate types**:
   ```bash
   cd sdk/codegen
   npm run generate
   ```

4. **Review changes**:
   ```bash
   git diff sdk/typescript/src/generated/
   git diff sdk/python/soroscan/generated/
   ```

5. **Update SDK clients** if needed to use new types

6. **Run tests**:
   ```bash
   # TypeScript SDK
   cd sdk/typescript
   npm test
   
   # Python SDK
   cd sdk/python
   pytest
   ```

7. **Commit everything together**:
   ```bash
   git add django-backend/soroscan/ingest/schema.py
   git add sdk/typescript/src/generated/
   git add sdk/python/soroscan/generated/
   git commit -m "feat: add new GraphQL types for X"
   ```

## CI/CD Integration

The `.github/workflows/sdk-codegen.yml` workflow:

### On Pull Requests
- ✅ Generates types from schema
- ✅ Runs SDK tests
- ❌ **Fails if generated types don't match committed files**
- 💡 Ensures developers run codegen before committing

### On Push to main/develop
- ✅ Generates types from schema
- ✅ Runs SDK tests
- ✅ **Auto-commits updated types if changed**
- 💡 Keeps types in sync automatically

### Workflow Triggers
- Changes to `django-backend/soroscan/ingest/schema.py`
- Changes to `sdk/codegen/**`
- Manual workflow dispatch

## Troubleshooting

### "Cannot connect to GraphQL endpoint"

**Problem**: Codegen can't reach the Django backend.

**Solution**:
```bash
# Start Django backend
cd django-backend
python manage.py runserver

# Verify it's running
curl http://localhost:8000/graphql/
```

### "Generated types don't match schema"

**Problem**: CI fails because types are out of sync.

**Solution**:
```bash
cd sdk/codegen
npm run generate
git add sdk/*/src/generated/ sdk/*/soroscan/generated/
git commit --amend --no-edit
git push --force-with-lease
```

### "Python type errors after generation"

**Problem**: Pydantic validation fails with generated types.

**Solution**:
1. Check if schema has breaking changes
2. Update SDK client code to match new types
3. Consider SDK version bump (semver)

### "TypeScript compilation errors"

**Problem**: Generated TypeScript types cause compilation errors.

**Solution**:
1. Check `codegen.yml` scalar mappings
2. Verify GraphQL schema is valid
3. Update TypeScript SDK to handle new types

## Advanced Configuration

### Custom Scalar Mappings

Edit `sdk/codegen/codegen.yml`:

```yaml
config:
  scalars:
    DateTime: string
    JSON: Record<string, any>
    BigInt: string  # Add custom scalar
    Decimal: string
```

### Custom Templates

Create custom templates in `sdk/codegen/templates/`:

```typescript
// templates/custom-type.ts
export type {{typeName}} = {
  {{#each fields}}
  {{name}}: {{type}};
  {{/each}}
};
```

### Environment Variables

- `GRAPHQL_ENDPOINT`: Override default endpoint (default: `http://localhost:8000/graphql/`)
- `SKIP_PYTHON_GEN`: Skip Python generation (TypeScript only)
- `SKIP_TS_GEN`: Skip TypeScript generation (Python only)

## Best Practices

### 1. Always Generate Before Committing
```bash
# Add to pre-commit hook
cd sdk/codegen && npm run generate
```

### 2. Version Generated Files
- ✅ **DO** commit generated files
- ✅ **DO** review generated diffs
- ❌ **DON'T** edit generated files manually

### 3. Document Schema Changes
```python
# In schema.py
@strawberry.type
class ContractType:
    """Represents a tracked Soroban contract.
    
    This type is used across all SDK clients and includes
    metadata, verification status, and event statistics.
    """
    id: int
    contract_id: str = strawberry.field(
        description="Stellar contract address (C...)"
    )
```

### 4. Test Generated Types
```typescript
// In SDK tests
import { ContractType } from './generated/types';

it('should match generated type', () => {
  const contract: ContractType = {
    id: 1,
    contract_id: 'C...',
    // ... type-safe!
  };
});
```

## Migration Guide

### Migrating from Manual Types to Generated Types

1. **Keep both during transition**:
   ```typescript
   // Old manual types
   import { ContractEvent } from './types';
   // New generated types
   import { EventType } from './generated/types';
   ```

2. **Create type aliases for compatibility**:
   ```typescript
   // types.ts
   export type { EventType as ContractEvent } from './generated/types';
   ```

3. **Update imports gradually**:
   ```typescript
   // Before
   import { ContractEvent } from './types';
   
   // After
   import { EventType } from './generated/types';
   ```

4. **Remove manual types** once migration is complete

## Support

- **Issues**: Report codegen issues on GitHub
- **Documentation**: See `sdk/codegen/README.md`
- **Examples**: Check `sdk/typescript/test/` and `sdk/python/tests/`
