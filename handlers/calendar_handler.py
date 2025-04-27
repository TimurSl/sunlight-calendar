from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

from useful import get_pwd

load_dotenv()

SERVICE_ACCOUNT_FILE = os.path.join(get_pwd(), 'service_account.json')
CALENDAR_ID = os.getenv("CALENDAR_ID")

class CalendarHandler:
    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/calendar.readonly"])
        self.service = build('calendar', 'v3', credentials=self.creds)

    def check_for_changes(self):
        now = datetime.now(timezone.utc)
        max_time = now + timedelta(days=2)

        events = self.service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now.isoformat(),
            timeMax=max_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        changes = []

        for e in events:
            event_id = e['id']
            etag = e['etag']

            if event_id not in self.known_events:
                changes.append(('new', e))
            elif self.known_events[event_id] != etag:
                changes.append(('updated', e))

            self.known_events[event_id] = etag

        # Удалённые события — те, что больше не вернулись
        current_ids = {e['id'] for e in events}
        deleted_ids = [eid for eid in self.known_events if eid not in current_ids]
        for eid in deleted_ids:
            changes.append(('deleted', {'id': eid}))
            del self.known_events[eid]

        return changes

    def get_upcoming_events(self, days=1):
        now = datetime.now(timezone.utc)
        max_time = now + timedelta(days=days)
        events = self.service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now.isoformat(),
            timeMax=max_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])
        return events
