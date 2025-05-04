import asyncio

import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from useful import get_pwd

from handlers.calendar_handler import CalendarHandler

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.path.exists(os.path.join(get_pwd(), 'logs')):
    os.makedirs(os.path.join(get_pwd(), 'logs'))

file_handler = logging.FileHandler(os.path.join(get_pwd(), 'logs', 'notifier.log'))
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)



import re

def convert_html_to_discord(html_text: str) -> str:
    # Convert bold tags
    text = re.sub(r'<\/?b>', '**', html_text)
    # Convert <br> to newlines
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Convert <a href="url">text</a> to [text](url)
    text = re.sub(r'<a href="([^"]+)"[^>]*>(.*?)<\/a>', r'[\2](\1)', text)
    # Remove any other leftover HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


load_dotenv()
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_NOTIFICATION_CHANNEL_ID"))

class Notifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.calendar = CalendarHandler()
        self.notified = set()
        self.check_calendar_events.start()

    @tasks.loop(minutes=1)
    async def check_calendar_events(self, called_from_user=False):
        await self.gather_events(called_from_user)

    async def gather_events(self, called_from_user, ctx=None):
        events = self.calendar.get_upcoming_events(days=1)
        channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
        for event in events:
            event_id = event['id']
            summary = event.get('summary', 'Untitled Event')
            description = event.get('description', 'No description provided')
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            logger.info(f"Event ID: {event_id}, Summary: {summary}, Start: {start_str}")

            start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            start_unix = int(start_time.timestamp())
            logger.info(f"Start time (ISO): {start_str}, Start time (Unix): {start_unix}")

            now_unix = int(datetime.now(timezone.utc).timestamp())
            notification_deltas = [
                ('8h', 8 * 3600),
                ('3h', 3 * 3600),
                ('1h', 1 * 3600),
                ('now', 0),
            ]

            for label, delta in notification_deltas:
                notify_time_unix = start_unix - delta
                logger.info(f"Notify time ({label}): {notify_time_unix}, Current time: {now_unix}")
                key = f"{event_id}_{label}"

                if notify_time_unix <= now_unix and key not in self.notified:
                    time_until = start_unix - now_unix

                    if time_until > 0:
                        # Событие ещё впереди — пишем сколько осталось
                        time_remaining_str = discord.utils.format_dt(start_time, style='R')  # <t:...:R>
                        logger.info(f"Time remaining: {time_remaining_str}")
                        status_msg = f"⏳ Starts {time_remaining_str}"
                        embed_notification = discord.Embed(
                            title=f"🔔 Upcoming Event: {summary}",
                            description=f"{convert_html_to_discord(description)}\n\n🕒 Start time: <t:{start_unix}:F>\n{status_msg}",
                            color=discord.Color.blue()
                        )
                        logger.info(f"Sending notification for event: {summary}")
                    else:
                        logger.info(f"Event has already started: {summary}")
                        # Событие уже началось
                        status_msg = f"✅ Event has **started**"
                        embed_notification = discord.Embed(
                            title=f"🔔 Event Started: {summary}",
                            description=f"{convert_html_to_discord(description)}\n\n🕒 Start time: <t:{start_unix}:F>\n{status_msg}",
                            color=discord.Color.green()
                        )
                        logger.info(f"Sending notification for event: {summary}")
                        # remove the event from the notified set

                    embed_notification.set_footer(text="Event ID: " + event_id)
                    if called_from_user:
                        if ctx:
                            await ctx.send(embed=embed_notification)
                            logger.info(f"Notification sent to user {ctx.author} for event: {summary}")
                    else:
                        await channel.send("@here" if not called_from_user else "", embed=embed_notification)
                        logger.info(f"Notification sent for event: {summary}")

                        self.notified.add(key)
                        logger.info(f"Added to notified set: {key}")
                        break

    @commands.hybrid_command(name="events", description="Get upcoming events from your calendar")
    async def events(self, ctx):
        logger.info(f"User {ctx.author} requested events.")
        await self.gather_events(called_from_user=True, ctx=ctx)
        logger.info(f"User {ctx.author} notified about events.")

    @check_calendar_events.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

        channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
        await channel.send("🔔 Notifier is now active! I will notify you about upcoming events.")
        await asyncio.sleep(10)
        await channel.purge(limit=1, check=lambda m: m.content.startswith("🔔 Notifier is now active!"))
