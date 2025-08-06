import os
import json
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)

# === CONFIG ===
BOT_TOKEN = "7494013782:AAG0BtRIHtS0VIHTwsQUFgEFulzSfKZOw3U"
ADMIN_ID = 6282055190
UPLOAD_DIR = "uploads"
PID_FILE = "pids.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# === PID Storage ===
def load_pids():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r") as f:
            return json.load(f)
    return {}

def save_pids(pids):
    with open(PID_FILE, "w") as f:
        json.dump(pids, f)

# === START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 Upload File", callback_data="upload")],
        [InlineKeyboardButton("📁 View Files", callback_data="view_files")],
        [InlineKeyboardButton("🗑️ Delete All Files", callback_data="delete_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to File Bot!\nSend me .zip, .py, .js, .php files or use options below:",
        reply_markup=reply_markup
    )

# === VIP ===
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📁 View Files", callback_data="view_files")],
            [InlineKeyboardButton("🗑️ Delete All Files", callback_data="delete_all")],
            [InlineKeyboardButton("⬅️ Back", callback_data="upload")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🔐 Admin Panel Access", reply_markup=reply_markup)
    else:
        await update.message.reply_text("❌ Only Admin can use this command!")

# === FILE UPLOAD ===
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    filename = document.file_name

    if not filename.endswith(('.zip', '.py', '.js', '.php')):
        return await update.message.reply_text("❌ Only .zip, .py, .js, .php files allowed.")

    file = await document.get_file()
    file_path = os.path.join(UPLOAD_DIR, filename)
    await file.download_to_drive(file_path)

    keyboard = [
        [InlineKeyboardButton("▶️ Run File", callback_data=f"run:{filename}"),
         InlineKeyboardButton("🗑️ Delete", callback_data=f"delete:{filename}")]
    ]
    await update.message.reply_text(
        f"✅ File `{filename}` uploaded!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === RUN BOT COMMAND ===
async def runbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if len(context.args) != 1:
        return await update.message.reply_text("❗ Usage: /runbot <filename>")

    filename = context.args[0]
    filepath = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(filepath):
        return await update.message.reply_text("❌ File not found.")

    await execute_file(update, filename, user_id)

# === STOP BOT COMMAND ===
async def stopbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if len(context.args) != 1:
        return await update.message.reply_text("❗ Usage: /stopbot <filename>")

    filename = context.args[0]
    pids = load_pids()

    if str(user_id) not in pids or filename not in pids[str(user_id)]:
        return await update.message.reply_text("⚠️ No running process found for this file.")

    pid = pids[str(user_id)][filename]
    try:
        os.kill(pid, 9)
        del pids[str(user_id)][filename]
        if not pids[str(user_id)]:
            del pids[str(user_id)]
        save_pids(pids)
        await update.message.reply_text(f"🛑 {filename} stopped.", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error stopping bot:\n{str(e)}", parse_mode="Markdown")

# === EXECUTE FILE ===
async def execute_file(update, filename, user_id):
    filepath = os.path.join(UPLOAD_DIR, filename)
    pids = load_pids()
    user_str = str(user_id)

    # Limit normal users to 2
    if user_id != ADMIN_ID:
        user_processes = pids.get(user_str, {})
        if len(user_processes) >= 2:
            return await update.message.reply_text("❌ Limit reached. Only 2 bots allowed per user.")

    if filename.endswith(".py"):
        cmd = ["python", filepath]
    elif filename.endswith(".php"):
        cmd = ["php", filepath]
    elif filename.endswith(".js"):
        cmd = ["node", filepath]
    else:
        return await update.message.reply_text("❌ Unsupported file type.")

    try:
        proc = subprocess.Popen(cmd)
        if user_str not in pids:
            pids[user_str] = {}
        pids[user_str][filename] = proc.pid
        save_pids(pids)
        await update.message.reply_text(f"✅ Running {filename} in background.", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to run:\n{str(e)}", parse_mode="Markdown")

# === BUTTON HANDLER ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    data = query.data

    if data == "upload":
        return await query.edit_message_text("📤 Send me .zip, .py, .js, .php files...")

    elif data == "delete_all":
        if user_id != ADMIN_ID:
            return await query.edit_message_text("❌ You are not authorized.")
        for f in os.listdir(UPLOAD_DIR):
            os.remove(os.path.join(UPLOAD_DIR, f))
        return await query.edit_message_text("🗑️ All uploaded files deleted.")

    elif data == "view_files":
        files = os.listdir(UPLOAD_DIR)
        if not files:
            return await query.edit_message_text("📂 No files uploaded.")
        buttons = [
            [InlineKeyboardButton(f"▶️ Run {f}", callback_data=f"run:{f}")]
            for f in files
        ]
        return await query.edit_message_text("📁 Uploaded Files:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("run:"):
        filename = data.split("run:")[1]
        await execute_file(query.message, filename, user_id)

    elif data.startswith("delete:"):
        filename = data.split("delete:")[1]
        path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(path):
            os.remove(path)
            return await query.edit_message_text(f"🗑️ {filename} deleted.", parse_mode="Markdown")
        else:
            return await query.edit_message_text("❌ File not found.")

# === BOT INIT ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("vip", vip))
    app.add_handler(CommandHandler("runbot", runbot))
    app.add_handler(CommandHandler("stopbot", stopbot))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()