import discord
import os
import psycopg2

from dotenv import load_dotenv

client = discord.Client()

load_dotenv()
discordToken = os.getenv("DISCORD_TOKEN")

databaseURL = os.getenv("DATABASE_URL")

connection = psycopg2.connect(databaseURL)
cursor = connection.cursor()