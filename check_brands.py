#!/usr/bin/env python3
# Скрипт для проверки покрытия брендов

# Оригинальный список брендов из сообщения пользователя
original_brands_raw = """BMW	BMW
Porsche	Porsche
Volkswagen	Volkswagen
Lincoln	Lincoln
Renault	Renault
Chang'an	Chang'an
Audi	Audi
Roewe	Roewe
GAC Trumpchi	GAC Trumpchi
Tesla	Tesla
Wei Pai	Wei Pai
Extremely krypton	Extremely krypton
Buick	Buick
Volvo	Volvo
Chery	Chery
Toyota	Toyota
Jetta	Jetta
Subaru	Subaru
Mercedes-Benz	Mercedes-Benz
Ford	Ford
Dongfeng popular	Dongfeng popular
Haval	Haval
BYD	BYD
Xiaopeng Motors	Xiaopeng Motors
Jeep	Jeep
Alfa Romeo	Alfa Romeo
Red flag	Red flag
Wuling Automobile	Wuling Automobile
Geely Automobile	Geely Automobile
Honda	Honda
Nissan	Nissan
Euler	Euler
Ideal car	Ideal car
Cadillac	Cadillac
Lynk	Lynk
Land Rover	Land Rover
MINI	MINI
Great Wall	Great Wall
Mitsubishi	Mitsubishi
Lan Tu	Lan Tu
Happy Road	Happy Road
Citroen	Citroen
modern	modern
Nezha Automobile	Nezha Automobile
Denza	Denza
Leopard	Leopard
Intellectual world	Intellectual world
tank	tank
Zero-running car	Zero-running car
AITO	AITO"""

# Уникальные бренды (исключая модели)
unique_brands = set()

for line in original_brands_raw.strip().split('\n'):
    if '\t' in line:
        name, orig_name = line.split('\t', 1)
        # Базовое название бренда (без моделей)
        base_name = name.split()[0] if ' ' in name else name
        unique_brands.add(base_name.strip())

print(f"Уникальных базовых брендов в оригинальном списке: {len(unique_brands)}")
print(f"\nСписок:\n{sorted(unique_brands)}")


