# Raymond AI Command Center

A command-driven website builder with a PHP dashboard on InfinityFree and a Python execution engine on Render.

## Architecture

- `dashboard/`: Chat-style PHP/Bootstrap interface. Deploy this folder to InfinityFree.
- `engine/`: FastAPI service deployed on Render.
- The dashboard forwards commands to the engine using a shared dashboard token.
- The engine uses an AI API key stored as a Render environment variable. ChatGPT web subscriptions are not an external API endpoint; API usage is configured separately.

## Current milestone

Initial project scaffold. Real code-generation, testing, and FTP deployment tools must be configured and tested before production use.

## Required Render environment variables

- `OPENAI_API_KEY`: API key for the model provider.
- `DASHBOARD_TOKEN`: long random secret shared with the PHP dashboard.
- `OPENAI_MODEL`: model name supported by the configured API (optional; defaults in the application).
- `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD`: InfinityFree FTP credentials (only needed for deployment).
- `FTP_PORT`: optional, defaults to 21.
- `FTP_REMOTE_DIR`: optional, defaults to `/htdocs`.

Never commit API keys, dashboard tokens, or FTP credentials to GitHub.

## Deploy

Deploy the Render service using the repository root and the Render configuration. Upload the contents of `dashboard/` to the chosen InfinityFree domain's `htdocs` directory. Set the dashboard's engine URL and shared token in its configuration.

## Safety

The execution engine must only write inside its isolated workspace. Production deployment should require explicit confirmation and should never delete or overwrite live files without a backup.
