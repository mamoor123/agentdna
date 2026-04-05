# Contributing to AgentDNA

Thanks for your interest! Here's how to get involved.

## Quick Start

```bash
git clone https://github.com/mamoor123/agentdna.git
cd agentdna
pip install -e ".[dev]"
pytest
```

## Ways to Contribute

### 🐛 Bug Reports
Open an issue with:
- What you expected
- What actually happened
- Steps to reproduce

### ✨ Features
Check existing issues first. For new ideas, open a discussion or issue tagged `enhancement`.

### 🔧 Code
1. Fork the repo
2. Create a branch: `git checkout -b feat/your-feature`
3. Make your changes
4. Run tests: `pytest`
5. Submit a PR

### 📖 Docs
Documentation improvements are always welcome — even fixing a typo counts.

## Good First Issues

Look for issues tagged [`good first issue`](../../labels/good%20first%20issue) — these are scoped, well-defined, and don't require deep context.

## Code Style

- Python: follow PEP 8, use `ruff` for linting
- TypeScript: follow the existing ESLint config
- Run `make lint` before submitting

## What We're Looking For

Right now, the highest-value contributions are:

1. **Framework integrations** — more plugins beyond LangChain/CrewAI
2. **Agent Card validators** — schema validation, linters
3. **Trust engine improvements** — better scoring algorithms
4. **Dashboard features** — search, filtering, agent comparisons
5. **Tests** — we always need more coverage

## Questions?

Open an issue or start a discussion. No question is too basic.

## License

By contributing, you agree your code will be licensed under the same license as the project.
