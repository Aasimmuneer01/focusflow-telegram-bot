
import os
import json
import logging
import requests
from flask import Flask, request

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SUPPORT_CHAT_ID = os.environ.get("SUPPORT_CHAT_ID", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
SUPPORT_FILE = "/tmp/focusflow_support.json"

app = Flask(__name__)


def send_message(chat_id, text):
    response = requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=15
    )
    response.raise_for_status()


def load_support():
    try:
        with open(SUPPORT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_support(data):
    with open(SUPPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


@app.route("/", methods=["GET"])
def home():
    return "FocusFlow Telegram Bot is running!"


@app.route("/telegram", methods=["POST"])
def telegram():
    update = request.get_json(silent=True) or {}
    message = update.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text", "").strip()

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
            "/support - Get help\n"
            "/about - About FocusFlow\n"
            "/help - Show commands"
        )

    elif command == "/help":
        reply = (
            "/start - Start the bot\n"
            "/features - Explore features\n"
            "/study - Study assistance\n"
            "/support - Get help\n"
            "/about - About FocusFlow"
        )

    elif command == "/features":
        reply = "FocusFlow helps you organize your study and productivity. 🎯"

    elif command == "/study":
        reply = "What subject are you studying today? 📚"

    elif command == "/support":
        support_users[chat_key] = True
        save_support(support_users)
        reply = (
            "Please describe your FocusFlow issue. 🛠️\n\n"
            "For example: Not installing\n\n"
            "Send /cancel to cancel."
        )

    elif command == "/cancel":
        if support_users.pop(chat_key, None):
            save_support(support_users)
            reply = "Support message cancelled."
        else:
            reply = "There is no active support request."

    elif command == "/about":
        reply = "FocusFlow is your study and productivity companion."

    elif command.startswith("/"):
        reply = "Unknown command. Send /help to see available commands."

    elif support_users.get(chat_key):
        support_users.pop(chat_key, None)
        save_support(support_users)

        if not SUPPORT_CHAT_ID:
            reply = "Sorry, support is temporarily unavailable. Please try again later."
        else:
            try:
                user = message.get("from", {})
                username = user.get("username", "Not provided")
                first_name = user.get("first_name", "Unknown")
                report = (
                    "📩 New FocusFlow Support Request\n\n"
                    f"Name: {first_name}\n"
                    f"Username: @{username}\n"
                    f"Chat ID: {chat_id}\n\n"
                    f"Issue:\n{text}"
                )
                send_message(SUPPORT_CHAT_ID, report)
                reply = (
                    "Thanks! ✅ Your issue has been forwarded "
                    "to the FocusFlow support owner."
                )
            except Exception:
                logging.exception("Failed to forward support request")
                reply = "Sorry, we couldn't forward your issue. Please try again later."

    else:
        reply = "I didn't understand that message. Send /help to see available commands."

    send_message(chat_id, reply)
    return {"ok": True}


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000"))
    )

