# Quick Start: SDK Code Generation

Generate type-safe SDK types from GraphQL schema in 3 steps.

## Prerequisites

- Node.js 20+ installed
- Django backend running on `http://localhost:8000`

## Steps

### 1. Install Dependencies

```bash
cd sdk/codegen
npm install
```

### 2. Generate Types

```bash
npm run generate
```

This creates:
- `sdk/typescript/src/generated/types.ts`
- `sdk/python/soroscan/generated/types.py`

### 3. Verify

```bash
# Check TypeScript SDK
cd ../typescript
npm test

# Check Python SDK
cd ../python
pytest tests/test_generated_types.py
```

## That's It!

Generated types are now ready to use in your SDK clients.

## Next Steps

- Read [CODEGEN_GUIDE.md](../CODEGEN_GUIDE.md) for detailed documentation
- See [README.md](./README.md) for configuration options
- Check [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) for technical details

## Common Commands

```bash
# Generate all types
npm run generate

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
```

## Troubleshooting

### Backend Not Running

```bash
cd ../../django-backend
python manage.py runserver
```

### Types Out of Sync

```bash
npm run generate
git add ../typescript/src/generated/ ../python/soroscan/generated/
git commit -m "chore: regenerate SDK types"
```

### Need Help?

- See [README.md](./README.md) for detailed troubleshooting
- Check [CODEGEN_GUIDE.md](../CODEGEN_GUIDE.md) for comprehensive guide
- Open an issue on GitHub
