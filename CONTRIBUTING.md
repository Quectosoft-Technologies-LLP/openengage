# Contributing to OpenEngage

Thank you for your interest! We welcome bug reports, feature requests, and PRs.

## Getting Started

1. Fork the repo and clone your fork
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes, add tests
4. Run the test suite: `cd ai_gateway && pytest tests/`
5. Push and open a PR to `develop`

## Code Standards

- Python: PEP-8, type hints required, docstrings for public methods
- React: ESLint + Prettier enforced
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)
- Tests: minimum 80% coverage on new code

## Reporting Bugs

Use GitHub Issues with the `bug` label. Include:
- OpenEngage version
- Docker / OS version
- Steps to reproduce
- Expected vs actual behavior

## Patent Policy

Any contribution must NOT implement methods covered by known Adobe/Marketo patents
(listed in README.md). All PRs are reviewed for patent safety before merge.
