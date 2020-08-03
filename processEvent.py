import asyncio
import logging
import errors
import filerw
import formatdt
import discord

from setup import client
from datetime import datetime, timedelta

async def processEventMessage(message):
     eventName = message.content[message.content.find("{") + 1:message.content.find("}")]
     eventGuild = int(message.guild.id)
     eventChannel = int(message.channel.id)
     eventDateTimeRaw = message.content[message.content.find("[") + 1:message.content.find("]")]
     try:
          eventTimeZone = eventDateTimeRaw.split()[2]
     except IndexError:
          eventTimeZone = "UTC" #subject to change
     eventDateTime = await formatdt.processDateTime(eventDateTimeRaw.split()[0], eventDateTimeRaw.split()[1], eventTimeZone)
     event = (eventName, eventGuild, eventChannel, eventDateTime, eventTimeZone)
     return event

async def processRecurringEventMessage(message):
     eventName = message.content[message.content.find("{") + 1:message.content.find("}")]
     eventGuild = message.guild.id
     eventChannel = message.channel.id
     eventDateTime = message.content[message.content.find("[") + 1:message.content.find("]")]
     try:
          eventStartDate = eventDateTime.split()[0].split("-")[0]
          eventEndDate = eventDateTime.split()[0].split("-")[1]
          logging.info("Inputted start date: {} and end date: {}".format(eventStartDate, eventEndDate))
     except IndexError:
          eventStartDate = eventDateTime.split()[0]
          eventEndDate = eventDateTime.split()[0]
     except Exception as e:
          logging.info("Recurring event date exception: {}".format(e))
     try:
          eventStartTime = eventDateTime.split()[1].split("-")[0]
          eventEndTime = eventDateTime.split()[1].split("-")[1]
          logging.info("Inputted start time: {} and end time: {}".format(eventStartTime, eventEndTime))
     except IndexError:
          raise errors.WrongCommandError
     except Exception as e:
          logging.info("Recurring event time exception: {}".format(e))
     try:
          eventTimeZone = eventDateTime.split()[2]
     except IndexError:
          eventTimeZone = "UTC"
     try:
          interval = int(eventDateTime.split()[3])
     except Exception as e:
          logging.info("Invalid time interval inputted: {}".format(eventDateTime.split()[3]))
          raise ValueError
     eventEndDateTime = await formatdt.processDateTime(eventEndDate, eventEndTime, eventTimeZone)
     logging.info("Final recurring event end date time: {}".format(eventEndDateTime))
     eventDateTime = await formatdt.processDateTime(eventStartDate, eventStartTime, eventTimeZone)
     logging.info("Final recurring event start date time: {}".format(eventDateTime))
     eventList = []
     while eventDateTime < eventEndDateTime:
          event = (eventName, eventGuild, eventChannel, eventDateTime, eventTimeZone)
          logging.info("New event: {}".format(event))
          eventList.append(event)
          eventDateTime = eventDateTime + timedelta(minutes = interval)
     return eventList

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
               await channel.send("hey guys {} is happening now!".format(eventName))
     else:
          for event in simultaneousEvents:
               #guild = client.get_guild(int(event[event.find("<") + 1: event.find(">")].split()[0]))
               channel = client.get_channel(int(event[1]))
               eventName = event[0]
               #eventTime = await formatdt.humanFormatEventTime(event)
               #await channel.send("hey guys we missed {} at {}:{}{}".format(eventName, str(eventTime[0]), eventTime[1], eventTime[2]))
               await channel.send("hey guys we missed {}!".format(eventName))
     await deleteEvent("events", simultaneousEvents)
     await cancelRunningEvent()
     try:
          await setTimerForClosestEvent()
     except IndexError:
          logging.info("no items in events list")
