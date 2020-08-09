import logging
import errors
import psycopg2

from datetime import datetime, timedelta
from psycopg2 import sql

class DatabaseConnection:

     def __init__(self, databaseURL):
          self.connection = psycopg2.connect(databaseURL, sslmode="require")
          self.cursor = self.connection.cursor()

     async def setTime(self, tz):
          command = sql.SQL('''SET TIMEZONE TO {timezone};''').format(
                    timezone = sql.Identifier(tz))
          self.cursor.execute(command)

     async def retrieveCurrentTime(self):
          command = sql.SQL("SELECT LOCALTIMESTAMP")
          self.cursor.execute(command)
          return self.cursor.fetchone()

     async def retrieveFirstEntry(self, database, key, columns):
          try:
               self.cursor.execute(
                    sql.SQL('SELECT {columns} FROM {table} ORDER BY {orderKey};').format(
                         columns = sql.SQL(', ').join(
                              sql.Identifier(database, column) for column in columns    
                         ), 
                         table = sql.Identifier(database), 
                         orderKey = sql.Identifier(database, key)))
               return self.cursor.fetchone()
          except Exception as e:
               logging.info("Error with retrieving first entry: {}".format(e))

     async def retrieveAllEntries(self, database):
          try:
               self.cursor.execute(
                    sql.SQL("SELECT * FROM {table}").format(
                         table = sql.Identifier(database)))
               return self.cursor.fetchall()
          except Exception as e:
               logging.info("Error with retrieving entries: {}".format(e))

     async def findEntries(self, database, searchTerms, columns):
          try:
               command = sql.SQL(
                    '''
                         SELECT {columns} 
                         FROM {table} 
                         WHERE {conditions}
                    ''').format(
                         columns = sql.SQL(', ').join(
                              sql.Identifier(database, column) for column in columns    
                         ),
                         table = sql.Identifier(database),
                         conditions = sql.SQL(' AND ').join(
                              sql.Composed([sql.Identifier(database, key), sql.SQL(" = "), sql.Placeholder()]) for key in searchTerms.keys()
                         )
                    )
               self.cursor.execute(command, list(searchTerms.values()))
               return self.cursor.fetchall()
          except Exception as e:
               logging.info("Error with retrieving entries with matching keys: {}".format(e))

     async def insertEntry(self, database, entry):
          command = sql.SQL(
               '''
                    INSERT INTO {table}
                    VALUES ({values});
               ''').format(
                    table = sql.Identifier(database),
                    values = sql.SQL(",").join(
                         sql.Placeholder() for item in entry
                    ))
          self.cursor.execute(command, entry)
          self.connection.commit()

     async def insertEvent(self, entry):
          try:
               await self.setTime(entry[4])
          except Exception as e:
               logging.info("Error with setting time zone: {}".format(e))
          else:
               try:
                    matches = await self.findEntries("events", {"name" : entry[0], "channel" : entry[2], "datetime" : entry[3]}, ["name", "channel", "datetime"])
                    if len(matches) != 0:
                         raise errors.RepetitionError
               except errors.RepetitionError:
                    logging.info("Entry already exists")
                    raise errors.RepetitionError
               except Exception as e:
                    logging.info("Error with retrieving matching entries: {}".format(e)) 
               else:
                    try:
                         await self.insertEntry("events", entry)
                    except Exception as e:
                         logging.info("Error with inserting data: {}".format(e))

     async def insertMultipleEvents(self, entriesList):
          try:
               await self.setTime(entriesList[0][4])
          except Exception as e:
               logging.info("Error with setting time zone: {}".format(e))
          else:
               try:
                    for entry in entriesList:
                         matches = await self.findEntries("events", {"name" : entry[0], "channel" : entry[2], "datetime" : entry[3]}, ["name"])
                         if len(matches) != 0:
                              raise errors.RepetitionError
               except errors.RepetitionError:
                    logging.info("Entry or entries already exist(s)")
                    raise errors.RepetitionError
               else:
                    try:
                         await self.insertEntry("events", entriesList)
                    except Exception as e:
                         logging.info("Error with inserting data: {}".format(e))

     async def deleteEntry(self, database, params):
          try:
               self.cursor.execute(
                    sql.SQL("DELETE FROM {table} WHERE {column};").format(
                         table = sql.Identifier(database),
                         column = sql.SQL(' AND ').join(
                              sql.Composed([sql.Identifier(database, key), sql.SQL(" = "), sql.Placeholder()]) for key in params.keys()
                         )), list(params.values()))
               self.connection.commit()
          except Exception as e:
               logging.info("Error with deleting data: {}".format(e))

     async def updateEntry(self, database, updates, conditions):
          command = sql.SQL(
               '''
                    UPDATE {table}
                    SET {updateValues}
                    WHERE {updateConditions}
               ''').format(
                    table = sql.Identifier(database),
                    updateValues = sql.SQL(',').join(
                         sql.Composed([sql.Identifier(key), sql.SQL(" = "), sql.Placeholder()]) for key in updates.keys()
                    ),
                    updateConditions = sql.SQL(' AND ').join(
                         sql.Composed([sql.Identifier(key), sql.SQL(" = "), sql.Placeholder()]) for key in conditions.keys()
                    )
               )
          try:
               self.cursor.execute(command, list(updates.values()) + list(conditions.values()))
               self.connection.commit()
          except Exception as e:
               logging.info("Error with updating data: {}".format(e))

