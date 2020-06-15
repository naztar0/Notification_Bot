#!/usr/bin/env python
import constants as c
import mysql.connector
import re
import datetime

from aiogram import Bot, Dispatcher, executor, types  # , utils
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

bot = Bot(c.token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Form(StatesGroup):
    type = State()
    subtype = State()
    regularity = State()
    Time = State()
    text = State()
    DateTime = State()


cancel_button = "❌ Отмена"
days = {"Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"}

main_buttons = ("Посмотреть сообщения", "Создать сообщение")
type_buttons = ("Одноразовое", "Повторяющееся")
subtype_buttons = ("Ежедневное", "По дням недели", "По числам месяца")


# главная клавиатура
def main_key():
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(types.KeyboardButton(main_buttons[0]))
    key.add(types.KeyboardButton(main_buttons[1]))
    return key


async def cancel(message, state):
    if message.text == cancel_button:
        await state.finish()
        await message.answer("Отменено!")
        return True
    return False


async def wrong_input(message, buttons, state):
    if message.text not in buttons:
        await state.finish()
        await message.answer("Неправильный ввод!")
        return True
    return False


def input_to_database(user, data):
    typ = data['type']
    if typ == type_buttons[0]: typ = 1
    else:
        typ = data['subtype']
        if typ == subtype_buttons[0]: typ = 2
        elif typ == subtype_buttons[1]: typ = 3
        elif typ == subtype_buttons[2]: typ = 4

    inputQuery = "INPUT INTO users (user_id, type, regularity, time, datetime, text, media)" \
                 "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    cursor.executemany(inputQuery, [(user, typ, str(data['reg']), data['time'], data['datetime'], data['text'], data['media'])])
    conn.commit()
    conn.close()


@dp.message_handler(commands=['start'])
async def message_handler(message: types.Message):
    # сброс всех пользовательских уведомлений, если он были
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    deleteQuery = "DELETE FROM users WHERE user_id=(%s)"
    cursor.execute(deleteQuery, [message.chat.id])
    conn.commit()
    conn.close()

    await message.answer("message_1")
    await message.answer("message_2", reply_markup=main_key())


@dp.message_handler(content_types=['text'])
async def message_handler(message: types.Message):
    if message.text == main_buttons[0]:  # Посмотреть сообщения
        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)
        selectQuery = "SELECT ID, text, media, regularity, time, datetime FROM users WHERE user_id=(%s)"
        cursor.execute(selectQuery, [message.chat.id])
        result = cursor.fetchall()
        conn.close()

        print(result)

    elif message.text == main_buttons[1]:  # Создать сообщение
        key = types.ReplyKeyboardMarkup(resize_keyboard=True)
        key.add(types.KeyboardButton(type_buttons[0]))
        key.add(types.KeyboardButton(type_buttons[1]))
        key.add(types.KeyboardButton(cancel_button))
        await Form.type.set()
        await message.answer("Выберите тип сообщения")


@dp.message_handler(content_types=['text'], state=Form.type)
async def choose_type(message: types.Message, state: FSMContext):
    if await cancel(message, state): return
    if await wrong_input(message, type_buttons, state): return

    async with state.proxy() as data:
        data['type'] = message.text

    await Form.next()  # подтипы
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if message.text == type_buttons[0]:
        await Form.next()  # регулярность
        await Form.next()  # время
        await Form.next()  # текст
        key.add(types.KeyboardButton(cancel_button))
        await message.answer("Введите текст сообщения", reply_markup=key)
    else:
        key.add(types.KeyboardButton(subtype_buttons[0]))
        key.add(types.KeyboardButton(subtype_buttons[1]))
        key.add(types.KeyboardButton(subtype_buttons[2]))
        key.add(types.KeyboardButton(cancel_button))
        await message.answer("Выберите подтип сообщения", reply_markup=key)


@dp.message_handler(content_types=['text'], state=Form.subtype)
async def choose_subtype(message: types.Message, state: FSMContext):
    if await cancel(message, state): return
    if await wrong_input(message, subtype_buttons, state): return

    async with state.proxy() as data:
        data['subtype'] = message.text

    await Form.next()  # регулярность
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if message.text == subtype_buttons[0]:
        await Form.next()  # время
        key.add(types.KeyboardButton(cancel_button))
        await message.answer("Введите время отправки сообщения\n_Например:_ `12:00`", reply_markup=key, parse_mode="Markdown")
    elif message.text == subtype_buttons[1]:
        key.add(days)
        key.add(types.KeyboardButton("Закончить выбор"))
        key.add(types.KeyboardButton(cancel_button))
        await message.answer("Выберите нужные дни недели, после чего нажмите кнопку 'Закончить выбор'", reply_markup=key)
    elif message.text == subtype_buttons[2]:
        await message.answer("Введите числа месяца через запятую\n_Например:_ `3, 7, 30`\n_Например:_ `21`", parse_mode="Markdown")


