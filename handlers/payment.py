from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database.mongo import payments_collection, houses, users_collection
from locations import get_city_name, get_region_name, get_city_id_by_name, get_region_id_by_name, get_districts_by_city_id, get_district_name, get_district_id_by_name
from datetime import datetime
from bson import ObjectId

router = Router()

async def get_user_language(user_id: int) -> str:
    user = await users_collection.find_one({"user_id": user_id})
    return user.get("language", "ru") if user else "ru"

class PaymentState(StatesGroup):
    City = State()
    District = State()
    Quarter = State()
    House = State()
    Entrance = State()
    Apartment = State()
    Month = State()
    AwaitingReceipt = State()

def get_back_button(language: str = "ru"):
    text = "🔙 Назад" if language == "ru" else "🔙 Orqaga"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data="back")]
    ])

# City/region translation now handled by locations.py

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database.mongo import payments_collection, houses, users_collection
from locations import get_city_name, get_region_name, get_city_id_by_name, get_region_id_by_name, get_districts_by_city_id, get_district_name, get_district_id_by_name
from datetime import datetime
from bson import ObjectId

@router.message(F.text.in_(["🧾 Мои оплаты", "🧾 To'lovlarim"]) | (F.text.lower() == "/history"))
async def show_payment_history(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    user_id = message.from_user.id

    MONTHS_RU = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    MONTHS_UZ = [
        "", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
    ]

    # Find all payments for this user
    payments = payments_collection.find({"user_id": user_id, "status": {"$in": ["pending", "approved"]}})
    lines = []
    async for p in payments:
        address = p.get("address", {})
        year = p.get("year")
        month = p.get("month")
        status = p.get("status")
        created_at = p.get("created_at")  # Assume this is a datetime or ISO string

        # Address parts
        city = get_city_name(address.get("city"), language) if address.get("city") else ""
        district = get_district_name(address.get("district"), language) if address.get("district") else ""
        quarter = address.get("quarter", "")
        house = address.get("house", "")
        entrance = address.get("entrance", "")
        apartment = address.get("apartment", "")

        # Localized month name
        if language == "ru":
            month_name = MONTHS_RU[month] if month and 1 <= month <= 12 else ""
            status_text = "✅Оплачено" if status == "approved" else "В ожидании"
            address_str = f"{city}, {district}, {quarter} квартал, {house} дом, {entrance} подъезд, {apartment} квартира"
        else:
            month_name = MONTHS_UZ[month] if month and 1 <= month <= 12 else ""
            status_text = "✅To'langan" if status == "approved" else "Kutilmoqda"
            address_str = f"{city}, {district}, {quarter}-kvartal, {house}-uy, {entrance}-podyezd, {apartment}-kvartira"

        # Format date
        date_str = ""
        if created_at:
            if isinstance(created_at, datetime):
                date_str = created_at.strftime("%d.%m.%Y")
            else:
                try:
                    date_str = datetime.fromisoformat(created_at).strftime("%d.%m.%Y")
                except Exception:
                    date_str = str(created_at)
        else:
            date_str = "-"

        line = (
            f"<b>{address_str}</b> - <i>{month_name} {year}</i> - "
            f"<b>{status_text}</b> (<i>{'Дата:' if language == "ru" else "Sana"} {date_str}</i>)"
        )
        lines.append(line)

    if not lines:
        text = "У вас нет истории оплат." if language == "ru" else "Sizda to'lovlar tarixi yo'q."
        await message.answer(text)
        return

    header = "🗓<b>Ваша история оплат:</b>" if language == "ru" else "🗓<b>To'lovlar tarixi:</b>"
    text = header + "\n\n" + "\n\n".join(lines)
    await message.answer(text, parse_mode="HTML")

@router.message((F.text.lower() == "/payment") | (F.text.in_(["💳 Оплатить домофон", "💳 Domofon to'lash"])))
async def start_payment(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    region_types = await houses.distinct("region_type")
    region_types = [r for r in region_types if r]
    if region_types:
        buttons = []
        for city_id in region_types:
            city_name = get_city_name(city_id, language)
            if city_name:
                buttons.append([KeyboardButton(text=city_name)])
        keyboard = ReplyKeyboardMarkup(
            keyboard=buttons,
            resize_keyboard=True
        )
        text = "Выберите ваш город:" if language == "ru" else "Shahringizni tanlang:"
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(PaymentState.City)
    else:
        text = "Нет доступных городов для оплаты." if language == "ru" else "To'lash uchun mavjud shaharlar yo'q."
        await message.answer(text)

@router.message(PaymentState.City)
async def select_city(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    city_name = message.text
    city_id = get_city_id_by_name(city_name)
    region_types = await houses.distinct("region_type")
    if city_id not in region_types:
        text = "Пожалуйста, выберите город из списка." if language == "ru" else "Iltimos, ro'yxatdan shaharni tanlang."
        await message.answer(text, reply_markup=get_back_button(language))
        return
    await state.update_data(city=city_id)

    # Use new logic: get all districts for the city, but only show those present in the DB
    all_districts = get_districts_by_city_id(city_id)
    db_district_ids = set(await houses.distinct("district", {"region_type": city_id}))
    districts = [d for d in all_districts if d["id"] in db_district_ids]
    if districts:
        buttons = []
        for district in districts:
            district_name = get_district_name(district["id"], language)
            if district_name:
                buttons.append([KeyboardButton(text=district_name)])
        keyboard = ReplyKeyboardMarkup(
            keyboard=buttons,
            resize_keyboard=True,
            one_time_keyboard=False
        )
        text = "Выберите район:" if language == "ru" else "Tumanni tanlang:"
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(PaymentState.District)
    else:
        text = "Нет доступных районов для выбранного города." if language == "ru" else "Tanlangan shahar uchun mavjud tumanlar yo'q."
        await message.answer(text, reply_markup=get_back_button(language))

@router.message(PaymentState.District)
async def select_district(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    data = await state.get_data()

    district_name = message.text
    district_id = get_district_id_by_name(district_name)
    db_district_ids = set(await houses.distinct("district", {"region_type": data['city']}))
    if district_id not in db_district_ids:
        text = "Пожалуйста, выберите район из списка." if language == "ru" else "Iltimos, ro'yxatdan tumani tanlang."
        await message.answer(text, reply_markup=get_back_button(language))
        return
    await state.update_data(district=district_id)
    quarters = await houses.distinct("quarter", {"region_type": data['city'], "district": district_id})
    quarters = [q for q in quarters if q]
    if quarters:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=quarter)] for quarter in quarters],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        text = "Выберите квартал:" if language == "ru" else "Kvartalni tanlang:"
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(PaymentState.Quarter)
    else:
        text = "Нет доступных кварталов для выбранного района." if language == "ru" else "Tanlangan tuman uchun mavjud kvartallar yo'q."
        await message.answer(text, reply_markup=get_back_button(language))

@router.message(PaymentState.Quarter)
async def select_quarter(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    data = await state.get_data()
    quarter = message.text
    quarters = await houses.distinct("quarter", {"region_type": data['city'], "district": data['district']})
    if quarter not in quarters:
        text = "Пожалуйста, выберите квартал из списка." if language == "ru" else "Iltimos, ro'yxatdan kvartalni tanlang."
        await message.answer(text, reply_markup=get_back_button(language))
        return
    await state.update_data(quarter=quarter)

    # Получаем список домов в этом квартале
    houses_list = await houses.distinct("house_number", {
        "region_type": data['city'],
        "district": data['district'],
        "quarter": quarter
    })
    houses_list = [h for h in houses_list if h]
    
    if houses_list:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=house)] for house in houses_list],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        text = "Выберите дом:" if language == "ru" else "Uyni tanlang:"
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(PaymentState.House)
    else:
        text = "Нет доступных домов в выбранном квартале." if language == "ru" else "Tanlangan kvartalda mavjud uylar yo'q."
        await message.answer(text, reply_markup=get_back_button(language))

