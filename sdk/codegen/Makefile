.PHONY: help install generate generate-ts generate-py introspect validate test clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	npm install

generate: ## Generate all SDK types (TypeScript + Python)
	npm run generate

generate-ts: ## Generate TypeScript types only
	npm run generate:typescript

generate-py: ## Generate Python types only
	npm run generate:python

introspect: ## Introspect and save GraphQL schema locally
	npm run introspect

validate: ## Generate types and run SDK tests
	npm run validate

test: ## Run SDK tests
	@echo "Testing TypeScript SDK..."
	cd ../typescript && npm test
	@echo "Testing Python SDK..."
	cd ../python && pytest

clean: ## Clean generated files and dependencies
	rm -rf node_modules
	rm -rf ../typescript/src/generated/*
	rm -rf ../python/soroscan/generated/*
	rm -f schema.graphql

watch: ## Watch mode - regenerate on schema changes
	npm run generate:watch

check-backend: ## Check if Django backend is running
	@curl -f http://localhost:8000/graphql/ > /dev/null 2>&1 && \
		echo "✅ Django backend is running" || \
		(echo "❌ Django backend is not running. Start it with: cd django-backend && python manage.py runserver" && exit 1)

setup: install check-backend generate ## Full setup: install, check backend, generate types
	@echo "✅ Setup complete!"
