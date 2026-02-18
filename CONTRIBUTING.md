# Contributing to SoroScan 🔍

Thank you for investing your time in contributing to SoroScan!

SoroScan is an open-source indexing layer designed to make Soroban smart contract data accessible and queryable. Whether you're fixing a bug, improving documentation, or building a new feature, we welcome your involvement.

The following is a set of guidelines for contributing to SoroScan and its packages.

<!-- ## ⚡ Quick Links

- **[View Open Issues](../../issues)** - Find a task to work on.
- **[Architecture Overview](../README.md#architecture)** - Understand the hybrid Rust/Django design.
- **[Discussions](../../discussions)** - Ask questions or propose new ideas.
 -->
---

## 🛠️ Development Workflow

### 1. Find an Issue
* Navigate to the **Issues** tab.
* Filter by `good-first-issue` if you are new to the project.
* **Claim it:** Please comment **"I'd like to work on this!"** on the issue thread to avoid duplicate work. Wait for a maintainer to assign it to you.
* Clone & Navigate after forking the repo.
```
git clone https://github.com/<your-username>/soroscan.git
cd soroscan
```

### 2. Environment Setup

This project requires **Rust**, **Python 3.11+**, **PostgreSQL**, and **Redis**.

#### 🐍 Backend (Django) Setup
The backend handles data ingestion, the API, and webhook dispatching.

```bash
# 1. Navigate to backend directory
cd django-backend

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure Environment
cp .env.example .env
# Edit .env with your local PostgreSQL credentials

# 5. Run Migrations & Start Server
python manage.py migrate
python manage.py runserver
```

🦀 Smart Contract (Rust) Setup
If you are modifying the core indexing logic or event emission standards.


```bash
# 1. Navigate to contracts directory
cd soroban-contracts/soroscan_core

# 2. Run tests to ensure environment is correct
cargo test

# 3. Build optimized WASM
cargo build --target wasm32-unknown-unknown --release
```

### 3. Making Changes

Branching: Create a new branch for your work.

```Bash
git checkout -b feat/your-feature-name
```
Code Style:

- **Python:** We adhere to PEP 8. Please run black . before committing.

- **Rust:** Please run cargo fmt before committing.


### Datbase Migrations 
If you modify models.py, ensure you generate migration files:

```Bash
python manage.py makemigrations
```
### 4. Testing
We prioritize stability. **Please run the test suite before submitting your PR.**

Django Tests:

```Bash
python manage.py test
```
Contract Tests:

```Bash
cargo test
```
Linting:
```Bash=# Python
ruff check .
black --check .

# Rust
cargo clippy -- -D warnings
cargo fmt --check
```

## 🚀 Submitting a Pull Request (PR)
Push your branch to your fork.
```
git push origin feat/your-feature-name
```

**Open a Pull Request against** the main branch.

**Title: Please use Conventional Commits format:**
```

feat: add websocket support

fix: resolve overflow in indexer

docs: update installation guide
```

Description: Reference the issue you are solving (e.g., Closes #12).

Validation: Ensure all CI checks pass.

📜 Code of Conduct
By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.