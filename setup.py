import discord
import os
import psycopg2

from dotenv import load_dotenv
from filerw import DatabaseConnection

client = discord.Client()

load_dotenv()
discordToken = os.getenv("DISCORD_TOKEN")

databaseURL = os.getenv("DATABASE_URL")

databaseConn = DatabaseConnection(databaseURL)