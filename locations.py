CITIES = [
    {
        "id": "tashkent_city",
        "ru": "г. Ташкент",
        "uz": "Toshkent shahri"
    },
]

REGIONS = [
    {"id": "tashkent_region", "ru": "обл. Ташкент", "uz": "Toshkent viloyati"}
]

DISTRICTS = [
    {"id": "almazar", "city_id": "tashkent_city", "ru": "Алмазарский район", "uz": "Olmazor tumani"},
    {"id": "bektemir", "city_id": "tashkent_city", "ru": "Бектемирский район", "uz": "Bektemir tumani"},
    {"id": "mirabad", "city_id": "tashkent_city", "ru": "Мирабадский район", "uz": "Mirobod tumani"},
    {"id": "mirzo_ulugbek", "city_id": "tashkent_city", "ru": "Мирзо-Улугбекский район", "uz": "Mirzo Ulug'bek tumani"},
    {"id": "sergeli", "city_id": "tashkent_city", "ru": "Сергелийский район", "uz": "Sergeli tumani"},
    {"id": "chilanzar", "city_id": "tashkent_city", "ru": "Чиланзарский район", "uz": "Chilonzor tumani"},
    {"id": "shaykhontokhur", "city_id": "tashkent_city", "ru": "Шайхантаурский район", "uz": "Shayxontohur tumani"},
    {"id": "yunusabad", "city_id": "tashkent_city", "ru": "Юнусабадский район", "uz": "Yunusobod tumani"},
    {"id": "yakkasaray", "city_id": "tashkent_city", "ru": "Яккасарайский район", "uz": "Yakkasaroy tumani"},
    {"id": "yashnobod", "city_id": "tashkent_city", "ru": "Яшнабадский район", "uz": "Yashnobod tumani"},
    {"id": "uchtepa", "city_id": "tashkent_city", "ru": "Учтепинский район", "uz": "Uchtepa tumani"},
    {"id": "yangi_hayot", "city_id": "tashkent_city", "ru": "Янгихаётский район", "uz": "Yangi hayot tumani"}
]

CITY_MAP = {city["id"]: city for city in CITIES}
REGION_MAP = {region["id"]: region for region in REGIONS}
DISTRICT_MAP = {district["id"]: district for district in DISTRICTS}

def get_city_name(city_id, language="ru"):
    city = CITY_MAP.get(city_id)
    if city:
        return city.get(language, city["ru"])
    return None

def get_region_name(region_id, language="ru"):
    region = REGION_MAP.get(region_id)
    if region:
        return region.get(language, region["ru"])
    return None

def get_district_name(district_id, language="ru"):
    district = DISTRICT_MAP.get(district_id)
    if district:
        return district.get(language, district["ru"])
    return None

def get_city_id_by_name(name):
    for city in CITIES:
        if name in (city["ru"], city["uz"]):
            return city["id"]
    return None

def get_region_id_by_name(name):
    for region in REGIONS:
        if name in (region["ru"], region["uz"]):
            return region["id"]
    return None

def get_district_id_by_name(name):
    for district in DISTRICTS:
        if name in (district["ru"], district["uz"]):
            return district["id"]
    return None

def get_districts_by_city_id(city_id):
    return [d for d in DISTRICTS if d["city_id"] == city_id]
