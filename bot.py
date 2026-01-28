import logging
import sqlite3
import requests
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ParseMode
from contextlib import contextmanager
from threading import Thread
from aiohttp import web
import os

# ============ CONFIGURATION ============
API_TOKEN = os.getenv("BOT_TOKEN", "8508060217:AAH87XK6qzB8NNmfdm3DBiCCEQRv1QxxkP0")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # ⚠️ REPLACE WITH YOUR ID
RAZORPAY_LINK = os.getenv("RAZORPAY_LINK", "YOUR_PAYMENT_LINK")
CHECK_INTERVAL = 1800  # 30 minutes (in seconds)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# ============ DATABASE ============
@contextmanager
def get_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            premium INTEGER DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
    logging.info("✅ Database initialized")

def is_premium(user_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT premium FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row and row[0] == 1

def get_user_count():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE premium=1")
        premium = cur.fetchone()[0]
        return total, premium

# ============ USER COMMANDS ============
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (msg.from_user.id,))
        conn.commit()
    
    await msg.answer(
        "📊 *Crypto Data Alert Bot*\n\n"
        "🔹 Funding Rate Extremes\n"
        "🔹 Token Unlock Alerts\n\n"
        "⚠️ _Educational data only_\n\n"
        "*Commands:*\n"
        "/free – Sample alerts\n"
        "/premium – Unlock full access\n"
        "/status – Check your subscription",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message_handler(commands=["free"])
async def free(msg: types.Message):
    await msg.answer(
        "🚨 *Sample Alert*\n\n"
        "Pair: BTCUSDT\n"
        "Funding Rate: +0.17%\n"
        "Bias: Longs overcrowded\n\n"
        "💡 _Upgrade for real-time alerts_ → /premium",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message_handler(commands=["premium"])
async def premium(msg: types.Message):
    if is_premium(msg.from_user.id):
        await msg.answer(
            "✅ *You already have Premium access!*\n\n"
            "Enjoy real-time funding alerts.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await msg.answer(
        f"🔓 *Premium Access*\n\n"
        "✔️ Real-time funding rate alerts\n"
        "✔️ Token unlock notifications\n"
        "✔️ Priority support\n\n"
        f"💳 *Pay here:*\n{RAZORPAY_LINK}\n\n"
        "📸 After payment, send screenshot to admin.\n"
        f"Your ID: `{msg.from_user.id}`",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message_handler(commands=["status"])
async def status(msg: types.Message):
    premium = is_premium(msg.from_user.id)
    status_text = "✅ *Premium Active*" if premium else "❌ *Free Plan*"
    
    await msg.answer(
        f"👤 *Your Status*\n\n"
        f"{status_text}\n"
        f"User ID: `{msg.from_user.id}`\n\n"
        f"{'Enjoying premium features! 🎉' if premium else 'Upgrade to premium → /premium'}",
        parse_mode=ParseMode.MARKDOWN
    )

# ============ ADMIN COMMANDS ============
@dp.message_handler(commands=["activate"])
async def activate(msg: types.Message):
    # Security check
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔ Unauthorized")
        return
    
    try:
        # Extract user ID from command
        parts = msg.text.split()
        if len(parts) != 2:
            await msg.answer(
                "❌ *Usage:*\n`/activate USER_ID`\n\n"
                "Example: `/activate 123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user_id = int(parts[1])
        
        # Activate premium
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET premium=1 WHERE user_id=?", (user_id,))
            conn.commit()
        
        # Notify admin
        await msg.answer(f"✅ *Premium activated for:*\n`{user_id}`", parse_mode=ParseMode.MARKDOWN)
        
        # Notify user
        try:
            await bot.send_message(
                user_id,
                "🎉 *Congratulations!*\n\n"
                "Your Premium subscription is now *ACTIVE*!\n\n"
                "You'll now receive:\n"
                "✔️ Real-time funding alerts\n"
                "✔️ Token unlock notifications\n\n"
                "Thank you for upgrading! 🚀",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.error(f"Could not notify user {user_id}: {e}")
    
    except ValueError:
        await msg.answer("❌ Invalid user ID. Must be a number.")
    except Exception as e:
        await msg.answer(f"❌ Error: {str(e)}")
        logging.error(f"Activation error: {e}")

@dp.message_handler(commands=["deactivate"])
async def deactivate(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔ Unauthorized")
        return
    
    try:
        user_id = int(msg.text.split()[1])
        
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET premium=0 WHERE user_id=?", (user_id,))
            conn.commit()
        
        await msg.answer(f"❌ *Premium deactivated for:*\n`{user_id}`", parse_mode=ParseMode.MARKDOWN)
        
        try:
            await bot.send_message(
                user_id,
                "⚠️ Your premium subscription has been deactivated.\n\n"
                "Contact support if you have questions.",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    except Exception as e:
        await msg.answer(f"❌ Error: {str(e)}")

@dp.message_handler(commands=["stats"])
async def stats(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    
    total, premium = get_user_count()
    
    await msg.answer(
        f"📊 *Bot Statistics*\n\n"
        f"👥 Total Users: `{total}`\n"
        f"💎 Premium Users: `{premium}`\n"
        f"🆓 Free Users: `{total - premium}`\n"
        f"📈 Conversion Rate: `{(premium/total*100) if total > 0 else 0:.1f}%`",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message_handler(commands=["broadcast"])
async def broadcast(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    
    try:
        # Extract message to broadcast
        broadcast_msg = msg.text.replace("/broadcast", "").strip()
        
        if not broadcast_msg:
            await msg.answer("❌ Usage: `/broadcast Your message here`", parse_mode=ParseMode.MARKDOWN)
            return
        
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE premium=1")
            users = cur.fetchall()
        
        success = 0
        failed = 0
        
        for user in users:
            try:
                await bot.send_message(user[0], broadcast_msg, parse_mode=ParseMode.MARKDOWN)
                success += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except Exception as e:
                failed += 1
                logging.error(f"Broadcast failed for {user[0]}: {e}")
        
        await msg.answer(
            f"📢 *Broadcast Complete*\n\n"
            f"✅ Sent: {success}\n"
            f"❌ Failed: {failed}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    except Exception as e:
        await msg.answer(f"❌ Error: {str(e)}")

# ============ FUNDING RATE ALERTS ============
def funding_rate_check():
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        alerts = []
        for item in data:
            try:
                rate = float(item["lastFundingRate"])
                if abs(rate) > 0.0015:  # Alert threshold
                    direction = "🔴 SHORT HEAVY" if rate > 0 else "🟢 LONG HEAVY"
                    alerts.append(
                        f"🚨 *Funding Alert*\n\n"
                        f"Pair: `{item['symbol']}`\n"
                        f"Rate: `{rate:.4f}` ({rate*100:.2f}%)\n"
                        f"Bias: {direction}\n\n"
                        f"⚠️ _Educational only_"
                    )
            except (KeyError, ValueError):
                continue
        
        return alerts
    except Exception as e:
        logging.error(f"Funding rate check error: {e}")
        return []

async def send_alerts():
    alerts = funding_rate_check()
    
    if not alerts:
        logging.info("No funding alerts to send")
        return
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE premium=1")
        users = cur.fetchall()
    
    logging.info(f"Sending {len(alerts)} alerts to {len(users)} premium users")
    
    for user in users:
        for alert in alerts[:5]:  # Limit to 5 alerts per user
            try:
                await bot.send_message(user[0], alert, parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(0.05)
            except Exception as e:
                logging.error(f"Failed to send alert to {user[0]}: {e}")

async def alert_scheduler():
    """Background task that runs every 30 minutes"""
    await asyncio.sleep(10)  # Wait for bot to start
    
    while True:
        try:
            logging.info("🔍 Checking funding rates...")
            await send_alerts()
            logging.info(f"✅ Next check in {CHECK_INTERVAL//60} minutes")
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)

# ============ KEEP-ALIVE WEB SERVER ============
def run_web():
    """Simple web server to keep Replit alive"""
    app = web.Application()
    
    async def health(request):
        total, premium = get_user_count()
        return web.Response(
            text=f"Bot is running!\nUsers: {total} | Premium: {premium}"
        )
    
    app.router.add_get('/', health)
    
    try:
        web.run_app(app, host='0.0.0.0', port=8080)
    except Exception as e:
        logging.error(f"Web server error: {e}")

# ============ STARTUP ============
async def on_startup(dp):
    """Run when bot starts"""
    logging.info("🤖 Bot starting...")
    asyncio.create_task(alert_scheduler())
    logging.info("✅ Alert scheduler started")

# ============ MAIN ============
if __name__ == "__main__":
    init_db()
    
    # Start keep-alive web server in background
    Thread(target=run_web, daemon=True).start()
    
    # Start bot
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
```

---

