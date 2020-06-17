#!/usr/bin/env python
import constants as c
import mysql.connector
import re
import datetime

from aiogram import Bot, Dispatcher, executor, types  # , utils
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

import admin_panel as ap
import loop_checker
import annihilator

bot = Bot(c.token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Form(StatesGroup):
    text = State()
    type = State()
    subtype = State()
    regularity = State()
    Time = State()
    DateTime = State()


class Delete(StatesGroup): num = State()


cancel_button = "❌ Отмена"
days = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

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
        await message.answer("Отменено!", reply_markup=main_key())
        return True
    return False


async def wrong_input(message, buttons, state):
    if message.text not in buttons:
        await state.finish()
        await message.answer("Неправильный ввод!")
        return True
    return False


def input_to_database(user, data):
    typ, reg = data['type'], data['reg']
    if typ == type_buttons[0]: typ = 1
    else:
        typ = data['subtype']
        if typ == subtype_buttons[0]: typ = 2
        elif typ == subtype_buttons[1]: typ = 3
        elif typ == subtype_buttons[2]: typ = 4
    if type(reg) == set or type(reg) == list:
        reg = str(list(reg))

    inputQuery = "INSERT INTO users (user_id, type, regularity, time, datetime, text, media) " \
                 "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    updateQuery = "UPDATE users SET type=(%s), regularity=(%s), time=(%s), datetime=(%s) WHERE ID=(%s)"
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    try:
        data['text']
    except KeyError:
        cursor.executemany(updateQuery, [(typ, reg, data['time'], data['datetime'], data['media'])])
    else:
        cursor.executemany(inputQuery, [(user, typ, reg, data['time'], data['datetime'], data['text'], data['media'])])
    conn.commit()
    conn.close()


def view_message(result, one=False):
    string = []
    if one: string = ""
    for res in result:
        text = "🚫 Нет"
        if res[1]: text = str(res[1])
        media = "🚫 Нет"
        if res[2]: media = "✅ Есть"
        typ = res[3]

        typ_str = None
        reg = "—"
        if typ == 1:
            typ_str = type_buttons[0]
            reg = datetime.datetime.strftime(res[6], "%d.%m.%y")
            tm = datetime.datetime.strftime(res[6], "%H:%M")
        else:
            tm = str(res[5].seconds // 3600).zfill(2) + ':' + str((res[5].seconds // 60) % 60).zfill(2)
            if typ == 2:
                typ_str = subtype_buttons[0]
                reg = subtype_buttons[0]
            elif typ == 3:
                typ_str = subtype_buttons[1]
                reg = ', '.join(eval(res[4]))
            elif typ == 4:
                typ_str = subtype_buttons[2]
                reg = ', '.join(eval(res[4]))

        if one:
            string = f"📌 *Тип отправки:* {typ_str}\n📆 *Дни отправки:* {reg}\n⏰ *Время отправки:* {tm}\n" \
                     f"🖼 *Фото:* {media}\n📄 *Текст:* {text}"
        else:
            string.append(f"\\[/1{res[0]}] ➖ 📝 *изменить*\n\\[/2{res[0]}] ➖ ❌ *удалить*\n"
                          f"📌 *Тип отправки:* {typ_str}\n📆 *Дни отправки:* {reg}\n⏰ *Время отправки:* {tm}\n"
                          f"🖼 *Фото:* {media}\n📄 *Текст:* {text}\n➖➖➖➖➖➖➖➖\n\n")
    return string


async def view_all_messages(message):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT ID, text, media, type, regularity, time, datetime FROM users WHERE user_id=(%s)"
    cursor.execute(selectQuery, [message.chat.id])
    result = cursor.fetchall()
    conn.close()

    string = view_message(result)
    if not string:
        await message.answer("У Вас ещё нет ни одного напоминания")
        return
    piece = []
    max_size = 4096
    for s in string:
        piece.append(s)
        if len(''.join(piece)) < max_size:
            continue
        del piece[-1]
        await message.answer(''.join(piece), parse_mode="Markdown")
        piece = [s]
    await message.answer(''.join(piece), parse_mode="Markdown")


def select_message(message):
    num = message.text[2:]
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT ID, text, media, type, regularity, time, datetime FROM users WHERE user_id=(%s) AND ID=(%s)"
    cursor.executemany(selectQuery, [(message.chat.id, num)])
    result = cursor.fetchall()
    conn.close()
    return result


async def edit_message(message, state):
    num = message.text[2:]
    result = select_message(message)
    if not result:
        await message.reply("Неправильная команда!")
        return
    string = "*Выбрано сообщение:\n\n*" + view_message(result, True) + "\n\n*Выберите новый тип для этого сообщения*"
    await Form.text.set()
    await Form.next()  # тип
    async with state.proxy() as data:
        data['media'] = num
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(types.KeyboardButton(type_buttons[0]))
    key.add(types.KeyboardButton(type_buttons[1]))
    key.add(types.KeyboardButton(cancel_button))
    await message.answer(string, reply_markup=key, parse_mode="Markdown")


async def delete_message(message, state):
    num = message.text[2:]
    result = select_message(message)
    if not result:
        await message.reply("Неправильная команда!")
        return
    string = "*Выбрано сообщение:\n\n*" + view_message(result, True) + "\n\n*Удалить это напоминание?*"
    await Delete.num.set()
    async with state.proxy() as data:
        data['num'] = num
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(types.KeyboardButton("Удалить"))
    key.add(types.KeyboardButton(cancel_button))
    await message.answer(string, parse_mode="Markdown", reply_markup=key)


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


@dp.message_handler(content_types=['text', 'photo'], state=Form.text)
async def choose_regularity(message: types.Message, state: FSMContext):
    if await cancel(message, state): return

    text = None
    try: photo = message.photo[-1].file_id
    except IndexError: photo = None
    async with state.proxy() as data:
        if photo is None:
            data['media'] = None
            text = message.text
        else:
            data['media'] = photo
            if message.caption:
                text = message.caption

    if text:
        text = str(text).replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')
        if len(text) > 150:
            async with state.proxy() as data:
                data['text'] = None
            await message.answer("Сообщение слишком длинное!")
            return
    async with state.proxy() as data:
        data['text'] = text

    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(types.KeyboardButton(type_buttons[0]))
    key.add(types.KeyboardButton(type_buttons[1]))
    key.add(types.KeyboardButton(cancel_button))
    await Form.next()
    await message.answer("Выберите тип сообщения", reply_markup=key)


@dp.message_handler(content_types=['text'], state=Form.type)
async def choose_type(message: types.Message, state: FSMContext):
    if await cancel(message, state): return
    if await wrong_input(message, type_buttons, state): return

    async with state.proxy() as data:
        data['type'] = message.text
        data['reg'], data['time'], data['datetime'] = None, None, None

    await Form.next()  # подтипы
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if message.text == type_buttons[0]:
        await Form.next()  # регулярность
        await Form.next()  # время
        await Form.next()  # дата и время
        key.add(types.KeyboardButton(cancel_button))
        await message.answer("Введите дату и время отправки сообщения\n\n_Например_: `2020.09.21 09:00`", parse_mode="Markdown", reply_markup=key)
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
        key.add(days[0], days[1])
        key.add(days[2], days[3])
        key.add(days[4], days[5], days[6])
        key.add(types.KeyboardButton("Закончить выбор"))
        key.add(types.KeyboardButton(cancel_button))
        await message.answer("Выберите нужные дни недели, после чего нажмите кнопку 'Закончить выбор'", reply_markup=key)
    elif message.text == subtype_buttons[2]:
        key.add(types.KeyboardButton(cancel_button))
        await message.answer("Введите числа месяца через запятую\n_Например:_ `3, 7, 30`\n_Например:_ `21`", parse_mode="Markdown", reply_markup=key)


@dp.message_handler(content_types=['text'], state=Form.regularity)
async def choose_regularity(message: types.Message, state: FSMContext):
    if await cancel(message, state): return
    text = str(message.text)

    async with state.proxy() as data:
        data = data

    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if data['subtype'] == subtype_buttons[1]:
        if text == "Закончить выбор":
            if not data['reg']:
                await message.answer("Выберите хотя-бы один день!")
            else:
                await Form.next()  # время
                key.add(types.KeyboardButton(cancel_button))
                await message.answer("Введите время отправки сообщения\n_Например:_ `12:00`", reply_markup=key, parse_mode="Markdown")
            return
        if await wrong_input(message, days, state): return

        async with state.proxy() as data:
            if not data['reg']:
                data['reg'] = set()
                data['reg'].add(text)
            else:
                data['reg'].add(text)
        await message.answer("Выбраны дни: " + ', '.join(data['reg']))

    elif data['subtype'] == subtype_buttons[2]:
        text = text.replace(' ', '')
        nums = {text.split(',')[x] for x in range(len(text.split(',')))}
        try:
            check = len(set(filter(lambda x: 0 < int(x) < 32, nums))) == len(nums)
        except ValueError:
            check = False
        if not check:
            await message.reply("Неправильный ввод!")
            return
        nums = sorted(nums, key=int)
        async with state.proxy() as data:
            data['reg'] = nums
        await message.answer("Выбраны числа: " + ', '.join(nums))
        await Form.next()  # время
        key.add(types.KeyboardButton(cancel_button))
        await message.answer("Введите время отправки сообщения\n_Например:_ `12:00`", reply_markup=key, parse_mode="Markdown")


@dp.message_handler(content_types=['text'], state=Form.Time)
async def choose_regularity(message: types.Message, state: FSMContext):
    if await cancel(message, state): return
    text = message.text

    try:
        nums = [int(text.split(':')[x]) for x in range(2)]
        tm = datetime.time(nums[0], nums[1])
    except ValueError:
        await message.reply("Неправильный ввод!")
        return
    except IndexError:
        await message.reply("Неправильный ввод!")
        return

    async with state.proxy() as data:
        data['time'] = tm

    await state.finish()
    input_to_database(message.from_user.id, data)
    await message.answer("Напоминание успешно сохранено!", reply_markup=main_key())


@dp.message_handler(content_types=['text'], state=Form.DateTime)
async def choose_regularity(message: types.Message, state: FSMContext):
    if await cancel(message, state): return

    text = message.text
    if not re.search(r"^(202\d\.[01]\d\.[0-3]\d [012]\d:[0-6]\d)$", text):
        await message.reply("Неправильный формат! Проверьте вводимые данные и попробуйте еще раз.")
        return
    year, month, day, hour, minute = int(text[:4]), int(text[5:7]), int(text[8:10]), int(text[11:13]), int(text[14:16])
    try:
        dt = datetime.datetime(year, month, day, hour, minute)
    except ValueError:
        await message.reply("Дата или время недействительны! Проверьте вводимые данные и попробуйте еще раз.")
        return

    async with state.proxy() as data:
        data['datetime'] = dt

    await state.finish()
    input_to_database(message.from_user.id, data)
    await message.answer("Напоминание успешно сохранено!", reply_markup=main_key())


@dp.message_handler(content_types=['text'], state=Delete.num)
async def choose_regularity(message: types.Message, state: FSMContext):
    if await cancel(message, state): return
    if message.text != "Удалить":
        await state.finish()
        await message.reply("Отменено", reply_markup=main_key())
        return

    async with state.proxy() as data:
        data = data['num']
    await state.finish()

    deleteQuery = "DELETE FROM users WHERE ID=(%s)"
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    cursor.execute(deleteQuery, [data])
    conn.commit()
    conn.close()
    await message.answer("Напоминание успешно удалено!", reply_markup=main_key())


# ADMIN PANEL
@dp.message_handler(commands=['admin'])
async def message_handler(message: types.Message):
    if message.chat.id == c.admin:
        await message.answer("/text\n/sticker\n/photo\n/video\n/poll")


@dp.message_handler(commands=['text'])
async def message_handler(message: types.Message, state: FSMContext):
    if message.chat.id == c.admin:
        await ap.admin_choose_type(message, "текст", state)


@dp.message_handler(commands=['sticker'])
async def message_handler(message: types.Message, state: FSMContext):
    if message.chat.id == c.admin:
        await ap.admin_choose_type(message, "стикер", state)


@dp.message_handler(commands=['photo'])
async def message_handler(message: types.Message, state: FSMContext):
    if message.chat.id == c.admin:
        await ap.admin_choose_type(message, "фото", state)


@dp.message_handler(commands=['video'])
async def message_handler(message: types.Message, state: FSMContext):
    if message.chat.id == c.admin:
        await ap.admin_choose_type(message, "видео", state)


@dp.message_handler(commands=['poll'])
async def message_handler(message: types.Message, state: FSMContext):
    if message.chat.id == c.admin:
        await ap.admin_choose_type(message, "опрос", state)


# ОБРАБОТКА ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ
@dp.message_handler(content_types=['text'])
async def message_handler(message: types.Message, state: FSMContext):
    if message.text == main_buttons[0]:  # Посмотреть сообщения
        await view_all_messages(message)

    elif message.text == main_buttons[1]:  # Создать сообщение
        key = types.ReplyKeyboardMarkup(resize_keyboard=True)
        key.add(types.KeyboardButton(cancel_button))
        await Form.text.set()
        await message.answer("Отправьте текст и/или фото напоминания", reply_markup=key)

    elif message.text == cancel_button:
        await message.answer("Отменено!", reply_markup=main_key())

    elif message.text[:2] == "/1":
        await edit_message(message, state)

    elif message.text[:2] == "/2":
        await delete_message(message, state)


if __name__ == "__main__":
    dp.loop.create_task(loop_checker.loop_checker())
    dp.loop.create_task(annihilator.loop_annihilator())
    executor.start_polling(dp, skip_updates=True)
