import logging
import errors
import psycopg2

from datetime import datetime, timedelta
from psycopg2 import sql

def retryConnection(function):
     async def handleFailure(*args):
          try:
               dbContents = await function(*args)
               return dbContents
          except Exception as e:
               logging.info("Error with database function {}: {}".format(str(function), e))
               for i in range(0, 5, 1):
                    try:
                         args[0].connection = psycopg2.connect(args[0].databaseURL, sslmode="require")
                         args[0].cursor = args[0].connection.cursor()                      
                         dbContents = await function(*args)
                         return dbContents
                    except Exception as e:
                         logging.info("Error with database function {}: {} after attempt {}".format(str(function), e, i))
                    else:
                         break
               else:
                    logging.info("No connection to server")
                    raise errors.NoServerConnectionError
     return handleFailure

class DatabaseConnection:

     def __init__(self, databaseURL):
          try:
               self.connection = psycopg2.connect(databaseURL, sslmode="require")
               self.cursor = self.connection.cursor()
          except:
               self.connection = ""
               self.cursor = ""
          self.databaseURL = databaseURL
     
     @retryConnection
     async def setTime(self, tz):
          command = sql.SQL('''SET TIMEZONE TO {timezone};''').format(
                    timezone = sql.Identifier(tz))
          self.cursor.execute(command)

     @retryConnection
     async def retrieveFirstEntry(self, database, key, columns):
          command = sql.SQL(
               '''
                    SELECT {columns} 
                    FROM {table} 
                    ORDER BY {orderKey};
               ''').format(
                    columns = sql.SQL(', ').join(
                         sql.Identifier(database, column) for column in columns    
                    ), 
                    table = sql.Identifier(database), 
                    orderKey = sql.Identifier(database, key)
               )
          self.cursor.execute(command)
          return self.cursor.fetchone()

     @retryConnection
     async def retrieveAllColumns(self, database):
          command = sql.SQL('''SELECT * FROM {table};''').format(
                    table = sql.Identifier(database)
               )
          self.cursor.execute(command)
          return self.cursor.fetchall()
     
     @retryConnection
     async def retrieveSpecificColumns(self, database, columns):
          command = sql.SQL('''SELECT {columns} FROM {table};''').format(
                    columns = sql.SQL(', ').join(
                         sql.Identifier(database, column) for column in columns    
                    ),
                    table = sql.Identifier(database)
               )
          self.cursor.execute(command)
          return self.cursor.fetchall()

     @retryConnection
     async def findEntries(self, database, searchTerms, columns):
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

     @retryConnection
     async def insertEntry(self, database, entry):
          command = sql.SQL(
               '''
                    INSERT INTO {table}
                    VALUES ({values});
               ''').format(
                    table = sql.Identifier(database),
                    values = sql.SQL(",").join(
                         sql.Placeholder() for item in entry
                    )
               )
          self.cursor.execute(command, entry)
          self.connection.commit()

     async def insertEvent(self, entry):
          try:
               await self.setTime(entry[4])
          except errors.NoServerConnectionError:
               raise errors.NoServerConnectionError
          except Exception as e:
               logging.info("Error with setting time zone: {}".format(e))
          else:
               try:
                    matches = await self.findEntries("events", {"name" : entry[0], "channel" : entry[2], "datetime" : entry[3]}, ["name", "channel", "datetime"])
                    if len(matches) != 0:
                         raise errors.RepetitionError
               except errors.NoServerConnectionError:
                    raise errors.NoServerConnectionError
               except errors.RepetitionError:
                    logging.info("Entry already exists")
                    raise errors.RepetitionError
               except Exception as e:
                    logging.info("Error with retrieving matching entries: {}".format(e)) 
               else:
                    try:
                         await self.insertEntry("events", entry)
                    except errors.NoServerConnectionError:
                         raise errors.NoServerConnectionError
                    except Exception as e:
                         logging.info("Error with inserting data: {}".format(e))

     async def insertMultipleEvents(self, entriesList):
          try:
               await self.setTime(entriesList[0][4])
          except errors.NoServerConnectionError:
               raise errors.NoServerConnectionError
          except Exception as e:
               logging.info("Error with setting time zone: {}".format(e))
          else:
               try:
                    for entry in entriesList:
                         matches = await self.findEntries("events", {"name" : entry[0], "channel" : entry[2], "datetime" : entry[3]}, ["name"])
                         if len(matches) != 0:
                              raise errors.RepetitionError
               except errors.NoServerConnectionError:
                    raise errors.NoServerConnectionError
               except errors.RepetitionError:
                    logging.info("Entry or entries already exist(s)")
                    raise errors.RepetitionError
               else:
                    try:
                         await self.insertEntry("events", entriesList)
                    except errors.NoServerConnectionError:
                         raise errors.NoServerConnectionError
                    except Exception as e:
                         logging.info("Error with inserting data: {}".format(e))

     @retryConnection
     async def deleteEntry(self, database, params):
          command = sql.SQL(
               '''
                    DELETE FROM {table} 
                    WHERE {column};
               ''').format(
                    table = sql.Identifier(database),
                    column = sql.SQL(' AND ').join(
                         sql.Composed([sql.Identifier(database, key), sql.SQL(" = "), sql.Placeholder()]) for key in params.keys()
                    )
               )
          self.cursor.execute(command, list(params.values()))
          self.connection.commit()

     @retryConnection
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
          self.cursor.execute(command, list(updates.values()) + list(conditions.values()))
          self.connection.commit()

