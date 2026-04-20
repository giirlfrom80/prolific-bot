import requests
import time

TELEGRAM_TOKEN = "8626572170:AAG7BENnkyWYjKg-V7yAxwlVhqgYOVp4xvQ"
CHAT_ID = "541545419"
CLIENT_ID = "pQJQs1EKM8T8C0BP5HlPclFc9Ynb97fP"
REFRESH_TOKEN = "v1.MS-ThHKd2u7Y9k-AgcOGwqCJg5puDWFwonAfPzL-DerwKypGKI8Lk8L43Inc1oCHVr3kys-ncvudN6t8y1R_bzA"

seen_ids = set()
access_token = None

def refresh_access_token():
    global access_token
    r = requests.post(
        "https://auth.prolific.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
        }
    )
    if r.status_code == 200:
        access_token = r.json().get("access_token")
        print("Token refreshed OK")
    else:
        print(f"Refresh error: {r.status_code} {r.text}")

def get_studies():
    url = "https://internal-api.prolific.com/api/v1/participant/studies/?sortBy=published_at&orderBy=asc&status=ACTIVE"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            return r.json().get("results", [])
    except Exception as e:
        print(f"Error: {e}")
    return []

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

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
            reward = study.get("reward", "?")
            duration = study.get("average_completion_time", "?")
            link = f"https://app.prolific.com/studies/{sid}"
            msg = f"🟢 <b>Новое исследование!</b>\n\n{name}\n💰 {reward}p\n⏱ ~{duration} мин\n\n{link}"
            send_telegram(msg)
    time.sleep(20)
