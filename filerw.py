import logging
import errors

from datetime import datetime, timedelta

def convertToDateNonCoroutine(event):
     eventYear = int(event[event.find("[") + 1: event.find("]")].split()[0])
     eventMonth = int(event[event.find("[") + 1: event.find("]")].split()[1])
     eventDay = int(event[event.find("[") + 1: event.find("]")].split()[2])
     eventTimeHours = int(event[event.find("[") + 1: event.find("]")].split()[3])
     eventTimeMinutes = int(event[event.find("[") + 1: event.find("]")].split()[4])
     eventDateTime = datetime(eventYear, eventMonth, eventDay, eventTimeHours, eventTimeMinutes) + timedelta(hours = 4)
     return eventDateTime

async def readFirstLine(fileName):
     file = open(fileName, "r")
     firstLine = file.readline()
     file.close()
     logging.info("first line of {} has been read".format(fileName))
     return firstLine

async def readFile(fileName):
     file = open(fileName, "r")
     fileContents = file.readlines()
     file.close()
     logging.info("{} has been read".format(fileName))
     return fileContents

async def appendNewEventToFile(fileName, event):
     file = open(fileName, "r+")
     fileContents = file.readlines()
     for line in fileContents:
          if line == event:
               logging.info("{} already exists".format(event[0:-1]))
               raise errors.RepetitionError
     else:
          fileContents.append(event)
          fileContents.sort(key = convertToDateNonCoroutine) #possibly have to make sort awaitable
          file.seek(0,0)
          file.writelines(fileContents)
     file.close()
     if event == fileContents[0] or event[event.find("[") + 1: event.find("]")] == fileContents[0][fileContents[0].find("[") + 1: fileContents[0].find("]")]:
          return True
     else:
          return False

async def overWriteFile(fileName, newContent):
     file = open(fileName, "w")
     file.writelines(newContent)
     file.close()
     return