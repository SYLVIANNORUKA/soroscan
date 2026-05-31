# Migration Guide: Manual Types → Generated Types

This guide helps you migrate from manually maintained SDK types to auto-generated types from the GraphQL schema.

## Overview

SoroScan SDKs now auto-generate types from the GraphQL schema, providing:
- ✅ Type safety guaranteed to match backend
- ✅ Automatic updates when schema changes
- ✅ Documentation from schema descriptions
- ✅ No manual synchronization needed

## Migration Strategy

We recommend a **gradual migration** approach:

1. Keep both manual and generated types during transition
2. Create type aliases for backward compatibility
3. Update imports gradually
4. Remove manual types once migration is complete

## Step-by-Step Migration

### Phase 1: Generate Types (No Breaking Changes)

#### 1.1 Generate Types

```bash
cd sdk/codegen
npm install
npm run generate
```

This creates:
- `sdk/typescript/src/generated/types.ts`
- `sdk/python/soroscan/generated/types.py`

#### 1.2 Verify Generation

```bash
# TypeScript
cd sdk/typescript
npm test

# Python
cd sdk/python
pytest tests/test_generated_types.py
```

### Phase 2: Create Compatibility Layer

#### 2.1 TypeScript Compatibility

Create type aliases in `sdk/typescript/src/types.ts`:

```typescript
// Export generated types with backward-compatible names
export type {
  EventType as ContractEvent,
  ContractType as Contract,
  EventConnection as EventsResponse,
  PageInfo,
} from './generated/types';

// Keep custom types that aren't in GraphQL schema
export interface SoroScanClientConfig {
  baseUrl: string;
  apiKey?: string;
  timeoutMs?: number;
}

// Re-export everything from generated types
export * from './generated/types';
```

#### 2.2 Python Compatibility

Create aliases in `sdk/python/soroscan/models.py`:

```python
"""Backward-compatible type aliases."""

# Import generated types
from soroscan.generated.types import (
    EventType as GeneratedEventType,
    ContractType as GeneratedContractType,
    EventConnection as GeneratedEventConnection,
)

# Create aliases for backward compatibility
ContractEvent = GeneratedEventType
TrackedContract = GeneratedContractType
EventsResponse = GeneratedEventConnection

# Re-export everything
from soroscan.generated.types import *

__all__ = [
    'ContractEvent',
    'TrackedContract',
    'EventsResponse',
    # ... other exports
]
```

### Phase 3: Update SDK Clients

#### 3.1 TypeScript Client

Update `sdk/typescript/src/client.ts`:

```typescript
// Before
import { ContractEvent, Contract } from './types';

// After - use generated types
import type { EventType, ContractType, EventConnection } from './generated/types';

export class SoroScanClient {
  async getEvents(params: GetEventsParams): Promise<EventConnection> {
    // Implementation using generated types
  }
  
  async getContract(contractId: string): Promise<ContractType> {
    // Implementation using generated types
  }
}
```

#### 3.2 Python Client

Update `sdk/python/soroscan/client.py`:

```python
# Before
from .models import ContractEvent, TrackedContract

# After - use generated types
from .generated.types import EventType, ContractType, EventConnection

class SoroScanClient:
    def get_events(self, **params) -> EventConnection:
        """Get events using generated types."""
        response = self._query(...)
        return EventConnection(**response)
    
    def get_contract(self, contract_id: str) -> ContractType:
        """Get contract using generated types."""
        response = self._query(...)
        return ContractType(**response)
```

### Phase 4: Update Tests

#### 4.1 TypeScript Tests

```typescript
// Before
import { ContractEvent } from '../src/types';

// After
import type { EventType } from '../src/generated/types';

describe('Events', () => {
  it('should fetch events', async () => {
    const events: EventType[] = await client.getEvents();
    expect(events).toBeDefined();
  });
});
```

#### 4.2 Python Tests

```python
# Before
from soroscan.models import ContractEvent

# After
from soroscan.generated.types import EventType

def test_get_events():
    events: list[EventType] = client.get_events()
    assert events is not None
```

### Phase 5: Update Documentation

#### 5.1 Update README

```markdown
## Types

SoroScan SDK uses auto-generated types from the GraphQL schema.

### TypeScript
\`\`\`typescript
import type { EventType, ContractType } from '@soroscan/sdk';
\`\`\`

### Python
\`\`\`python
from soroscan.generated.types import EventType, ContractType
\`\`\`

See [CODEGEN_GUIDE.md](../CODEGEN_GUIDE.md) for details.
```

#### 5.2 Update Examples

Update all code examples to use generated types.

### Phase 6: Remove Manual Types

Once migration is complete and all tests pass:

#### 6.1 Remove Manual Type Files

```bash
# TypeScript - keep only compatibility exports
# Remove detailed type definitions from src/types.ts

# Python - keep only compatibility exports
# Remove detailed type definitions from soroscan/models.py
```

#### 6.2 Update Imports

Remove compatibility layer and use generated types directly:

```typescript
// Final state - direct imports
import type { EventType, ContractType } from './generated/types';
```

```python
# Final state - direct imports
from soroscan.generated.types import EventType, ContractType
```

## Type Mapping Reference

### TypeScript

| Manual Type | Generated Type | Notes |
|-------------|----------------|-------|
| `ContractEvent` | `EventType` | Renamed for consistency |
| `Contract` | `ContractType` | Renamed for consistency |
| `EventsResponse` | `EventConnection` | GraphQL connection pattern |
| `PageInfo` | `PageInfo` | Same name |
| `ContractStats` | `ContractStats` | Same name |