@router.message(PaymentState.House)
async def select_house(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    data = await state.get_data()
    house = message.text

    existing_houses = await houses.distinct("house_number", {
        "region_type": data['city'],
        "district": data['district'],
        "quarter": data['quarter']
    })
    
    if house not in existing_houses:
        text = "Пожалуйста, выберите дом из списка." if language == "ru" else "Iltimos, ro'yxatdan uyni tanlang."
        await message.answer(text, reply_markup=get_back_button(language))
        return
    
    await state.update_data(house=house)

    entrances = await houses.distinct("entrance_number", {
        "region_type": data['city'],
        "district": data['district'],
        "quarter": data['quarter'],
        "house_number": house
    })
    entrances = [e for e in entrances if e]
    
    if entrances:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=entrance)] for entrance in entrances],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        text = "Выберите подъезд:" if language == "ru" else "Kirishni tanlang:"
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(PaymentState.Entrance)
    else:
        text = "Нет доступных подъездов в выбранном доме." if language == "ru" else "Tanlangan uyda mavjud kirishlar yo'q."
        await message.answer(text, reply_markup=get_back_button(language))

@router.message(PaymentState.Entrance)
async def select_entrance(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    data = await state.get_data()
    entrance = message.text

    entrances = await houses.distinct("entrance_number", {
        "region_type": data['city'],
        "district": data['district'],
        "quarter": data['quarter'],
        "house_number": data['house']
    })
    
    if entrance not in entrances:
        text = "Пожалуйста, выберите подъезд из списка." if language == "ru" else "Iltimos, ro'yxatdan kirishni tanlang."
        await message.answer(text, reply_markup=get_back_button(language))
        return
    
    await state.update_data(entrance=entrance)

    house_doc = await houses.find_one({
        "region_type": data['city'],
        "district": data['district'],
        "quarter": data['quarter'],
        "entrance_number": entrance
    })
    if not house_doc:
        text = "Не удалось найти дом для выбранного адреса." if language == "ru" else "Tanlangan manzil uchun uy topilmadi."
        await message.answer(text, reply_markup=get_back_button(language))
        return
    await state.update_data(house=house_doc.get('house_number', ''))

    apartment_start = house_doc.get("apartment_start")
    apartment_end = house_doc.get("apartment_end")
    if apartment_start is None or apartment_end is None:
        text = "Нет информации о квартирах для выбранного подъезда." if language == "ru" else "Tanlangan podyezd uchun kvartiralar haqida ma'lumot yo'q."
        await message.answer(text, reply_markup=get_back_button(language))
        return
    
    apartments = list(range(int(apartment_start), int(apartment_end) + 1))
    paid_apartments_cursor = payments_collection.find({
        "address.city": data['city'],
        "address.district": data['district'],
        "address.quarter": data['quarter'],
        "address.entrance": entrance,
        "status": {"$in": ["pending", "approved"]}
    })
    paid_apartments = set()
    async for doc in paid_apartments_cursor:
        apt = doc.get("address", {}).get("apartment")
        if apt:
            try:
                paid_apartments.add(int(apt))
            except Exception:
                pass
    unpaid_apartments = [apt for apt in apartments if apt not in paid_apartments]
    
    if not unpaid_apartments:
        text = "Все квартиры в этом подъезде уже оплатили." if language == "ru" else "Ushbu kirishdagi barcha kvartiralar allaqachon to'langan."
        await message.answer(text, reply_markup=get_back_button(language))
        return

    paid_apartments_list = ", ".join(str(apt) for apt in sorted(paid_apartments)) or "-"
    unpaid_apartments_list = ", ".join(str(apt) for apt in sorted(unpaid_apartments)) or "-"
    
    if language == "ru":
        text = (
            f"Квартиры, которые уже оплатили: {paid_apartments_list}\n"
            f"Квартиры, которые ещё не оплатили: {unpaid_apartments_list}\n"
            f"Выберите квартиру для оплаты:"
        )
    else:
        text = (
            f"To'langan kvartiralar: {paid_apartments_list}\n"
            f"To'lanmagan kvartiralar: {unpaid_apartments_list}\n"
            f"To'lash uchun kvartirani tanlang:"
        )
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=str(apt))] for apt in unpaid_apartments],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(PaymentState.Apartment)

