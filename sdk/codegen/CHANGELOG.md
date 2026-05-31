# Changelog

All notable changes to the SDK code generation tools will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-31

### Added
- Initial release of SDK code generation tools
- TypeScript type generation from GraphQL schema using GraphQL Code Generator
- Python Pydantic model generation from GraphQL schema
- Automatic docstring generation from schema descriptions
- CI workflow for automatic type generation on schema changes
- Validation tests for generated types in both SDKs
- Watch mode for development
- Schema introspection tool for offline development

### Features
- **TypeScript Generation**
  - Full type safety for all GraphQL types
  - Proper handling of nullable and list types
  - Enum types as TypeScript enums
  - JSDoc comments from schema descriptions
  - Separate files for types, operations, and resolvers

- **Python Generation**
  - Pydantic v2 models with full validation
  - Proper Python type hints (Optional, list, dict, etc.)
  - Enum classes for GraphQL enums
  - Docstrings from schema descriptions
  - JSON serialization support

- **CI Integration**
  - Automatic generation on schema changes
  - Validation that generated types match schema
  - Automatic commit of updated types (main/develop branches)
  - PR checks to ensure types are in sync

### Documentation
- Comprehensive README with usage instructions
- Troubleshooting guide
- Development workflow documentation
- CI integration guide

## [Unreleased]

### Planned
- Support for custom scalar type mappings
- GraphQL fragment generation
- SDK method generation from operations
- Automatic changelog generation for type changes
- Performance optimizations for large schemas
