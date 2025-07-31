from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.mongo import users_collection
from config import Config

router = Router()

async def get_user_language(user_id: int) -> str:
    user = await users_collection.find_one({"user_id": user_id})
    return user.get("language", "ru") if user else "ru"

def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")]
    ])

def user_keyboard(language: str = "ru"):
    texts = {
        "ru": {"pay": "💳 Оплатить домофон", "his": "🧾 Мои оплаты", "con": "📞Поддержка"},
        "uz": {"pay": "💳 Domofon to'lash", "his": "🧾 To'lovlarim", "con": "📞Kontaktlar"}
    }
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts[language]["pay"])],
            [KeyboardButton(text=texts[language]["his"])],
            [KeyboardButton(text=texts[language]["con"])]
            ],
        resize_keyboard=True
    )

def admin_keyboard(language: str = "ru"):
    texts = {
        "ru": {"pay": "💳 Оплатить домофон", "add": "➕ Добавить подъезд", "his": "🧾 Мои оплаты", "con": "📞Поддержка"},
        "uz": {"pay": "💳 Domofon to'lash", "add": "➕ Podyezd qo'shish", "his": "🧾 To'lovlarim", "con": "📞Kontaktlar"}
    }
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts[language]["pay"])],
            [KeyboardButton(text=texts[language]["his"])],
            [KeyboardButton(text=texts[language]["con"])],
            [KeyboardButton(text=texts[language]["add"])]
        ],
        resize_keyboard=True
    )

@router.message(F.text == "/start")
async def start_command(message: Message, state: FSMContext):
    user = await users_collection.find_one({"user_id": message.from_user.id})
    if not user:
        await message.answer(
            "Выберите язык / Tilni tanlang:",
            reply_markup=language_keyboard()
        )
    else:
        language = user.get("language", "ru")
        if message.from_user.id in Config().ADMINS:
            await message.answer(
                "🛠 Админ-панель и доступ пользователя активны." if language == "ru" 
                else "🛠 Admin panel va foydalanuvchi podyezd faol.",
                reply_markup=admin_keyboard(language)
            )
        else:
            await message.answer(
                "👋 Добро пожаловать! Выберите нужный пункт." if language == "ru" 
                else "👋 Xush kelibsiz! Kerakli bo'limni tanlang.",
                reply_markup=user_keyboard(language)
            )

@router.message(F.text == "/language")
async def change_language(message: Message):
    await message.answer(
        "Выберите язык / Tilni tanlang:",
        reply_markup=language_keyboard()
    )

@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    language = callback.data.split("_")[1]
    await users_collection.update_one(
        {"user_id": callback.from_user.id},
        {"$set": {"user_id": callback.from_user.id, "language": language}},
        upsert=True
    )
    
    if callback.from_user.id in Config().ADMINS:
        await callback.message.edit_text(
            "🛠 Админ-панель и доступ пользователя активны." if language == "ru" 
            else "🛠 Admin panel va foydalanuvchi podyezd faol."
        )
        await callback.message.answer(
            "Выберите действие:" if language == "ru" else "Harakatni tanlang:",
            reply_markup=admin_keyboard(language)
        )
    else:
        await callback.message.edit_text(
            "👋 Добро пожаловать! Выберите нужный пункт." if language == "ru" 
            else "👋 Xush kelibsiz! Kerakli bo'limni tanlang."
        )
        await callback.message.answer(
            "Выберите действие:" if language == "ru" else "Harakatni tanlang:",
            reply_markup=user_keyboard(language)
        )
    await callback.answer()