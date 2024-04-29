import logging
from typing import Text
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import random
import time
import datetime
from pydantic import NoneStr
from pytz import utc
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

bot = Bot(token="6769078740:AAE7TlYRzXl8PMO7WvMn84VszbZ_E15KKho", parse_mode='html')
dp = Dispatcher(bot, storage=MemoryStorage())

admin = 1814741745
coder = 1814741745

logging.basicConfig(filename='main.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def generate_key():
    s = '1234567890abcdefjkmnopqrstuviwxyzgABCDEFGHJKLMNPQRSTUVWXYZ'
    result = ''
    for i in range(25):
        result += random.choice(s)
    result += result[2] + result[5] + result[6] + result[10] + result[14] + result[17] + result[24]
    
    return result

def validate_key(key):
    try:
        hash = key[25:]
        key_hash = key[2] + key[5] + key[6] + key[10] + key[14] + key[17] + key[24]
        
        return key_hash == hash
    except:
        return False

def to_datetime(seconds):
    return datetime.datetime.utcfromtimestamp(seconds)

class database:
    def __init__(self):
        self.conn = sqlite3.connect("main.sqlite3")
        self.cursor = self.conn.cursor()
    def add_report(self, task_id, task_name, executor_id, content):
        self.cursor.execute('INSERT INTO reports (task_id, task_name, executor_id, content) VALUES (?,?,?,?)', (task_id, task_name, executor_id, str(content)))
        self.conn.commit()
        
        return [task_id, task_name, executor_id, content]
    def all_reports(self):
        self.cursor.execute('SELECT * FROM reports')
        return self.cursor.fetchall()
    def get_report(self, task_id):
        self.cursor.execute('SELECT * FROM reports WHERE task_id=?', (task_id,))
        return self.cursor.fetchone()
    def remove_report(self, report_id):
        self.cursor.execute('DELETE FROM reports WHERE task_id=?', (report_id,))
        self.conn.commit()
    def get_key_by_user(self, user_id):
        self.cursor.execute('SELECT * FROM keys WHERE user=?', (user_id,))
        return self.cursor.fetchone()
    def create_key(self, categories):
        key = generate_key()
        self.cursor.execute('INSERT INTO keys (text,categories) VALUES(?,?)', (key, str(categories)))
        self.conn.commit()
        
        return key
    def key_execute(self, user, key):
        self.cursor.execute('SELECT * FROM keys WHERE text=?', (key,))
        result = self.cursor.fetchall()
        if(result == []):
            return []
        else:
            if(result[-1][4] != 0):
                return []
            else:
                self.cursor.execute('UPDATE keys SET user=? WHERE text=?', (user, key))
                self.conn.commit()
                
                return result[-1]
    def key_delete_by_name(self, key):
        self.cursor.execute('DELETE FROM keys WHERE text=?', (key,))
        self.conn.commit()
    def key_delete_by_id(self, id):
        self.cursor.execute('DELETE FROM keys WHERE id=?', (id,))
        self.conn.commit()
    def active_user(self, id):
        self.cursor.execute('SELECT * FROM keys WHERE user=?', (id,))
        return (self.cursor.fetchall() != [])
    def get_all_categories(self):
        self.cursor.execute('SELECT * FROM categories')
        return self.cursor.fetchall()
    def get_category_name_by_id(self, id):
        self.cursor.execute('SELECT * FROM categories WHERE id=?', (id,))
        return self.cursor.fetchone()[1]
    def add_category(self, name):
        self.cursor.execute('INSERT INTO categories (name) VALUES (?)', (name,))
        self.conn.commit()
    def remove_category_by_id(self, id):
        self.cursor.execute('DELETE FROM categories WHERE id=?', (id,))
        self.conn.commit()
    def remove_category_by_name(self, name):
        self.cursor.execute('DELETE FROM categories WHERE name=?', (name,))
        self.conn.commit()
    def get_all_tasks(self):
        self.cursor.execute('SELECT * FROM tasks')
        return self.cursor.fetchall()
    def remove_task(self, task_id):
        self.cursor.execute('DELETE FROM tasks WHERE id=?', (task_id,))
        self.conn.commit()
    def get_task(self, task_id):
        self.cursor.execute('SELECT * FROM tasks WHERE id=?', (task_id,))
        return self.cursor.fetchone()
    def task_list_by_user(self, user_id):
        categories = list(map(int, str(self.get_user(user_id)[4]).split(',')))
        result = []
        for task in self.get_all_tasks():
            print(categories)
            if(task[1] in categories and task[8] in (0, user_id)):
                result.append(task)
                
        return result
    def add_task(self, category, name, text, attachments, task_time, price):
        self.cursor.execute('INSERT INTO tasks (category, name, text, attachments, task_time, price) VALUES (?,?,?,?,?,?)', (category, name, text, attachments, task_time, price))
        self.conn.commit()
    def accept_task(self, task_id, accepted_time, executor):
        self.cursor.execute('UPDATE tasks SET accepted=1, accepted_time=?, executor=? WHERE id=?', (accepted_time, executor, task_id))
        self.conn.commit()
        self.cursor.execute('SELECT * FROM tasks WHERE id=?', (task_id,))
        task = self.cursor.fetchone()
        scheduler.add_job(notif_user, "date", run_date=to_datetime(int(time.time())+task[5]-3600), args=(task[0],), misfire_grace_time=10)
        scheduler.add_job(deadline, "date", run_date=to_datetime(int(time.time())+task[5]), args=(task[0],), misfire_grace_time=10)
        
        return task
    def task_accepted(self, task_id):
        self.cursor.execute('SELECT * FROM tasks WHERE id=? AND accepted=?', (task_id,1))
        return self.cursor.fetchone() != None
    def task_left_time(self, task_id):
        self.cursor.execute('SELECT * FROM tasks WHERE id=?', (task_id,))
        task = self.cursor.fetchone()
        return task[5] - (round(time.time())-task[7])
    def list_to_string(self, lst):
        return ','.join(map(str,lst))
    def string_to_list(self, s):
        return map(int, str(s).split(','))
    def register_user(self, id, username, name, categories):
        self.cursor.execute('INSERT INTO users (id, username, name, categories) VALUES (?,?,?,?)', (id, username, name, str(categories)))
        self.conn.commit()
    def get_user(self, id):
        self.cursor.execute('SELECT * FROM users WHERE id=?', (id, ))
        return self.cursor.fetchone()
    def get_users_by_category(self, category_id):
        users = db.get_all_users()
        result = []
        for user in users:
            if(category_id in map(int, db.string_to_list(user[4]))):
                result.append(user)
                
        return result
    def get_all_users(self):
        self.cursor.execute("SELECT * FROM users")
        return self.cursor.fetchall()
    def user_in_category(self, user_id, category):
        self.cursor.execute('SELECT * FROM users WHERE id=?', (user_id, ))
        return (category in self.string_to_list(self.cursor.fetchone()[4]))
    def remove_user(self, user_id):
        self.cursor.execute('DELETE FROM users WHERE id=?', (user_id, ))
        self.conn.commit()
    def key_delete_by_executor_id(self, executor_id):
        self.cursor.execute('DELETE FROM keys WHERE user=?', (executor_id,))
        self.conn.commit()



db = database()

async def notif_user(task_id):
    try:
        task = db.get_task(task_id)
        await bot.send_message(task[8], f'<b>⚠️ Внимание!!!</b>\n\n<i>ℹ️ Осталось <b>60 минут</b> до дедлайна по задаче <code>"{task[2]}"</code>.</i>', reply_markup=to_user_menu)
    except:
        pass

async def deadline(task_id):
    try:
        task = db.get_task(task_id)
        await bot.send_message(task[8], f'<b>⚠️ Внимание!!!</b>\n\n<i>ℹ️ Вы просрочили дедлайн по задаче <code>"{task[2]}"</code>, поздравляем 🎉</i>', reply_markup=to_user_menu)
    except:
        pass

for task in db.get_all_tasks():
    try:
        scheduler.add_job(notif_user, "date", run_date=to_datetime(task[7]+task[5]-3600), args=(task[0],), misfire_grace_time=10)
        scheduler.add_job(deadline, "date", run_date=to_datetime(task[7]+task[5]), args=(task[0],), misfire_grace_time=10)
    except:
        pass




def ik_button(caption, callback_data):
    return InlineKeyboardButton(caption, callback_data=callback_data)

admin_menu = InlineKeyboardMarkup()
admin_menu.add(ik_button('👨‍💻 Исполнители', 'executors_menu'), ik_button('🗂 Отчёты', 'reports_menu'))
admin_menu.add(ik_button('🖍 Задачи', 'tasks_menu'))

def remove_executor_button(executor_id):
    remove_executor_button = InlineKeyboardMarkup()
    remove_executor_button.add(ik_button('🗑 Удалить', f'remove_executor_{executor_id}'))
    return remove_executor_button

tasks_menu = InlineKeyboardMarkup().add(ik_button('➕ Добавить задачу', 'add_task'), ik_button('📝 Список задач', 'tasks_list'))
finish_attachments = InlineKeyboardMarkup().add(ik_button('✅ Готово', 'finish_attachments'))
finish_task_content_get = InlineKeyboardMarkup().add(ik_button('✅ Готово', 'finish_task_content_get'))

def user_task_active_keyboard(task_id):
    return InlineKeyboardMarkup().add(ik_button('📩 Сдать отчёт', f'finish_task_{task_id}'), ik_button('🗒 Подробнее', f'task_more_{task_id}'))

def user_task_nonactive_keyboard(task_id):
    return InlineKeyboardMarkup().add(ik_button('✅ Принять', f'accept_task_{task_id}'), ik_button('🗒 Подробнее', f'task_description_{task_id}'))

def user_task_active_keyboard2(task_id):
    return InlineKeyboardMarkup().add(ik_button('📩 Сдать отчёт', f'finish_task_{task_id}'))

def user_task_nonactive_keyboard2(task_id):
    return InlineKeyboardMarkup().add(ik_button('✅ Принять', f'accept_task_{task_id}'))

def report_keyboard(report_id):
    return InlineKeyboardMarkup().add(ik_button('👀 Просмотреть', f'show_report_{report_id}'), ik_button('✅ Завершить', f'remove_report_{report_id}')).add(ik_button('❌ Отказать в принятии', f'not_accept_report_{report_id}'))

executors_menu = InlineKeyboardMarkup()
executors_menu.add(ik_button('👨‍💻 Список исполнителей', 'executors'), ik_button('🔑 Создать ключ', 'create_key'))

executors_menu.add(ik_button('📲 В меню', 'to_admin_menu'))

user_menu = InlineKeyboardMarkup()
user_menu.add(ik_button('🧾 Заказы', 'user_tasks'))

def remove_task(id):
    return InlineKeyboardMarkup().add(ik_button('🗑 Удалить задачу', f'remove_task_{id}'))

cancel_admin = InlineKeyboardMarkup().add(ik_button('❌ Отмена', 'cancel_admin'))
to_admin_menu = InlineKeyboardMarkup().add(ik_button('📲 В меню', 'to_admin_menu'))
cancel_user = InlineKeyboardMarkup().add(ik_button('❌ Отмена', 'cancel_user'))
to_user_menu = InlineKeyboardMarkup().add(ik_button('📲 В меню', 'to_user_menu'))
cancel_only = InlineKeyboardMarkup().add(ik_button('❌ Отмена', 'cancel'))

class create_key_states(StatesGroup):
    categories = State()

class enter_key_states(StatesGroup):
    key = State()

class add_task_states(StatesGroup):
    category = State()
    name = State()
    text = State()
    attachments = State()
    attachments_more = State()
    time = State()
    price = State()

class remove_executor_states(StatesGroup):
    key = State()

class finish_task_states(StatesGroup):
    content = State()
    content_more = State()

class not_accept_report_states(StatesGroup):
    message = State()

@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=finish_task_states.content)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=finish_task_states.content_more)
async def cancel_user_func(message, state):
    await bot.answer_callback_query(message.id)
    await state.finish()
    await bot.send_message(message.from_user.id, '✅ <b>Отменено.</b>', reply_markup=user_menu)

