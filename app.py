import os
import json
import time
import uuid
import asyncio
import requests
import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient

# ================= VARIABLES =================

MONGO_URI = os.getenv("MONGO_URI")

mongo = MongoClient(MONGO_URI)

db = mongo["osint_bot"]

users_col = db["users"]
premium_col = db["premium"]
groups_col = db["groups"]
gc_col = db["approved_gc"]
usage_col = db["usage"]

users_col.create_index("user_id")
premium_col.create_index("user_id")
groups_col.create_index("chat_id")
gc_col.create_index("chat_id")
usage_col.create_index("user_id")


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

CACHE = {}
CACHE_TTL = 3600

# ================= USER DATABASE =================

def add_user(user_id):

    users_col.update_one(
    {"user_id": user_id},
    {"$setOnInsert": {"joined": int(time.time())}},
    upsert=True
)


# ================= GROUP LIST DATABASE =================


def add_group(chat_id):

    groups_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id}},
        upsert=True
    )
    
# ================= DAILY LIMIT =================

def check_daily_limit(user_id):

    today = int(time.time() // 86400)

    data = usage_col.find_one({"user_id": user_id})

    if not data:

        usage_col.insert_one({
            "user_id": user_id,
            "day": today,
            "count": 1
        })

        return True

    if data["day"] != today:

        usage_col.update_one(
            {"user_id": user_id},
            {"$set": {"day": today, "count": 1}}
        )

        return True

    if data["count"] >= 3:
        return False

    usage_col.update_one(
        {"user_id": user_id},
        {"$inc": {"count": 1}}
    )

    return True

# ================= PREMIUM SYSTEM =================

def is_premium(user_id):

    data = premium_col.find_one({"user_id": user_id})

    if not data:
        return False

    if time.time() > data["expire"]:
        premium_col.delete_one({"user_id": user_id})
        return False

    return True

def get_remaining(user_id):

    data = premium_col.find_one({"user_id": user_id})

    if not data:
        return None

    remaining = data["expire"] - time.time()

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

    user = int(context.args[0])
    days = int(context.args[1])

    expire = time.time() + days * 86400

    premium_col.update_one(
        {"user_id": user},
        {"$set": {"expire": expire}},
        upsert=True
    )

    await update.message.reply_text("✅ Premium added")

# ================= BROADCAST =================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    targets = []

    for u in users_col.find():
        targets.append(u["user_id"])

    for g in groups_col.find():
        targets.append(g["chat_id"])

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

    gc_col.update_one(
        {"chat_id": chat.id},
        {"$set": {"chat_id": chat.id}},
        upsert=True
    )

    await update.message.reply_text("✅ This group has been approved.")

# ================= GC LIST =================

async def gclist(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    groups = list(gc_col.find())

    if not groups:
        await update.message.reply_text("❌ No approved groups.")
        return

    text = "👥 Approved Groups\n\n"

    for g in groups:

        chat_id = g["chat_id"]

        try:
            chat = await context.bot.get_chat(chat_id)

            name = chat.title or "Unknown"
            username = chat.username

            text += f"📛 Name: {name}\n"
            text += f"🆔 ID: <code>{chat_id}</code>\n"

            if username:
                link = f"https://t.me/{username}"
                text += f"🔗 <a href='{link}'>Open Group</a>\n"

        except:
            text += f"📛 Name: Unknown\n"
            text += f"🆔 ID: <code>{chat_id}</code>\n"

        text += "\n━━━━━━━━━━━━━━\n\n"

    await update.message.reply_text(text, parse_mode="HTML")
    
#================== PREMIUM LIST ==================================

async def premiumlist(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    users = list(premium_col.find())

    if not users:
        await update.message.reply_text("❌ No premium users.")
        return

    text = "⭐ Premium Users\n\n"

    for u in users:

        user_id = u["user_id"]
        expire = u.get("expire", 0)

        remaining = expire - time.time()

       days = int(remaining // 86400)
       hours = int((remaining % 86400) // 3600)

        try:
            user = await context.bot.get_chat(user_id)

            name = user.first_name or "User"
            username = user.username

            if username:
                link = f"https://t.me/{username}"
                text += f"👤 <a href='{link}'>{name}</a>\n"
                text += f"⏳ {days}d {hours}h remaining\n"
            else:
                text += f"👤 {name}\nID: <code>{user_id}</code>\n"

        except:
            text += f"👤 ID: <code>{user_id}</code>\n"

        text += "\n"

    await update.message.reply_text(text, parse_mode="HTML")

# ================= STATS =================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    total_users = users_col.count_documents({})
    total_groups = groups_col.count_documents({})
    total_premium = premium_col.count_documents({})
    total_requests = usage_col.count_documents({})
   
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

# ================= CACHE STATS =================

async def cachestats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    total_cache = len(CACHE)

    await update.message.reply_text(
f"""
⚡ Cache Statistics

Total Cache Entries: {total_cache}

Cache TTL: {CACHE_TTL} seconds
"""
    )

# ================= RESULT FORMATTER =================

def format_result(data):

    if not isinstance(data, dict):
        return "❌ Invalid API response"

    results = data.get("results") or data.get("result") or []

    if not results:
        return """🔎 Number Lookup Result

👤 Name: N/A
👨 Father: N/A

📱 Mobile: N/A
📞 Alt Mobile: N/A

📡 Circle/SIM: N/A

🏠 Address:
N/A

🆔 ID: N/A
📧 Email: N/A

━━━━━━━━━━━━━━
🔎 Data Source: @captainpapaj1
"""

    text = "🔎 Number Lookup Result\n\n"

    for i, item in enumerate(results[:5], start=1):

        name = item.get("name") or "N/A"
        father = item.get("father_name") or "N/A"
        mobile = item.get("mobile") or "N/A"
        alt = item.get("alt_mobile") or "N/A"
        circle = item.get("circle") or item.get("circle/sim") or "N/A"
        address = item.get("address") or "N/A"
        id_num = item.get("id_number") or item.get("id number") or "N/A"
        email = item.get("email") or "N/A"
        tc = item.get("truecaller_name") or "N/A"

        text += f"""📄 Result #{i}

👤 Name: {name}
👨 Father: {father}

📱 Mobile: {mobile}
📞 Alt Mobile: {alt}

📡 Circle/SIM: {circle}

🏠 Address:
{address}

🆔 ID: {id_num}
📧 Email: {email}

🔎 Truecaller: {tc}

━━━━━━━━━━━━━━

"""

    text += "🔎 Data Source: @captainpapaj1"

    return text[:4000]

# ================= TELEGRAM RESULT FORMATTER =================

def format_tg_result(data, target_id):

    # If API response is not a dictionary
    if not isinstance(data, dict):
        return "❌ Invalid API response"

    # If API returned status false
    if not data.get("success"):
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
👤 Username: {username_text}

━━━━━━━━━━━━━━
🔎 Data Source: @captainpapaj1
"""

    return text

# ================= VEHICLE RESULT FORMATTER =================

def format_vehicle_result(data, searched_number):

    if not isinstance(data, dict):
        return "❌ Invalid API response"

    if not data.get("success"):
        return "❌ No vehicle data found."

    info = data.get("data", {})

    owner_name = info.get("owner_name", "N/A")
    father_name = info.get("father_name", "N/A")

    vehicle_number = info.get("reg_no") or data.get("vehicle_number") or searched_number

    maker_model = info.get("maker_model", "N/A")
    vehicle_class = info.get("vehicle_class", "N/A")

    city = info.get("city", "N/A")
    rto = info.get("rto", "N/A")
    rto_code = info.get("rto_code", "N/A")

    address = info.get("address", "N/A")
    phone = info.get("phone", "N/A")

    fuel_type = info.get("fuel_type", "N/A")
    fuel_norms = info.get("fuel_norms", "N/A")

    chassis_no = info.get("chassis_no", "N/A")
    engine_no = info.get("engine_no", "N/A")

    insurance_company = info.get("insurance_company", "N/A")
    insurance_expiry = info.get("insurance_expiry", "N/A")

    reg_date = info.get("reg_date", "N/A")
    vehicle_age = info.get("vehicle_age", "N/A")
    fitness_upto = info.get("fitness_upto", "N/A")
    tax_upto = info.get("tax_upto", "N/A")

    return f"""
🚗 Vehicle Lookup Result

👤 Owner Name: {owner_name}
👨 Father Name: {father_name}

🔢 Vehicle Number: {vehicle_number}
🚘 Model: {maker_model}
🚙 Class: {vehicle_class}

🏢 RTO: {rto}
🧾 RTO Code: {rto_code}
🏙 City: {city}

📍 Address:
{address}

☎️ RTO Phone: {phone}

⛽ Fuel Type: {fuel_type}
📊 Fuel Norms: {fuel_norms}

🛠 Engine No: {engine_no}
🔩 Chassis No: {chassis_no}

🛡 Insurance: {insurance_company}
📅 Insurance Expiry: {insurance_expiry}

📅 Registration Date: {reg_date}
📆 Fitness Upto: {fitness_upto}
💰 Tax Upto: {tax_upto}

⌛ Vehicle Age: {vehicle_age}

━━━━━━━━━━━━━━
🔎 Data Source: @captainpapaj1
"""

#================== FREE FIRE FORMATTER ==========

def format_ff_result(data):

    info = data.get("info", {})

    return f"""
🎮 Free Fire Player

👤 Nickname: {info.get("👤 Nickname","N/A")}
🆔 UID: {info.get("🆔 ID","N/A")}

🌎 Region: {info.get("🌎 Region","N/A")}
🎖 Level: {info.get("🎖️ Level","N/A")}

🏆 Ranked Points: {info.get("🏆 Ranked Points","N/A")}
👍 Likes: {info.get("👍 Likes","N/A")}

📅 Created: {info.get("📅 Account Created","N/A")}
🕒 Last Login: {info.get("🕒 Last Login","N/A")}

━━━━━━━━━━━━━━
🔎 Data Source: @captainpapaj1
"""

# ================= UPI RESULT FORMATTER =================

def format_upi_result(data):

    return f"""
💳 UPI Lookup Result

👤 Name: {data.get("account_name","N/A")}
📱 UPI ID: {data.get("upi_id","N/A")}

🏦 Bank: {data.get("bank","N/A")}
🔑 IFSC: {data.get("ifsc","N/A")}

⚙️ PSP: {data.get("psp","N/A")}
🏪 Merchant: {data.get("is_merchant","N/A")}

━━━━━━━━━━━━━━
🔎 Data Source: {OWNER_USERNAME}
"""

# ================= JSON CLEANER =================

def clean_api_credits(data):

    # keys to remove completely
    remove_keys = [
        "endpoint",
        "example",
        "api",
        "api_url",
        "url",
        "developer",
        "credit",
        "source"
    ]

    # keys to replace with your username
    replace_keys = [
        "by",
        "owner",
        "api_by",
        "Owner",
        "API BY"
    ]

    if isinstance(data, dict):

        for key in list(data.keys()):

            # remove sensitive fields
            if key in remove_keys:
                del data[key]

            # replace credits
            elif key in replace_keys:
                data[key] = OWNER_USERNAME

            # recursive cleaning
            elif isinstance(data[key], (dict, list)):
                clean_api_credits(data[key])

    elif isinstance(data, list):

        for item in data:
            clean_api_credits(item)

    return data

# ================= CACHE CLEANER =================

async def cache_cleaner():

    while True:

        now = time.time()

        remove_keys = []

        for key, value in CACHE.items():

            # only check search cache objects
            if isinstance(value, dict) and "time" in value:

                if now - value["time"] > CACHE_TTL:
                    remove_keys.append(key)

        for key in remove_keys:
            del CACHE[key]

        await asyncio.sleep(600)  # clean every 10 minutes

# ================= USERNAME RESOLVER =================

async def resolve_username(context, username):

    try:
        chat = await context.bot.get_chat(username)

        if chat and chat.id:
            return str(chat.id)

    except:
        pass

    return None

# ================= MULTI API FALLBACK =================

def get_api_list(primary):

    apis = [primary]

    api2 = os.getenv(primary + "_2")
    api3 = os.getenv(primary + "_3")

    if api2:
        apis.append(api2)

    if api3:
        apis.append(api3)

    return apis

# ================= API CALL =================

async def call_api(update, api_url, value):

    user_id = update.effective_user.id
    chat = update.effective_chat

    # ---- LIMIT CHECK ----
    limit_needed = True

    if is_premium(user_id):
        limit_needed = False

    if chat.type in ["group", "supergroup"]:
        if gc_col.find_one({"chat_id": chat.id}):
            limit_needed = False

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

    # ================= CACHE CHECK =================

    cache_key = f"{hash(api_url)}:{value}"

    if cache_key in CACHE:

        cached = CACHE[cache_key]

        if time.time() - cached["time"] < CACHE_TTL:

            data = cached["data"]

            if api_url == TG_API:
                preview = format_tg_result(data, value)

            elif api_url == VEH_API and RESULT_MODE == "ui":
                preview = format_vehicle_result(data, value)

            elif RESULT_MODE == "ui":
                preview = format_result(data)

            else:
                preview = json.dumps(data, indent=2)

            safe_preview = html.escape(preview)

            await update.message.reply_text(
                f"🔎 Search Result\n\n<pre>{safe_preview}</pre>",
                parse_mode="HTML"
            )

            return
    
    # --------- API REQUEST ----------
    try:

        api_list = [api_url]

        # additional APIs
        alt2 = os.getenv(api_url + "_2")
        alt3 = os.getenv(api_url + "_3")

        if alt2:
            api_list.append(alt2)

        if alt3:
            api_list.append(alt3)

        data = None

        for api in api_list:

            try:

                url = api.format(value.strip()) if "{}" in api else f"{api}{value.strip()}"

                r = requests.get(url, timeout=20)

                if r.status_code != 200:
                    continue

                data = r.json()

                # clean credits
                data = clean_api_credits(data)

                if data:
                    break
    
            except:
                continue

        if not data:
            await update.message.reply_text("❌ All API servers failed.")
            return
        
        # -------- HANDLE API ERRORS / NO DATA --------

        error_msg = str(data.get("error","")).lower()

        # Detect API maintenance
        if "maintenance" in error_msg:
            await update.message.reply_text(
                "⚠️ API is currently under maintenance.\nPlease try again later."
            )
            return

        # Detect no data situations
        if (
            data.get("success") is False
            or "no matching records" in str(data.get("message","")).lower()
            or "no data" in error_msg
            or data.get("result") == []
            or data.get("results") == []
        ):
            await update.message.reply_text(
                "🔎 Search Result\n\n❌ No data found."
            )
            return


        # Generate unique ID for this response
        uid = str(uuid.uuid4())

        # Store result for JSON download
        CACHE[uid] = data

        # Save search cache
        CACHE[cache_key] = {
            "data": data,
            "time": time.time()
        }

        # ================= FORMAT RESULT =================

        if api_url == TG_API:
            preview = format_tg_result(data, value)

        elif api_url == VEH_API:
            preview = format_vehicle_result(data, value)

        elif api_url == UPI_API:
            preview = format_upi_result(data)

        elif api_url == FF_API:
            preview = format_ff_result(data)

        elif api_url == NUM_API:
            preview = format_result(data)

        else:
            preview = json.dumps(data, indent=2)

        # ================= CREATE BUTTONS =================

        buttons = []

        # Telegram profile button
        if api_url == TG_API:

            username = data.get("username")

            if username:
                url = f"https://t.me/{username}"
            else:
                url = f"tg://user?id={value}"

            buttons.append(
                [InlineKeyboardButton("👤 Open Telegram", url=url)]
            )

        # JSON download button
        buttons.append(
            [InlineKeyboardButton(
                "📄 Full JSON",
                callback_data=f"json_{uid}"
            )]
        )

        keyboard = InlineKeyboardMarkup(buttons)


        # ================= SEND RESULT =================

        safe_preview = html.escape(preview)
        title = "🔎 Telegram Lookup" if api_url == TG_API else "🔎 Search Result"

        try:
            await update.message.reply_text(
                f"{title}\n\n<pre>{safe_preview}</pre>",
                parse_mode="HTML",
                reply_markup=keyboard
            )

        except Exception as e:

            if "Button_user_invalid" in str(e) or "Button_user_privacy_restricted" in str(e):

                # remove Telegram button but keep JSON button
                buttons = [
                    [InlineKeyboardButton(
                        "📄 Full JSON",
                        callback_data=f"json_{uid}"
                  )]
                ]

                keyboard = InlineKeyboardMarkup(buttons)

                await update.message.reply_text(
                    f"{title}\n\n<pre>{safe_preview}</pre>",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )

            else:
                raise e

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
        await update.message.reply_text(
            "Usage:\n/tg USER_ID or @username"
        )
        return

    # If username provided
    if value.startswith("@"):

        resolved = await resolve_username(context, value)

        if not resolved:
            await update.message.reply_text(
                "❌ Cannot resolve username to ID.\nUser must interact with bot first."
            )
            return

        value = resolved

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

    data = clean_api_credits(CACHE.get(key))
 
    if not data:
        return

    filename = f"{key}.json"

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    await query.message.reply_document(open(filename, "rb"))

# ================= PREMIUM WATCHER =================

async def premium_watcher(application):

    while True:

        for user in premium_col.find():

            if time.time() > user["expire"]:

                try:
                    await application.bot.send_message(
                        user["user_id"],
                        "❌ Your premium has expired."
                    )
                except:
                    pass

                premium_col.delete_one({"user_id": user["user_id"]})

        await asyncio.sleep(3600)

# ================= START BACKGROUND =================

async def start_background(application):
    await application.bot.delete_webhook(drop_pending_updates=True)

    asyncio.create_task(premium_watcher(application))
    asyncio.create_task(cache_cleaner())

# ================= API CHECK =================

async def apicheck(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    api_groups = {
        "NUM": [NUM_API, os.getenv("NUM_API_2"), os.getenv("NUM_API_3")],
        "TG": [TG_API, os.getenv("TG_API_2"), os.getenv("TG_API_3")],
        "VEH": [VEH_API, os.getenv("VEH_API_2"), os.getenv("VEH_API_3")],
        "UPI": [UPI_API, os.getenv("UPI_API_2"), os.getenv("UPI_API_3")],
        "INSTA": [INSTA_API, os.getenv("INSTA_API_2"), os.getenv("INSTA_API_3")],
        "FAM": [FAM_API, os.getenv("FAM_API_2"), os.getenv("FAM_API_3")],
        "FF": [FF_API, os.getenv("FF_API_2"), os.getenv("FF_API_3")]
    }

    text = "🔎 API Diagnostic\n\n"

    for name, apis in api_groups.items():

        for i, url in enumerate(apis, start=1):

            if not url:
                continue

            label = f"{name}{i}"

            try:

                start = time.time()

                test_url = url.replace("{}", "1")

                r = requests.get(test_url, timeout=10)

                latency = int((time.time() - start) * 1000)

                if r.status_code != 200:
                    text += f"{label} → ❌ HTTP {r.status_code}\n"
                    continue

                try:
                    data = r.json()
                except ValueError:
                    text += f"{label} → ⚠ Invalid JSON\n"
                    continue

                if data.get("success") is False:

                    err = data.get("error") or data.get("message") or "API error"

                    text += f"{label} → ❌ {err}\n"

                else:

                    text += f"{label} → ✅ {latency}ms\n"

            except requests.exceptions.Timeout:

                text += f"{label} → ⏱ Timeout\n"

            except Exception:

                text += f"{label} → ❌ Offline\n"

        text += "\n"

    await update.message.reply_text(text)

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
    app.add_handler(CommandHandler("cache", cachestats))
    app.add_handler(CommandHandler("apicheck", apicheck))
    app.add_handler(CommandHandler("premiumlist", premiumlist))
    
    app.add_handler(CallbackQueryHandler(json_download, pattern="json_"))

    print(f"{BOT_NAME} Running")

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
