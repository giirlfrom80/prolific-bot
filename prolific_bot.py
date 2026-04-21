import requests
import time
import os
import psycopg2
import threading
import json
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = "8626572170:AAG7BENnkyWYjKg-V7yAxwlVhqgYOVp4xvQ"
CHAT_ID = "541545419"
CLIENT_ID = "pQJQs1EKM8T8C0BP5HlPclFc9Ynb97fP"
DATABASE_URL = os.environ["DATABASE_URL"]
PORT = int(os.environ.get("PORT", 8080))

seen_ids = set()
access_token = None
berlin = timezone(timedelta(hours=2))

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def load_refresh_token():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM tokens WHERE key = 'refresh_token'")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None

def save_refresh_token(token):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tokens (key, value) VALUES ('refresh_token', %s)
        ON CONFLICT (key) DO UPDATE SET value = %s
    """, (token, token))
    conn.commit()
    cur.close()
    conn.close()

def refresh_access_token():
    global access_token
    refresh_token = load_refresh_token()
    if not refresh_token:
        print("No refresh token in DB")
        return False
    r = requests.post(
        "https://auth.prolific.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
        }
    )
    if r.status_code == 200:
        data = r.json()
        access_token = data.get("access_token")
        new_refresh = data.get("refresh_token")
        if new_refresh:
            save_refresh_token(new_refresh)
        print("Token refreshed OK")
        return True
    else:
        print(f"Refresh error: {r.status_code} {r.text}")
        return False

def get_exchange_rates():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=5)
        if r.status_code == 200:
            rates = r.json().get("rates", {})
            return {
                "GBP_TO_EUR": 1 / rates.get("GBP", 0.85),
                "USD_TO_EUR": 1 / rates.get("USD", 1.08)
            }
    except:
        pass
    return {"GBP_TO_EUR": 1.18, "USD_TO_EUR": 0.93}

def get_submissions():
    url = "https://internal-api.p
