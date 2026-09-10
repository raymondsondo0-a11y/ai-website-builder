import os
import json
import hmac
import hashlib
import logging
import threading
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from github import Github

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MOMO_API_KEY = os.getenv("MOMO_API_KEY")
MOMO_WEBHOOK_SECRET = os.getenv("MOMO_WEBHOOK_SECRET")
MOMO_SENDER_ID = os.getenv("MOMO_SENDER_ID")
GITHUB_REPO = os.getenv("GITHUB_REPO", "raymondsondo0-a11y/ai-website-builder")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
MOMO_API_URL = "https://business.momo.tz/api/v3/whatsapp/send"

openai_client = OpenAI(api_key=OPENAI_API_KEY)
github_client = Github(GITHUB_TOKEN)
repo = github_client.get_repo(GITHUB_REPO)

SYSTEM_PROMPT = """
You are an expert autonomous website developer.

Understand the user's website-development request and produce complete website files.

Examples:
- Create a hotel website
- Build a restaurant website
- Add a booking page
- Change the homepage
- Add an admin dashboard
- Make the website responsive
- Add a contact form
- Fix a page

The project is hosted through GitHub and deployed automatically.
Prefer HTML5, CSS3, JavaScript, Bootstrap when useful, and PHP when server-side functionality is required.
Create production-quality, responsive code.

IMPORTANT: Return ONLY valid JSON using this structure:
{
  "message": "short explanation",
  "files": [
    {"path": "index.html", "content": "complete file content"}
  ]
}

Every file must contain COMPLETE content. Never use placeholders such as "put code here", "etc.", "...", or "same as above".
If the user asks to modify an existing website, provide complete replacement content for the files that need changing.
"""

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "service": "AI Website Builder",
        "webhook": "/webhook/momo"
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


def send_whatsapp(recipient, message):
    """Send a WhatsApp text message through Momo Business."""
    if not MOMO_API_KEY:
        logging.error("MOMO_API_KEY is not configured.")
        return False

    if not recipient or not message:
        return False

    payload = {
        "recipient": str(recipient),
        "message": message,
        "message_type": "text"
    }

    if MOMO_SENDER_ID:
        payload["sender_id"] = MOMO_SENDER_ID

    try:
        response = requests.post(
            MOMO_API_URL,
            headers={
                "Authorization": f"Bearer {MOMO_API_KEY}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

        logging.info(
            "Momo outbound response: %s %s",
            response.status_code,
            response.text[:1000]
        )
        return response.ok

    except Exception:
        logging.exception("Failed to send WhatsApp message.")
        return False


def verify_momo_signature(raw_body):
    """Verify Momo X-Signature when MOMO_WEBHOOK_SECRET is configured."""
    if not MOMO_WEBHOOK_SECRET:
        logging.warning(
            "MOMO_WEBHOOK_SECRET is not configured; signature check skipped."
        )
        return True

    provided_signature = request.headers.get("X-Signature", "")
    if not provided_signature:
        return False

    expected_signature = hmac.new(
        MOMO_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(
        provided_signature.lower(),
        expected_signature.lower()
    )


def generate_website(user_message):
    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    return json.loads(content.strip())


def write_file_to_github(path, content, commit_message):
    try:
        existing_file = repo.get_contents(path, ref=GITHUB_BRANCH)
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


def build_website(user_message):
    result = generate_website(user_message)
    files = result.get("files", [])

    if not files:
        raise ValueError("AI did not return any files.")

    commit_message = "AI Website Builder: " + user_message[:70]
    changed_files = []

    for file in files:
        path = file.get("path")
        content = file.get("content")

        if not path or content is None:
            continue
        if path.startswith("/"):
            raise ValueError("Invalid file path.")
        if ".." in path.split("/"):
            raise ValueError("Unsafe file path.")

        status = write_file_to_github(path, content, commit_message)
        changed_files.append({"path": path, "status": status})

    return {
        "message": result.get("message", "Website updated successfully."),
        "files": changed_files
    }


def process_website_request(user_message, recipient):
    """Perform the long AI/GitHub task in the background."""
    try:
        logging.info(
            "Starting website build for %s: %s",
            recipient,
            user_message
        )

        send_whatsapp(
            recipient,
            "⚙️ Nimeanza kazi sasa. AI inaandika website, inaweka files GitHub na kuandaa deployment. Nitakujulisha ikikamilika."
        )

        result = build_website(user_message)
        file_names = [item["path"] for item in result.get("files", [])]
        file_count = len(file_names)
        files_text = ", ".join(file_names[:8])
        if len(file_names) > 8:
            files_text += ", ..."

        send_whatsapp(
            recipient,
            "✅ Tayari mkuu! Website imekamilika.\n\n"
            f"📁 Files zilizotengenezwa: {file_count}\n"
            f"📝 {files_text}\n\n"
            "🚀 GitHub ime-update na deployment imeanza automatically."
        )

        logging.info("Website build completed successfully for %s", recipient)

    except Exception as error:
        logging.exception("Website build failed")
        send_whatsapp(
            recipient,
            "❌ Kuna tatizo wakati wa kutengeneza website yako. "
            "Nimegundua error na nimeisimamisha kwa usalama.\n\n"
            f"Error: {str(error)[:500]}"
        )


@app.route("/webhook/momo", methods=["POST"])
def momo_webhook():
    try:
        raw_body = request.get_data(cache=True)

        if not verify_momo_signature(raw_body):
            logging.warning("Invalid Momo X-Signature.")
            return jsonify({"received": False}), 401

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"received": False, "error": "Invalid JSON"}), 400

        logging.info("Momo webhook received: %s", data)

        event = data.get("event")
        direction = data.get("direction")

        # Only process real incoming customer messages.
        if event != "message.received" or direction == "outbound":
            logging.info(
                "Ignoring webhook event=%s direction=%s",
                event,
                direction
            )
            return jsonify({"received": True}), 200

        user_message = data.get("body")
        sender = data.get("sender")

        if not user_message:
            return jsonify({
                "received": False,
                "error": "No inbound message body found."
            }), 400

        if not sender:
            return jsonify({
                "received": False,
                "error": "No sender found."
            }), 400

        # Immediate reply so the customer knows the AI has started.
        send_whatsapp(
            sender,
            "👋 Nimepokea request yako. Naianza sasa hivi — nitakutumia update nikimaliza."
        )

        # Long-running work happens after the webhook is acknowledged.
        worker = threading.Thread(
            target=process_website_request,
            args=(user_message, sender),
            daemon=True
        )
        worker.start()

        return jsonify({"received": True}), 200

    except Exception as error:
        logging.exception("Webhook processing failed")
        return jsonify({
            "received": False,
            "error": str(error)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
