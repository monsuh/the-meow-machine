import logging
import filerw
from pytz import timezone
from datetime import datetime, timedelta

async def processDateTime(date, time, eventTz):
     try:
          utc = timezone("UTC")
          eventTimezone = timezone(eventTz)
          currentDateTime = utc.localize(datetime.utcnow()).astimezone(eventTimezone)
     except Exception as e:
          logging.info("Unable to retrieve current date: {}".format(e))
          raise ValueError
     if date == "today":
          logging.info("Current date in local time: {}".format(currentDateTime))
          year = currentDateTime.date().year
          month = currentDateTime.date().month
          day = currentDateTime.date().day
     elif date == "tomorrow":
          logging.info("Current date in local time: {}".format(currentDateTime))
          year = (currentDateTime + timedelta(days = 1)).date().year
          month = (currentDateTime + timedelta(days = 1)).date().month
          day = (currentDateTime + timedelta(days = 1)).date().day
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
     return eventTimezone.localize(datetime(year, month, day, hours, minutes))

async def humanFormatEventDateTime(event):
     eventTimezone = timezone(event[2])
     localizedTime = event[1].astimezone(eventTimezone)
     eventYear = localizedTime.date().year
     eventMonth = localizedTime.date().month
     eventDay = localizedTime.date().day
     eventHour = localizedTime.hour
     eventMeridian = ""
     if eventHour < 12:
          eventMeridian = "AM"
     else:
          eventHour = eventHour - 12
          eventMeridian = "PM"
     eventMinute = localizedTime.minute
     if eventMinute < 10:
          eventMinute = "0{}".format(eventMinute)
     return (eventYear, eventMonth, eventDay, eventHour, eventMinute, eventMeridian)