from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database.mongo import houses, payments_collection, users_collection
from locations import get_city_name, get_region_name, get_city_id_by_name, get_region_id_by_name, get_district_id_by_name, get_district_name, get_districts_by_city_id
from bson import ObjectId
from config import Config

router = Router()

async def get_user_language(user_id: int) -> str:
    user = await users_collection.find_one({"user_id": user_id})
    return user.get("language", "ru") if user else "ru"

class AddEntrance(StatesGroup):
    region_type = State()
    district = State()
    quarter = State()
    house_number = State()
    entrance_number = State()
    floors = State()
    apartment_start = State()
    apartment_end = State()

def region_type_inline_keyboard(language: str = "ru"):
    from locations import CITIES, REGIONS
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=city[language], callback_data=f"region_{city['id']}") for city in CITIES],
        [InlineKeyboardButton(text=region[language], callback_data=f"region_{region['id']}") for region in REGIONS]
    ])

def district_inline_keyboard(city_id, language: str = "ru"):
    districts = get_districts_by_city_id(city_id)
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=d[language], callback_data=f"district_{d['id']}")] for d in districts]
    )

district_values_ru = [
    "Алмазарский район", "Бектемирский район", "Мирабадский район", "Мирзо-Улугбекский район",
    "Сергелийский район", "Чиланзарский район", "Шайхантаурский район", "Юнусабадский район",
    "Яккасарайский район", "Яшнабадский район", "Учтепинский район", "Янгихаётский район"
]
district_values_uz = [
    "Olmazor tumani", "Bektemir tumani", "Mirobod tumani", "Mirzo Ulug'bek tumani",
    "Sergeli tumani", "Chilonzor tumani", "Shayxontohur tumani", "Yunusobod tumani",
    "Yakkasaroy tumani", "Yashnobod tumani", "Uchtepa tumani", "Yangi hayot tumani"
]

