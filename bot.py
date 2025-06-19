import logging
import os
import asyncio
from telegram import Update, Document
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
from utils.file_parser import parse_credentials_file
from automation.signup_playwright import automate_signup_playwright
from datetime import datetime

ASK_FOR_FILE = 1
user_signup_count = {}

# Set your tokens here
TELEGRAM_BOT_TOKEN = "7713625659:AAENH1XKYd7cLscbkKtuXGJ7ITcDzq0h6R4"

# Directory for temporary files
TEMP_DIR = "/data/data/com.termux/files/home/telegram_signup_bot_tmp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to the Beast Signup Bot!\n"
        "Send /signup <number> to start a batch signup.\n"
        "Example: /signup 5"
    )

async def signup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /signup <number>")
        return ConversationHandler.END
    signup_count = int(args[0])
    if signup_count < 1 or signup_count > 100:
        await update.message.reply_text("Please choose a number between 1 and 100.")
        return ConversationHandler.END
    user_signup_count[update.effective_user.id] = signup_count
    await update.message.reply_text(
        "Please send your credentials file.\n"
        "Each line must be: gmail@example.com:password"
    )
    return ASK_FOR_FILE

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document: Document = update.message.document
    if not document:
        await update.message.reply_text("Upload the credentials file.")
        return ASK_FOR_FILE
    file = await document.get_file()
    path = os.path.join(TEMP_DIR, f"{document.file_unique_id}.txt")
    await file.download_to_drive(path)
    try:
        creds = parse_credentials_file(path)
        signup_count = user_signup_count.get(update.effective_user.id, len(creds))
        creds = creds[:signup_count]
        if not creds:
            await update.message.reply_text("No valid credentials found in file.")
            return ConversationHandler.END
        await update.message.reply_text(
            f"Processing {len(creds)} accounts. You will get progress updates."
        )
        asyncio.create_task(process_accounts(update, creds))
    except Exception as e:
        logger.error("File parse error: %s", e)
        await update.message.reply_text("Failed to parse file. Please check the format.")
    finally:
        try: os.remove(path)
        except Exception: pass
    return ConversationHandler.END

async def process_accounts(update: Update, creds):
    user_id = update.effective_user.id
    total = len(creds)
    successes, failures = [], []
    await update.message.reply_text(f"🔥 Starting signup for {total} accounts...")
    for idx, cred in enumerate(creds):
        email = cred["email"]
        try:
            await update.message.reply_text(f"⏳ [{idx+1}/{total}] Processing: {email}")
            status, reason = await automate_signup_playwright(cred)
            if status:
                successes.append(email)
            else:
                failures.append((email, reason))
                await update.message.reply_text(f"❌ {email}: {reason}")
        except Exception as e:
            failures.append((email, f"Exception: {e}"))
            await update.message.reply_text(f"❌ {email}: Exception {e}")
    summary = (
        f"✅ Success: {len(successes)}\n"
        f"❌ Failed: {len(failures)}\n"
        "Success:\n" + "\n".join(successes)[:300] +
        ("\n...truncated..." if len(successes) > 10 else "") +
        "\n\nFailures:\n" + "\n".join([f"{e}: {r}" for e, r in failures])[:300]
    )
    await update.message.reply_text("🏁 Batch complete!\n" + summary)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("signup", signup_command)],
        states={ASK_FOR_FILE: [MessageHandler(filters.Document.ALL, receive_file)]},
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    logger.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
