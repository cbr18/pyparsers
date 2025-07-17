import asyncio
from api.che168.parser import Che168Parser
from api.dongchedi.parser import DongchediParser
from converters import decode_dongchedi_list_sh_price

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
        decoded_price = decode_dongchedi_list_sh_price(car.sh_price)
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
    print("CarsParser - Парсер автомобилей")
    print("=" * 50)
    
    # Тестируем Che168 парсер
    print("=== Парсинг Che168 ===")
    try:
        che168_parser = Che168Parser()
        che168_response = che168_parser.fetch_cars()
        
        if che168_response.data and che168_response.data.search_sh_sku_info_list:
            che168_cars = che168_response.data.search_sh_sku_info_list
            print(f"✅ Найдено {len(che168_cars)} машин на Che168")
            
            # Показываем первые 2 машины
            for i, car in enumerate(che168_cars[:2]):
                await print_car_info(car, f"Che168 (машина {i+1})")
        else:
            print("❌ Машины не найдены на Che168")
            
    except Exception as e:
        print(f"❌ Ошибка при парсинге Che168: {e}")
    
    # Тестируем Dongchedi парсер
    print("\n=== Парсинг Dongchedi ===")
    try:
        dongchedi_parser = DongchediParser()
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
