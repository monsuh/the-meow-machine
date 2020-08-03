import asyncio
import logging
import errors
import filerw
import formatdt
import discord

from setup import client
from pytz import timezone
from datetime import datetime, timedelta

async def processEventMessage(message):
     try:
          eventGuild = int(message.guild.id)
          eventChannel = int(message.channel.id)
     except Exception as e:
          logging.info("Event guild/channel id exception: {}".format(e))
          raise ValueError
     try:
          eventName = message.content[message.content.find("{") + 1:message.content.find("}")]
     except Exception as e:
          logging.info("Event name exception: {}".format(e))
          raise ValueError
     try:
          eventDateTimeRaw = message.content[message.content.find("[") + 1:message.content.find("]")]
     except Exception as e:
          logging.info("Event date time exception: {}".format(e))
          raise ValueError
     try:
          eventTimeZone = eventDateTimeRaw.split()[2]
     except IndexError:
          eventTimeZone = await filerw.findEntries("channel_timezones", {"channel" : eventChannel}, ["timezone"])
          if len(eventTimeZone) == 0:
               raise errors.NoTimeZoneError
          logging.info("Channel timezone: {}".format(eventTimeZone[0][0]))
          eventTimeZone = eventTimeZone[0][0]
     eventDateTime = await formatdt.processDateTime(eventDateTimeRaw.split()[0], eventDateTimeRaw.split()[1], eventTimeZone)
     event = (eventName, eventGuild, eventChannel, eventDateTime, eventTimeZone)
     return event

async def processRecurringEventMessage(message):
     try:
          eventGuild = int(message.guild.id)
          eventChannel = int(message.channel.id)
     except Exception as e:
          logging.info("Event guild/channel id exception: {}".format(e))
          raise ValueError
     try:
          eventName = message.content[message.content.find("{") + 1:message.content.find("}")]
     except Exception as e:
          logging.info("Event name exception: {}".format(e))
          raise ValueError
     try:
          eventDateTime = message.content[message.content.find("[") + 1:message.content.find("]")]
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
          eventTimeZone = await filerw.findEntries("channel_timezones", {"channel" : eventChannel}, ["timezone"])
          if len(eventTimeZone) == 0:
               raise errors.NoTimeZoneError
          logging.info("Channel timezone: {}".format(eventTimeZone[0][0]))
          eventTimeZone = eventTimeZone[0][0]
     eventEndDateTime = await formatdt.processDateTime(eventEndDate, eventEndTime, eventTimeZone)
     logging.info("Final recurring event end date time: {}".format(eventEndDateTime))
     eventDateTime = await formatdt.processDateTime(eventStartDate, eventStartTime, eventTimeZone)
     logging.info("Final recurring event start date time: {}".format(eventDateTime))
     await ensureValidTime(eventTimeZone, eventDateTime)
     eventList = []
     while eventDateTime < eventEndDateTime:
          event = (eventName, eventGuild, eventChannel, eventDateTime, eventTimeZone)
          logging.info("New event: {}".format(event))
          eventList.append(event)
          eventDateTime = eventDateTime + timedelta(minutes = eventInterval)
     return eventList

async def ensureValidTime(eventTz, eventDateTime):
     utc = timezone("UTC")
     eventTimeZone = timezone(eventTz)
     currentDateTime = utc.localize(datetime.utcnow()).astimezone(eventTimeZone)
     logging.info("Current date and time: {}".format(currentDateTime))
     logging.info("Inserted event datetime: {}".format(eventDateTime))
     if currentDateTime > eventDateTime:
          raise errors.EventTooEarlyError

async def determineNewestEventAndSetTimer(event):
     newestEventDate = await filerw.retrieveFirstEntry("events", "datetime", ["datetime"])
     newestEventDate = newestEventDate[0].astimezone(timezone(event[4]))
     logging.info("Earliest event date: {}".format(newestEventDate))
     if event[3] == newestEventDate:
          try:
               logging.info("{} has most imminent deadline".format(event[0]))
               await cancelRunningEvent()
               await setTimerForClosestEvent()
          except Exception as e:
               logging.info("Something went wrong setting a timer for the new event {}".format(e))

async def setTimerForClosestEvent():
     await filerw.setTime("UTC")
     event = await filerw.retrieveFirstEntry("events", "datetime", ["name", "channel", "datetime"])
     if event == None:
          raise IndexError
     else:
          logging.info("first entry: {}".format(event))
          task = asyncio.create_task(sendReminder(event))
          logging.info("setting timer for {}".format(event[0]))
          task.set_name("event timer")
          return task

async def cancelRunningEvent():
     taskSet = asyncio.all_tasks()
     for task in taskSet:
          if task.get_name() == "event timer":
               task.cancel()
               logging.info("currently running task has been cancelled")
               break
     else:
          logging.info("no currently running tasks")
     #guild = client.get_guild(int(event[event.find("<") + 1: event.find(">")].split()[0]))

async def deleteEvent(database, simultaneousEvents):
     for event in simultaneousEvents:
          await filerw.deleteEntry(database, {"name" : event[0], "channel" : event[1], "datetime" : event[2]})

async def findSimultaneousEvents(originalEvent):
     logging.info("Finding simultaneous events")
     simultaneousEvents = await filerw.findEntries("events", {"datetime" : originalEvent[2]}, ["name", "channel", "datetime"])
     return simultaneousEvents

async def findWaitTime(event):
     eventDateTime = event[2].replace(tzinfo=None) + timedelta(seconds = 6)
     currentDateTime = datetime.utcnow()
     return (eventDateTime - currentDateTime).total_seconds()

async def sendReminder(referenceEvent):
     simultaneousEvents = await findSimultaneousEvents(referenceEvent)
     logging.info("These are events happening simultaneously: {}".format(simultaneousEvents))
     waitTime = await findWaitTime(referenceEvent)
     logging.info("wait time for {} is {} s".format(referenceEvent[0], waitTime))
     if waitTime > 0:
          await asyncio.sleep(waitTime)
          for event in simultaneousEvents:
               #guild = client.get_guild(int(event[event.find("<") + 1: event.find(">")].split()[0]))
               channel = client.get_channel(int(event[1]))
               eventName = event[0]
               try:
                    await channel.send("hey guys {} is happening now!".format(eventName))
               except Exception as e:
                    logging.info("Could not send reminder message: {}".format(e))
     else:
          for event in simultaneousEvents:
               #guild = client.get_guild(int(event[event.find("<") + 1: event.find(">")].split()[0]))
               channel = client.get_channel(int(event[1]))
               eventName = event[0]
               #eventTime = await formatdt.humanFormatEventTime(event)
               #await channel.send("hey guys we missed {} at {}:{}{}".format(eventName, str(eventTime[0]), eventTime[1], eventTime[2]))
               try:
                    await channel.send("hey guys we missed {}!".format(eventName))
               except Exception as e:
                    logging.info("Could not send reminder message: {}".format(e))
     await deleteEvent("events", simultaneousEvents)
     await cancelRunningEvent()
     try:
          await setTimerForClosestEvent()
     except IndexError:
          logging.info("no items in events list")
