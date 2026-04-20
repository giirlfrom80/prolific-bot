import requests
import time

TELEGRAM_TOKEN = "8626572170:AAG7BENnkyWYjKg-V7yAxwlVhqgYOVp4xvQ"
CHAT_ID = "541545419"
PROLIFIC_EMAIL = "m.dolgopolova.03@gmail.com"
PROLIFIC_PASSWORD = "paRhiw-9zydfy-qibdis"

seen_ids = set()

def get_prolific_token():
    r = requests.post(
        "https://internal-api.prolific.com/api/v1/token/",
        json={"email": PROLIFIC_EMAIL, "password": PROLIFIC_PASSWORD}
    )
    if r.status_code == 200:
        return r.json().get("token")
    print(f"Auth error: {r.status_code} {r.text}")
    return None

def get_studies(token):
    url = "https://internal-api.prolific.com/api/v1/participant/studies/?sortBy=published_at&orderBy=asc&status=ACTIVE"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code == 200:
        return r.json().get("results", [])
    return []

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

token = get_prolific_token()
send_telegram("✅ Бот запущен! Слежу за новыми исследованиями на Prolific.")
token_refresh = time.time()

while True:
    if time.time() - token_refresh > 3000:
        token = get_prolific_token()
        token_refresh = time.time()
    if token:
        studies = get_studies(token)
        for study in studies:
            sid = study.get("id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                name = study.get("name", "Без названия")
                reward = study.get("reward", "?")
                duration = study.get("average_completion_time", "?")
                link = f"https://app.prolific.com/studies/{sid}"
                msg = f"🟢 <b>Новое исследование!</b>\n\n{name}\n💰 {reward}p\n⏱ ~{duration} мин\n\n{link}"
                send_telegram(msg)
    time.sleep(20)
