from api.dongchedifetch import fetch_dongchedi_cars
from models.response import ApiResponse
from api.che168fetch import fetch_che168_cars
from translate import translate_text
import json
from converters import decode_sh_price

# api_response = fetch_dongchedi_cars()
# for car in api_response.data.search_sh_sku_info_list:
#     output = []
#     output.append("-" * 40)
#     output.append(f"Марка: {translate_text(car.brand_name) if car.brand_name else ''}")
#     output.append(f"Модель: {translate_text(car.car_name) if car.car_name else ''}")
#     output.append(f"Серия: {translate_text(car.series_name) if car.series_name else ''}")
#     output.append(f"Год: {car.car_year}")
#     output.append(f"Город: {translate_text(car.car_source_city_name) if car.car_source_city_name else ''}")
#     output.append(f"Заголовок: {translate_text(car.title) if car.title else ''}")
#     if car.sh_price:
#         output.append(f"Цена: {decode_sh_price(car.sh_price)}")
#     else:
#         output.append("Цена:")
#     output.append(f"Ссылка на фото: {car.image}")
#     output.append("")
#     print("\n".join(output))

cars = fetch_che168_cars('url')
for car in cars:
    output = []
    output.append("-" * 40)
    output.append(f"Марка: {translate_text(car.brand_name) if car.brand_name else ''}")
    output.append(f"Модель: {translate_text(car.car_name) if car.car_name else ''}")
    output.append(f"Серия: {translate_text(car.series_name) if car.series_name else ''}")
    output.append(f"Год: {car.car_year}")
    output.append(f"Город: {translate_text(car.car_source_city_name) if car.car_source_city_name else ''}")
    output.append(f"Заголовок: {translate_text(car.title) if car.title else ''}")
    output.append(f"Заголовок (raw): {car.title if car.title else ''}")
    output.append(f"Цена: {decode_sh_price(car.sh_price) if car.sh_price else ''}")
    output.append(f"Ссылка на фото: {car.image}")
    output.append(f"Ссылка на карточку: {car.link}")
    output.append("")
    print("\n".join(output))
