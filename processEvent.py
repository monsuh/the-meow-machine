import asyncio
import logging
import errors
import filerw
import formatdt
import discord

from setup import client
from datetime import datetime, timedelta

async def processEventMessage(message):
     eventName = message.content[message.content.find("{"):message.content.find("}") + 1]
     eventGuild = message.guild.id
     eventChannel = message.channel.id
     eventDateTime = message.content[message.content.find("[") + 1:message.content.find("]")]
     eventDate = await formatdt.processDate(eventDateTime.split()[0])
     eventTime = await formatdt.processTime(eventDateTime.split()[1])
     event = "{} <{} {}> [{} {} {} {} {}]\n".format(eventName, eventGuild, eventChannel, eventDate[0], eventDate[1], eventDate[2], eventTime[0], eventTime[1])
     return event

async def processRecurringEventMessage(message):
     eventName = message.content[message.content.find("{"):message.content.find("}") + 1]
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
          interval = int(eventDateTime.split()[2])
     except Exception as e:
          logging.info("Invalid time interval inputted: {}".format(eventDateTime.split()[2]))
          raise ValueError
     eventStartDate = await formatdt.processDate(eventStartDate)
     eventEndDate = await formatdt.processDate(eventEndDate)
     eventStartTime = await formatdt.processTime(eventStartTime)
     eventEndTime = await formatdt.processTime(eventEndTime)
     eventEndDateTime = datetime(eventEndDate[0], eventEndDate[1], eventEndDate[2], eventEndTime[0], eventEndTime[1])
     logging.info("Final recurring event end date time: {}".format(eventEndDateTime))
     eventDateTime = datetime(eventStartDate[0], eventStartDate[1], eventStartDate[2], eventStartTime[0], eventStartTime[1])
     logging.info("Final recurring event start date time: {}".format(eventDateTime))
     eventList = []
     while eventDateTime < eventEndDateTime:
          event = "{} <{} {}> [{} {} {} {} {}]\n".format(eventName, eventGuild, eventChannel, eventDateTime.year, eventDateTime.month, eventDateTime.day, eventDateTime.hour, eventDateTime.minute)
          logging.info("New event: {}".format(event))
          eventList.append(event)
          eventDateTime = eventDateTime + timedelta(minutes = interval)
     return eventList

async def setTimerForClosestEvent():
     event = await filerw.readFirstLine("events.txt")
     if event == "":
          raise IndexError
     else:
          logging.info("first line of file: {}".format(event[0:-1]))
          task = asyncio.create_task(sendReminder(event))
          logging.info("setting timer for {}".format(event[0:-1]))
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

async def deleteEvent(fileName, simultaneousEvents):
     eventsList = await filerw.readFile(fileName)
     remainingEvents = []
     for i in range (0, len(eventsList), 1):
          if eventsList[i] not in simultaneousEvents:
               remainingEvents.append(eventsList[i])
     await filerw.overWriteFile(fileName, remainingEvents)

async def findSimultaneousEvents(originalEvent):
     logging.info("Finding simultaneous events")
     eventsList = await filerw.readFile("events.txt")
     eventsList = eventsList[1:]
     simultaneousEvents = []
     simultaneousEvents.append(originalEvent)
     referenceDateTime = originalEvent[originalEvent.find("[") + 1: originalEvent.find("]")]
     for event in eventsList:
          if event[event.find("[") + 1: event.find("]")] == referenceDateTime:
               simultaneousEvents.append(event)
          else:
               break
     return simultaneousEvents

async def findWaitTime(event):
     eventDateTime = await formatdt.convertToDate(event) + timedelta(seconds = 6)
     currentDateTime = datetime.utcnow()
     return (eventDateTime - currentDateTime).total_seconds()

async def sendReminder(referenceEvent):
     simultaneousEvents = await findSimultaneousEvents(referenceEvent)
     logging.info("These are events happening simultaneously: {}".format(simultaneousEvents))
     waitTime = await findWaitTime(referenceEvent)
     logging.info("wait time for {} is {} s".format(referenceEvent[0:-1], waitTime))
     if waitTime > 0:
          await asyncio.sleep(waitTime)
          for event in simultaneousEvents:
               #guild = client.get_guild(int(event[event.find("<") + 1: event.find(">")].split()[0]))
               channel = client.get_channel(int(event[event.find("<") + 1: event.find(">")].split()[1]))
               eventName = event[event.find("{") + 1: event.find("}")]
               await channel.send("hey guys {} is happening now!".format(eventName))
               #return (guild, channel, eventName)
     else:
          for event in simultaneousEvents:
               #guild = client.get_guild(int(event[event.find("<") + 1: event.find(">")].split()[0]))
               channel = client.get_channel(int(event[event.find("<") + 1: event.find(">")].split()[1]))
               eventName = event[event.find("{") + 1: event.find("}")]
               eventTime = await formatdt.humanFormatEventTime(event)
               await channel.send("hey guys we missed {} at {}:{}{}".format(eventName, str(eventTime[0]), eventTime[1], eventTime[2]))
               #return (guild, channel, eventName, eventTime)
     await deleteEvent("events.txt", simultaneousEvents)
     await cancelRunningEvent()
     try:
          await setTimerForClosestEvent()
     except IndexError:
          logging.info("no items in events list")
