import hashlib
import hmac
import json
import logging
import os
import re
import threading

import requests
from flask import Flask, jsonify, request
from github import Github
from github.GithubException import GithubException, UnknownObjectException
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "raymondsondo0-a11y/ai-website-builder")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
MOMO_API_TOKEN = os.getenv("MOMO_API_TOKEN") or os.getenv("MOMO_API_KEY")
MOMO_SEND_URL = os.getenv("MOMO_SEND_URL", "https://business.momo.tz/api/v3/whatsapp/send")
MOMO_SENDER_ID = os.getenv("MOMO_SENDER_ID")
MOMO_WEBHOOK_SECRET = os.getenv("MOMO_WEBHOOK_SECRET")

if not GITHUB_TOKEN:
    logging.warning("[CONFIG] GITHUB_TOKEN is not configured.")
if not OPENAI_API_KEY:
    logging.warning("[CONFIG] OPENAI_API_KEY is not configured.")
if not MOMO_API_TOKEN:
    logging.warning("[CONFIG] MOMO_API_TOKEN is not configured.")
if not MOMO_SENDER_ID:
    logging.warning("[CONFIG] MOMO_SENDER_ID is not configured. Using API default sender if supported.")

github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
repo = github_client.get_repo(GITHUB_REPO) if github_client else None
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

_processed_message_ids = set()
_processed_lock = threading.Lock()


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


def write_file_to_github(path, content, commit_message):
    if not repo:
        raise RuntimeError("GITHUB_TOKEN is not configured.")
    if not path or content is None:
        raise ValueError("File path/content is missing.")

    path = str(path).replace("\\", "/").lstrip("/")
    parts = path.split("/")
    if ".." in parts or any(part == "" for part in parts):
        raise ValueError(f"Unsafe file path: {path}")

    logging.info("[GITHUB] Writing file: %s", path)

    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        if isinstance(existing, list):
            raise ValueError(f"Path points to a directory: {path}")
        repo.update_file(
            path=path,
            message=commit_message,
            content=str(content),
            sha=existing.sha,
            branch=GITHUB_BRANCH,
        )
        logging.info("[GITHUB] Updated successfully: %s", path)
        return "updated"
    except UnknownObjectException:
        repo.create_file(
            path=path,
            message=commit_message,
            content=str(content),
            branch=GITHUB_BRANCH,
        )
        logging.info("[GITHUB] Created successfully: %s", path)
        return "created"
    except GithubException as error:
        details = error.data if getattr(error, "data", None) else str(error)
        logging.error("[GITHUB] FAILED writing %s: %s", path, details)
        raise RuntimeError(f"GitHub error while writing {path}: {details}") from error


def build_website_on_github(user_request, files):
    if not isinstance(files, list) or not files:
        raise ValueError("AI returned no website files.")

    logging.info("[GITHUB] Starting website save. Files returned by AI: %s", len(files))
    commit_message = "AI Website Builder: " + user_request[:70].strip()
    changed_files = []

    for file in files:
        if not isinstance(file, dict):
            logging.warning("[GITHUB] Skipping invalid file object returned by AI.")
            continue
        path = file.get("path")
        content = file.get("content")
        if not path or content is None:
            logging.warning("[GITHUB] Skipping file with missing path/content.")
            continue
        status = write_file_to_github(path, content, commit_message)
        changed_files.append({"path": str(path).replace("\\", "/").lstrip("/"), "status": status})

    if not changed_files:
        raise ValueError("AI returned no valid website files.")
    logging.info("[GITHUB] Website save completed. Changed files: %s", changed_files)
    return changed_files