@router.message(PaymentState.Apartment)
async def select_apartment(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    data = await state.get_data()
    
    house_doc = await houses.find_one({
        "region_type": data['city'],
        "district": data['district'],
        "quarter": data['quarter'],
        "entrance_number": data['entrance']
    })
    
    if not house_doc:
        text = "Ошибка: не найдена информация о подъезде." if language == "ru" else "Xato: Podyezd haqida ma'lumot topilmadi."
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return
    
    apartment_start = house_doc.get("apartment_start")
    apartment_end = house_doc.get("apartment_end")
    
    try:
        input_apartment = int(message.text)
    except ValueError:
        text = "Пожалуйста, введите корректный номер квартиры (только цифры)." if language == "ru" else "Iltimos, kvartira raqamini to'g'ri kiriting (faqat raqamlar)."
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        return
    
    if input_apartment < apartment_start or input_apartment > apartment_end:
        text = f"Квартира должна быть в диапазоне от {apartment_start} до {apartment_end}." if language == "ru" else f"Kvartira {apartment_start} dan {apartment_end} gacha bo'lishi kerak."
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        return
    
    await state.update_data(apartment=str(input_apartment))

    MONTHS_RU = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    MONTHS_UZ = [
        "", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
    ]

    from datetime import datetime, timedelta
    now = datetime.now()
    months = []
    for i in range(12):
        month_dt = (now.replace(day=1) + timedelta(days=32*i)).replace(day=1)
        months.append((month_dt.year, month_dt.month))

    payment_status = {}
    for year, month in months:
        exists = await payments_collection.find_one({
            "address.city": data['city'],
            "address.district": data['district'],
            "address.quarter": data['quarter'],
            "address.entrance": data['entrance'],
            "address.apartment": str(input_apartment),
            "year": year,
            "month": month,
            "status": {"$in": ["pending", "approved"]}
        })
        payment_status[(year, month)] = bool(exists)
    buttons = []
    for year, month in months:
        if language == "ru":
            month_name = MONTHS_RU[month]
        else:
            month_name = MONTHS_UZ[month]
        label = f"{month_name} {year} {'✅' if payment_status[(year, month)] else ''}"
        buttons.append([KeyboardButton(text=label)])
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)
    text = "Выберите месяц для оплаты:" if language == "ru" else "To'lash uchun oynini tanlang:"
    await message.answer(text, reply_markup=keyboard)
    await state.update_data(apartment=str(input_apartment), months=months, payment_status=payment_status)
    await state.set_state(PaymentState.Month)

