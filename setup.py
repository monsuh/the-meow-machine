import discord
import os

from dotenv import load_dotenv

client = discord.Client()

load_dotenv()
discordToken = os.getenv("DISCORD_TOKEN")