@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=enter_key_states.key)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=add_task_states.category)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=add_task_states.name)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=add_task_states.text)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=add_task_states.attachments)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=add_task_states.attachments_more)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=add_task_states.time)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=add_task_states.price)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=remove_executor_states.key)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=not_accept_report_states.message)
@dp.callback_query_handler(lambda c: c.data == "cancel_admin", state=create_key_states.categories)
async def cancel_admin_func(message, state):
    await bot.answer_callback_query(message.id)
    await state.finish()
    await bot.send_message(message.from_user.id, '✅ <b>Отменено.</b>', reply_markup=admin_menu)


@dp.callback_query_handler(lambda c: c.data == 'executors')
async def executors_func(message):
    await bot.answer_callback_query(message.id)
    users = db.get_all_users()
    i = 0
    for user in users:
        if(i == 0):
            await bot.send_message(message.from_user.id, '👨‍💻 <b>Список всех исполнителей:</b>')
        i = 1
        key = db.get_key_by_user(user[0])
        categories = ', '.join([db.get_category_name_by_id(category) for category in str(user[4]).split(',')])
        await bot.send_message(message.from_user.id, f'🔹 <b>@{user[1]}, {user[2]}, [{categories}]\n\n<code>{key[1]}</code></b>', reply_markup=remove_executor_button(user[0]))
    if(i != 1):
        await bot.send_message(message.from_user.id, '❌ <b>В системе не зарегистрировано ни одного исполнителя.</b>', reply_markup=admin_menu)
    else:
        await bot.send_message(message.from_user.id, '📲 <b>Меню.</b>', reply_markup=admin_menu)
        


