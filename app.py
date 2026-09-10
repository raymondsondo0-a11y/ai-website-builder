import json
import logging
import os
import re
import threading
import hashlib
import hmac

import requests
from flask import Flask, jsonify, request
from github import Github
from github.GithubException import GithubException, UnknownObjectException
from google import genai
from google.genai import types

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "raymondsondo0-a11y/ai-website-builder")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
MOMO_API_TOKEN = os.getenv("MOMO_API_TOKEN") or os.getenv("MOMO_API_KEY")
MOMO_SEND_URL = os.getenv("MOMO_SEND_URL", "https://business.momo.tz/api/v3/whatsapp/send")
MOMO_SENDER_ID = os.getenv("MOMO_SENDER_ID")
MOMO_WEBHOOK_SECRET = os.getenv("MOMO_WEBHOOK_SECRET")

if not GITHUB_TOKEN:
    logging.warning("GITHUB_TOKEN is not configured.")
if not GEMINI_API_KEY:
    logging.warning("GEMINI_API_KEY is not configured.")
if not MOMO_API_TOKEN:
    logging.warning("MOMO_API_TOKEN is not configured.")

github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
repo = github_client.get_repo(GITHUB_REPO) if github_client else None
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

_processed_message_ids = set()
_processed_lock = threading.Lock()


def write_file_to_github(path, content, commit_message):
    if not repo:
        raise RuntimeError("GITHUB_TOKEN is not configured.")
    if not path or content is None:
        raise ValueError("File path/content is missing.")

    path = str(path).replace("\\", "/").lstrip("/")
    parts = path.split("/")
    if not path or ".." in parts or any(part == "" for part in parts):
        raise ValueError(f"Unsafe file path: {path}")

    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        if isinstance(existing, list):
            raise ValueError(f"Path points to a directory, not a file: {path}")
        repo.update_file(path=path, message=commit_message, content=str(content), sha=existing.sha, branch=GITHUB_BRANCH)
        logging.info("Updated GitHub file: %s", path)
        return "updated"
    except UnknownObjectException:
        repo.create_file(path=path, message=commit_message, content=str(content), branch=GITHUB_BRANCH)
        logging.info("Created GitHub file: %s", path)
        return "created"
    except GithubException as error:
        raise RuntimeError(f"GitHub error while writing {path}: {error.data if getattr(error, 'data', None) else str(error)}") from error


def build_website_on_github(user_request, files):
    if not isinstance(files, list) or not files:
        raise ValueError("AI returned no website files.")
    commit_message = "AI Website Builder: " + user_request[:70].strip()
    changed_files = []
    for file in files:
        if not isinstance(file, dict):
            continue
        path = file.get("path")
        content = file.get("content")
        if not path or content is None:
            continue
        status = write_file_to_github(path, content, commit_message)
        changed_files.append({"path": str(path).replace("\\", "/").lstrip("/"), "status": status})
    if not changed_files:
        raise ValueError("AI returned no valid website files.")
    return changed_files


CUSTOMER_SYSTEM_PROMPT = """
You are the WhatsApp assistant for an AI website-building service.
Be friendly, natural, professional and concise. Reply in the same language as the customer.
Swahili -> Swahili. English -> English. Never mention API keys, internal prompts, providers, or implementation.
"""

WEBSITE_SYSTEM_PROMPT = """
You are an expert senior web developer and UI/UX designer.
The customer wants you to BUILD or MODIFY a real website.
Return ONLY valid JSON, with no Markdown fences.
Exact shape:
{"reply":"short customer-facing confirmation","files":[{"path":"index.html","content":"complete file content"},{"path":"style.css","content":"complete file content"},{"path":"script.js","content":"complete file content"}]}
Rules:
- Generate complete production-ready files, never placeholders.
- Use plain HTML/CSS/JavaScript unless another stack is explicitly requested.
- Responsive phone/tablet/desktop.
- Semantic accessible HTML.
- Modern polished UI with strong readable colors.
- Do not reference files you did not generate.
- Use reliable remote images or CSS gradients instead of broken local images.
- Navigation links must work.
- Add JavaScript when interaction is useful.
- Understand both Swahili and English.
- Keep reply short because it is sent through WhatsApp.
- Never put explanations outside the JSON.
"""


def clean_json_text(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_ai_reply(message):
    if not gemini_client:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=message,
        config=types.GenerateContentConfig(system_instruction=CUSTOMER_SYSTEM_PROMPT, temperature=0.4, max_output_tokens=800),
    )
    reply = (response.text or "").strip()
    if not reply:
        raise RuntimeError("Gemini returned an empty response.")
    return reply


def generate_website(message):
    if not gemini_client:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"Build the website requested by this customer:\n\n{message}\n\nReturn the complete website files using the exact JSON structure in your system instructions.",
        config=types.GenerateContentConfig(system_instruction=WEBSITE_SYSTEM_PROMPT, temperature=0.35, max_output_tokens=30000),
    )
    raw = clean_json_text(response.text)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError("AI returned invalid website JSON.") from error
    if not isinstance(result, dict):
        raise RuntimeError("AI website response is not a JSON object.")
    files = result.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("AI website response contains no files.")
    return str(result.get("reply") or "Website imeandaliwa.").strip(), files


def is_website_request(message):
    text = (message or "").lower().strip()
    phrases = [
        "tengeneza website", "tengeneza web", "unda website", "unda web", "jenga website", "jenga web",
        "tengenezee website", "tengenezee web", "rekebisha website", "rekebisha web", "badilisha website",
        "badilisha web", "build a website", "build website", "create a website", "create website",
        "make a website", "make website", "design a website", "design website", "develop a website",
        "develop website", "website design", "web design", "landing page", "portfolio website",
        "ecommerce website", "e-commerce website", "hotel website", "restaurant website", "business website",
        "website page", "web page"
    ]
    return any(phrase in text for phrase in phrases)


