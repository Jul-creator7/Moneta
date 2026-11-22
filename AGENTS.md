# Project workflow

Implement the current phase and wait for explicit authorization before starting another. Preserve existing user changes and Git history. Use the configured branch convention, defaulting to main for new repositories.

Keep React components reusable and accessible. Keep API routers thin and put business logic in services. Use Alembic for schema changes. Derive authenticated identity from validated tokens. Scope financial queries to the owner. Store money as integer minor units and keep all operations simulated. Keep secrets outside source control.

Before every phase checkpoint, run relevant tests and verify the frontend build. Fix critical failures, review Git status and the staged diff, and exclude secrets, local databases, virtual environments, and generated dependencies. Commit with a descriptive phase-specific message and push to the configured GitHub remote. Verify the remote branch tip. Preserve history and avoid force pushes without explicit authorization. Report features, checks, commit, branch, push status, remaining issues, and the next phase.
