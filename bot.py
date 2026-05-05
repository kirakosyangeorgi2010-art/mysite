import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ========== НАСТРОЙКИ - ЗАМЕНИТЕ НА ВАШИ ДАННЫЕ ==========
BOT_TOKEN = '8609830135:AAE__L_gE9j3jSy1WZvrBvtdgRcna6y1gnY'
ADMIN_ID = 5260847958  # ЗАМЕНИТЕ НА ВАШ TELEGRAM ID (узнайте у @userinfobot)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== ХРАНИЛИЩЕ ДАННЫХ (в памяти) ==========
data = {
    'proposals': [],
    'support_tickets': [],
    'next_id': 1
}

# ========== СОСТОЯНИЯ ==========
class ProposalState(StatesGroup):
    waiting_for_proposal = State()

class SupportState(StatesGroup):
    waiting_for_message = State()
    waiting_for_reply = State()

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    buttons = [
        [KeyboardButton(text="📝 Отправить предложение")],
        [KeyboardButton(text="🆘 Поддержка")],
        [KeyboardButton(text="ℹ️ О боте")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_proposal_keyboard(proposal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{proposal_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{proposal_id}")
        ],
        [InlineKeyboardButton(text="💬 Ответить с комментарием", callback_data=f"comment_{proposal_id}")]
    ])

def get_support_keyboard(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ответить", callback_data=f"reply_{ticket_id}")],
        [InlineKeyboardButton(text="❌ Закрыть обращение", callback_data=f"close_{ticket_id}")]
    ])

def get_admin_keyboard():
    buttons = [
        [KeyboardButton(text="📋 Список предложений"), KeyboardButton(text="🎫 Активные обращения")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Заблокированные")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ========== ОБРАБОТЧИКИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user = message.from_user
    
    # Проверка на блокировку
    if 'blocked' in data and user.id in data['blocked']:
        await message.answer("❌ Вы заблокированы.")
        return
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я бот для приёма предложений и обращений в поддержку.\n\n"
        f"📝 **Отправить предложение** — ваше сообщение уйдёт на модерацию\n"
        f"🆘 **Поддержка** — связь с администратором\n\n"
        f"⏱ Обычно ответ приходит в течение 24 часов.\n\n"
        f"🎮 Наш сайт с играми: https://pyplay.kesug.com"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.message(lambda message: message.text == "📝 Отправить предложение")
async def send_proposal(message: types.Message, state: FSMContext):
    user = message.from_user
    
    if 'blocked' in data and user.id in data['blocked']:
        await message.answer("❌ Вы заблокированы.")
        return
    
    await message.answer("✍️ Напишите ваше предложение или идею:")
    await state.set_state(ProposalState.waiting_for_proposal)

@dp.message(ProposalState.waiting_for_proposal)
async def receive_proposal(message: types.Message, state: FSMContext):
    user = message.from_user
    proposal_text = message.text
    
    proposal_id = data['next_id']
    data['next_id'] += 1
    
    new_proposal = {
        'id': proposal_id,
        'user_id': user.id,
        'username': user.username or user.first_name,
        'text': proposal_text,
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    
    data['proposals'].append(new_proposal)
    
    # Подтверждение пользователю
    await message.answer(
        f"✅ Ваше предложение №{proposal_id} отправлено на модерацию!\n\n"
        f"📋 Текст: {proposal_text[:200]}\n\n"
        f"Ответ придёт в течение 24 часов."
    )
    
    # Уведомление админу
    admin_text = (
        f"📨 **Новое предложение**\n\n"
        f"ID: #{proposal_id}\n"
        f"👤 Пользователь: @{user.username or user.first_name}\n"
        f"🆔 ID: `{user.id}`\n"
        f"💬 Текст:\n{proposal_text}"
    )
    
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=get_proposal_keyboard(proposal_id))
    await state.clear()

@dp.message(lambda message: message.text == "🆘 Поддержка")
async def support_request(message: types.Message, state: FSMContext):
    user = message.from_user
    
    if 'blocked' in data and user.id in data['blocked']:
        await message.answer("❌ Вы заблокированы.")
        return
    
    await message.answer("💬 Напишите ваше обращение в поддержку:")
    await state.set_state(SupportState.waiting_for_message)

@dp.message(SupportState.waiting_for_message)
async def receive_support_message(message: types.Message, state: FSMContext):
    user = message.from_user
    msg_text = message.text
    
    ticket_id = data['next_id']
    data['next_id'] += 1
    
    new_ticket = {
        'id': ticket_id,
        'user_id': user.id,
        'username': user.username or user.first_name,
        'message': msg_text,
        'status': 'open',
        'created_at': datetime.now().isoformat()
    }
    
    data['support_tickets'].append(new_ticket)
    
    await message.answer(
        f"✅ Ваше обращение №{ticket_id} отправлено!\n\n"
        f"Ответ придёт в течение 24 часов."
    )
    
    # Уведомление админу
    admin_text = (
        f"🎫 **Новое обращение в поддержку**\n\n"
        f"№{ticket_id}\n"
        f"👤 Пользователь: @{user.username or user.first_name}\n"
        f"🆔 ID: `{user.id}`\n"
        f"💬 Сообщение:\n{msg_text}"
    )
    
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=get_support_keyboard(ticket_id))
    await state.clear()

@dp.message(lambda message: message.text == "ℹ️ О боте")
async def about_bot(message: types.Message):
    await message.answer(
        "🤖 **О боте**\n\n"
        "Этот бот создан для приёма предложений и обращений в поддержку.\n\n"
        "📝 **Предложения** — проходят модерацию\n"
        "🆘 **Поддержка** — прямая связь с администратором\n\n"
        "🎮 **Сайт с играми:** https://pyplay.kesug.com\n\n"
        "👨‍💻 Администратор ответит в течение 24 часов.",
        parse_mode="Markdown"
    )

# ========== ОБРАБОТЧИКИ ДЛЯ АДМИНА ==========
@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text == "📋 Список предложений")
async def admin_list_proposals(message: types.Message):
    pending = [p for p in data['proposals'] if p['status'] == 'pending']
    
    if not pending:
        await message.answer("✅ Нет новых предложений на модерацию.")
        return
    
    for prop in pending[:10]:
        text = (
            f"📝 **Предложение #{prop['id']}**\n"
            f"👤 От: @{prop['username']}\n"
            f"🆔 ID: `{prop['user_id']}`\n"
            f"💬 {prop['text'][:300]}\n"
            f"📅 {prop['created_at'][:19]}"
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=get_proposal_keyboard(prop['id']))

