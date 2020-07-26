import logging
from datetime import datetime, timedelta

async def processDateTime(date, time):
     if date == "today":
          year = datetime.now().date().year
          month = datetime.now().date().month
          day = datetime.now().date().day
     elif date == "tomorrow":
          year = (datetime.now() + timedelta(days = 1)).date().year
          month = (datetime.now() + timedelta(days = 1)).date().month
          day = (datetime.now() + timedelta(days = 1)).date().day
     else:
          try:
               year = date.split("/")[0]
               month = date.split("/")[1]
               day = date.split("/")[2]
          except:
               logging.info("Invalid date inputted: {}".format(date))
               raise ValueError
     if time[-2:] == "AM":
          try:
               hours = time.split(":")[0]
               hours = int(hours)
               if hours > 12 or hours < 0:
                    raise ValueError
          except:
               logging.info("Invalid time hour value inputted: {}".format(time.split(":")[0]))
               raise ValueError
     elif time[-2:] == "PM":
          try:
               hours = int(time.split(":")[0]) + 12
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

async def humanFormatEventTime(event):
     eventHours = int(event[event.find("[") + 1: event.find("]")].split()[3])
     eventMeridian = "0"
     if eventHours < 12:
          eventMeridian = "AM"
     else:
          eventHours = eventHours - 12
          eventMeridian = "PM"
     eventMinutes = event[event.find("[") + 1: event.find("]")].split()[4]
     if int(eventMinutes) < 10:
          eventMinutes = "0{}".format(eventMinutes)
     return (eventHours, eventMinutes, eventMeridian)

async def convertToDate(event):
     eventYear = int(event[event.find("[") + 1: event.find("]")].split()[0])
     eventMonth = int(event[event.find("[") + 1: event.find("]")].split()[1])
     eventDay = int(event[event.find("[") + 1: event.find("]")].split()[2])
     eventTimeHours = int(event[event.find("[") + 1: event.find("]")].split()[3])
     eventTimeMinutes = int(event[event.find("[") + 1: event.find("]")].split()[4])
     eventDateTime = datetime(eventYear, eventMonth, eventDay, eventTimeHours, eventTimeMinutes)
     return eventDateTime