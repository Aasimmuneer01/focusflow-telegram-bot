
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

app = Flask(__name__)


def send_message(chat_id, text):
    response = requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
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

    # Only the configured support owner can send replies.
    if command == "/reply":
        if not SUPPORT_CHAT_ID or chat_key != SUPPORT_CHAT_ID:
            send_message(chat_id, "⛔ You are not authorized to use this command.")
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
                "❌ Ticket not found.\n"
                "It may have been lost after a server restart."
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
            "/features - Explore features\n"
            "/study - Study assistance\n"
            "/support - Report a problem\n"
            "/cancel - Cancel support request\n"
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
            "/cancel - Cancel support request\n"
            "/about - About FocusFlow"
        )

    elif command == "/features":
        reply = "FocusFlow helps you organize your studies and productivity. 🎯"

    elif command == "/study":
        reply = "What subject are you studying today? 📚"

    elif command == "/support":
        support_users[chat_key] = {
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        save_json(SUPPORT_FILE, support_users)

        reply = (
            "🛠️ FocusFlow Support\n\n"
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

    elif command == "/about":
        reply = "FocusFlow is your study and productivity companion."

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

