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

async def insertEntry(database, event):
     commands = (
          sql.SQL('''SET TIMEZONE TO {timezone};''').format(
               timezone = sql.Identifier(event[4])),
          sql.SQL(
          '''
               SELECT Name, Channel, Datetime 
               FROM {table} 
               WHERE Name = %s AND Channel = %s AND DATETIME = %s
               LIMIT 1
          ''').format(
               table = sql.Identifier(database)),
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
               match = cursor.execute(commands[1], (event[0], event[2], event[3]))
               if match != None:
                    raise errors.RepetitionError
          except errors.RepetitionError:
               logging.info("Entry already exists")
               raise errors.RepetitionError
          except Exception as e:
               logging.info("Error with retrieving matching events: {}".format(e)) 
          else:
               try:
                    cursor.execute(commands[2], (event[0], event[1], event[2], event[3]))
                    connection.commit()
               except Exception as e:
                    logging.info("Error with inserting data: {}".format(e))

async def deleteEntry(database, key, event):
     try:
          cursor.execute(
               sql.SQL("DELETE FROM {table} WHERE {column} = %s;").format(
                    table = sql.Identifier(database),
                    column = sql.Identifier(database, key)), [event[0]])
          connection.commit()
     except Exception as e:
          logging.info("Error with deleting data: {}".format(e))
