
import os
import json
import logging
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, request

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SUPPORT_CHAT_ID = os.environ.get("SUPPORT_CHAT_ID", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"

# Temporary support conversation state.
# Render's temporary filesystem may reset on restart.
SUPPORT_FILE = "/tmp/focusflow_support.json"

app = Flask(__name__)


def send_message(chat_id, text):
    response = requests.post(
        f"{API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True
        },
        timeout=15
    )
    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError("Telegram could not send the message")

    return result


def load_support():
    try:
        with open(SUPPORT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_support(data):
    try:
        with open(SUPPORT_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file)
    except OSError:
        logging.exception("Could not save support conversation state")
        raise


def get_user_details(message):
    user = message.get("from") or {}

    first_name = user.get("first_name") or ""
    last_name = user.get("last_name") or ""
    full_name = " ".join(
        part for part in (first_name, last_name) if part
    ) or "Not provided by Telegram"

    username = user.get("username")
    username_display = f"@{username}" if username else "Not provided"

    user_id = user.get("id", "Not provided")
    language = user.get("language_code", "Not provided")

    return full_name, username_display, user_id, language


@app.route("/", methods=["GET"])
def home():
    return "FocusFlow Telegram Bot is running!"


@app.route("/telegram", methods=["POST"])
def telegram():
    update = request.get_json(silent=True) or {}
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    text = (message.get("text") or "").strip()

    if not chat or not text:
        return {"ok": True}

    chat_id = chat["id"]
    chat_key = str(chat_id)
    command = text.split()[0].split("@")[0].lower()

    support_users = load_support()

    if command == "/start":
        support_users.pop(chat_key, None)
        save_support(support_users)

        reply = (
            "Welcome to FocusFlow! 🎯\n\n"
            "Your study and productivity companion.\n\n"
            "/features - Explore FocusFlow\n"
            "/study - Study assistance\n"
            "/support - Report a problem\n"
            "/cancel - Cancel a support request\n"
            "/about - About FocusFlow\n"
            "/help - Show commands"
        )

    elif command == "/help":
        reply = (
            "FocusFlow Commands 🎯\n\n"
            "/start - Start the bot\n"
            "/features - Explore features\n"
            "/study - Study assistance\n"
            "/support - Report a problem\n"
            "/cancel - Cancel a support request\n"
            "/about - About FocusFlow"
        )

    elif command == "/features":
        reply = (
            "FocusFlow helps you organize your study "
            "and productivity. 🎯"
        )

    elif command == "/study":
        reply = "What subject are you studying today? 📚"

    elif command == "/support":
        support_users[chat_key] = {
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        save_support(support_users)

        reply = (
            "🛠️ FocusFlow Support\n\n"
            "Please describe the problem you're experiencing.\n"
            "Example: My PDF is not opening.\n\n"
            "Send /cancel to cancel."
        )

    elif command == "/cancel":
        if support_users.pop(chat_key, None) is not None:
            save_support(support_users)
            reply = "Your support request was cancelled."
        else:
            reply = "You don't have an active support request."

    elif command == "/about":
        reply = "FocusFlow is your study and productivity companion."

    elif command.startswith("/"):
        reply = "Unknown command. Send /help to see available commands."

    elif chat_key in support_users:
        support_users.pop(chat_key, None)
        save_support(support_users)

        if not SUPPORT_CHAT_ID:
            logging.error("SUPPORT_CHAT_ID is not configured")
            reply = (
                "Sorry, support is temporarily unavailable. "
                "Please try again later."
            )
        else:
            try:
                full_name, username, user_id, language = (
                    get_user_details(message)
                )

                ticket_id = uuid.uuid4().hex[:8].upper()
                timestamp = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                )

                report = (
                    "📩 NEW FOCUSFLOW SUPPORT TICKET\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"Ticket ID: FF-{ticket_id}\n"
                    f"Date: {timestamp}\n\n"
                    "👤 USER DETAILS\n"
                    f"Name: {full_name}\n"
                    f"Username: {username}\n"
                    f"Telegram User ID: {user_id}\n"
                    f"Chat ID: {chat_id}\n"
                    f"Language: {language}\n\n"
                    "📝 REPORTED ISSUE\n"
                    f"{text}\n\n"
                    "Reply to this user through the bot "
                    "only if a reply feature is configured."
                )

                send_message(SUPPORT_CHAT_ID, report)

                reply = (
                    "Thanks! ✅ Your support request has been "
                    f"sent to the FocusFlow support owner.\n\n"
                    f"Ticket ID: FF-{ticket_id}\n"
                    "Keep this ID for reference."
                )

                logging.info(
                    "Forwarded support ticket FF-%s for user ID %s",
                    ticket_id,
                    user_id
                )

            except Exception:
                logging.exception("Failed to forward support request")
                reply = (
                    "Sorry, we couldn't forward your issue right now. "
                    "Please try again later."
                )

    else:
        reply = (
            "I didn't understand that message. "
            "Send /help to see available commands."
        )

    try:
        send_message(chat_id, reply)
    except Exception:
        logging.exception("Could not send reply to chat %s", chat_id)

    return {"ok": True}


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000"))
    )