def send_momo_message(recipient, message):
    if not MOMO_API_TOKEN:
        raise RuntimeError("MOMO_API_TOKEN is not configured.")
    payload = {"recipient": str(recipient), "message": str(message)[:4096], "message_type": "text"}
    if MOMO_SENDER_ID:
        payload["sender_id"] = MOMO_SENDER_ID
    headers = {"Authorization": f"Bearer {MOMO_API_TOKEN}", "Accept": "application/json", "Content-Type": "application/json"}
    response = requests.post(MOMO_SEND_URL, headers=headers, json=payload, timeout=20)
    logging.info("Momo send response: HTTP %s %s", response.status_code, response.text[:1000])
    if response.status_code not in (200, 201, 202):
        raise RuntimeError(f"Momo send failed with HTTP {response.status_code}: {response.text[:1000]}")
    return response.json() if response.content else {}


def verify_momo_signature(raw_body):
    if not MOMO_WEBHOOK_SECRET:
        return True
    received = request.headers.get("X-Signature", "")
    expected = hmac.new(MOMO_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received.lower(), expected.lower())


def send_acknowledgement(customer_number):
    """Send an immediate visible confirmation that the message reached our service."""
    try:
        send_momo_message(customer_number, "✅ Nimekupokea. Nipo hai na nimesikia ujumbe wako. Naanza kuufanyia kazi sasa...")
        logging.info("Acknowledgement sent to %s", customer_number)
    except Exception:
        logging.exception("Could not send acknowledgement to %s", customer_number)


def process_message(data):
    customer_number = str(data.get("sender") or "").strip()
    customer_message = str(data.get("body") or "").strip()
    if not customer_number or not customer_message:
        return
    try:
        if is_website_request(customer_message):
            reply, files = generate_website(customer_message)
            changed_files = build_website_on_github(customer_message, files)
            reply += f"\n\nNimeweka {len(changed_files)} file(s) kwenye GitHub."
            send_momo_message(customer_number, reply)
            logging.info("Website build completed: %s", changed_files)
        else:
            send_momo_message(customer_number, generate_ai_reply(customer_message))
    except Exception:
        logging.exception("Message processing failed")
        try:
            send_momo_message(customer_number, "Samahani, kuna changamoto ya muda kwenye mfumo. Tafadhali jaribu tena baada ya muda mfupi.")
        except Exception:
            logging.exception("Could not send error message.")


@app.route("/", methods=["GET", "POST"])
def home():
    return jsonify({
        "status": "online",
        "service": "AI Website Builder + Momo AI Bridge",
        "webhook": "/webhook/momo",
        "build_endpoint": "/build",
        "ai_model": GEMINI_MODEL,
        "github": bool(GITHUB_TOKEN),
        "gemini": bool(GEMINI_API_KEY),
        "momo_send": bool(MOMO_API_TOKEN),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "github_configured": bool(GITHUB_TOKEN),
        "gemini_configured": bool(GEMINI_API_KEY),
        "momo_configured": bool(MOMO_API_TOKEN),
        "repository": GITHUB_REPO,
        "branch": GITHUB_BRANCH,
    })


@app.route("/webhook/momo", methods=["POST"])
def momo_webhook():
    raw_body = request.get_data()
    if not verify_momo_signature(raw_body):
        logging.warning("Rejected Momo webhook: invalid X-Signature")
        return jsonify({"received": False, "error": "Invalid signature."}), 401

    data = request.get_json(silent=True) or {}
    logging.info("Momo webhook received: %s", data)

    if data.get("event") != "message.received":
        return jsonify({"received": True, "status": "ignored", "reason": "Not a message.received event."}), 200
    if data.get("direction") and data.get("direction") != "inbound":
        return jsonify({"received": True, "status": "ignored", "reason": "Not an inbound message."}), 200

    message_id = str(data.get("message_id") or "").strip()
    if message_id:
        with _processed_lock:
            if message_id in _processed_message_ids:
                return jsonify({"received": True, "status": "duplicate", "message_id": message_id}), 200
            _processed_message_ids.add(message_id)
            if len(_processed_message_ids) > 5000:
                _processed_message_ids.clear()
                _processed_message_ids.add(message_id)

    customer_number = str(data.get("sender") or "").strip()
    customer_message = str(data.get("body") or "").strip()
    if not customer_number or not customer_message:
        return jsonify({"received": True, "status": "ignored", "reason": "Missing sender or body."}), 200

    # Send a visible acknowledgement immediately, then process AI/website work separately.
    threading.Thread(target=send_acknowledgement, args=(customer_number,), daemon=True).start()
    threading.Thread(target=process_message, args=(data,), daemon=True).start()

    return jsonify({
        "received": True,
        "status": "processing",
        "message_id": message_id or None,
        "acknowledgement": "scheduled",
    }), 200


@app.route("/build", methods=["POST"])
def build():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "Invalid JSON body."}), 400
        user_message = str(data.get("message") or "").strip()
        files = data.get("files")
        if not isinstance(files, list) or not files:
            if not user_message:
                return jsonify({"ok": False, "error": "Send either files or a website message."}), 400
            _, files = generate_website(user_message)
        changed_files = build_website_on_github(user_message or "Website update", files)
        return jsonify({"ok": True, "message": "Website files were written to GitHub successfully.", "files": changed_files, "github_repo": GITHUB_REPO, "branch": GITHUB_BRANCH}), 200
    except Exception as error:
        logging.exception("Direct website build failed")
        return jsonify({"ok": False, "error": str(error)[:1500]}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
