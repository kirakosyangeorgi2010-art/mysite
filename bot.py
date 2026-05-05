import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = '8609830135:AAE__L_gE9j3jSy1WZvrBvtdgRcna6y1gnY'
ADMIN_ID = 5260847958  # ЗАМЕНИТЕ НА ВАШ TELEGRAM ID (узнайте у @userinfobot)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ========== ДАННЫЕ ==========
data = {'proposals': [], 'support_tickets': [], 'next_id': 1}

# ========== СОСТОЯНИЯ ==========
class ProposalState(StatesGroup):
    waiting_for_proposal = State()

class SupportState(StatesGroup):
    waiting_for_message = State()
    waiting_for_reply = State()

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    buttons = [
        [KeyboardButton("📝 Отправить предложение")],
        [KeyboardButton("🆘 Поддержка")],
        [KeyboardButton("ℹ️ О боте")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_proposal_keyboard(proposal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ Принять", callback_data=f"approve_{proposal_id}"),
         InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{proposal_id}")]
    ])

def get_support_keyboard(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ Ответить", callback_data=f"reply_{ticket_id}"),
         InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{ticket_id}")]
    ])

# ========== ОБРАБОТЧИКИ ==========
@dp.message_handler(Command('start'))
async def start_command(message: types.Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"📝 Отправить предложение\n"
        f"🆘 Поддержка\n\n"
        f"Сайт с играми: https://pyplay.kesug.com",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(lambda m: m.text == "📝 Отправить предложение")
async def ask_proposal(message: types.Message):
    await message.answer("✍️ Напишите ваше предложение:")
    await ProposalState.waiting_for_proposal.set()

@dp.message_handler(state=ProposalState.waiting_for_proposal)
async def receive_proposal(message: types.Message, state: FSMContext):
    pid = data['next_id']
    data['next_id'] += 1
    data['proposals'].append({
        'id': pid,
        'user_id': message.from_user.id,
        'text': message.text,
        'status': 'pending'
    })
    await message.answer(f"✅ Предложение #{pid} отправлено на модерацию!")
    await bot.send_message(
        ADMIN_ID,
        f"📨 Новое предложение #{pid}\n👤 {message.from_user.first_name}\n💬 {message.text}",
        reply_markup=get_proposal_keyboard(pid)
    )
    await state.finish()

@dp.message_handler(lambda m: m.text == "🆘 Поддержка")
async def ask_support(message: types.Message):
    await message.answer("💬 Напишите ваше обращение:")
    await SupportState.waiting_for_message.set()

@dp.message_handler(state=SupportState.waiting_for_message)
async def receive_support(message: types.Message, state: FSMContext):
    tid = data['next_id']
    data['next_id'] += 1
    data['support_tickets'].append({
        'id': tid,
        'user_id': message.from_user.id,
        'message': message.text,
        'status': 'open'
    })
    await message.answer(f"✅ Обращение #{tid} отправлено!")
    await bot.send_message(
        ADMIN_ID,
        f"🎫 Новое обращение #{tid}\n👤 {message.from_user.first_name}\n💬 {message.text}",
        reply_markup=get_support_keyboard(tid)
    )
    await state.finish()

@dp.message_handler(lambda m: m.text == "ℹ️ О боте")
async def about(message: types.Message):
    await message.answer("🤖 Бот предложений и поддержки\nСайт: https://pyplay.kesug.com")

@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[1])
    await callback.message.edit_text(f"✅ Предложение #{pid} одобрено")
    for p in data['proposals']:
        if p['id'] == pid:
            await bot.send_message(p['user_id'], f"✅ Ваше предложение #{pid} одобрено!")
            break
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[1])
    await callback.message.edit_text(f"❌ Предложение #{pid} отклонено")
    for p in data['proposals']:
        if p['id'] == pid:
            await bot.send_message(p['user_id'], f"❌ Предложение #{pid} отклонено")
            break
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("reply_"))
async def ask_reply(callback: types.CallbackQuery, state: FSMContext):
    tid = int(callback.data.split("_")[1])
    await state.update_data(ticket_id=tid)
    await callback.message.answer("✍️ Напишите ответ пользователю:")
    await SupportState.waiting_for_reply.set()
    await callback.answer()

@dp.message_handler(state=SupportState.waiting_for_reply)
async def send_reply(message: types.Message, state: FSMContext):
    data_tmp = await state.get_data()
    tid = data_tmp.get('ticket_id')
    for t in data['support_tickets']:
        if t['id'] == tid:
            await bot.send_message(t['user_id'], f"✅ Ответ на обращение #{tid}:\n{message.text}")
            await message.answer("✅ Ответ отправлен!")
            break
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith("close_"))
async def close(callback: types.CallbackQuery):
    tid = int(callback.data.split("_")[1])
    await callback.message.edit_text(f"❌ Обращение #{tid} закрыто")
    for t in data['support_tickets']:
        if t['id'] == tid:
            await bot.send_message(t['user_id'], f"❌ Обращение #{tid} закрыто администратором")
            break
    await callback.answer()

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