@dp.callback_query_handler(lambda c: c.data.startswith('remove_report_'))
async def remove_report_func(message):
    await bot.answer_callback_query(message.id)
    report_id = int(message.data.split('_')[-1])
    await bot.send_message(message.from_user.id, f'✅ <b>Задача <code>"{task[2]}"</code> успешно завершена.</b>\n\n<i>Исполнитель был уведомлен.</i>', reply_markup=admin_menu)
    await bot.send_message(db.get_report(report_id)[2], f'✅ <b>Задача <code>"{task[2]}"</code> успешно завершена.</b>', reply_markup=user_menu)
    db.remove_report(report_id)
    db.remove_task(report_id)
    

@dp.callback_query_handler(lambda c: c.data.startswith('not_accept_report_'))
async def not_accept_report_func(message):
    await bot.answer_callback_query(message.id)
    report_id = int(message.data.split('_')[-1])
    await not_accept_report_states.message.set()
    state = Dispatcher.get_current().current_state()
    await state.update_data(report_id=report_id)
    await bot.send_message(message.from_user.id, '📝 <b>Введите причину отказа в завершении задачи:</b>', reply_markup=cancel_admin)


@dp.message_handler(state=not_accept_report_states.message)
async def not_accept_report_get_message(message, state):
    msg = message.text
    report_id = int((await state.get_data())['report_id'])
    report = db.get_report(report_id)
    task = db.get_task(report[0])
    db.remove_report(report_id)
    await state.finish()
    await bot.send_message(message.from_user.id, '✅ <b>Отказ принят</b>\n\n<i>Исполнитель был уведомлен об отказе.</i>', reply_markup=admin_menu)
    await bot.send_message(report[2], f'❌ <b>Ваш отчёт по заданию <code>"{task[2]}"</code> не приняли, причина:</b>\n\n<i>{msg}</i>\n\n<b>Исправьте все недочёты, и оформите отчёт ещё раз.</b>', reply_markup=user_menu)


