import os
import json
import time
import uuid
import asyncio
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= VARIABLES =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

BOT_NAME = os.getenv("BOT_NAME", "LegendX Info Bot")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@captainpapaj1")

NUM_API = os.getenv("NUM_API")
TG_API = os.getenv("TG_API")
VEH_API = os.getenv("VEH_API")
UPI_API = os.getenv("UPI_API")
INSTA_API = os.getenv("INSTA_API")
FAM_API = os.getenv("FAM_API")

USAGE_FILE = "usage.json"
PREMIUM_FILE = "premium.json"
USERS_FILE = "users.json"
GC_FILE = "approved_gc.json"

CACHE = {}

# ================= FILE UTILS =================

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ================= USER DATABASE =================

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def add_user(user_id):

    users = load_users()

    if user_id not in users:
        users.append(user_id)
        save_users(users)

# ================= GROUP DATABASE =================

def load_gc():
    try:
        with open(GC_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_gc(groups):
    with open(GC_FILE, "w") as f:
        json.dump(groups, f, indent=2)

# ================= DAILY LIMIT =================

def check_daily_limit(user_id):

    data = load_json(USAGE_FILE)

    today = int(time.time() // 86400)
    user = str(user_id)

    if user not in data:
        data[user] = {"day": today, "count": 1}
        save_json(USAGE_FILE, data)
        return True

    if data[user]["day"] != today:
        data[user] = {"day": today, "count": 1}
        save_json(USAGE_FILE, data)
        return True

    if data[user]["count"] >= 3:
        return False

    data[user]["count"] += 1
    save_json(USAGE_FILE, data)

    return True

# ================= PREMIUM SYSTEM =================

def load_premium():
    return load_json(PREMIUM_FILE)

def save_premium(data):
    save_json(PREMIUM_FILE, data)

def is_premium(user_id):

    data = load_premium()
    user = str(user_id)

    if user not in data:
        return False

    expire = data[user]["expire"]

    if time.time() > expire:
        del data[user]
        save_premium(data)
        return False

    return True

def get_remaining(user_id):

    data = load_premium()
    user = str(user_id)

    if user not in data:
        return None

    expire = data[user]["expire"]
    remaining = expire - time.time()

    if remaining <= 0:
        return None

    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)

    return days, hours

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    add_user(user_id)

    premium = get_remaining(user_id)

    if premium:
        days, hours = premium
        status = f"⭐ Premium Active\n⏳ Remaining: {days}d {hours}h"
    else:
        status = "🆓 Free User\nLimit: 3 requests/day"

    keyboard = [
        [InlineKeyboardButton("💳 Buy Premium", url=f"https://t.me/{OWNER_USERNAME.replace('@','')}")]
    ]

    await update.message.reply_text(
f"""
🔎 {BOT_NAME}

{status}

Commands

/num NUMBER
/info TG_ID
/veh VEHICLE_NO
/upi UPI_ID
/insta USERNAME
/fam MOBILE

Owner: {OWNER_USERNAME}
""",
reply_markup=InlineKeyboardMarkup(keyboard)
)

# ================= PREMIUM STATUS =================

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):

    remain = get_remaining(update.effective_user.id)

    if not remain:
        await update.message.reply_text(
            f"❌ You are not premium.\nContact {OWNER_USERNAME}"
        )
        return

    days, hours = remain

    await update.message.reply_text(
f"""
⭐ Premium Status

Remaining:
{days} days {hours} hours
"""
)

# ================= BUY =================

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("👑 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@','')}")]
    ]

    await update.message.reply_text(
"""
⭐ Premium Access

Unlimited requests
Priority API access

Price: ₹200 / month
""",
reply_markup=InlineKeyboardMarkup(keyboard)
)

# ================= ADD PREMIUM =================

async def addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage:\n/addpremium USER_ID DAYS")
        return

    user = context.args[0]
    days = int(context.args[1])

    expire = time.time() + days*86400

    data = load_premium()

    data[user] = {"expire": expire}

    save_premium(data)

    await update.message.reply_text("✅ Premium added")

# ================= BROADCAST =================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    message = " ".join(context.args)

    users = load_users()

    sent = 0

    for user in users:

        try:
            await context.bot.send_message(user, message)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass

    await update.message.reply_text(f"Broadcast sent to {sent} users.")

# ================= APPROVE GC =================

async def approvegc(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    chat = update.effective_chat

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ This command must be used in a group.")
        return

    groups = load_gc()

    if chat.id not in groups:
        groups.append(chat.id)
        save_gc(groups)

    await update.message.reply_text("✅ This group has been approved.")
    
# ================= API CALL =================

async def call_api(update, api_url, value):

    user_id = update.effective_user.id
    chat = update.effective_chat

    # ---- LIMIT CHECK ----
    limit_needed = True

    # Premium users -> no limit
    if is_premium(user_id):
        limit_needed = False

    # Approved groups -> no limit
    if chat.type in ["group", "supergroup"]:
        groups = load_gc()
        if chat.id in groups:
            limit_needed = False

    # Apply daily limit only if needed
    if limit_needed:
        if not check_daily_limit(user_id):
            await update.message.reply_text(
f"""
🚫 Daily limit reached

Upgrade to premium.

Owner: {OWNER_USERNAME}
"""
            )
            return

    # ---- API REQUEST ----
    try:

        r = requests.get(api_url.format(value), timeout=15)
        data = r.json()

        uid = str(uuid.uuid4())
        CACHE[uid] = data

        preview = json.dumps(data, indent=2)[:3500]

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Full JSON", callback_data=f"json_{uid}")]
        ])

        await update.message.reply_text(
            f"```\n{preview}\n```",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except:
        await update.message.reply_text("API Error")
        
# ================= COMMAND WRAPPERS =================

async def num(update, context):
    if context.args: await call_api(update, NUM_API, context.args[0])

async def info(update, context):
    if context.args: await call_api(update, TG_API, context.args[0])

async def veh(update, context):
    if context.args: await call_api(update, VEH_API, context.args[0])

async def upi(update, context):
    if context.args: await call_api(update, UPI_API, context.args[0])

async def insta(update, context):
    if context.args: await call_api(update, INSTA_API, context.args[0])

async def fam(update, context):
    if context.args: await call_api(update, FAM_API, context.args[0])

# ================= JSON DOWNLOAD =================

async def json_download(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    key = query.data.split("_")[1]

    data = CACHE.get(key)

    if not data:
        return

    filename = f"{key}.json"

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    await query.message.reply_document(open(filename, "rb"))

# ================= PREMIUM WATCHER =================

async def premium_watcher(application):

    while True:

        data = load_premium()

        for user in list(data.keys()):

            expire = data[user]["expire"]

            if time.time() > expire:

                try:
                    await application.bot.send_message(
                        int(user),
                        "❌ Your premium has expired."
                    )
                except:
                    pass

                del data[user]

        save_premium(data)

        await asyncio.sleep(3600)

# ================= START BACKGROUND =================

async def start_background(application):
    asyncio.create_task(premium_watcher(application))

# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.post_init = start_background

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("buy", buy))

    app.add_handler(CommandHandler("num", num))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("veh", veh))
    app.add_handler(CommandHandler("upi", upi))
    app.add_handler(CommandHandler("insta", insta))
    app.add_handler(CommandHandler("fam", fam))

    app.add_handler(CommandHandler("addpremium", addpremium))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("approvegc", approvegc))

    app.add_handler(CallbackQueryHandler(json_download, pattern="json_"))

    print(f"{BOT_NAME} Running")

    app.run_polling()

if __name__ == "__main__":
    main()
