import os
import json
import logging
from flask import Flask, request, jsonify
from openai import OpenAI
from github import Github

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv(
    "GITHUB_REPO",
    "raymondsondo0-a11y/ai-website-builder"
)
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# --------------------------------------------------
# CLIENTS
# --------------------------------------------------

openai_client = OpenAI(api_key=OPENAI_API_KEY)
github_client = Github(GITHUB_TOKEN)

repo = github_client.get_repo(GITHUB_REPO)

# --------------------------------------------------
# SYSTEM PROMPT
# --------------------------------------------------

SYSTEM_PROMPT = """
You are an expert autonomous website developer.

Your job is to understand a user's website-development request
and produce complete website files.

The user may say things such as:

- Create a hotel website
- Build a restaurant website
- Add a booking page
- Change the homepage
- Add an admin dashboard
- Make the website responsive
- Add a contact form
- Fix the login page

The project is hosted through GitHub and deployed automatically.

When creating a website, prefer:

- HTML5
- CSS3
- JavaScript
- Bootstrap when useful
- PHP when server-side functionality is required

Create production-quality, responsive code.

IMPORTANT:
Return ONLY valid JSON.

The JSON must have this structure:

{
  "message": "short explanation",
  "files": [
    {
      "path": "index.html",
      "content": "complete file content"
    }
  ]
}

Every file must contain COMPLETE content.
Never use placeholders such as:
"put code here"
"etc."
"..."
or "same as above".

If the user asks to modify an existing website, provide the
complete replacement content for the files that need changing.
"""

# --------------------------------------------------
# HOME / HEALTH CHECK
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "service": "AI Website Builder",
        "webhook": "/webhook/momo"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy"
    })


# --------------------------------------------------
# OPENAI WEBSITE GENERATOR
# --------------------------------------------------

def generate_website(user_message):

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        temperature=0.2
    )

    content = response.choices[0].message.content

    # Remove markdown JSON fences if OpenAI returns them
    content = content.strip()

    if content.startswith("```json"):
        content = content[7:]

    if content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    return json.loads(content)


# --------------------------------------------------
# GITHUB FILE WRITER
# --------------------------------------------------

def write_file_to_github(path, content, commit_message):

    try:

        existing_file = repo.get_contents(
            path,
            ref=GITHUB_BRANCH
        )

        repo.update_file(
            path=path,
            message=commit_message,
            content=content,
            sha=existing_file.sha,
            branch=GITHUB_BRANCH
        )

        logging.info("Updated file: %s", path)

        return "updated"

    except Exception:

        repo.create_file(
            path=path,
            message=commit_message,
            content=content,
            branch=GITHUB_BRANCH
        )

        logging.info("Created file: %s", path)

        return "created"


# --------------------------------------------------
# BUILD WEBSITE
# --------------------------------------------------

def build_website(user_message):

    result = generate_website(user_message)

    files = result.get("files", [])

    if not files:
        raise ValueError("AI did not return any files.")

    commit_message = (
        "AI Website Builder: "
        + user_message[:70]
    )

    changed_files = []

    for file in files:

        path = file.get("path")
        content = file.get("content")

        if not path or content is None:
            continue

        # Basic security protection
        if path.startswith("/"):
            raise ValueError("Invalid file path.")

        if ".." in path.split("/"):
            raise ValueError("Unsafe file path.")

        status = write_file_to_github(
            path,
            content,
            commit_message
        )

        changed_files.append({
            "path": path,
            "status": status
        })

    return {
        "message": result.get(
            "message",
            "Website updated successfully."
        ),
        "files": changed_files
    }


# --------------------------------------------------
# MOMO WEBHOOK
# --------------------------------------------------

@app.route("/webhook/momo", methods=["POST"])
def momo_webhook():

    try:

        data = request.get_json(
            silent=True
        )

        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid JSON"
            }), 400

        logging.info(
            "Momo webhook received: %s",
            data
        )

        # --------------------------------------------------
        # Try to extract the customer's message.
        #
        # Different webhook providers may use different
        # JSON structures, so we support several common
        # possibilities.
        # --------------------------------------------------

        user_message = None

        possible_fields = [
            "message",
            "text",
            "body",
            "content",
            "message_text"
        ]

        for field in possible_fields:

            if field in data:
                value = data[field]

                if isinstance(value, str):
                    user_message = value
                    break

        # Nested message object
        if not user_message:

            message_object = data.get("message")

            if isinstance(message_object, dict):

                for field in [
                    "text",
                    "body",
                    "content"
                ]:

                    if field in message_object:

                        value = message_object[field]

                        if isinstance(value, str):
                            user_message = value
                            break

        if not user_message:

            return jsonify({
                "success": False,
                "error": "No message found in webhook payload."
            }), 400

        # --------------------------------------------------
        # BUILD / UPDATE WEBSITE
        # --------------------------------------------------

        result = build_website(
            user_message
        )

        # --------------------------------------------------
        # RESPONSE
        # --------------------------------------------------

        return jsonify({
            "success": True,
            "reply": result["message"],
            "files": result["files"]
        }), 200

    except Exception as e:

        logging.exception(
            "Webhook processing failed"
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# --------------------------------------------------
# RUN SERVER
# --------------------------------------------------

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