### Python

| Manual Type | Generated Type | Notes |
|-------------|----------------|-------|
| `ContractEvent` | `EventType` | Renamed for consistency |
| `TrackedContract` | `ContractType` | Renamed for consistency |
| `WebhookSubscription` | `WebhookType` | New in schema |
| `ContractStats` | `ContractStats` | Same name |
| `PaginatedResponse[T]` | `EventConnection` | GraphQL connection pattern |

## Breaking Changes

### TypeScript

1. **Field Name Changes**: GraphQL uses camelCase
   ```typescript
   // Before
   event.contract_id
   
   // After
   event.contractId
   ```

2. **Nullable Fields**: Explicit `| null` instead of `?`
   ```typescript
   // Before
   lastEventAt?: string
   
   // After
   lastEventAt: string | null
   ```

3. **Type Names**: Some types renamed for consistency
   ```typescript
   // Before
   ContractEvent
   
   // After
   EventType
   ```

### Python

1. **Field Names**: GraphQL uses snake_case (no change)
   ```python
   # Same
   event.contract_id
   ```

2. **Optional Fields**: Using `Optional[T]` consistently
   ```python
   # Before
   last_event_at: datetime | None
   
   # After
   last_event_at: Optional[datetime]
   ```

3. **Pydantic v2**: Generated types use Pydantic v2
   ```python
   # Before
   class Config:
       orm_mode = True
   
   # After
   class Config:
       from_attributes = True
   ```

## Version Compatibility

### Semantic Versioning

When releasing SDK versions with generated types:

- **Major version bump** (1.x.x → 2.0.0): Breaking changes in type names/structure
- **Minor version bump** (1.0.x → 1.1.0): New types added, backward compatible
- **Patch version bump** (1.0.0 → 1.0.1): Bug fixes, no type changes

### Deprecation Strategy

1. **v1.x**: Manual types (current)
2. **v2.0**: Generated types + compatibility layer
3. **v2.1**: Deprecation warnings for old imports
4. **v3.0**: Remove compatibility layer

## Testing Strategy

### During Migration

1. **Run both test suites**:
   ```bash
   # Test manual types
   npm test -- --testPathPattern=legacy
   
   # Test generated types
   npm test -- --testPathPattern=generated
   ```

2. **Compare responses**:
   ```typescript
   it('should match manual and generated types', () => {
     const manualEvent: ContractEvent = fetchEvent();
     const generatedEvent: EventType = fetchEvent();
     
     // Verify structure matches
     expect(manualEvent.id).toBe(generatedEvent.id);
   });
   ```

3. **Integration tests**:
   ```bash
   # Run against real API
   npm run test:integration
   ```

### After Migration

1. Remove legacy tests
2. Keep only generated type tests
3. Add regression tests for type changes

## Rollback Plan

If issues arise during migration:

### Quick Rollback

```bash
# Revert to manual types
git revert <commit-hash>

# Or use compatibility layer
# Keep both manual and generated types
```

### Gradual Rollback

1. Keep compatibility layer
2. Fix issues in generated types
3. Re-attempt migration

## Common Issues

### Issue: Type Mismatch Errors

**Problem**: Generated types don't match API responses

**Solution**:
1. Verify GraphQL schema is up to date
2. Regenerate types: `cd sdk/codegen && npm run generate`
3. Check for schema/API version mismatch

### Issue: Missing Types

**Problem**: Some types not generated

**Solution**:
1. Check if type is in GraphQL schema
2. Add to schema if missing
3. Regenerate types

### Issue: Pydantic Validation Errors

**Problem**: Python validation fails with generated types

**Solution**:
1. Check field types match API responses
2. Verify Optional fields are correct
3. Update schema if needed

## Support

### Getting Help

- **Documentation**: [CODEGEN_GUIDE.md](./CODEGEN_GUIDE.md)
- **Issues**: [GitHub Issues](https://github.com/soroscan/soroscan/issues)
- **Discussions**: [GitHub Discussions](https://github.com/soroscan/soroscan/discussions)

### Reporting Issues

When reporting migration issues, include:
1. SDK version
2. Error messages
3. Code snippets showing the issue
4. Steps to reproduce

## Timeline

Recommended migration timeline:

- **Week 1**: Generate types, create compatibility layer
- **Week 2**: Update SDK clients to use generated types
- **Week 3**: Update tests and documentation
- **Week 4**: Remove manual types, release new version

## Checklist

Use this checklist to track migration progress:

### Setup
- [ ] Generate types locally
- [ ] Verify generation works
- [ ] Run SDK tests

### Compatibility
- [ ] Create type aliases
- [ ] Update exports
- [ ] Test backward compatibility

### Migration
- [ ] Update SDK clients
- [ ] Update tests
- [ ] Update documentation
- [ ] Update examples

### Cleanup
- [ ] Remove manual types
- [ ] Remove compatibility layer
- [ ] Update version number
- [ ] Release new version

### Validation
- [ ] All tests pass
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] Examples work

## Conclusion

Migrating to generated types ensures your SDK stays in sync with the backend API automatically. While the migration requires some work upfront, the long-term benefits of type safety and automatic updates are worth it.

For questions or issues during migration, please reach out via GitHub Issues or Discussions.

---

**Last Updated**: May 31, 2026  
**SDK Version**: 2.0.0+  
**Status**: Ready for Migration
