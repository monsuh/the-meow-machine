import asyncio
import logging
import errors
import formatdt
import discord

from setup import client, databaseConn
from pytz import timezone
from datetime import datetime, timedelta

async def processEventMessage(message):
     try:
          eventGuild = int(message.guild.id)
     except:
          logging.info("No event guild, DM channel")
          eventGuild = 0
     try:
          if eventGuild == 0:
               eventChannel = int(message.author.id)
          else:
               eventChannel = int(message.channel.id)
     except Exception as e:
          logging.info("Event channel id exception: {}".format(e))
          raise ValueError
     try:
          startIndex = message.content.find("{")
          endIndex = message.content.find("}")
          if startIndex == -1 or endIndex == -1:
               raise ValueError
          else:
               eventName = message.content[startIndex + 1:endIndex]
               logging.info("Event name: {}".format(eventName))
     except Exception as e:
          logging.info("Event name exception: {}".format(e))
          raise ValueError
     try:
          startIndex = message.content.find("[")
          endIndex = message.content.find("]")
          if startIndex == -1 or endIndex == -1:
               raise ValueError
          else:
               eventDateTimeRaw = message.content[startIndex + 1:endIndex]
               logging.info("Event datetime: {}".format(eventDateTimeRaw))
     except Exception as e:
          logging.info("Event date time exception: {}".format(e))
          raise ValueError
     try:
          eventTimeZone = eventDateTimeRaw.split()[2]
     except IndexError:
          try:
               eventTimeZone = await databaseConn.findEntries("channel_timezones", {"channel" : eventChannel}, ["timezone"])
               if len(eventTimeZone) == 0:
                    raise errors.NoTimeZoneError
               logging.info("Channel timezone: {}".format(eventTimeZone[0][0]))
               eventTimeZone = eventTimeZone[0][0]
          except errors.NoTimeZoneError:
               raise errors.NoTimeZoneError
          except errors.NoServerConnectionError:
               raise errors.NoServerConnectionError
     eventDateTime = await formatdt.processDateTime(eventDateTimeRaw.split()[0], eventDateTimeRaw.split()[1], eventTimeZone)
     await formatdt.ensureValidTime(eventTimeZone, eventDateTime)
     event = (eventName, eventGuild, eventChannel, eventDateTime, eventTimeZone)
     return event

async def processRecurringEventMessage(message):
     try:
          eventGuild = int(message.guild.id)
     except Exception as e:
          logging.info("No event guild, is a DM a channel")
          eventGuild = 0
     try:
          if eventGuild == 0:
               eventChannel = int(message.author.id)
          else:
               eventChannel = int(message.channel.id)
     except Exception as e:
          logging.info("Event guild/channel id exception: {}".format(e))
          raise ValueError
     try:
          startIndex = message.content.find("{")
          endIndex = message.content.find("}")
          if startIndex == -1 or endIndex == -1:
               raise ValueError
          else:
               eventName = message.content[startIndex + 1:endIndex]
               logging.info("Event name: {}".format(eventName))
     except Exception as e:
          logging.info("Event name exception: {}".format(e))
          raise ValueError
     try:
          startIndex = message.content.find("[")
          endIndex = message.content.find("]")
          if startIndex == -1 or endIndex == -1:
               raise ValueError
          eventDateTime = message.content[startIndex + 1:endIndex]
          logging.info("Event datetime: {}".format(eventDateTime))
     except Exception as e:
          logging.info("Event date time exception: {}".format(e))
          raise ValueError
     try:
          eventInterval = int(message.content[message.content.find("<") + 1:message.content.find(">")])
     except Exception as e:
          logging.info("Event interval exception: {}".format(e))
          raise ValueError
     try:
          eventStartDate = eventDateTime.split()[0].split("-")[0]
          eventEndDate = eventDateTime.split()[0].split("-")[1]
          logging.info("Inputted start date: {} and end date: {}".format(eventStartDate, eventEndDate))
     except IndexError:
          eventStartDate = eventDateTime.split()[0]
          eventEndDate = eventDateTime.split()[0]
     except Exception as e:
          logging.info("Recurring event date exception: {}".format(e))
          raise ValueError
     try:
          eventStartTime = eventDateTime.split()[1].split("-")[0]
          eventEndTime = eventDateTime.split()[1].split("-")[1]
          logging.info("Inputted start time: {} and end time: {}".format(eventStartTime, eventEndTime))
     except IndexError:
          raise errors.WrongCommandError
     except Exception as e:
          logging.info("Recurring event time exception: {}".format(e))
          raise ValueError
     try:
          eventTimeZone = eventDateTime.split()[2]
     except IndexError:
          try:
               eventTimeZone = await databaseConn.findEntries("channel_timezones", {"channel" : eventChannel}, ["timezone"])
               if len(eventTimeZone) == 0:
                    raise errors.NoTimeZoneError
               logging.info("Channel timezone: {}".format(eventTimeZone[0][0]))
               eventTimeZone = eventTimeZone[0][0]
          except errors.NoTimeZoneError:
               raise errors.NoTimeZoneError
          except errors.NoServerConnectionError:
               raise errors.NoServerConnectionError
     eventEndDateTime = await formatdt.processDateTime(eventEndDate, eventEndTime, eventTimeZone)
     logging.info("Final recurring event end date time: {}".format(eventEndDateTime))
     eventDateTime = await formatdt.processDateTime(eventStartDate, eventStartTime, eventTimeZone)
     logging.info("Final recurring event start date time: {}".format(eventDateTime))
     await formatdt.ensureValidTime(eventTimeZone, eventDateTime)
     eventList = []
     while eventDateTime < eventEndDateTime:
          event = (eventName, eventGuild, eventChannel, eventDateTime, eventTimeZone)
          logging.info("New event: {}".format(event))
          eventList.append(event)
          eventDateTime = eventDateTime + timedelta(minutes = eventInterval)
     return eventList