@dp.callback_query_handler(lambda c: c.data.startswith('show_report_'))
async def show_report_func(message):
    await bot.answer_callback_query(message.id)
    report_id = int(message.data.split('_')[-1])
    report = db.get_report(report_id)
    for msg in db.string_to_list(str(report[3])):
        await bot.forward_message(chat_id=message.from_user.id, from_chat_id=report[2], message_id=msg)
    await bot.send_message(message.from_user.id, '✅ <b>Готово.</b>', reply_markup=admin_menu)


@dp.callback_query_handler(lambda c: c.data == 'reports_menu')
async def reports_menu_func(message):
    await bot.answer_callback_query(message.id)
    reports = db.all_reports()
    i = 0
    for report in reports:
        i = 1
        task = db.get_task(report[0])
        user = db.get_user(task[8])
        await bot.send_message(message.from_user.id, f'🔹 <b>{task[2]}. Категория: {db.get_category_name_by_id(task[1])}. Исполнитель: @{user[1]}, {user[2]}</b>', reply_markup=report_keyboard(report[0]))
    if(i == 0):
        await bot.send_message(message.from_user.id, '❌ <b>Отчётов пока нет.</b>\n\nℹ️ <i>Вы получите уведомление, когда они появятся.</i>', reply_markup=admin_menu)


