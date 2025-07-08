#!/usr/bin/env python3
"""
Пример использования Selenium парсера Che168
"""

from api.che168fetch import Che168Parser
from translate import translate_text
from converters import decode_sh_price

def main():
    print("🚗 Пример использования Selenium парсера Che168")
    print("=" * 50)
    
    # Создаем парсер с настройками
    parser = Che168Parser(headless=True)  # headless=True для работы в фоне
    
    print("⏳ Запускаем парсинг...")
    
    try:
        # Парсим с сайта
        response = parser.fetch_cars('url')
        
        if response.status == 200 and response.data.search_sh_sku_info_list:
            cars = response.data.search_sh_sku_info_list
            print(f"✅ Успешно найдено {len(cars)} машин")
            
            # Показываем информацию о первых 3 машинах
            for i, car in enumerate(cars[:3]):
                print(f"\n--- Машина {i+1} ---")
                
                if car.brand_name:
                    print(f"Марка: {translate_text(car.brand_name)}")
                if car.car_name:
                    print(f"Модель: {translate_text(car.car_name)}")
                if car.car_year:
                    print(f"Год: {car.car_year}")
                if car.car_mileage:
                    print(f"Пробег: {car.car_mileage} км")
                if car.sh_price:
                    decoded_price = decode_sh_price(car.sh_price)
                    print(f"Цена: {decoded_price}")
                if car.car_source_city_name:
                    print(f"Город: {translate_text(car.car_source_city_name)}")
                if car.title:
                    print(f"Заголовок: {translate_text(car.title)}")
                if car.link:
                    print(f"Ссылка: {car.link}")
                    
        else:
            print(f"❌ Ошибка: {response.message}")
            
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        print("\n💡 Убедитесь, что:")
        print("1. Установлен Chrome браузер")
        print("2. Установлен Selenium: pip install selenium")
        print("3. Скачан chromedriver и добавлен в PATH")

if __name__ == "__main__":
    main()