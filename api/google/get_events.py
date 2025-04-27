import datetime


from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

from useful import get_pwd
load_dotenv()


SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
SERVICE_ACCOUNT_FILE = os.path.join(get_pwd(), "service_account.json")
CALENDAR_ID = os.getenv("CALENDAR_ID")

# Авторизация
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=creds)

# Временные границы: с начала дня до конца завтрашнего дня
now = datetime.datetime.now(datetime.timezone.utc)
start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
end_of_tomorrow = start_of_today + datetime.timedelta(days=5)

# Получение событий
events_result = service.events().list(
    calendarId=CALENDAR_ID,
    timeMin=start_of_today.isoformat(),
    timeMax=end_of_tomorrow.isoformat(),
    singleEvents=True,
    orderBy='startTime'
).execute()

events = events_result.get('items', [])

# Вывод событий
for event in events:
    summary = event.get('summary', 'Без названия')
    start_time_str = event['start'].get('dateTime', event['start'].get('date'))
    start_time = datetime.datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
    unix_time = int(start_time.timestamp())
    print(f"{summary} — {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC — UNIX: {unix_time}")