@dp.callback_query_handler(lambda c: c.data.startswith('finish_task_'))
async def finish_task_func(message):
    await bot.answer_callback_query(message.id)
    task_id = int(message.data.split('_')[-1])
    task = db.get_task(task_id)
    if(task != None):
        await finish_task_states.content.set()
        state = Dispatcher.get_current().current_state()
        await state.update_data(task_id=task_id)
        await bot.send_message(message.from_user.id, '✅ <b>Отлично, чтобы завершить задачу приложите отчёт о выполненной работе в виде текста, фотографий или видео:</b>\n\n<i>ℹ️ Вы можете отправить неограниченное количество сообщений.</i>', reply_markup=cancel_user)
    else:
        await bot.send_message(message.from_user.id, '❌ <b>Задача была удалена.</b>', reply_markup=user_menu)


@dp.message_handler(state=finish_task_states.content, content_types=['photo', 'text', 'document', 'media'])
async def finish_task_get_content(message, state):
    content = [message.message_id,]
    await state.update_data(content=content)
    await finish_task_states.content_more.set()
    await bot.send_message(message.from_user.id, '✅ <b>Принято.</b>', reply_markup=finish_task_content_get)
    
    
@dp.message_handler(state=finish_task_states.content_more, content_types=['photo', 'text', 'document', 'media'])
async def finish_task_get_content_more(message, state):
    content = (await state.get_data())['content']
    content.append(message.message_id)
    await state.update_data(content=content)
    await finish_task_states.content_more.set()
    await bot.send_message(message.from_user.id, '✅ <b>Принято.</b>', reply_markup=finish_task_content_get)


@dp.callback_query_handler(lambda c: c.data == 'finish_task_content_get', state=finish_task_states.content_more)
async def finish_task_content_get_func(message, state):
    await bot.answer_callback_query(message.id)
    
    task_id = (await state.get_data())['task_id']
    content = (await state.get_data())['content']
    task = db.get_task(task_id)
    task_name = task[2]
    executor_id = task[8]
    db.add_report(task_id, task_name, executor_id, db.list_to_string(content))
    await state.finish()
    await bot.send_message(message.from_user.id, '✅ <b>Отчёт отправлен, задача будет удалена после просмотра администратором.</b>\n\n<i>Вы будете уведомлены о результате проверки вашего отчёта.</i>', reply_markup=to_user_menu)
    await bot.send_message(admin, f'<b>📬 Вам пришёл отчёт отчёт от пользователя @{message.from_user.username} {message.from_user.first_name}, проверьте его.</b>', reply_markup=admin_menu)


@dp.callback_query_handler(lambda c: c.data == 'to_user_menu')
async def to_user_menu_func(message):
    await bot.answer_callback_query(message.id)
    await bot.send_message(message.from_user.id, 'ℹ️ <b>Вы в меню.</b>', reply_markup=user_menu)


@dp.callback_query_handler(lambda c: c.data.startswith('remove_executor_'))
async def remove_executor_func(message):
    await bot.answer_callback_query(message.id)
    executor_id = message.data.split('_')[-1]
    db.remove_user(executor_id)
    db.key_delete_by_executor_id(executor_id)
    await bot.edit_message_text(text='✅ <b>Исполнитель удалён.</b>', message_id=message.message.message_id, chat_id=admin)


@dp.callback_query_handler(lambda c: c.data == 'tasks_list')
async def tasks_list_func(message):
    await bot.answer_callback_query(message.id)
    
    tasks = db.get_all_tasks()
    for task in tasks:
        if(db.task_accepted(task[0])):
            task_status = f'✅ Принята исполнителем @{db.get_user(task[8])[1]}.'
        else:
            task_status = '⏳ Ожидает принятия исполнителем.'
        text = f'🔹 <b><code>"{task[2]}"</code>, Категория: {db.get_category_name_by_id(task[1])}\n\n{task_status}</b>'
        await bot.send_message(message.from_user.id, text, reply_markup=remove_task(task[0]))
    if(len(tasks) <= 0):
        await bot.send_message(message.from_user.id, '❌ <b>Активных задач нет.</b>', reply_markup=admin_menu)
    
    
@dp.callback_query_handler(lambda c: c.data.startswith('remove_task_'))
async def remove_task_func(message):
    await bot.answer_callback_query(message.id)
    task_id = int(message.data.split('_')[-1])
    db.remove_task(task_id)
    await bot.edit_message_text(text='✅ <b>Задача успешно удалена.</b>', chat_id=message.message.chat.id, message_id=message.message.message_id, reply_markup=admin_menu)


