#!/usr/bin/env tsx
/**
 * Introspect GraphQL schema from Django backend
 * Saves schema to a local file for offline development
 */

import { writeFileSync } from 'fs';
import { join } from 'path';
import { getIntrospectionQuery, buildClientSchema, printSchema } from 'graphql';

const GRAPHQL_ENDPOINT = process.env.GRAPHQL_ENDPOINT || 'http://localhost:8000/graphql/';
const OUTPUT_PATH = join(__dirname, '../schema.graphql');

async function introspectSchema() {
  console.log(`🔍 Introspecting schema from ${GRAPHQL_ENDPOINT}...`);

  try {
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

    // Build and print schema
    const schema = buildClientSchema(data);
    const sdl = printSchema(schema);

    // Write to file
    writeFileSync(OUTPUT_PATH, sdl, 'utf-8');

    console.log(`✅ Schema saved to ${OUTPUT_PATH}`);
    console.log(`📊 Types: ${Object.keys(schema.getTypeMap()).length}`);
  } catch (error) {
    console.error('❌ Failed to introspect schema:', error);
    process.exit(1);
  }
}

introspectSchema();
