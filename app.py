import os
import json
import time
import uuid
import asyncio
import requests
import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= VARIABLES =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

BOT_NAME = os.getenv("BOT_NAME", "cap X Info Bot")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@captainpapaj1")

NUM_API = os.getenv("NUM_API")
TG_API = os.getenv("TG_API")
VEH_API = os.getenv("VEH_API")
UPI_API = os.getenv("UPI_API")
INSTA_API = os.getenv("INSTA_API")
FAM_API = os.getenv("FAM_API")
FF_API = os.getenv("FF_API")
RESULT_MODE = os.getenv("RESULT_MODE", "ui")
# json  = raw API JSON
# pretty = formatted UX result

USAGE_FILE = "usage.json"
PREMIUM_FILE = "premium.json"
USERS_FILE = "users.json"
GC_FILE = "approved_gc.json"
GROUPS_FILE = "groups.json"

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

# ================= GROUP LIST DATABASE =================

def load_groups():
    try:
        with open(GROUPS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_groups(groups):
    with open(GROUPS_FILE, "w") as f:
        json.dump(groups, f)

def add_group(chat_id):

    groups = load_groups()

    if chat_id not in groups:
        groups.append(chat_id)
        save_groups(groups)

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

    chat = update.effective_chat

    if chat.type in ["group", "supergroup"]:
        add_group(chat.id)

    premium = get_remaining(user_id)

    if premium:
        days, hours = premium
        status = f"⭐ Premium Active\n⏳ Remaining: {days}d {hours}h"
    else:
        status = "🆓 Free User\nLimit: 3 requests/day"

    keyboard = [
    [
        InlineKeyboardButton("🔎 Commands", callback_data="cmds"),
        InlineKeyboardButton("⭐ Premium", callback_data="premiuminfo")
    ],
    [
        InlineKeyboardButton("💳 Buy Premium", url=f"https://t.me/{OWNER_USERNAME.replace('@','')}")
    ]
]

    await update.message.reply_text(
f"""
╭━━━〔 🔎 {BOT_NAME} 〕━━━╮

👋 Welcome {update.effective_user.first_name}

📊 Your Status
{status}

━━━━━━━━━━━━━━

🔍 Available Lookups

📱 /num  → Mobile Number Info  
👤 /tg   → Telegram User Info  
🎮 /ff   → Free Fire UID Info
🚗 /veh  → Vehicle Details  
💳 /upi  → UPI Information  
📷 /insta → Instagram Lookup  
👪 /fam  → Family Members  
  
━━━━━━━━━━━━━━

⚡ Features
• Fast API response
• Cached results
• Premium unlimited searches

👑 Owner: {OWNER_USERNAME}

╰━━━━━━━━━━━━━━━━╯
""",
    reply_markup=InlineKeyboardMarkup(keyboard),
    parse_mode="HTML"
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

    users = load_users()
    groups = load_groups()
    targets = users + groups

    sent = 0

    # reply broadcast
    if update.message.reply_to_message:

        msg = update.message.reply_to_message

        for chat_id in targets:
            try:
                await msg.copy(chat_id=chat_id)
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass

    else:

        message = update.message.text.replace("/broadcast", "", 1).strip()

        if not message:
            await update.message.reply_text("Usage:\n/broadcast message\nor reply to a message with /broadcast")
            return

        for chat_id in targets:
            try:
                await context.bot.send_message(chat_id, message)
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass

    await context.bot.send_message(update.effective_chat.id, f"📢 Broadcast sent to {sent} chats.")

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

# ================= GC LIST =================

async def gclist(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    groups = load_gc()

    if not groups:
        await update.message.reply_text("❌ No approved groups.")
        return

    text = "✅ Approved Groups:\n\n"

    for gid in groups:
        text += f"{gid}\n"

    await update.message.reply_text(text)

# ================= STATS =================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    users = load_users()
    groups = load_groups()
    premium = load_premium()
    usage = load_json(USAGE_FILE)

    total_users = len(users)
    total_groups = len(groups)
    total_premium = len(premium)
    total_requests = len(usage)

    await update.message.reply_text(
f"""
📊 {BOT_NAME} Stats

👤 Users: {total_users}
👥 Groups: {total_groups}
⭐ Premium Users: {total_premium}
📈 Requests Today: {total_requests}

Owner: {OWNER_USERNAME}
"""
    )

# ================= RESULT FORMATTER =================

def format_result(data):

    if not isinstance(data, dict):
        return str(data)

    if "data" not in data:
        return json.dumps(data, indent=2)

    results = data.get("data", [])

    if not results:
        return "❌ No results found."

    text = "🔎 Search Result\n\n"

    for item in results[:5]:

        name = item.get("name", "N/A")
        father = item.get("father_name", "N/A")
        mobile = item.get("mobile", "N/A")
        alt = item.get("alt_mobile", "N/A")
        circle = item.get("circle", "N/A")
        address = item.get("address", "N/A")
        email = item.get("email", "N/A")
        idn = item.get("id_number", "N/A")

        text += f"""
👤 Name: {name}
👨 Father: {father}
📱 Mobile: {mobile}
📞 Alt: {alt}
📍 Circle: {circle}

🏠 Address:
{address}

🆔 ID: {idn}
📧 Email: {email}

━━━━━━━━━━━━━━
"""

    return text[:4000]

# ================= TELEGRAM RESULT FORMATTER =================

def format_tg_result(data, target_id):

    # If API response is not a dictionary
    if not isinstance(data, dict):
        return "❌ Invalid API response"

    # If API returned status false
    if not data.get("status"):
        return "❌ No result found."

    # Extract fields safely
    country = data.get("country", "N/A")
    code = data.get("country_code", "N/A")
    number = data.get("number", "N/A")
    username = data.get("username")

    if username:
        username_text = f"@{username}"
    else:
        username_text = "N/A"
    
    # Extract time data
    time_data = data.get("time_swap", {})

    fetched = time_data.get("fetched_at", "N/A")
    tz = time_data.get("timezone", "N/A")

    # Build formatted message
    text = f"""
🔎 Telegram Lookup

📱 API Result
🌍 Country: {country}
📞 Country Code: {code}
🔢 Number: {number}

⏱ Fetched At: {fetched}
🕒 Timezone: {tz}

━━━━━━━━━━━━━━

🤖 Telegram Info
🆔 User ID: {target_id}
👤 Username: @{username}
"""

    return text

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

    # =================  API REQUEST  =================
    try:

        # Send request to API with the provided value
        r = requests.get(api_url.format(value.strip()), timeout=15)

        # Check if API responded successfully
        if r.status_code != 200:
            await update.message.reply_text("❌ API Server Error")
            return

        # Try converting response into JSON
        try:
            data = r.json()
        except:
            await update.message.reply_text("❌ API returned invalid JSON")
            return

        # Generate unique ID for this response
        uid = str(uuid.uuid4())

        # Store result in cache so it can be downloaded later
        CACHE[uid] = data


        # ================= FORMAT RESULT =================

        # If the request is Telegram lookup (/tg)
        if api_url == TG_API:
            preview = format_tg_result(data, value)

        # If UI formatting mode is enabled
        elif RESULT_MODE == "ui":
            preview = format_result(data)

        # Otherwise return raw JSON text
        else:
            preview = json.dumps(data, indent=2)[:3500]


        # ================= CREATE BUTTONS =================

        # Create empty button list
        buttons = []

        # If Telegram lookup add "Open Telegram" button
        # If Telegram lookup add open profile button
        if api_url == TG_API:

            # Some APIs may return username instead of number
            
            username = data.get("username")

            if username:
               url = f"https://t.me/{username}"
            else:
                url = f"tg://user?id={value}"

            buttons.append(
                [InlineKeyboardButton("👤 Open Telegram", url=url)]
            )
                
        # Add button to download full JSON result
        buttons.append(
            [InlineKeyboardButton(
                "📄 Full JSON",
                callback_data=f"json_{uid}"
            )]
        )

        # Convert button list to Telegram keyboard
        keyboard = InlineKeyboardMarkup(buttons)


    # ================= SEND RESULT =================

        # Escape preview text for HTML safety
        safe_preview = html.escape(preview)

        # Dynamic title
        title = "🔎 Telegram Lookup" if api_url == TG_API else "🔎 Search Result"

        # Send result message
        await update.message.reply_text(
            f"{title}\n\n<pre>{safe_preview}</pre>",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    # ================= ERROR HANDLING =================

    except requests.exceptions.Timeout:
        await update.message.reply_text(
            "⚠️ API server is waking up. Try again in a few seconds."
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ API Error: {e}"
        )

        
# ================= VALUE HELPER =================

def get_value(update, context):

    if context.args:
        return context.args[0]

    if update.message.reply_to_message:
        if update.message.reply_to_message.text:
            return update.message.reply_to_message.text.strip()

    return None


# ================= COMMAND WRAPPERS =================

async def num(update, context):

    value = get_value(update, context)

    if not value:
        await update.message.reply_text("Usage:\n/num NUMBER\nor reply to number.")
        return

    await call_api(update, NUM_API, value)


async def tg(update, context):

    value = get_value(update, context)

    if not value:
        await update.message.reply_text("Usage:\n/tg TG_ID\nor reply to ID.")
        return

    await call_api(update, TG_API, value)


async def veh(update, context):

    value = get_value(update, context)

    if not value:
        await update.message.reply_text("Usage:\n/veh VEHICLE_NO\nor reply to vehicle.")
        return

    await call_api(update, VEH_API, value)


async def upi(update, context):

    value = get_value(update, context)

    if not value:
        await update.message.reply_text("Usage:\n/upi UPI_ID\nor reply to UPI.")
        return

    await call_api(update, UPI_API, value)


async def insta(update, context):

    value = get_value(update, context)

    if not value:
        await update.message.reply_text("Usage:\n/insta USERNAME\nor reply to username.")
        return

    await call_api(update, INSTA_API, value)


async def fam(update, context):

    value = get_value(update, context)

    if not value:
        await update.message.reply_text("Usage:\n/fam MOBILE\nor reply to number.")
        return

    await call_api(update, FAM_API, value)


async def ff(update, context):

    value = get_value(update, context)

    if not value:
        await update.message.reply_text("Usage:\n/ff UID\nor reply to UID.")
        return

    await call_api(update, FF_API, value)

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
    app.add_handler(CommandHandler("tg", tg))
    app.add_handler(CommandHandler("veh", veh))
    app.add_handler(CommandHandler("upi", upi))
    app.add_handler(CommandHandler("insta", insta))
    app.add_handler(CommandHandler("fam", fam))
    app.add_handler(CommandHandler("ff", ff))

    app.add_handler(CommandHandler("addpremium", addpremium))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("approvegc", approvegc))
    app.add_handler(CommandHandler("gclist", gclist))
    app.add_handler(CommandHandler("stats", stats))
    

    app.add_handler(CallbackQueryHandler(json_download, pattern="json_"))

    print(f"{BOT_NAME} Running")

    app.run_polling()

if __name__ == "__main__":
    main()
