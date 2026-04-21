import requests
import time
import os
import psycopg2

TELEGRAM_TOKEN = "8626572170:AAG7BENnkyWYjKg-V7yAxwlVhqgYOVp4xvQ"
CHAT_ID = "541545419"
CLIENT_ID = "pQJQs1EKM8T8C0BP5HlPclFc9Ynb97fP"
DATABASE_URL = os.environ["DATABASE_URL"]

seen_ids = set()
access_token = None

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

def get_studies():
    global access_token
    url = "https://internal-api.prolific.com/api/v1/participant/studies/?sortBy=published_at&orderBy=asc&status=ACTIVE"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            return r.json().get("results", [])
        elif r.status_code in (401, 403, 404):
            print("Token expired, refreshing...")
            if refresh_access_token():
                r2 = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
                print(f"Retry status: {r2.status_code}")
                if r2.status_code == 200:
                    return r2.json().get("results", [])
    except Exception as e:
        print(f"Error: {e}")
    return []

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

init_db()
refresh_access_token()
send_telegram("✅ Бот запущен! Слежу за новыми исследованиями на Prolific.")
last_refresh = time.time()

while True:
    if time.time() - last_refresh > 3000:
        refresh_access_token()
        last_refresh = time.time()
    studies = get_studies()
    for study in studies:
        sid = study.get("id")
        if sid and sid not in seen_ids:
            seen_ids.add(sid)
            name = study.get("name", "Без названия")
            reward = study.get("reward", 0)
            duration = study.get("average_completion_time", "?")
            link = f"https://app.prolific.com/studies/{sid}"
            msg = f"🟢 <b>Новое исследование!</b>\n\n{name}\n💰 £{reward/100:.2f}\n⏱ ~{duration} мин\n\n{link}"
            send_telegram(msg)
    time.sleep(20)
