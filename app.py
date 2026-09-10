import os
import logging
from flask import Flask, request, jsonify
from github import Github
from github.GithubException import GithubException, UnknownObjectException

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "raymondsondo0-a11y/ai-website-builder")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

if not GITHUB_TOKEN:
    logging.warning("GITHUB_TOKEN is not configured.")

github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
repo = github_client.get_repo(GITHUB_REPO) if github_client else None


def write_file_to_github(path, content, commit_message):
    """Create or update one file in the configured GitHub repository."""
    if not repo:
        raise RuntimeError("GITHUB_TOKEN is not configured.")

    if not path or content is None:
        raise ValueError("File path/content is missing.")

    path = str(path).replace("\\", "/").lstrip("/")

    # Keep the builder inside the repository and prevent path traversal.
    parts = path.split("/")
    if not path or ".." in parts or any(part == "" for part in parts):
        raise ValueError(f"Unsafe file path: {path}")

    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)

        # A file path must resolve to one file, not a directory listing.
        if isinstance(existing, list):
            raise ValueError(f"Path points to a directory, not a file: {path}")

        repo.update_file(
            path=path,
            message=commit_message,
            content=str(content),
            sha=existing.sha,
            branch=GITHUB_BRANCH,
        )
        logging.info("Updated GitHub file: %s", path)
        return "updated"

    except UnknownObjectException:
        # GitHub 404 means the file does not exist yet.
        repo.create_file(
            path=path,
            message=commit_message,
            content=str(content),
            branch=GITHUB_BRANCH,
        )
        logging.info("Created GitHub file: %s", path)
        return "created"

    except GithubException as error:
        logging.exception("GitHub error while writing %s", path)
        raise RuntimeError(
            f"GitHub error while writing {path}: {error.data if getattr(error, 'data', None) else str(error)}"
        ) from error


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "service": "AI Website Builder",
        "mode": "Momo AI Agent -> HTTP -> GitHub",
        "ai": "Handled by the existing Momo AI Agent / Message Flow",
        "openai_api": False,
        "momo_send_api": False,
        "build_endpoint": "/build",
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "github_configured": bool(GITHUB_TOKEN),
        "repository": GITHUB_REPO,
        "branch": GITHUB_BRANCH,
    })


@app.route("/build", methods=["POST"])
def build():
    """
    Backend endpoint used by the existing Momo AI Agent / Message Flow.

    Expected JSON:
    {
      "message": "short description of what was built",
      "files": [
        {"path": "index.html", "content": "complete file content"},
        {"path": "style.css", "content": "complete file content"}
      ]
    }
    """
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "ok": False,
                "error": "Invalid JSON body."
            }), 400

        files = data.get("files")
        if not isinstance(files, list) or not files:
            return jsonify({
                "ok": False,
                "error": "No files supplied. Send a non-empty files array."
            }), 400

        user_message = str(data.get("message") or "Website update").strip()
        commit_message = "AI Website Builder: " + user_message[:70]
        changed_files = []
        skipped_files = []

        for file in files:
            if not isinstance(file, dict):
                skipped_files.append({"reason": "File entry is not an object."})
                continue

            path = file.get("path")
            content = file.get("content")

            if not path or content is None:
                skipped_files.append({
                    "path": str(path) if path else None,
                    "reason": "Missing path or content."
                })
                continue

            status = write_file_to_github(
                path=path,
                content=content,
                commit_message=commit_message,
            )

            changed_files.append({
                "path": str(path).replace("\\", "/").lstrip("/"),
                "status": status,
            })

        if not changed_files:
            return jsonify({
                "ok": False,
                "error": "No valid files were supplied.",
                "skipped_files": skipped_files,
            }), 400

        logging.info("Website build committed: %s", changed_files)

        return jsonify({
            "ok": True,
            "message": "Website files were written to GitHub successfully.",
            "files": changed_files,
            "skipped_files": skipped_files,
            "github_repo": GITHUB_REPO,
            "branch": GITHUB_BRANCH,
        }), 200

    except Exception as error:
        logging.exception("Website build failed")
        return jsonify({
            "ok": False,
            "error": str(error)[:1500],
        }), 500


@app.route("/webhook/momo", methods=["POST"])
def momo_webhook():
    """
    Compatibility endpoint only.

    The Momo Message Flow / AI Agent should call POST /build after it
    generates the website files. This webhook does not call OpenAI,
    does not call a Momo send endpoint, and does not generate websites itself.
    """
    data = request.get_json(silent=True) or {}
    logging.info("Momo webhook received in compatibility mode: %s", data)

    return jsonify({
        "received": True,
        "status": "received",
        "message": "Use the Momo AI Agent / Message Flow to POST generated website files to /build.",
        "build_endpoint": "/build",
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
