
import os
import logging
import requests
from flask import Flask, request

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)


def send_message(chat_id, text):
    response = requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=15
    )
    response.raise_for_status()


@app.route("/", methods=["GET"])
def home():
    return "FocusFlow Telegram Bot is running!"


@app.route("/telegram", methods=["POST"])
def telegram():
    update = request.get_json(silent=True) or {}
    message = update.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text", "")

    if not chat or not text:
        return {"ok": True}

    chat_id = chat["id"]
    command = text.split()[0].split("@")[0].lower()

    if command == "/start":
        reply = (
            "Welcome to FocusFlow! 🎯\n\n"
            "Your study and productivity companion.\n\n"
            "Commands:\n"
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
        reply = "FocusFlow helps you organize your study and productivity."
    elif command == "/study":
        reply = "What subject are you studying today?"
    elif command == "/support":
        reply = "Please describe your FocusFlow issue."
    elif command == "/about":
        reply = "FocusFlow is your study and productivity companion."
    else:
        reply = "Unknown command. Send /help to see available commands."

    send_message(chat_id, reply)
    return {"ok": True}


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000"))
    )

