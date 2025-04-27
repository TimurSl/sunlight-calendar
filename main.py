import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

from cogs.Notifier import Notifier



load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True




class CustomBot(commands.Bot):
    async def setup_hook(self):
        await bot.add_cog(Notifier(bot))

        print("Reloaded all modules & synced commands.")

bot = CustomBot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

bot.run(TOKEN)
