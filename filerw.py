import logging
import errors
import psycopg2

from datetime import datetime, timedelta
from psycopg2 import sql

def retryConnection(function):
     """Decorate a database function to handle connection failures.

     Parameters
     ----------
     function : function
          The database function run within the decorator
     
     Returns
     -------
     function
          The decorated database function
     """
     async def handleFailure(*args):
          """Run a database function and reset the connection and cursor objects if an error is returned.

          Parameters
          ----------
          *args: List of arguments of variable length

          Raises
          ------
          errors.NoServerConnectionError
               If resetting the connection and cursor five times does not result in the database function executing properly.
          """
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
     """
     A class used to handle connections and operations with the PostgreSQL database.

     Attributes
     ----------
     connection : psycopg2.connection
     cursor : psycopg2.cursor

     Methods
     -------
     setTime(tz)
          Set the timezone of the database.
     retrieveFirstEntry(database, key, columns)
          Retrieve the first entry in a sorted column.
     retrieveAllColumns(database)
          Retrieve all columns of all entries from a table.
     retrieveSpecificColumns(database, columns)
          Retrieve specific columns of all entries from a table.
     findEntries(database, searchTerms, columns)
          Retrieve specific columns of entries meeting a user-defined requirement.
     insertEntry(database, entry)
          Insert an entry into a table.
     insertEvent(entry)
          Insert an event into a table after setting the timezone and checking for duplicates.
     insertMultipleEvents(entriesList)
          Insert multiple events into a table after setting the timezone and checking for duplicates.
     deleteEntry(self, database, params)
          Delete an entry from a table.
     updateEntry(self, database, updates, conditions)
          Update an entry in a table.
     """

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
          """Set the timezone of the database.

          Parameters
          ----------
          tz : str
               The timezone the database is set to
          """
          command = sql.SQL('''SET TIMEZONE TO {timezone};''').format(
                    timezone = sql.Identifier(tz))
          self.cursor.execute(command)

     @retryConnection
     async def retrieveFirstEntry(self, database, key, columns):
          """Retrieve the first entry in a sorted column.

          Parameters
          ----------
          database : str
               The name of the table the entry is retrieved from
          key : str
               The column name that the entries are sorted by
          columns : list
               The column name(s) of the entry that is/are returned
          
          Returns
          -------
          Tuple
               The information contained within the specified columns of the entry
          """
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
          """Retrieve all columns of all entries from a table.

          Parameters
          ----------
          database : str
               The name of the table the entry is retrieved from
          
          Returns
          -------
          List
               Tuples containing the information of every entry in the table
          """
          command = sql.SQL('''SELECT * FROM {table};''').format(
                    table = sql.Identifier(database)
               )
          self.cursor.execute(command)
          return self.cursor.fetchall()
     
     @retryConnection
     async def retrieveSpecificColumns(self, database, columns):
          """Retrieve specific columns of all entries from a table.

          Parameters
          ----------
          database : str
               The name of the table the entry is retrieved from
          columns : list
               The column name(s) of the entry that is/are returned
          
          Returns
          -------
          List
               Tuples containing the information of every entry in the table
          """
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
          """Retrieve specific columns of entries meeting a user-defined requirement.

          Parameters
          ----------
          database : str
               The name of the table the entry is retrieved from
          searchTerms : dictionary
               The column name(s) and information that the entry/ies returned must contain.
          columns : list
               The column name(s) of the entry/ies that is/are returned
          
          Returns
          -------
          List
               Tuples containing the information of every entry in the table
          """
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
          """Insert an event into a table after setting the timezone and checking for duplicates.

          Parameters
          ----------
          database : str
               The name of the table the entry is inserted into
          entry : tuple
               The entry that is being inserted into the table
          """
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
          """Insert multiple events into a table after setting the timezone and checking for duplicates.

          Parameters
          ----------
          entry : tuple
               The event that is being inserted into the events table
          """
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

     async def insertMultipleEvents(self, entriesList): #used for !recurringevents, but unsure if it results in better performance
          """Insert multiple events into a table after setting the timezone and checking for duplicates.

          Parameters
          ----------
          entriesList : list
               The events being inserted into the events table
          """
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
          """Delete an entry from a table.

          Parameters
          ----------
          database : str
               The name of the table the entry is deleted from
          params: dict
               The column name(s) and information that the entry/ies to be deleted must have 
          """
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
          """Update an entry in a table.

          Parameters
          ----------
          database : str
               The name of the table the entry is deleted from
          updates : dict
               The column name(s) and information that the entry/ies to be updated will be updated to have
          conditions : dict
               The column name(s) and information that the entry/ies to be updated must have
          """
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

