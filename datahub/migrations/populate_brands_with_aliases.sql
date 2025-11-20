-- Полный список автомобильных брендов с алиасами
-- Используйте INSERT для создания новых записей или UPDATE для существующих
-- Формат: name (английское название), orig_name (китайское/оригинальное), aliases (все варианты через запятую)

-- ============================================
-- НЕМЕЦКИЕ БРЕНДЫ
-- ============================================

-- Mercedes-Benz
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Mercedes-Benz', '奔驰', 
    'Mercedes-Benz,Mercedes,Mercedes Benz,MB,梅赛德斯,梅赛德斯-奔驰,AMG,Maybach,Smart,三叉星',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- BMW
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('BMW', '宝马',
    'BMW,B.M.W.,巴伐利亚,巴伐利亚发动机制造厂,宝马汽车,BMW M,BMW i,MINI,迷你',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Audi
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Audi', '奥迪',
    'Audi,奥迪汽车,四环,四环标志,Audi Sport,RS,S',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Volkswagen
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Volkswagen', '大众',
    'Volkswagen,VW,大众汽车,Volks,People''s Car,大众集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Porsche
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Porsche', '保时捷',
    'Porsche,保时捷汽车,Porsche 911,Porsche Taycan',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Opel
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Opel', '欧宝',
    'Opel,欧宝汽车,Opel Astra,Opel Corsa',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ЯПОНСКИЕ БРЕНДЫ
-- ============================================

-- Toyota
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Toyota', '丰田',
    'Toyota,丰田汽车,Toyota Camry,Toyota Corolla,Toyota Prius,Toyota Land Cruiser,雷克萨斯母公司,Lexus母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Honda
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Honda', '本田',
    'Honda,本田汽车,Honda Civic,Honda Accord,Honda CR-V,Acura母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Nissan
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Nissan', '日产',
    'Nissan,日产汽车,Nissan Altima,Nissan Sentra,Infiniti母公司,Datsun母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Mazda
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Mazda', '马自达',
    'Mazda,马自达汽车,Mazda 3,Mazda 6,Mazda CX-5',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Mitsubishi
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Mitsubishi', '三菱',
    'Mitsubishi,三菱汽车,Mitsubishi Lancer,Mitsubishi Outlander,三菱标志',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Subaru
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Subaru', '斯巴鲁',
    'Subaru,斯巴鲁汽车,Subaru Outback,Subaru Forester,富士重工',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Suzuki
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Suzuki', '铃木',
    'Suzuki,铃木汽车,Suzuki Swift,Suzuki Vitara',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lexus
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lexus', '雷克萨斯',
    'Lexus,雷克萨斯汽车,Lexus ES,Lexus RX,Lexus LS,Toyota高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Acura
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Acura', '讴歌',
    'Acura,讴歌汽车,Acura MDX,Acura TLX,Honda高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Infiniti
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Infiniti', '英菲尼迪',
    'Infiniti,英菲尼迪汽车,Infiniti Q50,Infiniti QX60,Nissan高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- АМЕРИКАНСКИЕ БРЕНДЫ
-- ============================================

-- Ford
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Ford', '福特',
    'Ford,福特汽车,Ford F-150,Ford Mustang,Ford Explorer,Lincoln母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Chevrolet
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Chevrolet', '雪佛兰',
    'Chevrolet,Chevy,雪佛兰汽车,Chevrolet Silverado,Chevrolet Tahoe,GM',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Cadillac
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Cadillac', '凯迪拉克',
    'Cadillac,凯迪拉克汽车,Cadillac Escalade,Cadillac CT5,GM高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Buick
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Buick', '别克',
    'Buick,别克汽车,Buick Enclave,Buick LaCrosse,GM',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- GMC
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('GMC', 'GMC',
    'GMC,GMC Sierra,GMC Yukon,General Motors,通用汽车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Jeep
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Jeep', '吉普',
    'Jeep,吉普汽车,Jeep Wrangler,Jeep Grand Cherokee,Jeep Cherokee',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Dodge
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Dodge', '道奇',
    'Dodge,道奇汽车,Dodge Ram,Dodge Charger,Dodge Challenger',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Chrysler
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Chrysler', '克莱斯勒',
    'Chrysler,克莱斯勒汽车,Chrysler 300,克莱斯勒集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Tesla
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Tesla', '特斯拉',
    'Tesla,特斯拉汽车,Tesla Model 3,Tesla Model S,Tesla Model Y,Tesla Model X',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lincoln
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lincoln', '林肯',
    'Lincoln,林肯汽车,Lincoln Navigator,Lincoln Continental,Ford高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- КОРЕЙСКИЕ БРЕНДЫ
-- ============================================

-- Hyundai
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Hyundai', '现代',
    'Hyundai,现代汽车,Hyundai Sonata,Hyundai Elantra,Hyundai Tucson,Genesis母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Kia
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Kia', '起亚',
    'Kia,起亚汽车,Kia Optima,Kia Sorento,Kia Sportage',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Genesis
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Genesis', '捷尼赛思',
    'Genesis,捷尼赛思汽车,Genesis G70,Genesis G80,Genesis GV80,Hyundai高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- SsangYong
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('SsangYong', '双龙',
    'SsangYong,Ssang Yong,双龙汽车,SsangYong Rexton',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ФРАНЦУЗСКИЕ БРЕНДЫ
-- ============================================

-- Renault
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Renault', '雷诺',
    'Renault,雷诺汽车,Renault Logan,Renault Duster,Nissan联盟',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Peugeot
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Peugeot', '标致',
    'Peugeot,标致汽车,Peugeot 308,Peugeot 3008,PSA',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Citroen
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Citroen', '雪铁龙',
    'Citroen,Citroën,雪铁龙汽车,Citroen C4,PSA',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- DS
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('DS', 'DS',
    'DS,DS Automobiles,DS 7,DS 9,PSA高端品牌,雪铁龙高端',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ИТАЛЬЯНСКИЕ БРЕНДЫ
-- ============================================

-- Ferrari
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Ferrari', '法拉利',
    'Ferrari,法拉利汽车,Ferrari 488,Ferrari F8,Scuderia Ferrari',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lamborghini
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lamborghini', '兰博基尼',
    'Lamborghini,兰博基尼汽车,Lamborghini Aventador,Lamborghini Huracan',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Maserati
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Maserati', '玛莎拉蒂',
    'Maserati,玛莎拉蒂汽车,Maserati Ghibli,Maserati Levante',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Fiat
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Fiat', '菲亚特',
    'Fiat,菲亚特汽车,Fiat 500,Fiat Panda,FCA',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Alfa Romeo
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Alfa Romeo', '阿尔法·罗密欧',
    'Alfa Romeo,Alfa,阿尔法·罗密欧汽车,Alfa Romeo Giulia,Alfa Romeo Stelvio',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lancia
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lancia', '蓝旗亚',
    'Lancia,蓝旗亚汽车,Lancia Delta,FCA',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- БРИТАНСКИЕ БРЕНДЫ
-- ============================================

-- Land Rover
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Land Rover', '路虎',
    'Land Rover,路虎汽车,Land Rover Defender,Land Rover Discovery,Range Rover母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Range Rover
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Range Rover', '揽胜',
    'Range Rover,揽胜汽车,Range Rover Sport,Range Rover Evoque,Land Rover系列',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Jaguar
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Jaguar', '捷豹',
    'Jaguar,捷豹汽车,Jaguar XF,Jaguar F-Pace,JLR',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Aston Martin
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Aston Martin', '阿斯顿·马丁',
    'Aston Martin,阿斯顿·马丁汽车,Aston Martin DB11,Aston Martin Vantage',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Bentley
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Bentley', '宾利',
    'Bentley,宾利汽车,Bentley Continental,Bentley Bentayga',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Rolls-Royce
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Rolls-Royce', '劳斯莱斯',
    'Rolls-Royce,Rolls Royce,RR,劳斯莱斯汽车,Rolls-Royce Phantom,Rolls-Royce Ghost',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Mini
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Mini', '迷你',
    'Mini,迷你汽车,Mini Cooper,Mini Countryman,BMW集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- McLaren
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('McLaren', '迈凯伦',
    'McLaren,迈凯伦汽车,McLaren 720S,McLaren GT',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ШВЕДСКИЕ БРЕНДЫ
-- ============================================

-- Volvo
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Volvo', '沃尔沃',
    'Volvo,沃尔沃汽车,Volvo XC90,Volvo S90,Volvo XC60,吉利集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ЧЕШСКИЕ БРЕНДЫ
-- ============================================

-- Skoda
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Skoda', '斯柯达',
    'Skoda,Škoda,斯柯达汽车,Skoda Octavia,Skoda Kodiaq,大众集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ИСПАНСКИЕ БРЕНДЫ
-- ============================================

-- SEAT
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('SEAT', '西雅特',
    'SEAT,西雅特汽车,SEAT Leon,SEAT Ibiza,大众集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- КИТАЙСКИЕ БРЕНДЫ
-- ============================================

-- BYD
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('BYD', '比亚迪',
    'BYD,比亚迪汽车,BYD Tang,BYD Han,电动车,Build Your Dreams',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Geely
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Geely', '吉利',
    'Geely,吉利汽车,Geely Coolray,Geely Tugella,Volvo母公司,领克母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Great Wall
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Great Wall', '长城',
    'Great Wall,长城汽车,哈弗母公司,Haval母公司,Wey母公司,Tank母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Haval
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Haval', '哈弗',
    'Haval,哈弗汽车,哈弗H6,Haval H6,Haval F7,长城汽车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Chery
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Chery', '奇瑞',
    'Chery,奇瑞汽车,Chery Tiggo,Chery Arrizo,Exeed母公司,Omoda母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Changan
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Changan', '长安',
    'Changan,长安汽车,Changan CS75,Changan UNI-T,长安福特',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- GAC
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('GAC', '广汽',
    'GAC,广汽集团,广汽传祺,GAC Trumpchi,广汽本田,广汽丰田',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- DongFeng
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('DongFeng', '东风',
    'DongFeng,东风汽车,东风日产,东风本田,东风悦达起亚',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Exeed
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Exeed', '星途',
    'Exeed,星途汽车,Exeed TXL,Exeed VX,Chery高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Omoda
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Omoda', '欧萌达',
    'Omoda,欧萌达汽车,Omoda 5,Chery品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Tank
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Tank', '坦克',
    'Tank,坦克汽车,Tank 300,Tank 500,长城汽车高端',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Zeekr
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Zeekr', '极氪',
    'Zeekr,极氪汽车,Zeekr 001,Zeekr 009,吉利高端电动',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Nio
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Nio', '蔚来',
    'Nio,蔚来汽车,Nio ES8,Nio ET7,电动车,蔚来换电',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Xpeng
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Xpeng', '小鹏',
    'Xpeng,Xpeng Motors,小鹏汽车,小鹏P7,小鹏G3,电动车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Li Auto
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Li Auto', '理想',
    'Li Auto,理想汽车,理想ONE,理想L9,增程式电动车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Brilliance
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Brilliance', '华晨',
    'Brilliance,华晨汽车,华晨宝马,华晨中华',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Haima
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Haima', '海马',
    'Haima,海马汽车,Haima S5,Haima 8S',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- JAC
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('JAC', '江淮',
    'JAC,江淮汽车,JAC S3,JAC T8,江淮大众',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lifan
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lifan', '力帆',
    'Lifan,力帆汽车,Lifan X50,Lifan X60',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Zotye
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Zotye', '众泰',
    'Zotye,众泰汽车,Zotye T600,Zotye SR9',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- РОССИЙСКИЕ БРЕНДЫ
-- ============================================

-- Lada
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lada', '拉达',
    'Lada,ВАЗ,拉达汽车,Lada Granta,Lada Vesta,Lada Niva,АвтоВАЗ',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- UAZ
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('UAZ', 'УАЗ',
    'UAZ,УАЗ,乌阿兹,UAZ Patriot,UAZ Hunter,Ульяновский автомобильный завод',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- GAZ
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('GAZ', 'ГАЗ',
    'GAZ,ГАЗ,嘎斯,GAZ Volga,GAZ Gazelle,Горьковский автомобильный завод',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Aurus
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Aurus', '阿鲁斯',
    'Aurus,Аурус,阿鲁斯汽车,Aurus Senat,俄罗斯豪华品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ДРУГИЕ БРЕНДЫ
-- ============================================

-- Bugatti
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Bugatti', '布加迪',
    'Bugatti,布加迪汽车,Bugatti Chiron,Bugatti Veyron,大众集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Maybach
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Maybach', '迈巴赫',
    'Maybach,迈巴赫汽车,Mercedes-Maybach,梅赛德斯-迈巴赫,Mercedes高端',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Smart
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Smart', ' smart',
    'Smart,smart汽车,Smart Fortwo,Smart Forfour,梅赛德斯品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Isuzu
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Isuzu', '五十铃',
    'Isuzu,五十铃汽车,Isuzu D-Max,Isuzu MU-X',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Daihatsu
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Daihatsu', '大发',
    'Daihatsu,大发汽车,Daihatsu Terios,Toyota子公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Datsun
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Datsun', '达特桑',
    'Datsun,达特桑汽车,Datsun GO,Datsun on-Do,Nissan品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Scion
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Scion', '赛恩',
    'Scion,赛恩汽车,Scion FR-S,Toyota品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Hummer
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Hummer', '悍马',
    'Hummer,悍马汽车,Hummer H2,Hummer EV,GMC品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Saab
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Saab', '萨博',
    'Saab,萨博汽车,Saab 9-3,Saab 9-5',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Rover
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Rover', '罗孚',
    'Rover,罗孚汽车,Rover 75,MG Rover',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Daewoo
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Daewoo', '大宇',
    'Daewoo,大宇汽车,Daewoo Matiz,Daewoo Nexia,GM Korea',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Ravon
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Ravon', '拉翁',
    'Ravon,拉翁汽车,Ravon Nexia,GM Uzbekistan',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ZAZ
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('ZAZ', 'ЗАЗ',
    'ZAZ,ЗАЗ,扎波罗热,Запорожский автомобильный завод',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ОБНОВЛЕНИЕ СУЩЕСТВУЮЩИХ БРЕНДОВ (если нужно обновить алиасы)
-- ============================================

-- Если бренды уже существуют, можно использовать UPDATE:
-- UPDATE brands SET aliases = 'новые_алиасы', updated_at = NOW() WHERE name = 'Brand Name';

-- ============================================
-- ПРОВЕРКА РЕЗУЛЬТАТА
-- ============================================

-- Посмотреть все созданные бренды с алиасами
-- SELECT name, orig_name, aliases FROM brands WHERE deleted_at IS NULL ORDER BY name;





