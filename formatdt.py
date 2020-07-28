import logging
import filerw
from datetime import datetime, timedelta

async def processDateTime(date, time, timezone):
     if date == "today":
          try:
               await filerw.setTime(timezone)
          except:
               raise ValueError
          currentDateTime = await filerw.retrieveCurrentTime()
          logging.info("Current date in local time: {}".format(currentDateTime))
          year = currentDateTime[0].date().year
          month = currentDateTime[0].date().month
          day = currentDateTime[0].date().day
     elif date == "tomorrow":
          try:
               await filerw.setTime(timezone)
          except:
               raise ValueError
          currentDateTime = await filerw.retrieveCurrentTime()
          logging.info("Current date in local time: {}".format(currentDateTime))
          year = (currentDateTime[0] + timedelta(days = 1)).date().year
          month = (currentDateTime[0] + timedelta(days = 1)).date().month
          day = (currentDateTime[0] + timedelta(days = 1)).date().day
     else:
          try:
               year = int(date.split("/")[0])
               month = int(date.split("/")[1])
               day = int(date.split("/")[2])
          except:
               logging.info("Invalid date inputted: {}".format(date))
               raise ValueError
     if time[-2:] == "AM":
          try:
               hours = int(time.split(":")[0])
               if hours == 12:
                    hours = 0
               if hours > 12 or hours < 0:
                    raise ValueError
          except:
               logging.info("Invalid time hour value inputted: {}".format(time.split(":")[0]))
               raise ValueError
     elif time[-2:] == "PM":
          try:
               hours = int(time.split(":")[0])
               if hours < 12:
                    hours = hours + 12
               if hours > 23 or hours < 12:
                    raise ValueError
          except:
               logging.info("Invalid time hour value inputted: {}".format(time.split(":")[0]))
               raise ValueError
     else:
          logging.info("Invalid meridian inputted: {}".format(time[-2:]))
          raise ValueError
     try:
          minutes = time.split(":")[1][0:2]
          minutes = int(minutes)
          if minutes < 0 or minutes > 59:
               raise ValueError
     except:
          logging.info("Invalid time minute value inputted: {}".format(time.split(":")[0]))
          raise ValueError
     return datetime(year, month, day, hours, minutes)

async def humanFormatEventDateTime(event):
     eventYear = event[1].date().year
     eventMonth = event[1].date().month
     eventDay = event[1].date().day
     eventHour = event[1].hour
     logging.info("Event hours: {}".format(eventHour))
     eventMeridian = ""
     if eventHour < 12:
          eventMeridian = "AM"
     else:
          eventHour = eventHour - 12
          eventMeridian = "PM"
     eventMinute = event[1].minute
     if eventMinute < 10:
          eventMinute = "0{}".format(eventMinute)
     return (eventYear, eventMonth, eventDay, eventHour, eventMinute, eventMeridian)