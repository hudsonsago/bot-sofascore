import time
import requests
from curl_cffi import requests as c_requests

# Credenciais
TELEGRAM_BOT_TOKEN = "8725940003:AAHRHvUYcVQ6fW2_6pbB0QJxTvJOCnXZQYg"
TELEGRAM_CHAT_ID = "1099565196"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.sofascore.com/'
}

# Bypass do proxy restrito do PythonAnywhere
NO_PROXY = {"http": "", "https": ""}

alerted_events = {}

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro Telegram: {e}")

def get_live_events():
    url = "https://api.sofascore.com/api/v3/event/live"
    try:
        response = c_requests.get(
            url, 
            headers=HEADERS, 
            impersonate="chrome120", 
            proxies=NO_PROXY
        )
        if response.status_code == 200:
            return response.json().get('events', [])
        return []
    except Exception as e:
        print(f"Erro SofaScore: {e}")
        return []

def parse_stat_group(groups, stat_name):
    for group in groups:
        for item in group.get('statisticsItems', []):
            if item.get('name', '').lower() == stat_name.lower():
                return int(item.get('home', 0)), int(item.get('away', 0))
    return 0, 0

def get_match_stats(event_id):
    url = f"https://api.sofascore.com/api/v3/event/{event_id}/statistics"
    try:
        response = c_requests.get(
            url, 
            headers=HEADERS, 
            impersonate="chrome120", 
            proxies=NO_PROXY
        )
        if response.status_code != 200:
            return None

        data = response.json().get('statistics', [])
        if not data:
            return None

        all_period = next((p for p in data if p.get('period') == 'ALL'), None)
        if not all_period:
            return None

        groups = all_period.get('groups', [])
        
        home_created, away_created = parse_stat_group(groups, 'Big chances')
        home_missed, away_missed = parse_stat_group(groups, 'Big chances missed')
        home_target, away_target = parse_stat_group(groups, 'Shots on target')

        return {
            'home_created': home_created,
            'away_created': away_created,
            'total_created': home_created + away_created,
            'home_missed': home_missed,
            'away_missed': away_missed,
            'home_target': home_target,
            'away_target': away_target
        }
    except Exception:
        return None

def analyze_and_notify():
    events = get_live_events()
    print(f"Buscando... Jogos ao vivo: {len(events)}")

    for event in events:
        event_id = event.get('id')
        home_team = event.get('homeTeam', {}).get('name')
        away_team = event.get('awayTeam', {}).get('name')
        home_score = event.get('homeScore', {}).get('current', 0)
        away_score = event.get('awayScore', {}).get('current', 0)
        description = event.get('status', {}).get('description', '')

        stats = get_match_stats(event_id)
        if not stats:
            continue

        total_big_chances = stats['total_created']
        total_goals = home_score + away_score
        chances_sem_gol = total_big_chances - total_goals
        last_alert_level = alerted_events.get(event_id, 0)

        # NÍVEL 2: URGENTE (3+ chances sem gol)
        if chances_sem_gol >= 3 and last_alert_level < 3:
            if total_goals == 0:
                cabecalho = "🚨🚨🚨 *URGENTE: 0x0 COM 3+ GRANDES CHANCES* 🚨🚨🚨"
            else:
                cabecalho = f"🚨🚨🚨 *URGENTE: {chances_sem_gol} GRANDES CHANCES APÓS O ÚLTIMO GOL* 🚨🚨🚨"

            msg = (
                f"{cabecalho}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ *PRESSÃO EXTREMA NA PARTIDA!*\n\n"
                f"⚽ *{home_team}* {home_score} x {away_score} *{away_team}*\n"
                f"⏱️ Status: {description}\n\n"
                f"🎯 *Grandes Chances Totais:* {total_big_chances} ({stats['home_created']} x {stats['away_created']})\n"
                f"❌ *Grandes Chances Perdidas:* {stats['home_missed'] + stats['away_missed']}\n"
                f"🥊 *Chutes no Gol:* {stats['home_target']} x {stats['away_target']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔗 [ABRIR NO SOFASCORE](https://www.sofascore.com/event/{event_id})"
            )
            send_telegram_alert(msg)
            alerted_events[event_id] = 3
            time.sleep(2)

        # NÍVEL 1: ATENÇÃO (2 chances sem gol)
        elif chances_sem_gol == 2 and last_alert_level < 2:
            if total_goals == 0:
                cabecalho = "🚨 *ALERTA: 0x0 COM 2 GRANDES CHANCES*"
            else:
                cabecalho = "🔥 *ALERTA: 2 GRANDES CHANCES APÓS O ÚLTIMO GOL*"

            msg = (
                f"{cabecalho}\n\n"
                f"⚽ *{home_team}* {home_score} x {away_score} *{away_team}*\n"
                f"⏱️ Status: {description}\n\n"
                f"🎯 *Grandes Chances Totais:* {total_big_chances} ({stats['home_created']} x {stats['away_created']})\n"
                f"❌ *Grandes Chances Perdidas:* {stats['home_missed'] + stats['away_missed']}\n"
                f"🥊 *Chutes no Gol:* {stats['home_target']} x {stats['away_target']}\n\n"
                f"🔗 [Abrir no SofaScore](https://www.sofascore.com/event/{event_id})"
            )
            send_telegram_alert(msg)
            alerted_events[event_id] = 2
            time.sleep(2)

if __name__ == "__main__":
    send_telegram_alert("🤖 *Bot do SofaScore Iniciado no PythonAnywhere!*")
    while True:
        try:
            analyze_and_notify()
        except Exception as e:
            print(f"Erro no loop: {e}")
        time.sleep(150)