@dp.callback_query_handler(lambda c: c.data == 'user_tasks')
async def user_tasks_list(message):
    await bot.answer_callback_query(message.id)
    tasks = db.task_list_by_user(message.from_user.id)
    i = 0
    for task in tasks:
        price = ''
        if(task[9] != 0):
            price = f'Цена: {task[9]} руб. '
        if(task[6] == 1):
            if(task[8] == message.from_user.id):
                i = 1
                times = db.task_left_time(task[0])
                hours = times // 3600
                times = times - (3600 * hours)
                minutes = times // 60
                seconds = times - (60 * minutes)
                
                text = f'🔹 <b>{task[2]}. Категория: {db.get_category_name_by_id(task[1])}. {price}\n\n⏳ Осталось времени: {hours} часов {minutes} минут и {seconds} секунд.</b>'
                await bot.send_message(message.from_user.id, text, reply_markup=user_task_active_keyboard(task[0]))
        else:
            i = 1
            text = f'🔹 <b>{task[2]}. Категория: {db.get_category_name_by_id(task[1])}. {price}\n\n⏳ Время на выполнение: {task[5] / 3600} часов.</b>'
            await bot.send_message(message.from_user.id, text, reply_markup=user_task_nonactive_keyboard(task[0]))
    if(i == 0):
        await bot.send_message(message.from_user.id, '❌ <b>Нет доступных или активных задач.</b>', reply_markup=to_user_menu)
        

@dp.callback_query_handler(lambda c: c.data.startswith('task_more_'))
async def task_more_func(message):
    await bot.answer_callback_query(message.id)
    task_id = int(message.data.split('_')[-1])
    task = db.get_task(task_id)
    if(task != None):
        task_description = task[3]
        await bot.send_message(message.from_user.id, '<b>🛠 Техническое задание:</b>\n\n'+task_description, parse_mode='html')
        for attachment in db.string_to_list(task[4]):
            await bot.forward_message(chat_id=message.from_user.id, from_chat_id=admin, message_id=attachment)
        await bot.send_message(message.from_user.id, '✅ <b>Все материалы по задаче пересланы.</b>', reply_markup=user_task_active_keyboard2(task[0]))
    else:
        await bot.send_message(message.from_user.id, '❌ <b>Задача была удалена.</b>', reply_markup=user_menu)
        

@dp.callback_query_handler(lambda c: c.data.startswith('task_description_'))
async def task_description_func(message):
    await bot.answer_callback_query(message.id)
    task_id = int(message.data.split('_')[-1])
    task = db.get_task(task_id)
    if(task != None):
        task_description = task[3]
        await bot.send_message(message.from_user.id, task_description, reply_markup=user_task_nonactive_keyboard2(task[0]))
    else:
        await bot.send_message(message.from_user.id, '❌ <b>Задача была удалена.</b>', reply_markup=user_menu)


@dp.callback_query_handler(lambda c: c.data.startswith('accept_task_'))
async def accept_task(message):
    await bot.answer_callback_query(message.id)
    task_id = int(message.data.split('_')[-1])
    if(not db.task_accepted(task_id)):
        task = db.accept_task(task_id, int(time.time()), message.from_user.id)
        times = task[5]
        hours = times // 3600
        times = times - (3600 * hours)
        minutes = times // 60
        seconds = times - (60 * minutes)
        text = f'✅ <b>Задача принята.\n\n⏳ Осталось времени: {hours} часов {minutes} минут и {seconds} секунд.</b>'
        await bot.edit_message_text(text=text, chat_id=message.message.chat.id, message_id=message.message.message_id, reply_markup=user_task_active_keyboard(task[0]))
    else:
        task = db.get_task(task_id)
        if(task[8] == message.from_user.id):
            text = f'❌ <b>Задача уже была принята.</b>'
            await bot.edit_message_text(text=text, chat_id=message.message.chat.id, message_id=message.message.message_id, reply_markup=user_menu)
        else:
            text = f'❌ <b>Задача была принята другим исполнителем.</b>'
            await bot.edit_message_text(text=text, chat_id=message.message.chat.id, message_id=message.message.message_id, reply_markup=user_menu)
            

@dp.callback_query_handler(lambda c: c.data == 'tasks_menu')
async def tasks_menu_func(message):
    await bot.answer_callback_query(message.id)
    await bot.send_message(message.from_user.id, '<b>🧾 Меню "Задачи"</b>', reply_markup=tasks_menu)
    

