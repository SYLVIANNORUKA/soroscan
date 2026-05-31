#!/usr/bin/env tsx
/**
 * Generate Python Pydantic models from GraphQL schema
 * Reads the TypeScript generated types and converts them to Python
 */

import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';
import { getIntrospectionQuery, buildClientSchema, GraphQLSchema, GraphQLObjectType, GraphQLInputObjectType, GraphQLEnumType, GraphQLScalarType, GraphQLList, GraphQLNonNull, isObjectType, isInputObjectType, isEnumType, isScalarType, isListType, isNonNullType } from 'graphql';

const GRAPHQL_ENDPOINT = process.env.GRAPHQL_ENDPOINT || 'http://localhost:8000/graphql/';
const OUTPUT_DIR = join(__dirname, '../../python/soroscan/generated');
const OUTPUT_FILE = join(OUTPUT_DIR, 'types.py');

// GraphQL scalar to Python type mapping
const SCALAR_TYPE_MAP: Record<string, string> = {
  String: 'str',
  Int: 'int',
  Float: 'float',
  Boolean: 'bool',
  ID: 'str',
  DateTime: 'datetime',
  Date: 'date',
  Time: 'time',
  JSON: 'dict[str, Any]',
  UUID: 'str',
};

interface TypeInfo {
  pythonType: string;
  imports: Set<string>;
  isOptional: boolean;
}

function getFieldType(type: any, schema: GraphQLSchema): TypeInfo {
  const imports = new Set<string>();
  let isOptional = true;
  let pythonType = 'Any';

  // Handle NonNull wrapper
  if (isNonNullType(type)) {
    isOptional = false;
    type = type.ofType;
  }

  // Handle List wrapper
  if (isListType(type)) {
    const innerType = getFieldType(type.ofType, schema);
    imports.add('typing');
    for (const imp of innerType.imports) {
      imports.add(imp);
    }
    pythonType = `list[${innerType.pythonType}]`;
    return { pythonType, imports, isOptional };
  }

  // Handle Scalar types
  if (isScalarType(type)) {
    const scalarName = type.name;
    pythonType = SCALAR_TYPE_MAP[scalarName] || 'Any';
    
    if (scalarName === 'DateTime') {
      imports.add('datetime');
    } else if (scalarName === 'Date') {
      imports.add('datetime');
    } else if (scalarName === 'Time') {
      imports.add('datetime');
    } else if (scalarName === 'JSON') {
      imports.add('typing');
    }
    
    return { pythonType, imports, isOptional };
  }

  // Handle Enum types
  if (isEnumType(type)) {
    pythonType = type.name;
    return { pythonType, imports, isOptional };
  }

  // Handle Object/Input types
  if (isObjectType(type) || isInputObjectType(type)) {
    pythonType = type.name;
    return { pythonType, imports, isOptional };
  }

  return { pythonType: 'Any', imports, isOptional };
}

function generateEnumClass(enumType: GraphQLEnumType): string {
  const values = enumType.getValues();
  const description = enumType.description ? `    """${enumType.description}"""` : '';
  
  const enumValues = values.map(value => {
    const valueDesc = value.description ? `  # ${value.description}` : '';
    return `    ${value.name} = "${value.value}"${valueDesc}`;
  }).join('\n');

  return `
class ${enumType.name}(str, Enum):
${description}
${enumValues}
`;
}

