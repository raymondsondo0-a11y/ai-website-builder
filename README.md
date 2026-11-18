# Raymond AI Command Center

A command-driven website factory. The current production backend is the Flask application in `app.py`.

## Current architecture

- `app.py`: Flask backend. It generates website files with the configured OpenAI API, commits them to the configured GitHub repository, and can receive Momo webhook messages.
- `.github/workflows/deploy-infinityfree.yml`: existing GitHub Actions workflow. A push to `main` triggers the existing FTP deployment to InfinityFree. This workflow is intentionally left unchanged.
- `dashboard/`: an early PHP dashboard scaffold. It currently calls a separate FastAPI `/command` endpoint in `engine/`; that endpoint is a planning-only prototype and is not the production website-generation backend yet.
- `engine/`: experimental FastAPI scaffold. It is not the Render service selected by this configuration.

## Render deployment

Render must run the root Flask application, not the planning-only FastAPI prototype in `engine/`.

The Blueprint uses the repository root, installs `requirements.txt`, starts `app.py` with Gunicorn, and checks `/health`.

Configure these environment variables in Render:

- `OPENAI_API_KEY`: OpenAI API key. Keep it in Render, never in Git.
- `OPENAI_MODEL`: supported model identifier; change only to a model available to your API account.
- `GITHUB_TOKEN`: token with permission to write contents to the target repository.
- `GITHUB_REPO`: defaults to `raymondsondo0-a11y/ai-website-builder`.
- `GITHUB_BRANCH`: defaults to `main`.
- `MOMO_API_TOKEN`: optional Momo Business API token.
- `MOMO_SENDER_ID`: optional Momo sender ID.
- `MOMO_WEBHOOK_SECRET`: optional webhook signature secret.
- `MOMO_SEND_URL`: optional Momo send endpoint.

Do not paste secrets into chat or commit them to GitHub. Add them through Render's Environment settings.

## Deployment flow

1. A website request reaches the Flask backend.
2. The backend asks the AI to generate complete website files.
3. The backend commits those files to the configured GitHub branch.
4. A push to `main` triggers the existing InfinityFree workflow.

The current dashboard in `dashboard/` still needs to be connected safely to the Flask API before it can be treated as a working web interface. Do not deploy the experimental `engine/` as the production backend.

## Other platforms

Vercel is not configured yet. It should only be added for a project with a supported frontend build (for example, a separate static/JavaScript frontend); it is not a replacement for the PHP hosting workflow.

Supabase is not configured yet. It should be added when the factory has a defined database/auth/storage use case and a project-specific migration/configuration. It is not a generic hosting destination.

## Safety

- Never commit API keys, dashboard tokens, Momo tokens, or FTP credentials.
- Keep the existing InfinityFree deployment workflow intact until a separate deployment test confirms any replacement.
- Require explicit confirmation before overwriting or deleting a live website.
