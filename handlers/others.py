from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database.mongo import users_collection

router = Router()

async def get_user_language(user_id: int) -> str:
    user = await users_collection.find_one({"user_id": user_id})
    return user.get("language", "ru") if user else "ru"

@router.message(F.text.in_(["📞Поддержка", "📞Kontaktlar"]) | (F.text.lower() == "/contacts"))
async def start_add_entrance(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    text = {
        "ru": "<b>Техник домофонов:</b> +998883300338\n<b>Администратор:</b> +998507121600",
        "uz": "<b>Domofon texniki:</b> +998883300338\n<b>Administrator:</b> +998507121600"
    }
    
    await message.answer(text[language], parse_mode="HTML")