import logging
import sqlite3
import requests
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = "8508060217:AAH87XK6qzB8NNmfdm3DBiCCEQRv1QxxkP0"
RAZORPAY_LINK = "YOUR_PAYMENT_LINK"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# DB
conn = sqlite3.connect("users.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    premium INTEGER DEFAULT 0
)
""")
conn.commit()

def is_premium(user_id):
    cur.execute("SELECT premium FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row and row[0] == 1

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    cur.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (msg.from_user.id,))
    conn.commit()
    await msg.answer(
        "📊 Crypto Data Alert Bot\n\n"
        "• Funding Rate Extremes\n"
        "• Token Unlock Alerts\n\n"
        ⚠️ Educational data only\n\n"
        "Commands:\n"
        "/free – sample alerts\n"
        "/premium – unlock full access"
    )

@dp.message_handler(commands=["free"])
async def free(msg: types.Message):
    await msg.answer(
        "🚨 Sample Alert\n\n"
        "BTCUSDT Funding: +0.17%\n"
        "Bias: Longs overcrowded\n\n"
        "Upgrade for real-time alerts → /premium"
    )

@dp.message_handler(commands=["premium"])
async def premium(msg: types.Message):
    await msg.answer(
        f"🔓 Premium Access\n\n"
        "✔ Real-time funding rate alerts\n"
        "✔ Token unlock alerts\n\n"
        f"💳 Pay here:\n{RAZORPAY_LINK}\n\n"
        "After payment send screenshot to admin."
    )

# --- FUNDING RATE CHECK ---
def funding_rate_check():
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    data = requests.get(url).json()
    alerts = []
    for item in data:
        rate = float(item["lastFundingRate"])
        if rate > 0.0015 or rate < -0.0015:
            alerts.append(
                f"🚨 Funding Rate Extreme\n\n"
                f"Pair: {item['symbol']}\n"
                f"Funding: {rate}\n\n"
                "⚠️ Educational data only"
            )
    return alerts

# --- ALERT SENDER ---
async def send_alerts():
    alerts = funding_rate_check()
    cur.execute("SELECT user_id FROM users WHERE premium=1")
    users = cur.fetchall()
    for user in users:
        for alert in alerts:
            await bot.send_message(user[0], alert)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)