@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text == "🎫 Активные обращения")
async def admin_list_tickets(message: types.Message):
    open_tickets = [t for t in data['support_tickets'] if t['status'] == 'open']
    
    if not open_tickets:
        await message.answer("✅ Нет активных обращений.")
        return
    
    for ticket in open_tickets[:10]:
        text = (
            f"🎫 **Обращение #{ticket['id']}**\n"
            f"👤 От: @{ticket['username']}\n"
            f"🆔 ID: `{ticket['user_id']}`\n"
            f"💬 {ticket['message'][:300]}\n"
            f"📅 {ticket['created_at'][:19]}"
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=get_support_keyboard(ticket['id']))

@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    total_proposals = len(data['proposals'])
    pending = len([p for p in data['proposals'] if p['status'] == 'pending'])
    approved = len([p for p in data['proposals'] if p['status'] == 'approved'])
    rejected = len([p for p in data['proposals'] if p['status'] == 'rejected'])
    
    open_tickets = len([t for t in data['support_tickets'] if t['status'] == 'open'])
    total_tickets = len(data['support_tickets'])
    
    stats_text = (
        f"📊 **Статистика**\n\n"
        f"📝 **Предложения:**\n"
        f"└ Всего: {total_proposals}\n"
        f"└ Ожидают: {pending}\n"
        f"└ Одобрено: {approved}\n"
        f"└ Отклонено: {rejected}\n\n"
        f"🎫 **Поддержка:**\n"
        f"└ Всего: {total_tickets}\n"
        f"└ Активных: {open_tickets}"
    )
    await message.answer(stats_text, parse_mode="Markdown")

@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text == "👥 Заблокированные")
async def admin_blocked(message: types.Message):
    blocked = data.get('blocked', [])
    if not blocked:
        await message.answer("📭 Нет заблокированных пользователей.")
        return
    
    text = "🚫 **Заблокированные пользователи:**\n\n"
    for uid in blocked:
        text += f"└ 🆔 `{uid}`\n"
    await message.answer(text, parse_mode="Markdown")
    
    await message.answer(
        "Чтобы разблокировать: напишите /unblock ID\n"
        "Чтобы заблокировать: напишите /block ID"
    )

# ========== КОМАНДЫ АДМИНА ==========
@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text and message.text.startswith("/block"))
async def block_user(message: types.Message):
    try:
        user_id = int(message.text.split()[1])
        if 'blocked' not in data:
            data['blocked'] = []
        if user_id not in data['blocked']:
            data['blocked'].append(user_id)
            await message.answer(f"✅ Пользователь {user_id} заблокирован.")
        else:
            await message.answer(f"⚠️ Пользователь {user_id} уже в черном списке.")
    except:
        await message.answer("❌ Использование: /block 123456789")