@router.message(PaymentState.Month)
async def select_month(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    data = await state.get_data()
    month_names = [
        None,
        "Январь" if language == "ru" else "Yanvar",
        "Февраль" if language == "ru" else "Fevral",
        "Март" if language == "ru" else "Mart",
        "Апрель" if language == "ru" else "Aprel",
        "Май" if language == "ru" else "May",
        "Июнь" if language == "ru" else "Iyun",
        "Июль" if language == "ru" else "Iyul",
        "Август" if language == "ru" else "Avgust",
        "Сентябрь" if language == "ru" else "Sentabr",
        "Октябрь" if language == "ru" else "Oktabr",
        "Ноябрь" if language == "ru" else "Noyabr",
        "Декабрь" if language == "ru" else "Dekabr"
    ]
    # Parse month and year from button text
    selected = message.text.strip().split()
    if len(selected) < 2:
        await message.answer("Пожалуйста, выберите месяц из списка." if language == "ru" else "Iltimos, oyni ro'yxatdan tanlang.")
        return
    month_name = selected[0]
    year = int(selected[1])
    # Find month number
    try:
        month = month_names.index(month_name)
    except ValueError:
        await message.answer("Пожалуйста, выберите месяц из списка." if language == "ru" else "Iltimos, oyni ro'yxatdan tanlang.")
        return
    await state.update_data(year=year, month=month)
    # Warn if already paid
    payment_status = data.get('payment_status', {})
    if payment_status.get((year, month)):
        await message.answer("Внимание: за этот месяц уже оплачено! Вы можете оплатить снова, если хотите." if language == "ru" else "Diqqat: bu oy uchun to'lov allaqachon qilingan! Yana to'lash mumkin.")
    # Show address and month confirmation
    city_name = get_city_name(data['city'], language)
    district_name = get_district_name(data['district'], language)
    address_text = (
        (f"🏢 <b>Ваш адрес:</b>\n" if language == "ru" else f"🏢 <b>Manzilingiz:</b>\n") +
        (f"<b>Город:</b> {city_name}\n" if language == "ru" else f"<b>Shahar:</b> {city_name}\n") +
        (f"<b>Район:</b> {district_name}\n" if language == "ru" else f"<b>Tuman:</b> {district_name}\n") +
        (f"<b>Квартал:</b> {data['quarter']}\n" if language == "ru" else f"<b>Kvartal:</b> {data['quarter']}\n") +
        (f"<b>Дом:</b> {data['house']}\n" if language == "ru" else f"<b>Uy:</b> {data['house']}\n") +
        (f"<b>Подъезд:</b> {data['entrance']}\n" if language == "ru" else f"<b>Podyezd:</b> {data['entrance']}\n") +
        (f"<b>Квартира:</b> {data['apartment']}\n" if language == "ru" else f"<b>Kvartira:</b> {data['apartment']}\n") +
        (f"<b>Месяц:</b> {month_name} {year}\n" if language == "ru" else f"<b>Oy:</b> {month_name} {year}\n")
    )
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить" if language == "ru" else "✅ Tasdiqlash", callback_data="confirm_address"),
         InlineKeyboardButton(text="🔙 Изменить" if language == "ru" else "🔙 O'zgartirish", callback_data="change_address")]
    ])
    await message.answer(address_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await message.answer(
        "Подтвердите или измените адрес и месяц оплаты:" if language == "ru" else "Manzil va oy to'g'riligini tasdiqlang yoki o'zgartiring:",
        reply_markup=confirm_keyboard
    )
    await state.set_state(PaymentState.AwaitingReceipt)

@router.callback_query(F.data == "confirm_address")
async def confirm_address(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    
    if not callback.from_user.username:
        text = (
            "❗️ Для продолжения оплаты необходимо установить username в настройках Telegram.\n"
            "Пожалуйста, перейдите в настройки Telegram и установите уникальное имя пользователя (username), затем повторите попытку."
        ) if language == "ru" else (
            "❗️ To'lovni davom ettirish uchun Telegram sozlamalarida username o'rnatishingiz kerak.\n"
            "Iltimos, Telegram sozlamalariga o'ting va foydalanuvchi nomini (username) o'rnating, so'ng qayta urinib ko'ring."
        )
        await callback.message.answer(text)
        await state.clear()
        return
    
    if language == "ru":
        payment_text = (
            "💳 <b>Оплата домофона</b>\n"
            "<b>Сумма:</b> 8 000 сум\n"
            "<b>Реквизиты:</b> 8600 XXXX XXXX XXXX (AGROBANK)\n"
            "\n"
            "⚠️ После оплаты отправьте фото квитанции для подтверждения."
        )
    else:
        payment_text = (
            "💳 <b>Domofon to'lash</b>\n"
            "<b>Summa:</b> 8 000 so'm\n"
            "<b>Rekvizitlar:</b> 8600 XXXX XXXX XXXX (AGROBANK)\n"
            "\n"
            "⚠️ To'lovdan so'ng tasdiqlash uchun kvitansiya rasmini yuboring."
        )
    
    await callback.message.answer(payment_text, parse_mode="HTML")
    await state.set_state(PaymentState.AwaitingReceipt)
    await callback.answer()

@router.callback_query(F.data == "change_address")
async def change_address(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    await state.set_state(PaymentState.Apartment)
    text = "Введите номер квартиры снова:" if language == "ru" else "Kvartira raqamini qayta kiriting:"
    await callback.message.answer(text)
    await callback.answer()

@router.message(PaymentState.AwaitingReceipt, F.photo)
async def handle_receipt(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    data = await state.get_data()
    file_id = message.photo[-1].file_id

    # Only store minimal address info and selected year/month
    address = {
        "city": data['city'],
        "district": data['district'],
        "quarter": data['quarter'],
        "house": data['house'],
        "entrance": data['entrance'],
        "apartment": data['apartment']
    }
    payment_data = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "address": address,
        "year": data.get('year'),
        "month": data.get('month'),
        "receipt_file_id": file_id,
        "amount": 8000,
        "status": "pending",
        "created_at": datetime.utcnow(),
    }
    result = await payments_collection.insert_one(payment_data)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{result.inserted_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{result.inserted_id}")]
    ])

    city_name = get_city_name(data['city'], 'uz')
    district_name = get_district_name(data['district'], 'uz')
    caption = (
        f"🧾 <b>Yangi kvitansiya</b> @{message.from_user.username or 'Foydalanuvchi'}\n"
        f"<b>Manzil:</b> {city_name}, {district_name}, kvartal {data['quarter']}\n"
        f"<b>Uy:</b> {data['house']}, podyezd {data['entrance']}, kv. {data['apartment']}\n"
        f"<b>Summa:</b> 8 000 UZS"
    )

    # if language == "ru":
    #     caption = (
    #         f"🧾 <b>Новая квитанция</b> от @{message.from_user.username or 'Пользователь'}\n"
    #         f"<b>Адрес:</b> {data['city']}, {data['district']}, квартал {data['quarter']}\n"
    #         f"<b>Дом:</b> {data['house']}, подъезд {data['entrance']}, кв. {data['apartment']}\n"
    #         f"<b>Сумма:</b> 10 000 UZS"
    #     )
    # else:
    #     caption = (
    #         f"🧾 <b>Yangi kvitansiya</b> @{message.from_user.username or 'Foydalanuvchi'}\n"
    #         f"<b>Manzil:</b> {data['city']}, {data['district']}, kvartal {data['quarter']}\n"
    #         f"<b>Uy:</b> {data['house']}, kirish {data['entrance']}, kv. {data['apartment']}\n"
    #         f"<b>Summa:</b> 10 000 UZS"
    #     )

    await message.bot.send_photo(
        chat_id=-4802250699,
        photo=file_id,
        caption=caption,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    text = "Квитанция отправлена. Ожидайте подтверждения." if language == "ru" else "Kvitansiya yuborildi. Tasdiqlanishini kuting."
    await message.answer(text)
    await state.clear()

@router.callback_query(F.data.startswith("approve:") | F.data.startswith("reject:"))
async def handle_payment_approval(call: types.CallbackQuery):
    language = await get_user_language(call.from_user.id)
    action, payment_id = call.data.split(":", 1)
    original_caption = call.message.caption or ""
    payment_doc = await payments_collection.find_one({"_id": ObjectId(payment_id)})
    user_id = payment_doc.get("user_id") if payment_doc else None

    if action == "approve":
        status = "\n\n✅ <b>Оплата подтверждена</b>" if language == "ru" else "\n\n✅ <b>To'lov tasdiqlandi</b>"
        await payments_collection.update_one({"_id": ObjectId(payment_id)}, {"$set": {"status": "approved"}})
        if user_id:
            try:
                user_language = await get_user_language(user_id)
                text = "✅ Ваша оплата домофона подтверждена! Спасибо за своевременную оплату." if user_language == "ru" else "✅ Domofon to'lovingiz tasdiqlandi! O'z vaqtida to'laganingiz uchun rahmat."
                await call.bot.send_message(chat_id=user_id, text=text)
            except Exception:
                pass
    else:
        status = "\n\n❌ <b>Оплата отклонена</b>" if language == "ru" else "\n\n❌ <b>To'lov rad etildi</b>"
        await payments_collection.update_one({"_id": ObjectId(payment_id)}, {"$set": {"status": "rejected"}})
        if user_id:
            try:
                user_language = await get_user_language(user_id)
                text = "❌ Ваша оплата домофона была отклонена. Пожалуйста, проверьте данные и попробуйте снова." if user_language == "ru" else "❌ Domofon to'lovingiz rad etildi. Iltimos, ma'lumotlarni tekshiring va qayta urinib ko'ring."
                await call.bot.send_message(chat_id=user_id, text=text)
            except Exception:
                pass
    
    await call.message.edit_caption(
        caption=original_caption + status,
        parse_mode="HTML",
        reply_markup=None
    )
    text = "Статус обновлён." if language == "ru" else "Holat yangilandi."
    await call.answer(text)

@router.callback_query(F.data == "back")
async def back_handler(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    current_state = await state.get_state()
    
    if current_state == PaymentState.District.state:
        await state.set_state(PaymentState.City)
        region_types = await houses.distinct("region_type")
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=region)] for region in region_types],
            resize_keyboard=True
        )
        text = "Выберите ваш город:" if language == "ru" else "Shahringizni tanlang:"
        await callback.message.answer(text, reply_markup=keyboard)
    
    elif current_state == PaymentState.Quarter.state:
        await state.set_state(PaymentState.District)
        data = await state.get_data()
        districts = await houses.distinct("district", {"region_type": data['city']})
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=district)] for district in districts],
            resize_keyboard=True
        )
        text = "Выберите район:" if language == "ru" else "Tumanni tanlang:"
        await callback.message.answer(text, reply_markup=keyboard)
    
    elif current_state == PaymentState.House.state:
        await state.set_state(PaymentState.Quarter)
        data = await state.get_data()
        quarters = await houses.distinct("quarter", {
            "region_type": data['city'],
            "district": data['district']
        })
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=quarter)] for quarter in quarters],
            resize_keyboard=True
        )
        text = "Выберите квартал:" if language == "ru" else "Kvartalni tanlang:"
        await callback.message.answer(text, reply_markup=keyboard)
    
    elif current_state == PaymentState.Entrance.state:
        await state.set_state(PaymentState.House)
        data = await state.get_data()
        houses_list = await houses.distinct("house_number", {
            "region_type": data['city'],
            "district": data['district'],
            "quarter": data['quarter']
        })
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=house)] for house in houses_list],
            resize_keyboard=True
        )
        text = "Выберите дом:" if language == "ru" else "Uyni tanlang:"
        await callback.message.answer(text, reply_markup=keyboard)

    elif current_state == PaymentState.Apartment.state:
        await state.set_state(PaymentState.Entrance)
        data = await state.get_data()
        entrances = await houses.distinct("entrance_number", {
            "region_type": data['city'],
            "district": data['district'],
            "quarter": data['quarter']
        })
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=entrance)] for entrance in entrances],
            resize_keyboard=True
        )
        text = "Выберите подъезд:" if language == "ru" else "Kirishni tanlang:"
        await callback.message.answer(text, reply_markup=keyboard)
    
    await callback.answer()