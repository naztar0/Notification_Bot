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


class Form_admin(StatesGroup):
    func_elem_role = State()
    data = State()


# выбор типа
async def admin_choose_type(message, elem, state):
    await Form_admin.func_elem_role.set()
    async with state.proxy() as data:
        data['elem_role'] = [elem, None]
    choices = "/mom_with_children\n/remote_admin\n/unemployed\n/self_employed\n/remote_top\n/remote_student\n/worker\n/ALL"
    await message.answer("Выбери группу, которой нужно отправить:\n\n" + choices)


@dp.message_handler(state=Form_admin.func_elem_role)
async def admin_get_role(message: types.Message, state: FSMContext):
    role = str(message.text)[1:]
    async with state.proxy() as data:
        elem = data['func_elem_role'][0]
        data['func_elem_role'][1] = role
    if role not in {"mom_with_children", "remote_admin", "unemployed", "self_employed", "remote_top", "remote_student", "worker", "ALL"}:
        await message.answer("Ошибка ввода!")
        await state.finish()
        return
    await Form_admin.next()
    await message.answer(f"Отправь {elem} для рассылки")


def get_users(role):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    if role == "ALL":
        selectQuery = "SELECT user_id FROM users"
        cursor.execute(selectQuery)
    else:
        selectQuery = "SELECT user_id FROM users WHERE role=(%s)"
        cursor.execute(selectQuery, [role])
    users = cursor.fetchall()
    conn.close()
    return users


@dp.message_handler(state=Form_admin.data)
async def admin_choose_func(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        func = data['func_elem_role'][0]
        role = data['func_elem_role'][1]
    await state.finish()

    if func == "текст":
        await admin_send_text(message, role)
    elif func == "стикер":
        await admin_send_sticker(message, role)
    elif func == "фото":
        await admin_send_photo(message, role)
    elif func == "видео":
        await admin_send_video(message, role)
    elif func == "опрос":
        await admin_send_poll(message, role)


async def admin_send_text(message, role):
    try: text = message.text
    except AttributeError: return
    users = get_users(role)
    i = 0
    for user in users:
        try:
            await bot.send_message(user[0], text)
            i += 1
        except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))


async def admin_send_sticker(message, role):
    try: fileID = message.sticker.file_id
    except AttributeError: return
    users = get_users(role)
    i = 0
    for user in users:
        try:
            await bot.send_sticker(user[0], fileID)
            i += 1
        except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))


async def admin_send_photo(message, role):
    try: fileID = message.photo[-1].file_id
    except AttributeError: return
    except TypeError: return
    users = get_users(role)
    i = 0
    for user in users:
        try:
            await bot.send_photo(user[0], fileID)
            i += 1
        except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))


async def admin_send_video(message, role):
    try: fileID = message.video.file_id
    except AttributeError: return
    users = get_users(role)
    i = 0
    for user in users:
        try:
            await bot.send_video(user[0], fileID)
            i += 1
        except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))


async def admin_send_poll(message, role):
    users = get_users(role)
    i = 0
    for user in users:
        try:
            await bot.forward_message(user[0], message.chat.id, message.message_id)
            i += 1
        except utils.exceptions.BotBlocked: pass
    await message.answer("Количество пользователей, получивших сообщение: " + str(i))
