# 🔄 Development & Git Workflow

Guidelines for contributors and maintaining a clean project history.

## Branching Strategy
- **main**: The stable, production-ready branch. All releases are tagged here.
- **feature/[name]**: Temporary branches for developing new modules or UI features.

## Commit Conventions
We follow clear, descriptive commit messages:
- `feat`: A new feature (e.g., `feat: Add AI anomaly detection`).
- `fix`: A bug fix (e.g., `fix: Resolve Bluetooth import error`).
- `docs`: Documentation updates.
- `refactor`: Code changes that neither fix a bug nor add a feature.

## Fresh Start Policy
If the project history needs to be reset for branding or cleanup:
1. Re-initialize Git: `rm -rf .git && git init`
2. Create a clean "Initial commit".
3. Force-push to remotes: `git push -f origin main`
