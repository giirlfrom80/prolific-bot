import requests
import time

TELEGRAM_TOKEN = "8626572170:AAG7BENnkyWYjKg-V7yAxwlVhqgYOVp4xvQ"
CHAT_ID = "541545419"
PROLIFIC_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InljRnBPRDNkZnNIaHA1MUpSdngxUSJ9.eyJleHRlcm5hbFVzZXJJZCI6IjY5ZTUzMWU4ZjBmNWVkYzExODFiZmQzNCIsImNsaWVudE5hbWUiOiJGcm9udCBFbmQiLCJpc3MiOiJodHRwczovL2F1dGgucHJvbGlmaWMuY29tLyIsInN1YiI6ImF1dGgwfDVjMzUxY2ZmLTVhOWMtNGNkMC1hMWIxLTJjMjYyNDBkMWNhMCIsImF1ZCI6WyJodHRwczovL2ludGVybmFsLWFwaS5wcm9saWZpYy5jb20iLCJodHRwczovL3Byb2xpZmljLnVrLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NzY3MDg5MTYsImV4cCI6MTc3NjcxMjUxNiwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBvZmZsaW5lX2FjY2VzcyIsImF6cCI6InBRSlFzMUVLTThUOEMwQlA1SGxQY2xGYzlZbmI5N2ZQIn0.Ni0f3Gb7sBNSVgLlhWjKv1I-tiqM-6Ft16uwgqF6Y0ivhAHSL7Y1pzW1e-RhqKBAHaX9BDejbIT7xmGcgDsbfz2AT-AnHpJcwC7g8ZAsSHjkv13anJyEMC3Lom4vXJ2coo8vMcllQm_ySooED5tCQHtSdUM6Kqm35JgOl6Dn76clAozcg9yeCJ-bNDQZBKHTZ6s2tVaoNZJoRhTR_U57sr4XU-xkMoA1I_7Amqyv9OfnX23MWaItUOWNA7epiOeLbeR8gm6hX_mc9elw6qUss70F2U1mCgZGNvsG86z4jhIeN5FZPn-9K3y1Fh6F2_qa2zICa_G9TMBxOVK7H6xUaw"

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
