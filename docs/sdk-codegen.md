---
title: SDK Code Generation
description: Auto-generate type-safe SDK types from GraphQL schema
---

# SDK Code Generation

SoroScan automatically generates type-safe SDK types from the GraphQL schema, ensuring SDKs always match the backend API without manual synchronization.

## Overview

The code generation pipeline:

1. **Schema Introspection**: Fetches GraphQL schema from Django backend
2. **Type Generation**: Creates TypeScript and Python types
3. **Documentation**: Preserves schema descriptions as code comments
4. **Validation**: Runs SDK tests to verify generated types
5. **CI Integration**: Automatically updates types on schema changes

## Quick Start

### Generate Types Locally

```bash
cd sdk/codegen
npm install
npm run generate
```

This generates:
- TypeScript types in `sdk/typescript/src/generated/`
- Python Pydantic models in `sdk/python/soroscan/generated/`

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

## Type Mappings

### GraphQL to TypeScript

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

### GraphQL to Python

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

## Development Workflow

### 1. Modify GraphQL Schema

Edit `django-backend/soroscan/ingest/schema.py`:

```python
@strawberry.type
class ContractType:
    """Represents a tracked Soroban contract."""
    id: int
    contract_id: str = strawberry.field(
        description="Stellar contract address (C...)"
    )
    name: str
    # Add new field
    verified: bool = strawberry.field(
        description="Whether contract is verified"
    )
```

### 2. Generate Types

```bash
cd sdk/codegen
npm run generate
```

### 3. Review Changes

```bash
git diff sdk/typescript/src/generated/
git diff sdk/python/soroscan/generated/
```

### 4. Update SDK Clients

Update SDK client code to use new types:

```typescript
// TypeScript SDK
interface GetContractResponse {
  contract: ContractType; // Now includes 'verified' field
}
```

```python
# Python SDK
def get_contract(self, contract_id: str) -> ContractType:
    # ContractType now includes 'verified' field
    pass
```

### 5. Run Tests

```bash
# TypeScript
cd sdk/typescript && npm test

# Python
cd sdk/python && pytest
```

### 6. Commit Changes

```bash
git add django-backend/soroscan/ingest/schema.py
git add sdk/typescript/src/generated/
git add sdk/python/soroscan/generated/
git commit -m "feat: add contract verification field"
```

## CI/CD Integration

### Automatic Type Generation

The GitHub Actions workflow (`.github/workflows/sdk-codegen.yml`):

**On Pull Requests:**
- Generates types from schema
- Runs SDK tests
- **Fails if types are out of sync** (forces developers to run codegen)

**On Push to main/develop:**
- Generates types from schema
- Runs SDK tests
- **Auto-commits updated types** if changed

### Workflow Triggers

- Changes to `django-backend/soroscan/ingest/schema.py`
- Changes to `sdk/codegen/**`
- Manual dispatch

## Configuration

### Codegen Configuration

Edit `sdk/codegen/codegen.yml`:

```yaml
schema:
  - ${GRAPHQL_ENDPOINT:-http://localhost:8000/graphql/}

generates:
  ../typescript/src/generated/types.ts:
    plugins:
      - typescript
    config:
      scalars:
        DateTime: string
        JSON: Record<string, any>
        # Add custom scalars
        BigInt: string
```

### Environment Variables

- `GRAPHQL_ENDPOINT`: GraphQL endpoint URL (default: `http://localhost:8000/graphql/`)
- `SKIP_PYTHON_GEN`: Skip Python generation
- `SKIP_TS_GEN`: Skip TypeScript generation

## Best Practices

### 1. Document Schema Types

Add descriptions to GraphQL types - they become code comments:

```python
@strawberry.type
class EventType:
    """Represents an indexed contract event.
    
    Events are emitted by Soroban contracts and indexed
    by SoroScan for querying and real-time subscriptions.
    """
    id: int
    event_type: str = strawberry.field(
        description="Event type name (e.g., 'transfer', 'swap')"
    )
```

Generates:

```typescript
/**
 * Represents an indexed contract event.
 * 
 * Events are emitted by Soroban contracts and indexed
 * by SoroScan for querying and real-time subscriptions.
 */
export interface EventType {
  id: number;
  /** Event type name (e.g., 'transfer', 'swap') */
  eventType: string;
}
```

### 2. Version Generated Files

- ✅ **DO** commit generated files
- ✅ **DO** review generated diffs in PRs
- ❌ **DON'T** edit generated files manually

### 3. Test Generated Types

Add tests to verify generated types work correctly:

```typescript
// sdk/typescript/test/generated-types.test.ts
import { ContractType } from '../src/generated/types';

it('should have correct type structure', () => {
  const contract: ContractType = {
    id: 1,
    contract_id: 'C...',
    name: 'Test',
    // TypeScript ensures all required fields are present
  };
});
```

### 4. Handle Breaking Changes

When making breaking schema changes:

1. Bump SDK major version (semver)
2. Document migration in CHANGELOG
3. Provide migration guide for SDK users

## Troubleshooting

### Cannot Connect to GraphQL Endpoint

**Problem**: Codegen can't reach Django backend.

**Solution**:
```bash
cd django-backend
python manage.py runserver
curl http://localhost:8000/graphql/  # Verify it's running
```

### Generated Types Out of Sync

**Problem**: CI fails because types don't match schema.

**Solution**:
```bash
cd sdk/codegen
npm run generate
git add sdk/*/src/generated/ sdk/*/soroscan/generated/
git commit -m "chore: regenerate SDK types"
```

### Python Type Validation Errors

**Problem**: Pydantic validation fails with generated types.

**Solution**:
1. Check for breaking schema changes
2. Update SDK client code
3. Verify scalar type mappings in `codegen.yml`

## Advanced Usage

### Custom Scalar Mappings

Map GraphQL scalars to custom types:

```yaml
# codegen.yml
config:
  scalars:
    BigInt: string
    Decimal: string
    URL: string
```

### Watch Mode for Development

Auto-regenerate on schema changes:

```bash
cd sdk/codegen
npm run generate:watch
```

### Offline Development

Save schema locally for offline work:

```bash
cd sdk/codegen
npm run introspect  # Saves to schema.graphql
```

Then use local schema:

```yaml
# codegen.yml
schema: ./schema.graphql
```

## Resources

- [Full Guide](../sdk/CODEGEN_GUIDE.md) - Comprehensive documentation
- [GraphQL Code Generator](https://the-guild.dev/graphql/codegen) - Tool documentation
- [Pydantic](https://docs.pydantic.dev/) - Python validation library
- [CI Workflow](../.github/workflows/sdk-codegen.yml) - GitHub Actions setup

## Support

- **Issues**: [GitHub Issues](https://github.com/soroscan/soroscan/issues)
- **Discussions**: [GitHub Discussions](https://github.com/soroscan/soroscan/discussions)
- **Email**: team@soroscan.io