@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text and message.text.startswith("/unblock"))
async def unblock_user(message: types.Message):
    try:
        user_id = int(message.text.split()[1])
        if 'blocked' in data and user_id in data['blocked']:
            data['blocked'].remove(user_id)
            await message.answer(f"✅ Пользователь {user_id} разблокирован.")
        else:
            await message.answer(f"⚠️ Пользователь {user_id} не в черном списке.")
    except:
        await message.answer("❌ Использование: /unblock 123456789")

# ========== CALLBACK ДЛЯ ПРЕДЛОЖЕНИЙ ==========
@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_proposal(callback: types.CallbackQuery):
    proposal_id = int(callback.data.split("_")[1])
    
    for prop in data['proposals']:
        if prop['id'] == proposal_id:
            prop['status'] = 'approved'
            await callback.message.edit_text(f"✅ **Одобрено!**\nПредложение #{proposal_id} принято.")
            await bot.send_message(
                prop['user_id'],
                f"✅ **Ваше предложение #{proposal_id} одобрено!**\n\nСпасибо за ваш вклад!\nСайт с играми: https://pyplay.kesug.com"
            )
            break
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_proposal(callback: types.CallbackQuery):
    proposal_id = int(callback.data.split("_")[1])
    
    for prop in data['proposals']:
        if prop['id'] == proposal_id:
            prop['status'] = 'rejected'
            await callback.message.edit_text(f"❌ **Отклонено**\nПредложение #{proposal_id} отклонено.")
            await bot.send_message(
                prop['user_id'],
                f"❌ **Ваше предложение #{proposal_id} отклонено.**\n\nСпасибо за обращение!"
            )
            break
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("comment_"))
async def comment_proposal(callback: types.CallbackQuery, state: FSMContext):
    proposal_id = int(callback.data.split("_")[1])
    await state.update_data({'proposal_id': proposal_id, 'action': 'comment'})
    await callback.message.answer("✍️ Напишите комментарий (он будет отправлен пользователю):")
    await state.set_state("waiting_for_comment")
    await callback.answer()

# ========== CALLBACK ДЛЯ ОБРАЩЕНИЙ ==========
@dp.callback_query(lambda c: c.data.startswith("reply_"))
async def reply_ticket(callback: types.CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.split("_")[1])
    await state.update_data({'ticket_id': ticket_id, 'action': 'reply'})
    await callback.message.answer("✍️ Напишите ответ пользователю:")
    await state.set_state("waiting_for_ticket_reply")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("close_"))
async def close_ticket(callback: types.CallbackQuery):
    ticket_id = int(callback.data.split("_")[1])
    
    for ticket in data['support_tickets']:
        if ticket['id'] == ticket_id and ticket['status'] == 'open':
            ticket['status'] = 'closed'
            await callback.message.edit_text(f"❌ Обращение #{ticket_id} закрыто.")
            await bot.send_message(
                ticket['user_id'],
                f"❌ **Ваше обращение #{ticket_id} закрыто администратором.**\n\nСпасибо за обращение!"
            )
            break
    
    await callback.answer()

# ========== ОБРАБОТКА ОТВЕТОВ АДМИНА ==========
@dp.message(StateFilter("waiting_for_comment"))
async def process_comment(message: types.Message, state: FSMContext):
    data_tmp = await state.get_data()
    proposal_id = data_tmp.get('proposal_id')
    comment = message.text
    
    for prop in data['proposals']:
        if prop['id'] == proposal_id:
            await bot.send_message(
                prop['user_id'],
                f"📝 **Комментарий администратора к предложению #{proposal_id}:**\n\n{comment}"
            )
            await message.answer(f"✅ Комментарий отправлен пользователю.")
            break
    
    await state.clear()

@dp.message(StateFilter("waiting_for_ticket_reply"))
async def process_ticket_reply(message: types.Message, state: FSMContext):
    data_tmp = await state.get_data()
    ticket_id = data_tmp.get('ticket_id')
    reply = message.text
    
    for ticket in data['support_tickets']:
        if ticket['id'] == ticket_id and ticket['status'] == 'open':
            ticket['admin_reply'] = reply
            ticket['status'] = 'closed'
            await bot.send_message(
                ticket['user_id'],
                f"✅ **Ответ на ваше обращение #{ticket_id}:**\n\n{reply}\n\nОбращение закрыто. Если остались вопросы, создайте новое."
            )
            await message.answer(f"✅ Ответ отправлен пользователю. Обращение #{ticket_id} закрыто.")
            break
    
    await state.clear()

# ========== ЗАПУСК ==========
async def main():
    print("🤖 Бот запущен и работает!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