function generateModelClass(type: GraphQLObjectType | GraphQLInputObjectType, schema: GraphQLSchema): string {
  const fields = Object.values(type.getFields());
  const description = type.description ? `    """${type.description}"""` : '';
  
  const allImports = new Set<string>();
  const fieldDefs: string[] = [];

  for (const field of fields) {
    const fieldType = getFieldType(field.type, schema);
    
    for (const imp of fieldType.imports) {
      allImports.add(imp);
    }

    let pythonFieldType = fieldType.pythonType;
    if (fieldType.isOptional) {
      pythonFieldType = `Optional[${pythonFieldType}]`;
      allImports.add('typing');
    }

    const fieldDesc = field.description ? `, description="${field.description.replace(/"/g, '\\"')}"` : '';
    const defaultValue = fieldType.isOptional ? ' = None' : '';
    
    fieldDefs.push(`    ${field.name}: ${pythonFieldType}${defaultValue}${fieldDesc ? ` = Field(${fieldDesc.slice(2)})` : ''}`);
  }

  return `
class ${type.name}(BaseModel):
${description}
${fieldDefs.join('\n') || '    pass'}

    class Config:
        """Pydantic model configuration."""
        from_attributes = True
        populate_by_name = True
`;
}

async function generatePythonTypes() {
  console.log(`🐍 Generating Python types from ${GRAPHQL_ENDPOINT}...`);

  try {
    // Fetch schema
    const response = await fetch(GRAPHQL_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: getIntrospectionQuery(),
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const { data, errors } = await response.json();

    if (errors) {
      console.error('❌ GraphQL errors:', errors);
      process.exit(1);
    }

    const schema = buildClientSchema(data);
    const typeMap = schema.getTypeMap();

    // Collect all types
    const enums: GraphQLEnumType[] = [];
    const models: (GraphQLObjectType | GraphQLInputObjectType)[] = [];

    for (const [name, type] of Object.entries(typeMap)) {
      // Skip internal GraphQL types
      if (name.startsWith('__')) continue;
      
      // Skip Query, Mutation, Subscription root types
      if (name === 'Query' || name === 'Mutation' || name === 'Subscription') continue;

      if (isEnumType(type)) {
        enums.push(type);
      } else if (isObjectType(type) || isInputObjectType(type)) {
        models.push(type);
      }
    }

    // Generate Python code
    const imports = [
      '"""Auto-generated types from GraphQL schema.',
      '',
      'DO NOT EDIT MANUALLY - This file is auto-generated by sdk/codegen.',
      'Run `npm run generate` from sdk/codegen/ to regenerate.',
      '"""',
      '',
      'from datetime import date, datetime, time',
      'from enum import Enum',
      'from typing import Any, Optional',
      '',
      'from pydantic import BaseModel, Field',
      '',
    ];

    const enumCode = enums.map(e => generateEnumClass(e)).join('\n');
    const modelCode = models.map(m => generateModelClass(m, schema)).join('\n');

    const output = [
      ...imports,
      '# ─────────────────────────────────────────────────────────────────────────────',
      '# Enums',
      '# ─────────────────────────────────────────────────────────────────────────────',
      enumCode,
      '',
      '# ─────────────────────────────────────────────────────────────────────────────',
      '# Models',
      '# ─────────────────────────────────────────────────────────────────────────────',
      modelCode,
    ].join('\n');

    // Ensure output directory exists
    mkdirSync(OUTPUT_DIR, { recursive: true });

    // Write output file
    writeFileSync(OUTPUT_FILE, output, 'utf-8');

    // Write __init__.py
    const initFile = join(OUTPUT_DIR, '__init__.py');
    const exportNames = [
      ...enums.map(e => e.name),
      ...models.map(m => m.name),
    ];
    
    const initContent = [
      '"""Generated types from GraphQL schema."""',
      '',
      'from .types import (',
      ...exportNames.map(name => `    ${name},`),
      ')',
      '',
      '__all__ = [',
      ...exportNames.map(name => `    "${name}",`),
      ']',
    ].join('\n');
    
    writeFileSync(initFile, initContent, 'utf-8');

    console.log(`✅ Generated ${enums.length} enums and ${models.length} models`);
    console.log(`📝 Output: ${OUTPUT_FILE}`);
  } catch (error) {
    console.error('❌ Failed to generate Python types:', error);
    process.exit(1);
  }
}

generatePythonTypes();