async def determineIfNewestEventIsMostPertinent(event):
     try:
          newestEventDate = await databaseConn.retrieveFirstEntry("events", "datetime", ["datetime"])
          newestEventDate = newestEventDate[0].astimezone(timezone(event[4]))
          logging.info("Earliest event date: {}".format(newestEventDate))
          if event[3] == newestEventDate:
               try:
                    logging.info("{} has most imminent deadline".format(event[0]))
                    await cancelRunningEvent()
                    await setTimerForClosestEvent()
               except errors.NoServerConnectionError:
                    raise errors.NoServerConnectionError
               except Exception as e:
                    logging.info("Something went wrong setting a timer for the new event {}".format(e))
     except errors.NoServerConnectionError:
          raise errors.NoServerConnectionError

async def setTimerForClosestEvent():
     try:
          await databaseConn.setTime("UTC")
          event = await databaseConn.retrieveFirstEntry("events", "datetime", ["name", "guild", "channel", "datetime", "timezone"])
          if event == None:
               raise IndexError
          else:
               logging.info("first entry: {}".format(event))
               task = asyncio.create_task(sendReminder(event))
               logging.info("setting timer for {}".format(event[0]))
               task.set_name("event timer")
               return task
     except IndexError:
          pass
     except errors.NoServerConnectionError:
          raise errors.NoServerConnectionError

async def cancelRunningEvent():
     taskSet = asyncio.all_tasks()
     for task in taskSet:
          if task.get_name() == "event timer":
               task.cancel()
               logging.info("currently running task has been cancelled")
               break
     else:
          logging.info("no currently running tasks")

async def deleteEvent(database, simultaneousEvents):
     for event in simultaneousEvents:
          await databaseConn.deleteEntry(database, {"name" : event[0], "channel" : event[2], "datetime" : event[3]})

async def findSimultaneousEvents(originalEvent):
     logging.info("Finding simultaneous events")
     simultaneousEvents = await databaseConn.findEntries("events", {"datetime" : originalEvent[3]}, ["name", "guild", "channel", "datetime", "timezone"])
     return simultaneousEvents

async def findWaitTime(event):
     eventDateTime = event[3].replace(tzinfo=None) + timedelta(seconds = 6)
     currentDateTime = datetime.utcnow()
     return (eventDateTime - currentDateTime).total_seconds()

async def sendReminder(referenceEvent):
     try:
          simultaneousEvents = await findSimultaneousEvents(referenceEvent)
          logging.info("These are events happening simultaneously: {}".format(simultaneousEvents))
          waitTime = await findWaitTime(referenceEvent)
          logging.info("wait time for {} is {} s".format(referenceEvent[0], waitTime))
          if waitTime > 0:
               await asyncio.sleep(waitTime)
               for event in simultaneousEvents:
                    if event[1] == 0:
                         channel = client.get_user(event[2])
                    else:
                         channel = client.get_channel(event[2])
                    eventName = event[0]
                    try:
                         await channel.send("Hey gamers, {} is happening now!".format(eventName))
                    except Exception as e:
                         logging.info("Could not send reminder message: {}".format(e))
          else:
               for event in simultaneousEvents:
                    if event[1] == 0:
                         channel = client.get_user(event[2])
                    else:
                         channel = client.get_channel(event[2])
                    try:
                         eventTime = await formatdt.humanFormatEventDateTime(event[3], event[4])
                         await channel.send("Oh no! We missed {} at {}/{}/{} {}:{}{} {}".format(event[0], eventTime[0], eventTime[1], eventTime[2], eventTime[3], eventTime[4], eventTime[5], event[4]))
                    except Exception as e:
                         logging.info("Could not send reminder message: {}".format(e))
          await deleteEvent("events", simultaneousEvents)
          await cancelRunningEvent()
          try:
               await setTimerForClosestEvent()
          except IndexError:
               logging.info("no items in events list")
     except errors.NoServerConnectionError:
          raise errors.NoServerConnectionError

async def checkTimezoneGuildAndDMs(availableGuilds):
     savedGuilds = await databaseConn.retrieveSpecificColumns("channel_timezones", ["guild"])
     savedGuilds = list(dict.fromkeys(savedGuilds))
     savedGuilds.remove((0,))
     logging.info(savedGuilds)
     for guild in savedGuilds:
          if guild[0] not in availableGuilds:
               logging.info("{} not in guilds that meow machine is connected to".format(guild[0]))
               await databaseConn.deleteEntry("channel_timezones", {"guild": guild[0]})
          else:
               logging.info("{} in guilds that meow machine is connected to".format(guild[0]))