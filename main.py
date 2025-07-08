import asyncio
from api.parser_factory import ParserFactory
from converters import decode_sh_price

async def print_car_info(car, source_name="Unknown"):
    """Универсальная функция для вывода информации о машине"""
    output = []
    output.append("-" * 50)
    output.append(f"Источник: {source_name}")
    output.append("-" * 50)
    
    # Основная информация
    if car.brand_name:
        output.append(f"Марка: {car.brand_name}")
    if car.car_name:
        output.append(f"Модель: {car.car_name}")
    if car.series_name:
        output.append(f"Серия: {car.series_name}")
    if car.car_year:
        output.append(f"Год: {car.car_year}")
    if car.car_source_city_name:
        output.append(f"Город: {car.car_source_city_name}")
    if car.car_mileage:
        output.append(f"Пробег: {car.car_mileage} км")
    
    # Цена
    if car.sh_price:
        decoded_price = decode_sh_price(car.sh_price)
        output.append(f"Цена: {decoded_price}")
    
    # Заголовок
    if car.title:
        output.append(f"Заголовок: {car.title}")
    
    # Ссылки
    if car.image:
        output.append(f"Фото: {car.image}")
    if car.link:
        output.append(f"Ссылка: {car.link}")
    
    # Дополнительная информация
    if car.tags_v2:
        output.append(f"Теги: {car.tags_v2}")
    
    output.append("")
    print("\n".join(output))

async def main():
    """Основная функция для работы с парсерами"""
    print("CarsParser - Парсер автомобилей (Dongchedi)")
    print("=" * 50)
    
    # Получаем доступные парсеры
    available_parsers = ParserFactory.get_available_parsers()
    print(f"Доступные парсеры: {available_parsers}")
    print()
    
    # Тестируем Dongchedi парсер
    print("=== Парсинг Dongchedi ===")
    try:
        dongchedi_parser = ParserFactory.get_parser('dongchedi')
        dongchedi_response = dongchedi_parser.fetch_cars()
        
        if dongchedi_response.data and dongchedi_response.data.search_sh_sku_info_list:
            dongchedi_cars = dongchedi_response.data.search_sh_sku_info_list
            print(f"✅ Найдено {len(dongchedi_cars)} машин на Dongchedi")
            
            # Показываем первые 2 машины
            for i, car in enumerate(dongchedi_cars[:2]):
                await print_car_info(car, f"Dongchedi (машина {i+1})")
        else:
            print("❌ Машины не найдены на Dongchedi")
            
    except Exception as e:
        print(f"❌ Ошибка при парсинге Dongchedi: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())