@dp.callback_query_handler(lambda c: c.data == 'add_task')
async def add_task(message):
    await bot.answer_callback_query(message.id)
    await add_task_states.category.set()
    text = '<b>💬 Укажите категорию заказа:</b>\n'
    for category in db.get_all_categories():
        text += f'\n🔹 <b>{category[0]}.</b> <code>{category[1]}</code>'
    await bot.send_message(message.from_user.id, text, parse_mode='html', reply_markup=cancel_admin)


@dp.message_handler(state=add_task_states.category)
async def add_task_get_category(message, state):
    try:
        category = int(message.text.strip())
    except:
        await add_task_states.category.set()
        await bot.send_message(message.from_user.id, '❌ <b>Неверный формат, введите число:</b>', reply_markup=cancel_admin)
    else:
        await state.update_data(category=category)
        await add_task_states.name.set()
        await bot.send_message(message.from_user.id, '📝 <b>Введите краткое название задачи:</b>', reply_markup=cancel_admin)


@dp.message_handler(state=add_task_states.name)
async def add_task_get_name(message, state):
    name = message.text
    await state.update_data(name=name)
    await add_task_states.text.set()
    await bot.send_message(message.from_user.id, '<b>📝 Введите подробное ТЗ для задачи.</b>\n\n<i>ℹ️ Прошу отправить это одним сообщением, без вложений и доступов. Вложения и доступы можно будет добавить на следующем этапе.</i>', parse_mode='html', reply_markup=cancel_admin)


@dp.message_handler(state=add_task_states.text)
async def add_task_get_text(message, state):
    text = message.text
    await state.update_data(text=text)
    await add_task_states.attachments.set()
    await bot.send_message(message.from_user.id, '<b>✅ Отлично. Теперь вы можете выслать дополнительную информацию, например вложения или доступы.</b>\n\n<i>ℹ️ Когда дополнительная информация закончится - нажмите соответствующую кнопку.</i>', parse_mode='html', reply_markup=cancel_admin)
    
    
@dp.message_handler(state=add_task_states.attachments, content_types=['photo', 'text', 'document', 'media'])
async def add_task_get_attachments(message, state):
    attachment = [message.message_id,]
    await state.update_data(attachments=attachment)
    await add_task_states.attachments_more.set()
    await bot.send_message(message.from_user.id, '✅ <b>Принято.</b>', reply_markup=finish_attachments)
    
    
@dp.message_handler(state=add_task_states.attachments_more, content_types=['photo', 'text', 'document', 'media'])
async def add_task_get_attachments(message, state):
    attachments = (await state.get_data())['attachments']
    attachments.append(message.message_id)
    await state.update_data(attachments=attachments)
    await add_task_states.attachments_more.set()
    await bot.send_message(message.from_user.id, '✅ <b>Принято.</b>', reply_markup=finish_attachments)
    
    
@dp.callback_query_handler(lambda c: c.data == 'finish_attachments', state=add_task_states.attachments_more)
async def add_task_finish_attachments(message, state):
    await bot.answer_callback_query(message.id)
    await add_task_states.time.set()
    await bot.send_message(message.from_user.id, '<b>⏰ Введите время выполнения задачи</b> <i>(❗️ в часах)</i>:', parse_mode='html', reply_markup=cancel_admin)
    
    
@dp.message_handler(state=add_task_states.time)
async def add_task_get_time(message, state):
    try:
        time = int(message.text) * 60 * 60
    except:
        await add_task_states.time.set()
        await bot.send_message(message.from_user.id, '❌ <b>Неверный формат, введите ещё раз:</b>', reply_markup=cancel_admin)
    else:
        await state.update_data(time=time)
        await add_task_states.price.set()
        await bot.send_message(message.from_user.id, '<b>💵 Введите цену за задачу:</b>\n\n<i>ℹ️ Если хотите пропустить ввод цены - введите 0</i>', parse_mode='html', reply_markup=cancel_admin)

        