@router.message(F.text.in_(["➕ Добавить подъезд", "➕ Podyezd qo'shish"]))
async def start_add_entrance(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    text = "Выберите тип региона:" if language == "ru" else "Hudud turini tanlang:"
    await message.answer(text, reply_markup=region_type_inline_keyboard(language))
    await state.set_state(AddEntrance.region_type)

@router.callback_query(F.data.startswith("region_"))
async def region_selected(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    region_id = callback.data.replace("region_", "")
    
    await state.update_data(region_type=region_id)
    
    text = "Выберите район:" if language == "ru" else "Tumanni tanlang:"
    if region_id.startswith("tashkent_city"):
        await callback.message.edit_text(text, reply_markup=district_inline_keyboard(region_id, language))
        await state.set_state(AddEntrance.district)
    else:
        await callback.message.edit_text("Пока поддерживается только г. Ташкент." if language == "ru" else "Hozircha faqat Toshkent shahri qo'llab-quvvatlanadi.")
        await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("district_"))
async def district_selected(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    district_id = callback.data.replace("district_", "")
    await state.update_data(district=district_id)
    text = "Введите квартал:" if language == "ru" else "Kvartalni kiriting:"
    await callback.message.edit_text(text)
    await state.set_state(AddEntrance.quarter)
    await callback.answer()

@router.message(AddEntrance.quarter)
async def input_house(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    await state.update_data(quarter=message.text)
    text = "Введите номер дома:" if language == "ru" else "Uy raqamini kiriting:"
    await message.answer(text)
    await state.set_state(AddEntrance.house_number)

@router.message(AddEntrance.house_number)
async def input_entrance(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    await state.update_data(house_number=message.text)
    text = "Введите номер подъезда:" if language == "ru" else "Podyezd raqamini kiriting:"
    await message.answer(text)
    await state.set_state(AddEntrance.entrance_number)

@router.message(AddEntrance.entrance_number)
async def input_floors(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    await state.update_data(entrance_number=message.text)
    text = "Сколько этажей в подъезде?" if language == "ru" else "Kirishda necha qavat bor?"
    await message.answer(text)
    await state.set_state(AddEntrance.floors)

@router.message(AddEntrance.floors)
async def input_apartment_start(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    await state.update_data(floors=int(message.text))
    text = "С какой квартиры начинается нумерация?" if language == "ru" else "Raqamlash qaysi kvartirani boshlaydi?"
    await message.answer(text)
    await state.set_state(AddEntrance.apartment_start)

@router.message(AddEntrance.apartment_start)
async def input_apartment_end(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    await state.update_data(apartment_start=int(message.text))
    text = "На какой квартире заканчивается подъезд?" if language == "ru" else "Podyezd qaysi kvartira bilan tugaydi?"
    await message.answer(text)
    await state.set_state(AddEntrance.apartment_end)

@router.message(AddEntrance.apartment_end)
async def finish_addition(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    data = await state.get_data()
    await houses.insert_one({
        "region_type": data['region_type'],
        "district": data['district'],
        "quarter": data['quarter'],
        "house_number": data['house_number'],
        "entrance_number": data['entrance_number'],
        "floors": data['floors'],
        "apartment_start": data['apartment_start'],
        "apartment_end": int(message.text)
    })

    region_type_name = get_city_name(data['region_type'], language) or get_region_name(data['region_type'], language)
    district_name = get_district_name(data['district'], language)
    if language == "ru":
        await message.answer(
            f"✅ Подъезд добавлен:\n"
            f"🏙 {region_type_name}, {district_name}\n"
            f"Квартал: {data['quarter']}, Дом: {data['house_number']}\n"
            f"Подъезд: {data['entrance_number']} | Этажей: {data['floors']}\n"
            f"Диапазон квартир: {data['apartment_start']}–{message.text}"
        )
    else:
        await message.answer(
            f"✅ Podyezd qo'shildi:\n"
            f"🏙 {region_type_name}, {district_name}\n"
            f"Kvartal: {data['quarter']}, Uy: {data['house_number']}\n"
            f"Podyezd: {data['entrance_number']} | Qavatlar: {data['floors']}\n"
            f"Kvartira oralig'i: {data['apartment_start']}–{message.text}"
        )
    await state.clear()

@router.callback_query(F.data.startswith("approve:"))
async def approve_payment(callback: CallbackQuery):
    language = await get_user_language(callback.from_user.id)
    payment_id = callback.data.split(":")[1]

    payment = await payments_collection.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        text = "Платёж не найден." if language == "ru" else "To'lov topilmadi."
        await callback.answer(text, show_alert=True)
        return

    await payments_collection.update_one(
        {"_id": ObjectId(payment_id)},
        {"$set": {"status": "approved", "checked_by": callback.from_user.id}}
    )

    await callback.message.edit_caption(callback.message.caption + "\n\n✅ Оплата подтверждена администратором." if language == "ru" else "\n\n✅ To'lov administrator tomonidan tasdiqlandi.")
    text = "Оплата подтверждена" if language == "ru" else "To'lov tasdiqlandi"
    await callback.answer(text)

    user_id = payment.get("user_id")
    if user_id:
        user_language = await get_user_language(user_id)
        text = "✅ Ваша оплата подтверждена!" if user_language == "ru" else "✅ Sizning to'lovingiz tasdiqlandi!"
        await callback.bot.send_message(user_id, text)

@router.callback_query(F.data.startswith("reject:"))
async def reject_payment(callback: CallbackQuery):
    language = await get_user_language(callback.from_user.id)
    payment_id = callback.data.split(":")[1]

    payment = await payments_collection.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        text = "Платёж не найден." if language == "ru" else "To'lov topilmadi."
        await callback.answer(text, show_alert=True)
        return

    await payments_collection.update_one(
        {"_id": ObjectId(payment_id)},
        {"$set": {"status": "rejected", "checked_by": callback.from_user.id}}
    )

    await callback.message.edit_caption(callback.message.caption + "\n\n❌ Оплата отклонена администратором." if language == "ru" else "\n\n❌ To'lov administrator tomonidan rad etildi.")
    text = "Оплата отклонена" if language == "ru" else "To'lov rad etildi"
    await callback.answer(text)

    user_id = payment.get("user_id")
    if user_id:
        user_language = await get_user_language(user_id)
        text = "❌ Ваша оплата отклонена." if user_language == "ru" else "❌ Sizning to'lovingiz rad etildi."
        await callback.bot.send_message(user_id, text)