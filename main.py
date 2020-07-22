'''
Moved functions into modules for better organization
'''

import discord
import asyncio
import logging
import errors
import filerw
import formatdt
import processEvent

from setup import client, discordToken
from datetime import datetime, timedelta
from random import randint
from pathlib import Path

@client.event
async def on_ready():
     await client.change_presence(activity=discord.Game(name='!help'))
     logging.disable()
     logging.basicConfig(filename='console.log', filemode='w', level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')
     logging.info("We online boys")
     try:
          await processEvent.setTimerForClosestEvent()
     except IndexError:
          logging.info("no items in events list")

@client.event
async def on_message(message):
     if message.author == client.user:
          return
     elif message.content.startswith("!help"):
          await message.channel.send(">>> Commands:\n!poke @someone\n!catpic\n!event {event name} [date (today OR tomorrow OR YYYY/MM/DD) hours:minutesAM/PM (NOTE ALL TIMES IN EST)]")
     elif message.content.startswith("!poke"):
          if len(message.mentions) != 0:
               for mention in message.mentions:
                    await message.channel.send("{} just poked {}. it's super effective.".format(message.author.mention, mention.mention))      
          else:
               await message.channel.send("{} just poked themselves out of confusion.".format(message.author.mention))
     elif message.content.startswith("!catpic"):
          catpic = Path("pics/cat.jpg")
          await message.channel.send(file=discord.File(catpic))
     elif message.content.startswith("!stuffypic"):
          try:
               stuffyName = message.content.split()[1]
               randomNumber = 1
               stuffyPicsFolder = Path("pics")
               await message.channel.send(file=discord.File(stuffyPicsFolder / "{}_{}.png".format(stuffyName, str(randomNumber))))
          except FileNotFoundError:
               await message.channel.send("an oopsie happened there are no stuffies named {}".format(stuffyName))
          except IndexError:
               await message.channel.send("did you remember to name which stuffy you wanted?")
     elif message.content.startswith("!simulatesteven"):
          await message.channel.send("indeed")
     elif message.content.startswith("!event"):
          try:
               event = await processEvent.processEventMessage(message)
               logging.info("New event received: {}".format(event[0:-1]))
               isNewEventNewestEvent = await filerw.appendNewEventToFile("events.txt", event)
               if isNewEventNewestEvent == True:
                    try:
                         await processEvent.cancelRunningEvent()
                         await processEvent.setTimerForClosestEvent()
                    except Exception as e:
                         logging.info("Something went wrong appending the new event {}".format(e))
          except ValueError:
               await message.channel.send("did you type everything in correctly?")
          except errors.RepetitionError:
               await message.channel.send("you already set this as an event")
          except Exception as e:
               logging.info("Something went wrong appending the new event {}".format(e))
          else:
               await message.channel.send("inputted")
     elif message.content.startswith("!recurringevent"):
          try:
               eventsList = await processEvent.processRecurringEventMessage(message)
               for event in eventsList:
                    isNewEventNewestEvent = await filerw.appendNewEventToFile("events.txt", event)
                    if isNewEventNewestEvent == True:
                         try:
                              await processEvent.cancelRunningEvent()
                              await processEvent.setTimerForClosestEvent()
                         except Exception as e:
                              logging.info("Something went wrong waiting for the new event {}".format(e))
          except ValueError:
               await message.channel.send("did you type everything in correctly?")
          except errors.RepetitionError:
               await message.channel.send("you already set this as an event")
          except errors.WrongCommandError:
               await message.channel.send("you should use !event instead for events occurring at a single time")
          except Exception as e:
               logging.info("Something went wrong appending the new event {}".format(e))
          else:
               await message.channel.send("inputted")
     elif message.content.startswith("!deleteevent"):
          try:
               event = await processEvent.processEventMessage(message)
               await processEvent.deleteEvent("events.txt", event)
               await processEvent.cancelRunningEvent()
               await processEvent.setTimerForClosestEvent()
               channel = client.get_channel(int(event[event.find("<") + 1: event.find(">")].split()[1]))
               await asyncio.create_task(channel.send("{} has been deleted".format(event[event.find("{") + 1: event.find("}")])))
          except Exception as e:
               logging.info("Something went wrong appending the new event {}".format(e))
               await asyncio.create_task(message.channel.send("something has gone wrong here"))
     elif message.content.startswith("!showevents"):
          try:
               allEventsList = await filerw.readFile("events.txt")
               channelEventsList = []
               for event in allEventsList:
                    if event.find(str(message.channel.id)) != -1:
                         eventTime = await formatdt.humanFormatEventTime(event)
                         formattedEvent = "{} at {}:{}{}\n".format(event[event.find("{") + 1:event.find("}")], str(eventTime[0]), eventTime[1], eventTime[2])
                         channelEventsList.append(formattedEvent)
               logging.info(channelEventsList)
               if len(channelEventsList) == 0:
                    await asyncio.create_task(message.channel.send("You have no events scheduled."))
               else:
                    channelEventsText = ""
                    for event in channelEventsList:
                         channelEventsText = channelEventsText + event
                    await asyncio.create_task(message.channel.send("Please note that events are channel specific:\n{}".format(channelEventsText)))
          except Exception as e:
               logging.info("Something went wrong appending the new event {}".format(e))
               await asyncio.create_task(message.channel.send("something has gone wrong here"))
     if message.author == client.user:
          return
     elif message.content.lower().find("sippy") != -1:
          if message.content.lower().find("good job sippy") != -1:
               await message.channel.send("Why thank you {}! I pride myself on my excellent quality of work. Although I am passionate about this job and do it because I love it, it is always nice to get a little validation from a nice person like you.".format(message.author.mention))
          else:
               await message.channel.send("meow")

client.run(discordToken)
