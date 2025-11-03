from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    CallbackQuery,
)
import logging
import asyncio
import json
import os
from datetime import datetime

TOKEN = "8231149964:AAF8-9uV4M2yngZcMyxk9UPK05PsHRCZt64"

dp = Dispatcher()
DATA_FILE = "data.json"
user_data = {}




def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)




@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    await message.answer("👋 Salom! Iltimos, ismingizni kiriting:")
    user_data[user_id] = {"step": "name"}




@dp.message(Command("menu"))
async def menu_handler(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Yangi topshiriq qo‘shish")],
            [KeyboardButton(text="📋 Bugungi topshiriqlar")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Kerakli amalni tanlang:", reply_markup=keyboard)



@dp.message()
async def handle_messages(message: Message):
    user_id = message.from_user.id
    user_key = str(user_id)
    data = load_data()


    if user_id not in user_data and user_key not in data:
        await message.answer("Iltimos, /start buyrug‘ini yuboring.")
        return


    if user_id in user_data and user_data[user_id].get("step") == "name":
        name = message.text.strip()
        user_data[user_id]["name"] = name
        user_data[user_id]["step"] = "age"
        await message.answer("Yaxshi! Endi yoshingizni kiriting:")
        return


    if user_id in user_data and user_data[user_id].get("step") == "age":
        if not message.text.isdigit():
            await message.answer("Iltimos, yoshni raqam bilan kiriting.")
            return
        age = int(message.text)
        name = user_data[user_id]["name"]
        data[user_key] = {"name": name, "age": age, "todos": []}
        save_data(data)
        await message.answer(
            f"✅ Rahmat, {name}! Sizning yoshingiz {age} deb saqlandi.\n"
            "Endi /menu orqali topshiriqlaringizni boshqaring."
        )
        del user_data[user_id]
        return


    if message.text == "📝 Yangi topshiriq qo‘shish":
        user_data[user_id] = {"step": "new_task"}
        await message.answer("🆕 Yangi topshiriq matnini kiriting:")
        return


    if user_id in user_data and user_data[user_id].get("step") == "new_task":
        task_text = message.text.strip()
        if not task_text:
            await message.answer("Topshiriq matnini kiriting.")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        data.setdefault(user_key, {}).setdefault("todos", []).append(
            {"task": task_text, "done": False, "date": today}
        )
        save_data(data)

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Bugungi topshiriqlar", callback_data="view_tasks")]
            ]
        )

        await message.answer(f"✅ Topshiriq qo‘shildi: {task_text}", reply_markup=markup)
        del user_data[user_id]
        return


    if message.text == "📋 Bugungi topshiriqlar":
        await send_todo_list(message, user_key)
        return

    await message.answer("Men sizni tushunmadim. /menu ni bosing.")



@dp.callback_query(F.data == "view_tasks")
async def view_tasks_callback(callback: CallbackQuery):
    user_key = str(callback.from_user.id)
    await send_todo_list(callback.message, user_key)
    await callback.answer()


@dp.callback_query(F.data.startswith("done_"))
async def mark_done_callback(callback: CallbackQuery):
    user_key = str(callback.from_user.id)
    data = load_data()
    idx = int(callback.data.split("_")[1])

    todos = data.get(user_key, {}).get("todos", [])
    if idx < 0 or idx >= len(todos):
        await callback.answer("Noto‘g‘ri tanlov.")
        return

    todos[idx]["done"] = True
    save_data(data)
    await callback.answer("✅ Topshiriq bajarildi!")
    await send_todo_list(callback.message, user_key, edit=True)


async def send_todo_list(message: Message, user_key: str, edit=False):
    data = load_data()
    todos = data.get(user_key, {}).get("todos", [])
    today = datetime.now().strftime("%Y-%m-%d")

    today_tasks = [t for t in todos if t["date"] == today]

    if not today_tasks:
        text = "📭 Bugungi kun uchun hech qanday topshiriq yo‘q."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    text = "📋 *Bugungi topshiriqlar:*\n\n"
    buttons = []

    for i, t in enumerate(today_tasks):
        status = "✅" if t["done"] else "🕓"
        text += f"{i+1}. {status} {t['task']}\n"
        if not t["done"]:
            buttons.append([
                InlineKeyboardButton(text=f"✅ {t['task']}", callback_data=f"done_{i}")
            ])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.answer(text, parse_mode="Markdown", reply_markup=markup)



async def daily_reminder(bot: Bot):
    while True:
        now = datetime.now()
        if now.hour == 9 and now.minute == 0:
            data = load_data()
            for user_key, info in data.items():
                user_id = int(user_key)
                todos = [t for t in info.get("todos", []) if not t["done"]]
                if todos:
                    text = "⏰ *Eslatma! Bajarilmagan topshiriqlaringiz:*\n\n"
                    text += "\n".join([f"• {t['task']}" for t in todos])
                    await bot.send_message(user_id, text, parse_mode="Markdown")
        await asyncio.sleep(60)



async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    asyncio.create_task(daily_reminder(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