def clean_json_text(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_ai_reply(message):
    if not openai_client:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    logging.info("[AI] Starting normal chat generation with OpenAI. Model=%s", OPENAI_MODEL)
    response = openai_client.responses.create(
        model=OPENAI_MODEL,
        instructions=CUSTOMER_SYSTEM_PROMPT,
        input=message,
        max_output_tokens=800,
    )
    reply = (response.output_text or "").strip()
    if not reply:
        raise RuntimeError("OpenAI returned an empty response.")
    logging.info("[AI] Normal chat generation completed with OpenAI.")
    return reply


def generate_website(message):
    if not openai_client:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    logging.info("[AI] Starting website generation with OpenAI. Model=%s", OPENAI_MODEL)
    response = openai_client.responses.create(
        model=OPENAI_MODEL,
        instructions=WEBSITE_SYSTEM_PROMPT,
        input=(
            "Build the website requested by this customer:\n\n"
            f"{message}\n\n"
            "Return the complete website files using the exact JSON structure in your system instructions."
        ),
        max_output_tokens=30000,
    )

    raw = clean_json_text(response.output_text)
    logging.info("[AI] OpenAI website response received. Parsing JSON.")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as error:
        logging.error("[AI] FAILED: invalid JSON returned by OpenAI.")
        raise RuntimeError("AI returned invalid website JSON.") from error

    if not isinstance(result, dict):
        raise RuntimeError("AI website response is not a JSON object.")
    files = result.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("AI website response contains no files.")

    logging.info("[AI] Website generation completed with OpenAI. %s file(s) returned.", len(files))
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

    payload = {
        "recipient": str(recipient),
        "message": str(message)[:4096],
        "message_type": "text",
    }
    if MOMO_SENDER_ID:
        payload["sender_id"] = MOMO_SENDER_ID

    headers = {
        "Authorization": f"Bearer {MOMO_API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    logging.info("[MOMO] Sending message to %s", recipient)
    try:
        response = requests.post(MOMO_SEND_URL, headers=headers, json=payload, timeout=20)
    except requests.RequestException as error:
        logging.error("[MOMO] FAILED: network error: %s", error)
        raise RuntimeError(f"Momo network error: {error}") from error

    logging.info("[MOMO] Send response: HTTP %s %s", response.status_code, response.text[:1000])
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
    try:
        send_momo_message(customer_number, "✅ Nimekupokea. Nipo hai na nimesikia ujumbe wako. Naanza kuufanyia kazi sasa...")
        logging.info("[MOMO] Acknowledgement sent to %s", customer_number)
    except Exception:
        logging.exception("[MOMO] Could not send acknowledgement to %s", customer_number)


def deployment_workflow_exists():
    if not repo:
        return False
    for path in [
        ".github/workflows/deploy.yml",
        ".github/workflows/deploy-infinityfree.yml",
        ".github/workflows/infinityfree.yml",
    ]:
        try:
            repo.get_contents(path, ref=GITHUB_BRANCH)
            return True
        except Exception:
            continue
    return False


def friendly_processing_error(error):
    message = str(error or "").lower()
    if "openai" in message or "ai returned" in message:
        return "⚠️ Nimepata tatizo kwenye hatua ya AI wakati wa kutengeneza website. Hakuna files zilizothibitishwa kuwa zimekamilika. Tafadhali jaribu tena."
    if "github" in message or "github_token" in message:
        return "⚠️ Website imetengenezwa na AI, lakini nimekwama wakati wa kuiweka GitHub. Nimehifadhi error kwenye system logs kwa ajili ya troubleshooting."
    if "momo" in message:
        return "⚠️ Kazi imefanyika lakini nimepata tatizo wakati wa kutuma majibu kupitia WhatsApp. Tafadhali jaribu tena."
    return "⚠️ Nimepata tatizo wakati wa kuendelea na kazi yako. Nimehifadhi hatua iliyoshindikana kwenye system logs. Tafadhali jaribu tena."


def process_message(data):
    customer_number = str(data.get("sender") or "").strip()
    customer_message = str(data.get("body") or "").strip()
    message_id = str(data.get("message_id") or "").strip()

    if not customer_number or not customer_message:
        logging.warning("[PROCESS] Missing sender or body. message_id=%s", message_id)
        return

    logging.info("[PROCESS] START message_id=%s customer=%s website_request=%s", message_id, customer_number, is_website_request(customer_message))

    try:
        if is_website_request(customer_message):
            logging.info("[PROCESS] STEP 1/4: Website request detected.")
            logging.info("[PROCESS] STEP 2/4: Sending request to OpenAI.")
            reply, files = generate_website(customer_message)

            logging.info("[PROCESS] STEP 3/4: Saving generated files to GitHub.")
            changed_files = build_website_on_github(customer_message, files)
            workflow_ready = deployment_workflow_exists()
            logging.info("[DEPLOY] GitHub files saved. InfinityFree workflow configured=%s", workflow_ready)

            if workflow_ready:
                reply += f"\n\n✅ Nimeweka {len(changed_files)} file(s) kwenye GitHub. GitHub Actions imeanzishiwa deployment kwenda InfinityFree."
            else:
                reply += f"\n\n✅ Nimeweka {len(changed_files)} file(s) kwenye GitHub. Lakini InfinityFree deployment workflow haijaonekana kwenye repository bado."

            logging.info("[PROCESS] STEP 4/4: Sending final website status to customer.")
            send_momo_message(customer_number, reply)
            logging.info("[PROCESS] SUCCESS website build message_id=%s files=%s", message_id, changed_files)
        else:
            logging.info("[PROCESS] Normal chat request detected. Starting OpenAI.")
            reply = generate_ai_reply(customer_message)
            send_momo_message(customer_number, reply)
            logging.info("[PROCESS] SUCCESS normal chat message_id=%s", message_id)

    except Exception as error:
        logging.exception("[PROCESS] FAILED message_id=%s customer=%s", message_id, customer_number)
        error_message = friendly_processing_error(error)
        logging.error("[PROCESS] Customer error message: %s", error_message)
        try:
            send_momo_message(customer_number, error_message)
            logging.info("[PROCESS] Error notification sent to customer.")
        except Exception:
            logging.exception("[PROCESS] Could not send customer error notification.")


def handle_momo_webhook():
    raw_body = request.get_data()
    if not verify_momo_signature(raw_body):
        logging.warning("[WEBHOOK] Rejected Momo webhook: invalid X-Signature")
        return jsonify({"received": False, "error": "Invalid signature."}), 401

    data = request.get_json(silent=True) or {}
    logging.info("[WEBHOOK] Momo webhook received: %s", data)
    if not isinstance(data, dict):
        return jsonify({"received": False, "error": "Invalid JSON payload."}), 400

    if data.get("event") != "message.received":
        return jsonify({"received": True, "status": "ignored", "reason": "Not a message.received event."}), 200
    if data.get("direction") and data.get("direction") != "inbound":
        return jsonify({"received": True, "status": "ignored", "reason": "Not an inbound message."}), 200

    message_id = str(data.get("message_id") or "").strip()
    if message_id:
        with _processed_lock:
            if message_id in _processed_message_ids:
                logging.info("[WEBHOOK] Duplicate Momo message ignored: %s", message_id)
                return jsonify({"received": True, "status": "duplicate", "message_id": message_id}), 200
            _processed_message_ids.add(message_id)
            if len(_processed_message_ids) > 5000:
                _processed_message_ids.clear()
                _processed_message_ids.add(message_id)

    customer_number = str(data.get("sender") or "").strip()
    customer_message = str(data.get("body") or "").strip()
    if not customer_number or not customer_message:
        logging.warning("[WEBHOOK] Missing sender/body. payload=%s", data)
        return jsonify({"received": True, "status": "ignored", "reason": "Missing sender or body."}), 200

    logging.info("[WEBHOOK] ACCEPTED message_id=%s sender=%s body_length=%s", message_id, customer_number, len(customer_message))
    threading.Thread(target=send_acknowledgement, args=(customer_number,), daemon=True).start()
    threading.Thread(target=process_message, args=(data,), daemon=True).start()

    return jsonify({"received": True, "status": "processing", "message_id": message_id or None, "acknowledgement": "scheduled"}), 200


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        return handle_momo_webhook()
    return jsonify({
        "status": "online",
        "service": "AI Website Builder + Momo AI Bridge",
        "webhook": "/webhook/momo",
        "build_endpoint": "/build",
        "ai_model": OPENAI_MODEL,
        "github": bool(GITHUB_TOKEN),
        "openai": bool(OPENAI_API_KEY),
        "momo_send": bool(MOMO_API_TOKEN),
        "infinityfree_workflow": deployment_workflow_exists(),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "github_configured": bool(GITHUB_TOKEN),
        "openai_configured": bool(OPENAI_API_KEY),
        "momo_configured": bool(MOMO_API_TOKEN),
        "repository": GITHUB_REPO,
        "branch": GITHUB_BRANCH,
        "infinityfree_workflow": deployment_workflow_exists(),
    })


@app.route("/webhook/momo", methods=["POST"])
@app.route("/webhook/momo/", methods=["POST"])
def momo_webhook():
    return handle_momo_webhook()


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
        return jsonify({
            "ok": True,
            "message": "Website files were written to GitHub successfully.",
            "files": changed_files,
            "github_repo": GITHUB_REPO,
            "branch": GITHUB_BRANCH,
            "infinityfree_workflow": deployment_workflow_exists(),
        }), 200
    except Exception as error:
        logging.exception("[BUILD] Direct website build failed")
        return jsonify({"ok": False, "error": str(error)[:1500]}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
