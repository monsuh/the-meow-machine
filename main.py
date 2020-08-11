'''
Moved functions into modules for better organization
'''

import discord
import asyncio
import logging
import errors
import formatdt
import processEvent

from setup import client, discordToken, databaseConn
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
     except Exception as e:
          logging.info("Error with initializing: {}".format(e))
     try:
          availableGuilds = client.guilds
          for i in range(0, len(availableGuilds), 1):
               availableGuilds[i] = availableGuilds[i].id
          logging.info(availableGuilds)
          await asyncio.create_task(processEvent.checkTimezoneGuildAndDMs(availableGuilds))
     except Exception as e:
          logging.info("Error with checking guilds: {}".format(e))

@client.event
async def on_message(message):
     if message.author == client.user:
          return
     elif message.content.startswith("!help"):
          profilePicURL = "https://cdn.discordapp.com/avatars/727349589870641243/d76f675a731663b4ff92db78c6093ff3.png?size=256" 
          helpMessage = discord.Embed(
               description = "Type these into chat so that Meow Machine (aka Sippy) knows how to help you",
               type = "rich", 
               colour = discord.Colour.dark_green()
          )
          helpMessage.set_author(name = "Commands", icon_url = profilePicURL)
          helpMessage.add_field(name = "!poke", value = "Give a quick poke\n`!poke`\n`!poke @someone`", inline = False)
          helpMessage.add_field(name = "!catpic", value = "Get a pic of a lovely little \"cat\"", inline = False)
          helpMessage.add_field(name = "!stuffypic", value = "Get a pic of a cute stuffy\n`!stuffypic stuffy-name`\nOptions for stuffy name include dozer, mrrat, oracle, oswald, sippy, snorlax, sparky, stingray, and strawberry", inline = False)
          helpMessage.add_field(name = "!simulatesteven", value = "Allow the spirit of a 17-year-old boy named Steven to temporarily possess Sippy", inline = False)
          helpMessage.add_field(name = "!event", value = "Set an event which Sippy will remind you of at the designated time\n`{}`\n For date, use today OR tomorrow OR YYYY/MM/DD.\nWrite time as hours:minutesAM/PM (ex. 1:01PM).\nTimezone is optional if you use !settimezone beforehand. See !settimezone for a list of possible timezones.".format(r"!event {name} [date time timezone]"), inline = False)
          helpMessage.add_field(name = "!recurringevent", value = "Set events that happen multiple times\n`{}`\nFor date, refer to !event. Note that you can specify the date once if the recurring event happens throughout only one day.\nFor time, refer to !event. Note that an event will not be set for the ending time.\nTimezone is optional if you use !settimezone beforehand. See !settimezone for a list of possible timezones.\n Interval refers to the time between each event in minutes.".format(r"!recurringevent {name} [date-date time-time timezone] <interval>"), inline = False)
          helpMessage.add_field(name = "!settimezone", value = "Set the timezone of your channel\n`!settimezone timezone`\nClick [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for a list of timezone names", inline = False)
          helpMessage.add_field(name = "!deleteevent", value = "Delete a singular event\n`{}`\nRefer to !event for formatting instructions for date, time, and timezone.".format(r"!deleteevent {name} [date time timezone]"), inline = False)
          helpMessage.add_field(name = "!deleterecurringevent", value = "Delete a recurring event\n`{}`\nRefer to !recurringevent for formatting instructions for date, time, and timezone.".format(r"!deleterecurringevent {name} [date-date time-time timezone] <interval>"), inline = False)
          helpMessage.add_field(name = "!showevents", value = "See the events that you have set within a channel", inline = False)
          helpMessage.set_footer(text = "If you think Sippy's doing a good job, make sure to let her know!")
          await message.channel.send(embed = helpMessage)
     elif message.content.startswith("!poke"):
          if len(message.mentions) != 0:
               for mention in message.mentions:
                    await message.channel.send("{} just poked {}. It's super effective.".format(message.author.mention, mention.mention))      
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
               await message.channel.send("You must be mistaken. There are no stuffies named {}".format(stuffyName))
          except IndexError:
               await message.channel.send("Did you remember to name which stuffy you wanted?")
     elif message.content.startswith("!simulatesteven"):
          await message.channel.send(":o")
          await message.channel.send("indeed")
     elif message.content.startswith("!event"):
          try:
               event = await processEvent.processEventMessage(message)
               logging.info("New event received: {}".format(event))
               await databaseConn.insertEvent(event)
               await processEvent.determineIfNewestEventIsMostPertinent(event)
          except errors.EventTooEarlyError:
               logging.info("ERROR: Event time set before current time")
               await message.channel.send("You are trying to schedule this event to occur before the current time. NO! I'm gonna cry :'(")
          except ValueError:
               await message.channel.send("Did you type everything in correctly?")
          except errors.RepetitionError:
               await message.channel.send("You already set this as an event.")
          except errors.NoTimeZoneError:
               logging.info("ERROR: No specified timezone")
               await message.channel.send("You did not specify a timezone and you do not have a timezone saved for this channel. You can set one with !settimezone and check !help for a list of valid timezones.")
          except errors.NoServerConnectionError:
               await message.channel.send("Sorry, I can't process your request because the servers are down right now. :(")
          except Exception as e:
               logging.info("Something went wrong waiting for the new event: {}".format(e))
          else:
               await message.channel.send("Inputted.")
     elif message.content.startswith("!recurringevent"):
          try:
               eventsList = await processEvent.processRecurringEventMessage(message)
               if len(eventsList) == 0:
                    raise ValueError
               elif len(eventsList) > 20:
                    raise errors.TooManyEventsError
               else:
                    for event in eventsList:
                         await databaseConn.insertEvent(event)
                    await processEvent.determineIfNewestEventIsMostPertinent(eventsList[0])
          except ValueError:
               await message.channel.send("Did you type everything in correctly?")
          except errors.RepetitionError:
               await message.channel.send("You already set this as an event.")
          except errors.WrongCommandError:
               await message.channel.send("You should use !event for events occurring at a single time.")
          except errors.EventTooEarlyError:
               logging.info("ERROR: Event time set before current time")
               await message.channel.send("You are trying to schedule this event to occur before the current time. NO! I'm gonna cry :'(")
          except errors.NoTimeZoneError:
               logging.info("ERROR: No specified timezone")
               await message.channel.send("You did not specify a timezone and you do not have a timezone saved for this channel. You can set one with !settimezone and check !help for a list of valid timezones.")
          except errors.TooManyEventsError:
               logging.info("ERROR: Too many events to insert")
               await message.channel.send("Whoa there bucko, that's too many events. I'm baby, I cannot hold that many events.")
          except errors.NoServerConnectionError:
               await message.channel.send("Sorry, I can't process your request because the servers are down right now. :(")
          except Exception as e:
               logging.info("Something went wrong waiting for the new event: {}".format(e))
          else:
               await message.channel.send("Inputted.")
     elif message.content.startswith("!deleteevent"):
          try:
               event = await processEvent.processEventMessage(message)
               logging.info("name: {}, channel: {}, datetime: {}".format(event[0], event[2], event[3]))
               eventToDelete = await databaseConn.findEntries("events", {"name": event[0], "channel": event[2], "datetime": event[3]}, ["name"])
               if len(eventToDelete) > 0:
                    await databaseConn.deleteEntry("events", {"name": event[0], "channel": event[2], "datetime": event[3]})
                    await processEvent.cancelRunningEvent()
                    await processEvent.setTimerForClosestEvent()
                    channel = client.get_channel(event[2])
                    await channel.send("{} has been deleted".format(event[0]))
               else:
                    raise errors.EventDoesNotExistError
          except errors.EventDoesNotExistError:
               await message.channel.send("You are trying to delete an event that doesn't exist.")
          except errors.NoServerConnectionError:
               await message.channel.send("Sorry, I can't process your request because the servers are down right now. :(")
          except errors.EventTooEarlyError:
               logging.info("ERROR: Event time set before current time")
               await message.channel.send("You are deleting an event that should have already occurred and subsequently been deleted.")
          except errors.NoTimeZoneError:
               logging.info("ERROR: No specified timezone")
               await message.channel.send("You did not specify a timezone and you do not have a timezone saved for this channel. You can set one with !settimezone and check !help for a list of valid timezones.")
          except Exception as e:
               logging.info("Something went wrong deleting the new event {}".format(e))
               await message.channel.send("Something has gone wrong deleting your event.")
     elif message.content.startswith("!deleterecurringevent"):
          try:
               eventsList = await processEvent.processRecurringEventMessage(message)
               if len(eventsList) == 0:
                    raise ValueError
               else:
                    for event in eventsList:
                         eventToDelete = await databaseConn.findEntries("events", {"name": event[0], "channel": event[2], "datetime": event[3]}, ["name"])
                         if len(eventToDelete) == 0:
                              raise errors.EventDoesNotExistError
                    for event in eventsList:
                         await databaseConn.deleteEntry("events", {"name": event[0], "channel": event[2], "datetime": event[3]})
                    await processEvent.cancelRunningEvent()
                    await processEvent.setTimerForClosestEvent()
          except ValueError:
               await message.channel.send("Did you type everything in correctly?")
          except errors.WrongCommandError:
               await message.channel.send("You should use !deleteevent to delete events occurring at a single time.")
          except errors.EventTooEarlyError:
               logging.info("ERROR: Event time set before current time")
               await message.channel.send("You are deleting an event that should have already occurred and subsequently been deleted.")
          except errors.NoTimeZoneError:
               logging.info("ERROR: No specified timezone")
               await message.channel.send("You did not specify a timezone and you do not have a timezone saved for this channel. You can set one with !settimezone and check !help for a list of valid timezones.")
          except errors.EventDoesNotExistError:
               await message.channel.send("You are trying to delete a minimum of one event that doesn't exist.")
          except errors.NoServerConnectionError:
               await message.channel.send("Sorry, I can't process your request because the servers are down right now. :(")
          except Exception as e:
               logging.info("Something went wrong waiting for the new event: {}".format(e))
          else:
               channel = client.get_channel(eventsList[0][2])
               await channel.send("set of recurring events named {} has been deleted".format(eventsList[0][0]))
     elif message.content.startswith("!showevents"):
          try:
               allEventsList = await databaseConn.findEntries("events", {"channel": message.channel.id}, ["name", "datetime", "timezone"])
               channelEventsList = []
               for event in allEventsList:
                    eventTime = await formatdt.humanFormatEventDateTime(event[1], event[2])
                    formattedEvent = "{} at {}/{}/{} {}:{}{} {}\n".format(event[0], eventTime[0], eventTime[1], eventTime[2], eventTime[3], eventTime[4], eventTime[5], event[2]) #change to reflect event timezone
                    channelEventsList.append(formattedEvent)
               logging.info(channelEventsList)
               if len(channelEventsList) == 0:
                    await message.channel.send("You have no events scheduled.")
               else:
                    channelEventsText = ""
                    for event in channelEventsList:
                         channelEventsText = channelEventsText + event
                    await message.channel.send("Please note that events are channel specific:\n{}".format(channelEventsText))
          except errors.NoServerConnectionError:
               await message.channel.send("Sorry, I can't process your request because the servers are down right now. :(")
          except Exception as e:
               logging.info("Something went wrong showing event {}".format(e))
               await message.channel.send("Something has gone wrong retrieving your channel events.")
     elif message.content.startswith("!settimezone"):
          try:
               channelTimezone = message.content.split()[1]
               try:
                    guild = message.guild.id
               except:
                    logging.info("No guild, DM channel")
                    guild = 0
               channel = message.channel.id
               await formatdt.testTimezone(channelTimezone)
               logging.info("guild: {}, channel: {}, timezone: {}".format(guild, channel, channelTimezone))
               existingChannel = await databaseConn.findEntries("channel_timezones", {"channel" : channel}, ["timezone"])
               logging.info("The database already has this value saved for channel {}: {}".format(channel, existingChannel))
               if len(existingChannel) == 0:
                    await databaseConn.insertEntry("channel_timezones", (guild, channel, channelTimezone))
                    logging.info("New channel timezone added")
               else:
                    await databaseConn.updateEntry("channel_timezones", {"timezone" : channelTimezone}, {"channel" : channel})
                    logging.info("Previous channel timezone updated")
          except IndexError:
               await message.channel.send("Make sure to indicate a timezone.")
          except errors.InvalidTimeZoneError:
               await message.channel.send("You inputted something that was not a timezone.")
          except errors.NoServerConnectionError:
               await message.channel.send("Sorry, I can't process your request because the servers are down right now. :(")
          except Exception as e:
               logging.info("Something went wrong saving timezone {}.".format(e))
          else:
               await message.channel.send("The timezone has been set to {}.".format(channelTimezone))
     if message.author == client.user:
          return
     elif message.content.lower().find("sippy") != -1:
          if message.content.lower().find("good job sippy") != -1:
               await message.channel.send("Why thank you {}! I pride myself on my excellent quality of work. Although I am passionate about this job and do it because I love it, it is always nice to get a little validation from a nice person like you.".format(message.author.mention))
          else:
               await message.channel.send("meow")

client.run(discordToken)