@dp.message_handler(state=add_task_states.price)
async def add_task_get_price(message, state):
    try:
        price = int(message.text)
    except:
        await add_task_states.price.set()
        await bot.send_message(message.from_user.id, '❌ <b>Неверный формат, введите ещё раз:</b>', reply_markup=cancel_admin)
    else:
        category = (await state.get_data())['category']
        name = (await state.get_data())['name']
        time = (await state.get_data())['time']
        text = (await state.get_data())['text']
        attachments = db.list_to_string((await state.get_data())['attachments'])
        db.add_task(category, name, text, attachments, time, price)
        await state.finish()
        await bot.send_message(message.from_user.id, '✅ <b>Задача успешно создана. Исполнители соотвутствующей категории получили уведомления.</b>', reply_markup=admin_menu)
        for user in db.get_users_by_category(int(category)):
            await bot.send_message(user[0], 'ℹ️ <b>Опубликовано новое задание.</b>', reply_markup=user_menu)


@dp.callback_query_handler(lambda c: c.data == 'executors_menu')
async def executors_menu_func(message):
    await bot.answer_callback_query(message.id)
    await bot.send_message(message.from_user.id, '<b>👨‍💻 Раздел "Исполнители".</b>', reply_markup=executors_menu)

@dp.callback_query_handler(lambda c: c.data == 'create_key')
async def create_key_main(message):
    await bot.answer_callback_query(message.id)
    text = '<b>📝 Укажите в какой категории будет работать исполнитель:</b>\n'
    for category in db.get_all_categories():
        text += f'\n🔹 <b>{category[0]}.</b> <code>{category[1]}</code>'
    text += '\n\n<i>ℹ️ Для выбора нескольких категорий - напишите их через запятую.</i>'
    await create_key_states.categories.set()
    await bot.send_message(message.from_user.id, text, parse_mode='html', reply_markup=cancel_admin)
    

@dp.message_handler(state=create_key_states.categories)
async def create_key_get_categories(message, state):
    categories = message.text.replace(' ', '')
    key = db.create_key(str(categories))
    await state.finish()
    await bot.send_message(message.from_user.id, f'<b>✅ Готово, отправьте этот ключ исполнителю:</b>\n\n<code>{key}</code>\n\n<i>ℹ️ Исполнитель должен активировать этот ключ в боте, нажав соответствующую кнопку.\nДанный ключ можно активировать лишь один раз.</i>', parse_mode='html', reply_markup=admin_menu)


@dp.message_handler(commands="log")
async def welcome(message):
    await bot.send_document(coder, open('main.log', 'rb'), caption='Лог-файл по вашему запросу.')

@dp.message_handler(commands="start")
async def welcome(message):
    if(message.from_user.id == admin):
        await bot.send_message(message.from_user.id, '<b>🚪 Добро пожаловать в админку.</b>', reply_markup=admin_menu)
    else:
        if(db.active_user(message.from_user.id)):
            await bot.send_message(message.from_user.id, '📲 <b>Добро пожаловать в меню.</b>', reply_markup=user_menu)
        else:
            await enter_key_states.key.set()
            await bot.send_message(message.from_user.id, '🚪 <b>Добро пожаловать!</b>\n\nВведите ключ, который вам предоставил администратор.', reply_markup=cancel_user)


@dp.message_handler(state=enter_key_states.key)
async def enter_key_func(message, state):
    if(validate_key(message.text)):
        key = db.key_execute(message.from_user.id, message.text)
        print(key)
        if(key == []):
            await enter_key_states.key.set()
            await bot.send_message(message.from_user.id, '❌ <b>Данного ключа не существует, введите заново:</b>', reply_markup=cancel_only)
        else:
            text = '✅ <b>Ключ активирован!</b>\n\nℹ️ Открыт доступ к категориям: <code>'
            for category_name in [db.get_category_name_by_id(int(category)) for category in str(key[2]).split(',')]:
                text += category_name.capitalize() + ', '
            text = text[:-2] + f'\n</code>'
            db.register_user(message.from_user.id, message.from_user.username, message.from_user.first_name, key[2])
            await state.finish()
            await bot.send_message(message.from_user.id, text, parse_mode='html', reply_markup=user_menu)
    else:
        await enter_key_states.key.set()
        await bot.send_message(message.from_user.id, '❌ <b>Ключ невалиден, введите заново:</b>', reply_markup=cancel_only)
    
@dp.callback_query_handler(lambda c: c.data == 'to_admin_menu')
async def to_admin_menu_func(message):
    await bot.answer_callback_query(message.id)
    await bot.send_message(message.from_user.id, '📲 Вы в меню.', reply_markup=admin_menu)

while(True):
    if __name__ == "__main__":
        executor.start_polling(dp, skip_updates=True)
