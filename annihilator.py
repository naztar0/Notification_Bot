#!/usr/bin/env python
import constants as c
import mysql.connector
import datetime
import asyncio

query1 = "UPDATE notifications SET flag=0"
query2 = "UPDATE admin_notifications SET flag=0"


async def loop_annihilator():
    while True:
        if datetime.datetime.now().hour == 0 and datetime.datetime.now().minute == 2:
            conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
            cursor = conn.cursor(buffered=True)
            cursor.execute(query1)
            cursor.execute(query2)
            conn.commit()
            conn.close()
        await asyncio.sleep(10)
