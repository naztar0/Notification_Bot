#!/usr/bin/env python
import constants as c
import mysql.connector
import asyncio
import datetime

from aiogram import Bot, Dispatcher, utils

bot = Bot(c.token)
dp = Dispatcher(bot)

select_query = "SELECT * FROM admin_notifications WHERE flag=0 LIMIT 50 OFFSET %s"
select_all_users_query = "SELECT user_id FROM users"
rows_count_query = f"SELECT TABLE_ROWS FROM TABLES WHERE TABLE_SCHEMA = '{c.db}' AND TABLE_NAME = 'admin_notifications'"
flag_set_query = "UPDATE admin_notifications SET flag=1 WHERE ID=(%s)"
delete_query = "DELETE FROM admin_notifications WHERE ID=(%s)"


async def send_notification(text, media, users):
    for user in users:
        try:
            if media:
                await bot.send_photo(user[0], media, text)
            else:
                await bot.send_message(user[0], text)
        except utils.exceptions.BotBlocked: pass
        except utils.exceptions.UserDeactivated: pass
        except utils.exceptions.ChatNotFound: pass
        except utils.exceptions.BadRequest: pass


async def loop_checker():
    while True:
        now = datetime.datetime.now()
        now = datetime.datetime(now.year, now.month, now.day, now.hour, now.minute)
        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database="INFORMATION_SCHEMA")
        cursor = conn.cursor(buffered=True)
        cursor.execute(rows_count_query)
        rows = cursor.fetchone()[0]
        conn.close()
        print("admin rows:", rows)

        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)

        cursor.execute(select_all_users_query)
        users = cursor.fetchall()

        for offset in range(0, rows, 50):
            cursor.execute(select_query, [offset])
            results = cursor.fetchall()
            for user in results:
                ID, Type, regularity, time, Datetime, text, media = \
                    user[0], user[1], user[2], user[3], user[4], user[5], user[6]

                if Type == 1:
                    if Datetime == now:
                        await send_notification(text, media, users)
                        cursor.execute(delete_query, [ID])
                else:
                    time = [time.seconds // 3600, (time.seconds // 60) % 60]
                    if time[0] == now.hour and time[1] == now.minute:
                        if Type == 2:
                            await send_notification(text, media, users)
                            cursor.execute(flag_set_query, [ID])

                        elif Type == 3:
                            weekday_now = datetime.datetime.weekday(datetime.datetime.now())
                            days = eval(regularity)
                            for day in days:
                                if day == 'Пн': day = 0
                                elif day == 'Вт': day = 1
                                elif day == 'Ср': day = 2
                                elif day == 'Чт': day = 3
                                elif day == 'Пт': day = 4
                                elif day == 'Сб': day = 5
                                elif day == 'Вс': day = 6

                                if day == weekday_now:
                                    await send_notification(text, media, users)
                                    cursor.execute(flag_set_query, [ID])
                        elif Type == 4:
                            days = eval(regularity)
                            for day in days:
                                if int(day) == now.day:
                                    await send_notification(text, media, users)
                                    cursor.execute(flag_set_query, [ID])
                conn.commit()
        conn.close()
        await asyncio.sleep(30)
