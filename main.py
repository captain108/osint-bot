import os
import json
import time
import uuid
import asyncio
import requests

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= VARIABLES =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

OWNER_USERNAME = "@captainpapaj1"

NUM_API = os.getenv("NUM_API")
TG_API = os.getenv("TG_API")
VEH_API = os.getenv("VEH_API")
UPI_API = os.getenv("UPI_API")
INSTA_API = os.getenv("INSTA_API")
FAM_API = os.getenv("FAM_API")

# ================= FILES =================

USAGE_FILE = "usage.json"
PREMIUM_FILE = "premium.json"

CACHE = {}

# ================= UTIL =================

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ================= DAILY LIMIT =================

def check_daily_limit(user_id):

    data = load_json(USAGE_FILE)

    today = int(time.time() // 86400)
    user = str(user_id)

    if user not in data:
        data[user] = {"day": today, "count": 1}
        save_json(USAGE_FILE, data)
        return True, 1

    if data[user]["day"] != today:
        data[user] = {"day": today, "count": 1}
        save_json(USAGE_FILE, data)
        return True, 1

    if data[user]["count"] >= 3:
        return False, 3

    data[user]["count"] += 1
    save_json(USAGE_FILE, data)

    return True, data[user]["count"]

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

    premium = get_remaining(user_id)

    if premium:
        days, hours = premium
        status = f"⭐ Premium Active\n⏳ Remaining: {days}d {hours}h\n"
    else:
        status = "🆓 Free User\nLimit: 3 requests/day\n"

    keyboard = [
        [InlineKeyboardButton("💳 Buy Premium", url="https://t.me/captainpapaj1")]
    ]

    await update.message.reply_text(
f"""
🔎 LegendX Info Bot

{status}

Commands

/num 9876543210
/info TG_ID
/veh VEHICLE_NO
/upi UPI_ID
/insta USERNAME
/fam MOBILE

Owner: {OWNER_USERNAME}
""",
reply_markup=InlineKeyboardMarkup(keyboard)
)

# ================= PREMIUM COMMAND =================

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    remain = get_remaining(user_id)

    if not remain:
        await update.message.reply_text(
            f"❌ You are not premium.\n\nContact {OWNER_USERNAME} to buy."
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
        [InlineKeyboardButton("👑 Contact Owner", url="https://t.me/captainpapaj1")]
    ]

    await update.message.reply_text(
"""
⭐ Premium Access

Unlimited requests
Priority access

Price: ₹200 / month
""",
reply_markup=InlineKeyboardMarkup(keyboard)
)

# ================= OWNER ADD PREMIUM =================

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

    data[user] = {
        "expire": expire,
        "notified": False
    }

    save_premium(data)

    await update.message.reply_text("✅ Premium added")

# ================= API CALL =================

async def call_api(update, api_url, value):

    user_id = update.effective_user.id

    if not is_premium(user_id):

        ok, used = check_daily_limit(user_id)

        if not ok:
            await update.message.reply_text(
f"""
🚫 Daily limit reached

Upgrade to premium.

Owner: {OWNER_USERNAME}
"""
)
            return

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
    if not context.args: return
    await call_api(update, NUM_API, context.args[0])

async def info(update, context):
    if not context.args: return
    await call_api(update, TG_API, context.args[0])

async def veh(update, context):
    if not context.args: return
    await call_api(update, VEH_API, context.args[0])

async def upi(update, context):
    if not context.args: return
    await call_api(update, UPI_API, context.args[0])

async def insta(update, context):
    if not context.args: return
    await call_api(update, INSTA_API, context.args[0])

async def fam(update, context):
    if not context.args: return
    await call_api(update, FAM_API, context.args[0])

# ================= JSON BUTTON =================

async def json_download(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    key = query.data.split("_")[1]

    data = CACHE.get(key)

    if not data:
        await query.message.reply_text("Expired")
        return

    filename = f"{key}.json"

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    await query.message.reply_document(open(filename, "rb"))

# ================= PREMIUM WATCHER =================

async def premium_watcher(app):

    while True:

        data = load_premium()

        for user in list(data.keys()):

            expire = data[user]["expire"]

            if time.time() > expire:

                try:
                    await app.bot.send_message(
                        int(user),
                        "❌ Premium expired."
                    )
                except:
                    pass

                del data[user]

        save_premium(data)

        await asyncio.sleep(3600)

# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

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

    app.add_handler(CallbackQueryHandler(json_download, pattern="json_"))

    asyncio.create_task(premium_watcher(app))

    print("LegendX Bot Running")

    app.run_polling()

if __name__ == "__main__":
    main()
