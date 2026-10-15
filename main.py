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

SUPPORT_FILE = "/tmp/focusflow_support.json"
TICKETS_FILE = "/tmp/focusflow_tickets.json"

APP_URL = "https://noteshub9.vercel.app"

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
        raise RuntimeError("Telegram message failed")

    return result


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file)


def get_user_details(message):
    user = message.get("from") or {}

    name = " ".join(
        part for part in (
            user.get("first_name", ""),
            user.get("last_name", "")
        ) if part
    ) or "Unknown Person"

    username = user.get("username")
    username = f"@{username}" if username else "Not provided"

    return (
        name,
        username,
        user.get("id", "Unknown"),
        user.get("language_code", "Not provided")
    )


def app_information():
    return (
        "🎯 FOCUSFLOW — STUDY SMARTER\n\n"
        "FocusFlow is a study and productivity app "
        "designed to help you stay organized and focused.\n\n"
        "✨ WHAT YOU CAN EXPLORE\n"
        "📚 Study resources and learning materials\n"
        "📝 Study planning and task organization\n"
        "⏱️ Focus and productivity tools\n"
        "📈 Tools to help manage your study routine\n\n"
        "📲 INSTALL / ACCESS FOCUSFLOW\n"
        f"{APP_URL}\n\n"
        "Open the website and follow the available "
        "instructions to access or install the app.\n\n"
        "🛠️ Need help? Send /support\n"
        "ℹ️ More information: /about"
    )


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

    support_users = load_json(SUPPORT_FILE)
    tickets = load_json(TICKETS_FILE)

    # Owner-only support replies
    if command == "/reply":
        if not SUPPORT_CHAT_ID or chat_key != SUPPORT_CHAT_ID:
            send_message(
                chat_id,
                "⛔ You are not authorized to use this command."
            )
            return {"ok": True}

        parts = text.split(maxsplit=2)

        if len(parts) < 3:
            send_message(
                chat_id,
                "Usage:\n/reply FF-TICKETID Your message here"
            )
            return {"ok": True}

        ticket_id = parts[1].upper()
        reply_text = parts[2]
        ticket = tickets.get(ticket_id)

        if not ticket:
            send_message(
                chat_id,
                "❌ Ticket not found. It may have been lost "
                "after a server restart or redeployment."
            )
            return {"ok": True}

        try:
            send_message(
                ticket["chat_id"],
                "📩 Reply from FocusFlow Support\n\n" + reply_text
            )
            send_message(
                chat_id,
                f"✅ Reply delivered successfully!\nTicket: {ticket_id}"
            )
        except Exception:
            logging.exception("Could not deliver ticket reply")
            send_message(
                chat_id,
                "❌ Reply could not be delivered. "
                "The user may have blocked the bot."
            )

        return {"ok": True}

    if command == "/start":
        support_users.pop(chat_key, None)
        save_json(SUPPORT_FILE, support_users)

        reply = (
            "Welcome to FocusFlow! 🎯\n\n"
            "Your study and productivity companion.\n\n"
            "/app - App information and installation\n"
            "/about - About FocusFlow\n"
            "/features - Explore features\n"
            "/study - Study assistance\n"
            "/support - Report a problem\n"
            "/cancel - Cancel a support request\n"
            "/help - Show commands"
        )

    elif command == "/help":
        reply = (
            "🎯 FOCUSFLOW BOT HELP\n\n"
            "/start - Start the bot\n"
            "/app - App information and installation\n"
            "/about - About FocusFlow\n"
            "/features - Explore features\n"
            "/study - Study assistance\n"
            "/support - Report a problem\n"
            "/cancel - Cancel a support request\n\n"
            "Choose /app to find the FocusFlow website."
        )

    elif command in ("/app", "/install", "/download"):
        reply = app_information()

    elif command == "/about":
        reply = (
            "🎯 ABOUT FOCUSFLOW\n\n"
            "FocusFlow is a study and productivity app "
            "created to help students organize learning "
            "materials, plan tasks, and build better "
            "study routines.\n\n"
            "📲 Website and installation information:\n"
            f"{APP_URL}\n\n"
            "For help with an issue, use /support.\n"
            "For app information, use /app."
        )

    elif command == "/features":
        reply = (
            "✨ FOCUSFLOW FEATURES\n\n"
            "📚 Study resources\n"
            "📝 Task and study organization\n"
            "⏱️ Focus and productivity tools\n"
            "📈 Study routine management\n\n"
            "Available features may depend on the app version.\n"
            "Visit the website for more information:\n"
            f"{APP_URL}"
        )

    elif command == "/study":
        reply = (
            "📚 Ready to study?\n\n"
            "Tell me what subject you're studying today.\n"
            "For app-related problems, use /support."
        )

    elif command == "/support":
        support_users[chat_key] = {
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        save_json(SUPPORT_FILE, support_users)

        reply = (
            "🛠️ FOCUSFLOW SUPPORT\n\n"
            "Please describe the problem you're experiencing.\n"
            "Example: My Maths PDF is not opening.\n\n"
            "Send /cancel to cancel."
        )

    elif command == "/cancel":
        if support_users.pop(chat_key, None) is not None:
            save_json(SUPPORT_FILE, support_users)
            reply = "Your support request was cancelled."
        else:
            reply = "You don't have an active support request."

    elif command.startswith("/"):
        reply = "Unknown command. Send /help to see available commands."

    elif chat_key in support_users:
        support_users.pop(chat_key, None)
        save_json(SUPPORT_FILE, support_users)

        if not SUPPORT_CHAT_ID:
            reply = "Sorry, support is temporarily unavailable."
        else:
            try:
                name, username, user_id, language = get_user_details(message)
                ticket_id = "FF-" + uuid.uuid4().hex[:8].upper()
                timestamp = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                )

                report = (
                    "📩 NEW FOCUSFLOW SUPPORT TICKET\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"Ticket ID: {ticket_id}\n"
                    f"Date: {timestamp}\n\n"
                    "👤 USER DETAILS\n"
                    f"Name: {name}\n"
                    f"Username: {username}\n"
                    f"Telegram User ID: {user_id}\n"
                    f"Chat ID: {chat_id}\n"
                    f"Language: {language}\n\n"
                    "📝 REPORTED ISSUE\n"
                    f"{text}"
                )

                send_message(SUPPORT_CHAT_ID, report)

                tickets[ticket_id] = {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "created_at": timestamp
                }
                save_json(TICKETS_FILE, tickets)

                reply = (
                    "Thanks! ✅ Your support request has been sent.\n\n"
                    f"Ticket ID: {ticket_id}\n"
                    "Keep this ID for reference."
                )

            except Exception:
                logging.exception("Failed to forward support request")
                reply = (
                    "Sorry, we couldn't forward your issue right now. "
                    "Please try again later."
                )

    else:
        reply = (
            "I didn't understand that message.\n"
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
