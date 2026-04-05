# Contributing to AgentDNA

Thanks for your interest in contributing! 🧬

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/agentdna.git`
3. Create a branch: `git checkout -b feature/my-feature`

## Project Structure

```
agentdna/
├── src/
│   ├── registry/       # Core API server (FastAPI)
│   ├── trust/          # Trust scoring engine
│   ├── sandbox/        # Agent verification sandbox
│   ├── marketplace/    # Task marketplace & escrow
│   ├── sdk/
│   │   ├── python/     # Python SDK
│   │   └── typescript/ # TypeScript SDK
│   ├── cli/            # CLI tool
│   └── dashboard/      # Web dashboard
├── tests/
├── docs/
├── examples/
└── SPEC.md             # Full specification
```

## Development

### Python SDK

```bash
cd src/sdk/python
pip install -e ".[dev]"
pytest
```

### Registry Server

```bash
cd src/registry
pip install -e ".[server]"
uvicorn server:app --reload
```

### TypeScript SDK

```bash
cd src/sdk/typescript
npm install
npm run build
```

## What to Work On

Check the [Issues](https://github.com/mamoor123/agentdna/issues) page. Look for:

- `good first issue` — great for newcomers
- `help wanted` — we'd love your help
- `enhancement` — new features

## Code Style

- **Python**: Use `ruff` for linting and formatting
- **TypeScript**: Use ESLint + Prettier
- **Commits**: Use conventional commits (`feat:`, `fix:`, `docs:`)

## Pull Requests

1. Keep PRs focused — one feature or fix per PR
2. Add tests for new functionality
3. Update docs if you change public APIs
4. Fill out the PR template

## Questions?

Open a [Discussion](https://github.com/mamoor123/agentdna/discussions) — we're friendly!

## License

By contributing, you agree your contributions will be licensed under Apache 2.0.
