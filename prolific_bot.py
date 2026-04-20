import requests
import time

TELEGRAM_TOKEN = "8626572170:AAG7BENnkyWYjKg-V7yAxwlVhqgYOVp4xvQ"
CHAT_ID = "541545419"
PROLIFIC_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InljRnBPRDNkZnNIaHA1MUpSdngxUSJ9.eyJleHRlcm5hbFVzZXJJZCI6IjY5ZTUzMWU4ZjBmNWVkYzExODFiZmQzNCIsImNsaWVudE5hbWUiOiJGcm9udCBFbmQiLCJtZmFfZmFjdG9ycyI6W10sImlzcyI6Imh0dHBzOi8vYXV0aC5wcm9saWZpYy5jb20vIiwic3ViIjoiYXV0aDB8NWMzNTFjZmYtNWE5Yy00Y2QwLWExYjEtMmMyNjI0MGQxY2EwIiwiYXVkIjpbImh0dHBzOi8vaW50ZXJuYWwtYXBpLnByb2xpZmljLmNvbSIsImh0dHBzOi8vcHJvbGlmaWMudWsuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTc3NjY5Mjg4MiwiZXhwIjoxNzc2Njk2NDgyLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIG9mZmxpbmVfYWNjZXNzIiwiYXpwIjoicFFKUXMxRUtNOFQ4QzBCUDVIbFBjbEZjOVluYjk3ZlAifQ.Zc42_FB8Gm-AG0QIRSqvwMi7zH95T38C45w8TYzmS26BgD7BQjqRpXH3D3EtV9EtGNdk6RILkmMbpSLVZPfTYQiFKbVt_r2AAzGmNxsKVZvItrkK4drWg-x5wqVeQ-vd470F3Gs9Zh5ZQQk3APzxvj_OH1oK1OveU6SzY4iiOxB3EHSPRG7bTkVEbv_7DtSWinAQfvO8XzFWyCpqws_wZBoDSP96Jufr97srK-n2ogYN70Mt-qAxt4jDfILAEE-6iHLGFXjM6Njf3wbQX48vy8SHo6w_yFvHFfELRWtw2fuasoJ8voPrIgT29hoit3fCdqqJCWvBJ5GbpmZbepj4Ag"

HEADERS = {
    "Authorization": f"Bearer {PROLIFIC_TOKEN}",
    "Content-Type": "application/json"
}

seen_ids = set()

def get_studies():
    url = "https://internal-api.prolific.com/api/v1/participant/studies/?sortBy=published_at&orderBy=asc&status=ACTIVE"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:500]}")
        if r.status_code == 200:
            return r.json().get("results", [])
    except Exception as e:
        print(f"Error: {e}")
    return []

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

send_telegram("✅ Бот запущен! Слежу за новыми исследованиями на Prolific.")

while True:
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
