#!/usr/bin/env python
import constants as c
import mysql.connector
import datetime
import asyncio

query = "UPDATE users SET flag=0"


async def loop_annihilator():
    while True:
        if datetime.datetime.now().hour == 0 and datetime.datetime.now().minute == 0:
            conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
            cursor = conn.cursor(buffered=True)
            cursor.execute(query)
            conn.commit()
            conn.close()
        await asyncio.sleep(10)
