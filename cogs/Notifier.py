import asyncio

import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

from api.google.get_events import unix_time
from handlers.calendar_handler import CalendarHandler

load_dotenv()
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_NOTIFICATION_CHANNEL_ID"))

class Notifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.calendar = CalendarHandler()
        self.notified = set()
        self.check_calendar_events.start()

    @tasks.loop(minutes=1)
    async def check_calendar_events(self):
        now = datetime.now(timezone.utc)
        events = self.calendar.get_upcoming_events(days=1)
        channel = self.bot.get_channel(DISCORD_CHANNEL_ID)

        for event in events:
            event_id = event['id']
            summary = event.get('summary', 'Untitled Event')
            description = event.get('description', 'No description provided')
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            unix_timestamp = int(start_time.timestamp())

            now = datetime.now(timezone.utc)
            notification_deltas = [
                ('24h', timedelta(hours=24)),
                ('3h', timedelta(hours=3)),
                ('1h', timedelta(hours=1)),
                ('now', timedelta(seconds=30))
            ]

            for label, delta in notification_deltas:
                notify_time = start_time - delta
                if notify_time.tzinfo is None:
                    notify_time = notify_time.replace(tzinfo=timezone.utc)

                unix_timestamp = int(start_time.timestamp())
                key = f"{event_id}_{label}"

                if abs((now - notify_time).total_seconds()) <= 60 and key not in self.notified:
                    time_until = start_time - now

                    if time_until.total_seconds() > 0:
                        # Событие ещё впереди — пишем сколько осталось
                        time_remaining_str = discord.utils.format_dt(start_time, style='R')  # <t:...:R>
                        status_msg = f"⏳ Starts {time_remaining_str}"
                        embed_notification = discord.Embed(
                            title=f"🔔 Upcoming Event: {summary}",
                            description=f"{description}\n\n🕒 Start time: <t:{unix_timestamp}:F>\n{status_msg}",
                            color=discord.Color.blue()
                        )
                    else:
                        # Событие уже началось
                        status_msg = f"✅ Event has **started**"
                        embed_notification = discord.Embed(
                            title=f"🔔 Event Started: {summary}",
                            description=f"{description}\n\n🕒 Start time: <t:{unix_timestamp}:F>\n{status_msg}",
                            color=discord.Color.green()
                        )

                    await channel.send("@here", embed=embed_notification)
                    self.notified.add(key)
                    break

    @check_calendar_events.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

        channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
        await channel.send("🔔 Notifier is now active! I will notify you about upcoming events.")
        await asyncio.sleep(10)
        await channel.purge(limit=1, check=lambda m: m.content.startswith("🔔 Notifier is now active!"))
