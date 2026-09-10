import os
import logging
from flask import Flask, request, jsonify
from github import Github

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
    if not repo:
        raise RuntimeError("GITHUB_TOKEN is not configured.")

    if not path or content is None:
        raise ValueError("File path/content is missing.")

    path = str(path).replace("\\", "/").lstrip("/")
    if not path or ".." in path.split("/"):
        raise ValueError(f"Unsafe file path: {path}")

    try:
        existing_file = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(
            path=path,
            message=commit_message,
            content=str(content),
            sha=existing_file.sha,
            branch=GITHUB_BRANCH,
        )
        logging.info("Updated GitHub file: %s", path)
        return "updated"
    except Exception as error:
        if "404" not in str(error):
            logging.info("Creating GitHub file %s after lookup result: %s", path, error)
        repo.create_file(
            path=path,
            message=commit_message,
            content=str(content),
            branch=GITHUB_BRANCH,
        )
        logging.info("Created GitHub file: %s", path)
        return "created"


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "service": "AI Website Builder",
        "mode": "Momo AI Agent -> HTTP -> GitHub",
        "message": "This service no longer calls OpenAI or the Momo send API."
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/build", methods=["POST"])
def build():
    """
    Endpoint for the Momo AI Agent / Message Flow.

    Expected JSON:
    {
      "message": "short description of what was built",
      "files": [
        {"path": "index.html", "content": "complete file content"}
      ]
    }
    """
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "Invalid JSON body."}), 400

        files = data.get("files")
        if not isinstance(files, list) or not files:
            return jsonify({
                "ok": False,
                "error": "No files supplied. The Momo AI Agent must provide a files array."
            }), 400

        user_message = str(data.get("message") or "Website update")
        commit_message = "AI Website Builder: " + user_message[:70]
        changed_files = []

        for file in files:
            if not isinstance(file, dict):
                continue

            path = file.get("path")
            content = file.get("content")
            if not path or content is None:
                continue

            status = write_file_to_github(path, content, commit_message)
            changed_files.append({"path": str(path), "status": status})

        if not changed_files:
            return jsonify({"ok": False, "error": "No valid files were supplied."}), 400

        logging.info("Website build committed: %s", changed_files)
        return jsonify({
            "ok": True,
            "message": "Website files were written to GitHub successfully.",
            "files": changed_files,
            "github_repo": GITHUB_REPO,
            "branch": GITHUB_BRANCH
        }), 200

    except Exception as error:
        logging.exception("Website build failed")
        return jsonify({
            "ok": False,
            "error": str(error)[:1000]
        }), 500


@app.route("/webhook/momo", methods=["POST"])
def momo_webhook():
    """
    Kept only for compatibility with the current Momo webhook while we move
    website building into the Momo Message Flow / AI Agent.

    It does NOT call OpenAI and does NOT call the Momo send API.
    """
    data = request.get_json(silent=True) or {}
    logging.info("Momo webhook received (compatibility mode): %s", data)
    return jsonify({
        "received": True,
        "status": "received",
        "message": "Route website requests through the Momo Message Flow / AI Agent to POST /build."
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
