# Contributing to HubEx

Thank you for your interest in contributing! This guide explains how to get started.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USER/hubex-backend.git`
3. Create a branch: `git checkout -b feature/my-feature`
4. Make changes, test, commit
5. Push and open a Pull Request

## Development Setup

```bash
# Backend
cp .env.example .env
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npx vite --port 5173
```

## Code Style

### Python (Backend)
- Python 3.11+
- Type hints everywhere
- Async/await for all DB operations
- Pydantic models for all API schemas
- SQLAlchemy ORM (never raw SQL)

### TypeScript (Frontend)
- Vue 3 + Composition API (`<script setup>`)
- TypeScript strict mode
- Tailwind CSS for styling
- i18n for all user-facing strings

## Pull Request Process

1. Ensure your code builds without errors (`npx vite build`)
2. Run existing tests if available
3. Update documentation if you change behavior
4. Write a clear PR description explaining what and why
5. Link relevant issues

## Reporting Issues

- Use GitHub Issues
- Include: Steps to reproduce, expected vs actual behavior, browser/OS info
- For security issues: Email directly (do not open public issue)

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions will be licensed under the project's license (AGPL v3 for Community Edition).
