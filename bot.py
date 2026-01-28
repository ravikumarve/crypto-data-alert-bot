import logging
import sqlite3
import requests
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from contextlib import contextmanager
import os

API_TOKEN = os.getenv("BOT_TOKEN", "8508060217:AAH87XK6qzB8NNmfdm3DBiCCEQRv1QxxkP0")
RAZORPAY_LINK = "YOUR_PAYMENT_LINK"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@contextmanager
def get_db():
    conn = sqlite3.connect("users.db")
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
            premium INTEGER DEFAULT 0
        )
        """)
        conn.commit()

def is_premium(user_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT premium FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row and row[0] == 1

@dp.message(Command("start"))
async def start(message: types.Message):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (message.from_user.id,))
        conn.commit()
    
    await message.answer(
        "📊 Crypto Data Alert Bot\n\n"
        "• Funding Rate Extremes\n"
        "• Token Unlock Alerts\n\n"
        "⚠️ Educational data only\n\n"
        "Commands:\n"
        "/free – sample alerts\n"
        "/premium – unlock full access"
    )

@dp.message(Command("free"))
async def free(message: types.Message):
    await message.answer(
        "🚨 Sample Alert\n\n"
        "BTCUSDT Funding: +0.17%\n"
        "Bias: Longs overcrowded\n\n"
        "Upgrade for real-time alerts → /premium"
    )

@dp.message(Command("premium"))
async def premium(message: types.Message):
    await message.answer(
        f"🔓 Premium Access\n\n"
        "✔ Real-time funding rate alerts\n"
        "✔ Token unlock alerts\n\n"
        f"💳 Pay here:\n{RAZORPAY_LINK}\n\n"
        "After payment send screenshot to admin."
    )

def funding_rate_check():
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        alerts = []
        for item in data:
            rate = float(item["lastFundingRate"])
            if rate > 0.0015 or rate < -0.0015:
                alerts.append(
                    f"🚨 Funding Rate Extreme\n\n"
                    f"Pair: {item['symbol']}\n"
                    f"Funding: {rate:.4f}\n\n"
                    "⚠️ Educational data only"
                )
        return alerts
    except Exception as e:
        logging.error(f"Error fetching funding rates: {e}")
        return []

async def send_alerts():
    alerts = funding_rate_check()
    if not alerts:
        return
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE premium=1")
        users = cur.fetchall()
    
    for user in users:
        for alert in alerts:
            try:
                await bot.send_message(user[0], alert)
                await asyncio.sleep(0.05)
            except Exception as e:
                logging.error(f"Failed to send to {user[0]}: {e}")

async def alert_loop():
    while True:
        await send_alerts()
        await asyncio.sleep(3600)

async def main():
    init_db()
    asyncio.create_task(alert_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