@dp.message_handler(content_types=['text'], state=Form.regularity)
async def choose_regularity(message: types.Message, state: FSMContext):
    if await cancel(message, state): return
    text = str(message.text)

    async with state.proxy() as data:
        data = data

    if data['subtype'] == subtype_buttons[1]:
        if text == "Закончить выбор":
            if not data['reg']:
                await message.answer("Выберите хотя-бы один день!")
            else:
                await Form.next()  # время
                key = types.ReplyKeyboardMarkup()
                key.add(types.KeyboardButton(cancel_button))
                await message.answer("Введите время отправки сообщения\n_Например:_ `12:00`", reply_markup=key, parse_mode="Markdown")
            return
        if await wrong_input(message, days, state): return

        async with state.proxy() as data:
            if not data['reg']:
                data['reg'] = {}
                data['reg'].append(text)
            else:
                data['reg'].append(text)
        await message.answer("Выбраны дни: " + ', '.join(data['reg']))

    elif data['subtype'] == subtype_buttons[2]:
        text = text.replace(' ', '')
        nums = {text.split(',')[x] for x in range(len(text.split(',')))}
        try:
            check = len(set(filter(lambda x: 0 < int(x) < 32, nums))) == len(nums)
        except ValueError:
            check = False
        if not check:
            await message.answer("Неправильный ввод!")
            return
        async with state.proxy() as data:
            data['reg'] = nums
        await message.answer("Выбраны числа: " + ', '.join(nums))
        await Form.next()  # время
        key = types.ReplyKeyboardMarkup()
        key.add(types.KeyboardButton(cancel_button))
        await message.answer("Введите время отправки сообщения\n_Например:_ `12:00`", reply_markup=key, parse_mode="Markdown")


@dp.message_handler(content_types=['text'], state=Form.Time)
async def choose_regularity(message: types.Message, state: FSMContext):
    if await cancel(message, state): return
    text = message.text

    nums = [text.split(':')[x] for x in range(2)]
    try:
        check = 0 < int(nums[0]) < 24 and 0 < int(nums[1]) < 60
    except ValueError:
        check = False
    if not check:
        await message.answer("Неправильный ввод!")
        return

    async with state.proxy() as data:
        data['time'] = nums

    await Form.next()
    await message.answer("Отправьте текст и/или фото напоминания")


@dp.message_handler(content_types=['text', 'photo'], state=Form.text)
async def choose_regularity(message: types.Message, state: FSMContext):
    if await cancel(message, state): return

    try: photo = message.photo[-1].file_id
    except IndexError: photo = None
    async with state.proxy() as data:
        if photo is None:
            data['text'] = message.text
        else:
            data['text'] = message.caption
            data['media'] = photo

    text = data['text']
    if len(text) > 250:
        async with state.proxy() as data:
            data['text'] = None
        await message.answer("Сообщение слишком длинное!")
        return

    async with state.proxy() as data:
        data['text'] = text

    if data['type'] == type_buttons[0]:
        await Form.next()
        await message.answer("Введите дату и время отправки сообщения\n\n_Например_: `2020.09.21 09:00`")
        return
    else:
        await state.finish()
        input_to_database(message.from_user.id, data)
        await message.answer("Сообщение успешно создано!")


@dp.message_handler(content_types=['text', 'photo'], state=Form.DateTime)
async def choose_regularity(message: types.Message, state: FSMContext):
    if await cancel(message, state): return

    text = message.text
    if not re.search(r"^(202\d\.[01]\d\.[0-3]\d [012]\d:[0-6]\d)$", text):
        await message.reply("Неправильный формат! Проверьте вводимые данные и попробуйте еще раз.")
        return
    year, month, day, hour, minute = int(text[:4]), int(text[5:7]), int(text[8:10]), int(text[11:13]), int(text[14:16])
    if not 0 < month < 13 or 0 < day < 32 or hour < 24 or minute < 60:
        await message.reply("Неправильный формат! Проверьте вводимые данные и попробуйте еще раз.")
        return

    dt = datetime.datetime(year, month, day, hour, minute)
    async with state.proxy() as data:
        data['datetime'] = dt
        input_to_database(message.from_user.id, data)
        await message.answer("Сообщение успешно создано!")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
