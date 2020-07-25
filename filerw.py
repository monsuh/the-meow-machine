import logging
import errors

from datetime import datetime, timedelta
from setup import connection, cursor
from psycopg2 import sql

async def retrieveFirstEntry(database, key):
     try:
          cursor.execute(
               sql.SQL('SELECT * FROM {table} ORDER BY {orderKey};').format(
                    table = sql.Identifier(database), 
                    orderKey = sql.Identifier(database, key)))
          return cursor.fetchone()
     except Exception as e:
          logging.info("Error with retrieving first entry: {}".format(e))

async def retrieveAllEntries(database):
     try:
          cursor.execute(
               sql.SQL("SELECT * FROM {table}").format(
                    table = sql.Identifier(database)))
          return cursor.fetchall()
     except Exception as e:
          logging.info("Error with retrieving entries: {}".format(e))

async def findEntries(database, searchTerms):
     try:
          command = sql.SQL(
               '''
                    SELECT {columns} 
                    FROM {table} 
                    WHERE {conditions}
                    LIMIT 1
               ''').format(
                    columns = sql.SQL(', ').join(
                         sql.Identifier(database, key) for key in searchTerms.keys()    
                    ),
                    table = sql.Identifier(database),
                    conditions = sql.SQL(' AND ').join(
                         sql.Composed([sql.Identifier(database, key), sql.SQL(" = "), sql.Placeholder()]) for key in searchTerms.keys()
                    )
               )
          print(command.as_string(connection))
          print(list(searchTerms.values()))
          cursor.execute(command, list(searchTerms.values()))
          return cursor.fetchall()
     except Exception as e:
          logging.info("Error with retrieving entries with matching keys: {}".format(e))

async def insertEntry(database, entry):
     commands = (
          sql.SQL('''SET TIMEZONE TO {timezone};''').format(
               timezone = sql.Identifier(entry[4])),
          sql.SQL(
          '''
               INSERT INTO {table}
               VALUES (%s, %s, %s, %s);
          ''').format(
               table = sql.Identifier(database))
     )
     try:
          cursor.execute(commands[0])
     except Exception as e:
          logging.info("Error with setting time zone: {}".format(e))
     else:
          try:
               match = await findEntries("events", {"name" : entry[0], "channel" : entry[2], "datetime" : entry[3]})
               if match != None:
                    raise errors.RepetitionError
          except errors.RepetitionError:
               logging.info("Entry already exists")
               raise errors.RepetitionError
          except Exception as e:
               logging.info("Error with retrieving matching entries: {}".format(e)) 
          else:
               try:
                    cursor.execute(commands[1], (entry[0], entry[1], entry[2], entry[3]))
                    connection.commit()
               except Exception as e:
                    logging.info("Error with inserting data: {}".format(e))

async def deleteEntry(database, key, entry):
     try:
          cursor.execute(
               sql.SQL("DELETE FROM {table} WHERE {column} = %s;").format(
                    table = sql.Identifier(database),
                    column = sql.Identifier(database, key)), [entry[0]])
          connection.commit()
     except Exception as e:
          logging.info("Error with deleting data: {}".format(e))
