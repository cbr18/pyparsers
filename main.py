from api.parser_factory import ParserFactory
from translate import translate_text
from converters import decode_sh_price

def print_car_info(car, source_name="Unknown"):
    """Универсальная функция для вывода информации о машине"""
    output = []
    output.append("-" * 50)
    output.append(f"Источник: {source_name}")
    output.append("-" * 50)
    
    # Основная информация
    if car.brand_name:
        output.append(f"Марка: {translate_text(car.brand_name)}")
    if car.car_name:
        output.append(f"Модель: {translate_text(car.car_name)}")
    if car.series_name:
        output.append(f"Серия: {translate_text(car.series_name)}")
    if car.car_year:
        output.append(f"Год: {car.car_year}")
    if car.car_source_city_name:
        output.append(f"Город: {translate_text(car.car_source_city_name)}")
    if car.car_mileage:
        output.append(f"Пробег: {car.car_mileage} км")
    
    # Цена
    if car.sh_price:
        decoded_price = decode_sh_price(car.sh_price)
        output.append(f"Цена: {decoded_price}")
    
    # Заголовок
    if car.title:
        output.append(f"Заголовок: {translate_text(car.title)}")
    
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

def main():
    """Основная функция для работы с парсерами"""
    print("CarsParser - Парсер автомобилей с Selenium")
    print("=" * 50)
    
    # Получаем доступные парсеры
    available_parsers = ParserFactory.get_available_parsers()
    print(f"Доступные парсеры: {available_parsers}")
    print()
    
    # Тестируем Che168 парсер с локальным файлом (быстрое тестирование)
    print("=== Парсинг Che168 с локального файла ===")
    try:
        parser = ParserFactory.get_parser('che168')
        response = parser.fetch_cars('local')  # Используем локальный файл для быстрого тестирования
        
        if response.data and response.data.search_sh_sku_info_list:
            cars = response.data.search_sh_sku_info_list
            print(f"✅ Успешно найдено {len(cars)} машин")
            
            # Показываем первые 3 машины
            for i, car in enumerate(cars[:3]):
                print_car_info(car, f"Che168 Local (машина {i+1})")
                
            # Статистика
            print(f"\n📊 Статистика:")
            years = {}
            prices = []
            
            for car in cars:
                if car.car_year:
                    years[car.car_year] = years.get(car.car_year, 0) + 1
                if car.sh_price:
                    try:
                        price = float(car.sh_price)
                        prices.append(price)
                    except:
                        pass
            
            if years:
                print(f"Годы выпуска: {sorted(years.keys())}")
            if prices:
                avg_price = sum(prices) / len(prices)
                print(f"Средняя цена: {avg_price:.2f} млн юаней")
                
        else:
            print("❌ Машины не найдены")
            
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
    
    # Тестируем Dongchedi парсер
    print("\n=== Парсинг Dongchedi ===")
    try:
        dongchedi_parser = ParserFactory.get_parser('dongchedi')
        dongchedi_response = dongchedi_parser.fetch_cars()
        
        if dongchedi_response.data and dongchedi_response.data.search_sh_sku_info_list:
            dongchedi_cars = dongchedi_response.data.search_sh_sku_info_list
            print(f"✅ Найдено {len(dongchedi_cars)} машин на Dongchedi")
            
            # Показываем первые 2 машины
            for i, car in enumerate(dongchedi_cars[:2]):
                print_car_info(car, f"Dongchedi (машина {i+1})")
        else:
            print("❌ Машины не найдены на Dongchedi")
            
    except Exception as e:
        print(f"❌ Ошибка при парсинге Dongchedi: {e}")
    
    print("\n" + "="*60)
    print("💡 Для тестирования Selenium парсера:")
    print("1. Убедитесь, что установлен Chrome браузер")
    print("2. Скачайте ChromeDriver с https://chromedriver.chromium.org/")
    print("3. Добавьте ChromeDriver в PATH")
    print("4. Запустите: python examples/selenium_usage.py")

if __name__ == "__main__":
    main()
