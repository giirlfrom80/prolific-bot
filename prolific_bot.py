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
last_token_warning = 0

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

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

def send_token_warning():
    global last_token_warning
    if time.time() - last_token_warning > 3600:
        send_telegram("🔴 <b>ОБНОВИТЕ ТОКЕН</b>\n\nОткройте prolific-bot-production.up.railway.app на app.prolific.com и нажмите кнопку.")
        last_token_warning = time.time()

def refresh_access_token():
    global access_token
    refresh_token = load_refresh_token()
    if not refresh_token:
        print("No refresh token in DB")
        send_token_warning()
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
        send_token_warning()
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
    url = "https://internal-api.prolific.com/api/v1/participant/submissions/?ordering=-started_at&page_size=100"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        print(f"Submissions status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Got {len(data.get('results', []))} submissions")
            return data.get("results", [])
        elif r.status_code in (401, 403, 404):
            if refresh_access_token():
                r2 = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
                if r2.status_code == 200:
                    return r2.json().get("results", [])
    except Exception as e:
        print(f"Error getting submissions: {e}")
    return []

def format_time(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}ч {minutes}мин"
    return f"{minutes}мин"

def get_stats():
    submissions = get_submissions()
    print(f"Processing {len(submissions)} submissions")
    rates = get_exchange_rates()
    now = datetime.now(berlin)

    today_eur = 0
    today_count = 0
    today_seconds = 0
    month_eur = 0
    month_count = 0
    month_seconds = 0

    skip_statuses = {"TIMED-OUT", "RETURNED"}

    for s in submissions:
        if s.get("status") in skip_statuses:
            continue
        if not s.get("is_complete"):
            continue
        completed = s.get("completed_at")
        if not completed:
            continue
        dt = datetime.fromisoformat(completed.replace("Z", "+00:00")).astimezone(berlin)
        reward = s.get("submission_reward", {})
        amount = reward.get("amount", 0) / 100
        currency = reward.get("currency", "GBP")
        rate = rates["GBP_TO_EUR"] if currency == "GBP" else rates["USD_TO_EUR"]
        eur = amount * rate
        time_taken = float(s.get("time_taken") or 0)

        if dt.year == now.year and dt.month == now.month:
            month_eur += eur
            month_count += 1
            month_seconds += time_taken
            if dt.date() == now.date():
                today_eur += eur
                today_count += 1
                today_seconds += time_taken

    today_hours = today_seconds / 3600
    hourly = (today_eur / today_hours) if today_hours > 0 else 0

    msg = "📊 <b>Статистика Prolific</b>\n\n"
    msg += "<b>Сегодня</b>\n"
    msg += f"💶 Заработано: €{today_eur:.2f}\n"
    msg += f"📋 Исследований: {today_count}\n"
    msg += f"⏱ Время: {format_time(today_seconds)}\n"
    if hourly > 0:
        msg += f"💰 Ставка: €{hourly:.2f}/час\n"
    msg += "\n<b>За месяц</b>\n"
    msg += f"💶 Заработано: €{month_eur:.2f}\n"
    msg += f"📋 Исследований: {month_count}\n"
    msg += f"⏱ Время: {format_time(month_seconds)}\n"
    msg += f"\n<i>Курс: £1 = €{rates['GBP_TO_EUR']:.2f}, $1 = €{rates['USD_TO_EUR']:.2f}</i>"

    return msg

def get_studies():
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
                if r2.status_code == 200:
                    return r2.json().get("results", [])
    except Exception as e:
        print(f"Error: {e}")
    return []

def check_telegram_commands():
    offset = None
    while True:
        try:
            params = {"timeout": 10}
            if offset:
                params["offset"] = offset
            r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", params=params, timeout=15)
            if r.status_code == 200:
                updates = r.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {}).get("text", "")
                    if msg == "/stats":
                        send_telegram(get_stats())
        except Exception as e:
            print(f"Telegram error: {e}")
        time.sleep(2)

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Prolific Token Updater</title>
    <style>
        body { font-family: sans-serif; max-width: 400px; margin: 100px auto; text-align: center; background: #f5f5f5; }
        button { padding: 15px 30px; font-size: 18px; background: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; }
        button:hover { background: #45a049; }
        #status { margin-top: 20px; font-size: 16px; }
    </style>
</head>
<body>
    <h2>🤖 Prolific Bot</h2>
    <p>Открой эту страницу находясь на app.prolific.com и нажми кнопку</p>
    <button onclick="updateToken()">Обновить токен</button>
    <div id="status"></div>
    <script>
        async function updateToken() {
            const status = document.getElementById('status');
            status.innerHTML = '<b>⏳ Обновляю...</b>';
            try {
                const key = Object.keys(localStorage).find(k => k.startsWith('oidc.user:https://auth.prolific.com'));
                if (!key) { status.innerHTML = '<b>❌ Не найден токен. Залогинься на Prolific.</b>'; return; }
                const data = JSON.parse(localStorage.getItem(key));
                const token = data.refresh_token;
                if (!token) { status.innerHTML = '<b>❌ Refresh token не найден.</b>'; return; }
                const resp = await fetch('/update_token', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token })
                });
                if (resp.ok) { status.innerHTML = '<b>✅ Токен обновлён! Бот снова работает.</b>'; }
                else { status.innerHTML = '<b>❌ Ошибка при обновлении.</b>'; }
            } catch(e) { status.innerHTML = '<b>❌ Ошибка: ' + e.message + '</b>'; }
        }
    </script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())

    def do_POST(self):
        if self.path == '/update_token':
            length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(length))
            token = body.get('token')
            if token:
                save_refresh_token(token)
                refresh_access_token()
                send_telegram("🔄 Токен обновлён вручную через браузер!")
                self.send_response(200)
            else:
                self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_bot():
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

init_db()
refresh_access_token()
send_telegram("✅ Бот запущен! Напиши /stats для статистики.")

threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=check_telegram_commands, daemon=True).start()

print(f"Starting web server on port {PORT}")
HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
