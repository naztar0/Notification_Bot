#!/usr/bin/env python
import constants as c
import mysql.connector

from aiogram import Bot, Dispatcher, types, utils
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

bot = Bot(c.token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Admin(StatesGroup):
    func = State()
    type = State()
    min_count = State()
    data = State()


cancel_button = "❌ Отмена"
buttons_funcs = ("Текст", "Стикер", "Фото", "Видео", "Опрос")
buttons_types = ("Тип 1", "Тип 2", "Тип 3", "Тип 4", "Все типы с огр.", "Все пользователи")


# выбор типа
async def choose_type(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['func'] = message.text
    await Admin.next()  # type
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(buttons_types[0], buttons_types[1])
    key.add(buttons_types[2], buttons_types[3])
    key.add(buttons_types[4], buttons_types[5])
    key.add(cancel_button)
    await message.answer("Выберите пользователей\n\n"
                         "Тип 1 - Одноразовое\nТип 2 - Ежедневное\nТип 3 - По дням недели\nТип 4 - По числам месяца", reply_markup=key)


async def choose_users_min_count(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['type'] = message.text
    await Admin.next()  # min_count
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(cancel_button)
    if message.text == buttons_types[5]:
        await Admin.next()  # data
        await message.answer(f"Отправьте {data['func']} для рассылки", reply_markup=key)
    else:
        await message.answer("Введите минимальное количество сообщений, которые соответствуют " + message.text, reply_markup=key)


async def input_data(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['min'] = int(message.text)
    await Admin.next()  # data
    await message.answer(f"Отправьте {data['func']} для рассылки")


def get_users(users_type, min_count):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    select_all_users_query = "SELECT user_id FROM users"
    cursor.execute(select_all_users_query)
    all_users = cursor.fetchall()
    res_users = all_users.copy()
    if min_count:
        if users_type:
            selectQuery = "SELECT ID FROM notifications WHERE user_id=(%s) AND type=(%s) HAVING COUNT(ID) >= %s"
            for user in all_users:
                cursor.executemany(selectQuery, [(user[0], users_type, min_count)])
                match = cursor.fetchone()
                if not match:
                    res_users.remove(user)
        else:
            selectQuery = "SELECT ID FROM notifications WHERE user_id=(%s) HAVING COUNT(ID) >= %s"
            for user in all_users:
                cursor.executemany(selectQuery, [(user[0], min_count)])
                match = cursor.fetchone()
                if not match:
                    res_users.remove(user)
    conn.close()
    return res_users


async def choose_func(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        func = data['func']
        users_type = data['type']
        min_count = data['min']
    await state.finish()

    if users_type == buttons_types[5]:
        min_count = None
    if users_type == buttons_types[4] or users_type == buttons_types[5]:
        users_type = None
    else:
        users_type = int(users_type[4:])

    users = get_users(users_type, min_count)

    if func == buttons_funcs[0]:
        await admin_send_text(message, users)
    elif func == buttons_funcs[1]:
        await admin_send_sticker(message, users)
    elif func == buttons_funcs[2]:
        await admin_send_photo(message, users)
    elif func == buttons_funcs[3]:
        await admin_send_video(message, users)
    elif func == buttons_funcs[4]:
        await admin_send_poll(message, users)


async def admin_send_text(message, users):
    try: text = message.text
    except AttributeError: return
    i = 0
    if users:
        for user in users:
            try:
                await bot.send_message(user[0], text)
                i += 1
            except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))


async def admin_send_sticker(message, users):
    try: fileID = message.sticker.file_id
    except AttributeError: return
    i = 0
    if users:
        for user in users:
            try:
                await bot.send_sticker(user[0], fileID)
                i += 1
            except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))


async def admin_send_photo(message, users):
    try: fileID = message.photo[-1].file_id
    except AttributeError: return
    except TypeError: return
    i = 0
    if users:
        for user in users:
            try:
                await bot.send_photo(user[0], fileID)
                i += 1
            except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))


async def admin_send_video(message, users):
    try: fileID = message.video.file_id
    except AttributeError: return
    i = 0
    if users:
        for user in users:
            try:
                await bot.send_video(user[0], fileID)
                i += 1
            except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))


async def admin_send_poll(message, users):
    i = 0
    if users:
        for user in users:
            try:
                await bot.forward_message(user[0], message.chat.id, message.message_id)
                i += 1
            except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))
