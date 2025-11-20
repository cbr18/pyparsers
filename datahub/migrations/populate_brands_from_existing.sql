-- SQL скрипт для заполнения таблицы brands со всеми брендами и их алиасами
-- Создан на основе существующих брендов в базе данных

-- ============================================
-- НЕМЕЦКИЕ БРЕНДЫ
-- ============================================

-- BMW - все модели BMW
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('BMW', '宝马',
    'BMW,宝马,B.M.W.,巴伐利亚,BMW 5 Series,BMW X2,BMW X5,BMW X3,BMW X7,BMW 3 Series,BMW 2 Series,BMW 7 Series,BMW 4 Series,BMW 1 Series,BMW M3,BMW M4,BMW M5,BMW M2,BMW Z4,BMW X6,BMW X4,BMW iX3,BMW i3,BMW i4,BMW i5,BMW iX,BMW M235L,BMW X1,宝马5系,宝马X2,宝马X5,宝马X3,宝马X7,宝马3系,宝马2系,宝马7系,宝马4系,宝马1系,宝马M3,宝马M4,宝马M5,宝马M2,宝马Z4,宝马X6,宝马X4',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Mercedes-Benz - все модели Mercedes
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Mercedes-Benz', '奔驰',
    'Mercedes-Benz,Mercedes,Mercedes Benz,MB,奔驰,梅赛德斯,AMG,Maybach,Maybach S-class,Maybach GLS,Mercedes-Benz C-class,Mercedes-Benz A-class,Mercedes-Benz E-class,Mercedes-Benz S-class,Mercedes-Benz G-class,Mercedes-Benz GLE,Mercedes-Benz GLS,Mercedes-Benz GLC,Mercedes-Benz GLB,Mercedes-Benz CLA,Mercedes-Benz V-class,Mercedes-Benz R-class,Mercedes-Benz B-class,Mercedes-Benz EQE,Mercedes-Benz EQC,Mercedes-Benz EQA,Mercedes-Benz EQB,Mercedes-Benz EQS,Mercedes-Benz CLE,Mercedes-Benz SLC,奔驰C级,奔驰A级,奔驰E级,奔驰S级,奔驰G级,奔驰GLE,奔驰GLS,奔驰GLC,奔驰GLB,奔驰CLA,奔驰V级,奔驰R级,奔驰B级,奔驰EQE,奔驰EQC,奔驰EQA,奔驰EQB,奔驰EQS,奔驰CLE,奔驰SLC,迈巴赫,迈巴赫S级,迈巴赫GLS',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Audi - все модели Audi
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Audi', '奥迪',
    'Audi,奥迪,Audi A3,Audi A4,Audi A5,Audi A6,Audi A7,Audi A8,Audi Q3,Audi Q4,Audi Q5,Audi Q6,Audi Q7,Audi Q8,Audi S3,Audi S4,Audi S5,Audi S8,Audi SQ7,Audi TT,Audi R8,Audi A6L,Audi A4L,Audi A5L,Audi A7L,Audi Q5L,Audi Q2L,Audi e-tron,Audi RS,奥迪A3,奥迪A4,奥迪A5,奥迪A6,奥迪A7,奥迪A8,奥迪Q3,奥迪Q4,奥迪Q5,奥迪Q6,奥迪Q7,奥迪Q8',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Volkswagen - все модели VW
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Volkswagen', '大众',
    'Volkswagen,VW,大众,Jetta,捷达,Jetta VA3,Jetta VA7,Jetta VS5,ID.4,ID.6,ID.3,Volkswagen ID.7,Passat,帕萨特,Tiguan,途观,Tiguan L,途观L,Tiguan X,途观X,Tuyue,途岳,Tanyue,探岳,Tanyue X,探岳X,Tanyue GTE,探岳GTE,Touran,途安,Tourao,途锐,Tourang,途昂,Explore,探界者,Sagitar,速腾,Bora,宝来,Lavida,朗逸,Lingdu,凌渡,Polo,Polo,Touruiou,途锐欧,Santana,桑塔纳,Beetle,甲壳虫,Golf,高尔夫,Golf GTI,高尔夫GTI',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Porsche - все модели Porsche
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Porsche', '保时捷',
    'Porsche,保时捷,Porsche 911,保时捷911,Cayenne,卡宴,Macan,Macan,Panamera,Panamera New Energy,Taycan,保时捷911,保时捷718,保时捷卡宴,保时捷Macan,保时捷Panamera,保时捷Taycan',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- MINI
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('MINI', 'MINI',
    'MINI,Mini,迷你,MINI Cooper,迷你Cooper,Electric MINI,电动MINI,BMW集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- smart
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('smart', 'smart',
    'smart,smart汽车,smart Wizard#1,smart精灵#1,smart Wizard#3,smart精灵#3,smart Wizard#5,smart精灵#5,梅赛德斯品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Skoda
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Skoda', '斯柯达',
    'Skoda,Škoda,斯柯达,Octavia,明锐,Krok,柯珞克,Kodiak,柯迪亚克,Kodiak GT,Yeti,Yeti,大众集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ЯПОНСКИЕ БРЕНДЫ
-- ============================================

-- Toyota
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Toyota', '丰田',
    'Toyota,丰田,Camry,凯美瑞,Corolla,卡罗拉,RAV4 Rongfang,RAV4荣放,Highlander,汉兰达,Crown Lufang,皇冠陆放,Crown Road,冠道,crown,皇冠,C-HR,Toyota C-HR,Corolla Sharp amplifier,卡罗拉锐放,Asian dragon,亚洲龙,Asian lion,亚洲狮,YARiS,Prado,普拉多,Land Cruiser,兰德酷路泽,Sienna,赛那SIENNA,SIENNA,bZ3,bZ5,Toyota bZ3,Toyota bZ5,TIIDA,骐达,Wilanda,威兰达,Wilfa,威尔法,Elfa,埃尔法,Lexus母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Honda
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Honda', '本田',
    'Honda,本田,Accord,雅阁,Civic,思域,CR-V,本田CR-V,UR-V,本田UR-V,XR-V,本田XR-V,HR-V,本田HR-V,Fit,飞度,Odyssey,奥德赛,Ai Lishen,艾力绅,Yingshipai,英仕派,LIFE,Honda e:NS1,e:NP1,e:NP2,eπ007,eπ008,Dongfeng Honda,东风本田,Guangqi Honda,广汽本田',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Nissan
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Nissan', '日产',
    'Nissan,日产,Teana,天籁,Sylphy,轩逸,Xuan Yi,轩逸,Qashqai,逍客,TIIDA,骐达,Loulan,楼兰,Patrol,途乐,Toure,途乐,Nissan N7,日产N7,Infiniti母公司,Datsun母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Mazda
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Mazda', '马自达',
    'Mazda,马自达,Mazda 3,马自达3,Mazda CX-5,马自达CX-5,Mazda CX-8,马自达CX-8,Mazda CX-4,马自达CX-4,Mazda CX-50 Xingya,马自达CX-50行也,Mazda MX-5,马自达MX-5,Atez,阿特兹',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Mitsubishi
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Mitsubishi', '三菱',
    'Mitsubishi,三菱,Pajero,帕杰罗,Outlander,欧蓝德,Jinxuan ASX,劲炫ASX,ASX',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Subaru
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Subaru', '斯巴鲁',
    'Subaru,斯巴鲁,Forester,森林人,Outback,傲虎',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Suzuki
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Suzuki', '铃木',
    'Suzuki,铃木,Swift,雨燕,Vitra,维特拉,Jimny,吉姆尼',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lexus
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lexus', '雷克萨斯',
    'Lexus,雷克萨斯,Lexus ES,Lexus RX,Lexus LS,Lexus NX,Lexus UX,Lexus GX,Lexus LX,Lexus IS,Lexus GS,Lexus CT,Lexus RZ,Lexus LM,Toyota高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Acura
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Acura', '讴歌',
    'Acura,讴歌,Acura CDX,讴歌CDX,Acura RDX,讴歌RDX,Honda高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Infiniti
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Infiniti', '英菲尼迪',
    'Infiniti,英菲尼迪,Infiniti Q50,英菲尼迪Q50,Infiniti Q50L,Infiniti Q60,Infiniti QX30,Infiniti QX50,Infiniti QX60,Infiniti QX80,Infiniti ESQ,Infiniti Q70,Nissan高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- АМЕРИКАНСКИЕ БРЕНДЫ
-- ============================================

-- Ford
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Ford', '福特',
    'Ford,福特,Ford Mustang,福特Mustang,福特烈马,Ford F-150,福特F-150,Ford F-150 Raptor,福特F-150猛禽,Ford electric Horse,福特电动马,Explorer,探险者,Explorer Plus,探索者Plus,Explorer 06,探索06,Explorer Plus,探索者Plus,Edge,锐界,Sharp World,锐界,Territory,领界,Ruiji,锐际,Mondeo,蒙迪欧,Focus,福克斯,Fox,福克斯,Regal,君威,Fiesta,菲斯塔,Escort,福睿斯,Forrest,福睿斯,Changan Ford,长安福特,Lincoln母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Chevrolet
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Chevrolet', '雪佛兰',
    'Chevrolet,Chevy,雪佛兰,Cruze,科鲁泽,Kovoz,科沃兹,Blazer,开拓者,Traverse,Trailblazer,开拓者,Malibu,迈锐宝,Mai Ruibao,迈锐宝,Mai Ruibao XL,迈锐宝XL,Equinox,探界者,Tahoe,GM',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Cadillac
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Cadillac', '凯迪拉克',
    'Cadillac,凯迪拉克,Cadillac Escalade,凯迪拉克Escalade,Escalade ESCALADE,Cadillac CT5,凯迪拉克CT5,Cadillac CT6,凯迪拉克CT6,Cadillac CT4,凯迪拉克CT4,Cadillac XTS,凯迪拉克XTS,Cadillac XT4,凯迪拉克XT4,Cadillac XT5,凯迪拉克XT5,Cadillac XT6,凯迪拉克XT6,Cadillac ATS-L,凯迪拉克ATS-L,GM高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Buick
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Buick', '别克',
    'Buick,别克,Buick GL8,别克GL8,Buick GL6,别克GL6,Regal,君威,Lacrosse,君越,Excelle,英朗,Yinglang,英朗,Angkewei,昂科威,Angkewei S,昂科威S,Angkewei Plus,昂科威Plus,Angke Flag,昂科旗,Angkola,昂科拉,Angkola GX,昂科拉GX,VELITE,GM',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- GMC
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('GMC', 'GMC',
    'GMC,GMC Sierra,GMC Yukon,General Motors,通用汽车,Hummer,悍马',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Jeep
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Jeep', '吉普',
    'Jeep,吉普,Jeep Wrangler,吉普Wrangler,Wrangler,牧马人,Grand Cherokee,大切诺基,Grand Commander,大指挥官,Guide,指南者,Free light,自由光,Freeman,自由侠,Challenger,挑战者,Gladiator,角斗士',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Dodge
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Dodge', '道奇',
    'Dodge,道奇,Dodge Ram,Dodge Charger,Dodge Challenger,RAM',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Chrysler
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Chrysler', '克莱斯勒',
    'Chrysler,克莱斯勒,Chrysler 300C,克莱斯勒300C,克莱斯勒集团',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Tesla
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Tesla', '特斯拉',
    'Tesla,特斯拉,Tesla Model 3,Tesla Model S,Tesla Model Y,Tesla Model X,Model,特斯拉Model 3,特斯拉Model S,特斯拉Model Y,特斯拉Model X',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lincoln
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lincoln', '林肯',
    'Lincoln,林肯,Lincoln Navigator,林肯Navigator,Navigator,领航员,Navigator (import),领航员(进口),Lincoln Continental,林肯Continental,Lincoln Z,林肯Z,Lincoln MKC,林肯MKC,Lincoln MKX,林肯MKX,Flying Home,飞行家,Flying Home (imported),飞行家(进口),Adventurer,冒险家,Ford高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- КОРЕЙСКИЕ БРЕНДЫ
-- ============================================

-- Hyundai
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('modern', '现代',
    'Hyundai,modern,现代,Hyundai Sonata,现代Sonata,Sonata,索纳塔,Hyundai Elantra,现代Elantra,Elantra,伊兰特,Hyundai Tucson,现代Tucson,Tucson,途胜,Beijing Hyundai,北京现代,Genesis母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Kia
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Kia', '起亚',
    'Kia,起亚,Kia K2,起亚K2,Kia K3,起亚K3,Kia K4,起亚K4,Kia K5,起亚K5,KX3,KX5,Kia KX5,Kia KX7,Stinger,斯汀格,Smart running,智跑,KX,奕跑,Yi Ran,奕跑,ZR-V',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Genesis
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Genisys', '捷尼赛思',
    'Genesis,Genisys,捷尼赛思,Genesis G70,Genesis G80,Genesis GV80,Genisys G90,Hyundai高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ФРАНЦУЗСКИЕ БРЕНДЫ
-- ============================================

-- Renault
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Renault', '雷诺',
    'Renault,雷诺,Coreo,科雷傲,Granvia,格瑞维亚,Nissan联盟',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Peugeot
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Peugeot', '标致',
    'Peugeot,标致,Peugeot 301,标致301,Peugeot 2008,标致2008,Peugeot 3008,标致3008,Peugeot 308,标致308,Peugeot 4008,标致4008,Peugeot 408,标致408,Peugeot 5008,标致5008,Peugeot 508,标致508,Peugeot 508L,标致508L,PSA',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Citroen
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Citroen', '雪铁龙',
    'Citroen,Citroën,雪铁龙,Citroen C3-XR,雪铁龙C3-XR,Citroen C4,雪铁龙C4,Citroen C5,雪铁龙C5,Citroen C6,雪铁龙C6,C4,C4 Sega,C4世嘉,Tianyi,天逸,C5 X,Versailles C5,凡尔赛C5,PSA',
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
    'Ferrari,法拉利,Ferrari 488,法拉利488,Ferrari F8,法拉利F8,SF90,SF90XX,Ferrari 296,法拉利296,Roma,Scuderia Ferrari',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lamborghini
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lamborghini', '兰博基尼',
    'Lamborghini,兰博基尼,Lamborghini Aventador,兰博基尼Aventador,Lamborghini Huracan,兰博基尼Huracan,Huracán,Huracán,Revuelto',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Maserati
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Maserati', '玛莎拉蒂',
    'Maserati,玛莎拉蒂,Maserati Ghibli,玛莎拉蒂Ghibli,Ghibli,Maserati Levante,玛莎拉蒂Levante,Levante,Maserati MC20,玛莎拉蒂MC20',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Alfa Romeo
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Alfa Romeo', '阿尔法·罗密欧',
    'Alfa Romeo,Alfa,阿尔法·罗密欧,Alfa Romeo Giulia,阿尔法·罗密欧Giulia,Giulia,朱丽叶,Alfa Romeo Stelvio,阿尔法·罗密欧Stelvio,Stelvio,斯坦维',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- БРИТАНСКИЕ БРЕНДЫ
-- ============================================

-- Land Rover
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Land Rover', '路虎',
    'Land Rover,路虎,Land Rover Defender,路虎卫士,Range Rover,揽胜,Range Rover Sport,揽胜运动,Range Rover Star Pulse,揽胜星脉,Range Rover Aurora,揽胜极光,Range patrol,揽巡,Discover,发现,Discover Shenxing,发现神行,Discover sports,发现运动,JLR',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Jaguar
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Jaguar', '捷豹',
    'Jaguar,捷豹,Jaguar XF,捷豹XF,Jaguar XFL,捷豹XFL,Jaguar XJ,捷豹XJ,Jaguar XE,捷豹XE,Jaguar XEL,捷豹XEL,Jaguar F-TYPE,捷豹F-TYPE,Jaguar E-PACE,捷豹E-PACE,Jaguar F-PACE,捷豹F-PACE,JLR',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Aston Martin
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Aston Martin', '阿斯顿·马丁',
    'Aston Martin,阿斯顿·马丁,Aston Martin DB11,阿斯顿·马丁DB11,Aston Martin DBS,阿斯顿·马丁DBS,Aston Martin DBX,阿斯顿·马丁DBX,Aston Martin Vantage,阿斯顿·马丁Vantage',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Bentley
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Bentley', '宾利',
    'Bentley,宾利,Bentley Continental,宾利Continental,Bentley Bentayga,宾利Bentayga,Tim Yue,添越,Continental,欧陆,Flying,飞驰',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Rolls-Royce
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Rolls-Royce', '劳斯莱斯',
    'Rolls-Royce,Rolls Royce,RR,劳斯莱斯,Rolls-Royce Phantom,劳斯莱斯Phantom,Phantom,魅影,Rolls-Royce Ghost,劳斯莱斯Ghost,Gust,古思特,Cullinan,库里南',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- McLaren
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('McLaren', '迈凯伦',
    'McLaren,迈凯伦,McLaren 720S,迈凯伦720S,McLaren 650S,迈凯伦650S,McLaren 570,迈凯伦570,McLaren 600LT,迈凯伦600LT,McLaren 540C,迈凯伦540C,McLaren GT,迈凯伦GT',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lotus Sports Car
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lotus Sports Car', '莲花跑车',
    'Lotus,Lotus Sports Car,莲花,Lotus跑车,EMIRA',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ШВЕДСКИЕ БРЕНДЫ
-- ============================================

-- Volvo
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Volvo', '沃尔沃',
    'Volvo,沃尔沃,Volvo XC90,沃尔沃XC90,Volvo S90,沃尔沃S90,Volvo XC60,沃尔沃XC60,Volvo S60,沃尔沃S60,Volvo V60,沃尔沃V60,Volvo V90,沃尔沃V90,Volvo XC40,沃尔沃XC40,Volvo V40,沃尔沃V40,Volvo EM90,沃尔沃EM90,吉利集团,Polestar,极星',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- КИТАЙСКИЕ БРЕНДЫ
-- ============================================

-- BYD
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('BYD', '比亚迪',
    'BYD,比亚迪,BYD Tang,比亚迪唐,Tang,唐,Tang L,唐L,BYD Han,比亚迪汉,Han,汉,Han L,汉L,BYD F3,比亚迪F3,BYD F0,比亚迪F0,BYD S7,比亚迪S7,BYD e2,比亚迪e2,BYD e5,比亚迪e5,Seal,海豹,Seal 05,海豹05,Seal 06,海豹06,Seal 07,海豹07,Seal 06GT,Seal 06 New Energy,海豹06新能源,Dolphin EV,海豚,dolphin,海豚,Yuan,元,Yuan PLUS,元PLUS,Yuan Pro,元Pro,Yuan UP,元UP,Yuanxin Energy,元新能源,Qin,秦,Qin PLUS,秦PLUS,Qin Yuan,秦PLUS,Qin L,秦L,Qinxin Energy,秦新能源,Qing Dynasty,秦王朝,Song,宋,Song Pro,宋Pro,Song PLUS,宋PLUS,Songyuan New Energy,宋PLUS新能源,Songjiang New Energy,宋Pro新能源,Song MAX,宋MAX,Song L,宋L,电动车,Build Your Dreams',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Geely Automobile
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Geely Automobile', '吉利汽车',
    'Geely,Geely Automobile,吉利,吉利汽车,Emgrand,帝豪,Emgrand GS,帝豪GS,Emgrand S,帝豪S,Emgrand L,Emgrand GL,帝豪GL,Emgrand New Energy,帝豪新能源,Emgrand GSe,Emgrand GSe,帝豪GSe,Boyue,博越,Boyue L,博越L,Vision,远景,Vision X3,远景X3,Vision X6,远景X6,Vision X1,远景X1,Vision S1,远景S1,Xingrui,星瑞,Xingyue,星越,Xingyue L,星越L,Xingyue L Extended Range,星越L增程,Xingyue S,Xingyue New Energy,星越新能源,Binrui,缤瑞,Binyue,缤越,Binyue New Energy,缤越新能源,Geely ICON,吉利ICON,Geely Galaxy,吉利银河,Galaxy L7,银河L7,Galaxy L6,银河L6,Galaxy E8,银河E8,Galaxy E5,银河E5,Galaxy Sparkle 6,银河星耀6,Galaxy Sparkle 7,银河星耀7,Galaxy Sparkle 8,银河星耀8,Galaxy Starship 7,银河星舰7,Geely Geometry,吉利几何,Geely Geometry E Firefly,吉利几何E萤火虫,firefly firefly,萤火虫,Geely Geometry C,吉利几何C,Geely Geometry G6,吉利几何G6,Geely Geometry A,吉利几何A,Geely Radar Horizon,吉利雷达地平线,Volvo母公司,Lynk母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Great Wall
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Great Wall', '长城',
    'Great Wall,Great Wall,长城,长城汽车,Haval母公司,Wey母公司,Tank母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Haval
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Haval', '哈弗',
    'Haval,哈弗,Haval H6,哈弗H6,Haval H5,哈弗H5,Haval H5 Classic,哈弗H5经典,Haval H4,哈弗H4,Haval H2,哈弗H2,Haval H2s,哈弗H2s,Haval H1,哈弗H1,Haval H7,哈弗H7,Haval H8,哈弗H8,Haval H9,哈弗H9,Haval M6,哈弗M6,Haval F5,Haval F7,哈弗F7,Haval Red Rabbit,哈弗赤兔,Haval Big Dog,哈弗大狗,Haval Cool Dog,哈弗酷狗,Haval Beast,哈弗神兽,Haval''s first love,哈弗初恋,Haval Xiaolong MAX,哈弗小龙MAX,Haval Raptors Fuel,哈弗猛龙燃油,Haval Raptors New Energy,哈弗猛龙新能源,长城汽车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Tank
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('tank', '坦克',
    'Tank,tank,坦克,Tank 300,坦克300,Tank 300 New energy,坦克300新能源,Tank 400,坦克400,Tank 400 New energy,坦克400新能源,Tank 500,坦克500,Tank 500 New energy,坦克500新能源,Tank 700 New energy,坦克700新能源,Leopard,豹,Leopard 5,豹5,Leopard 8,豹8,Co-creation tank 300,共创坦克300,长城汽车高端',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Chery
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Chery', '奇瑞',
    'Chery,奇瑞,Chery Tiggo,奇瑞Tiggo,Tiggo 8,瑞虎8,Tiggo 8L,瑞虎8L,Tiggo 7,瑞虎7,Tiggo 5x,瑞虎5x,Tiggo 3x,瑞虎3x,Tiggo 3xe,Tiggo 9,瑞虎9,Arrizo 5,艾瑞泽5,Arrizo 8,艾瑞泽8,Arrizo GX,艾瑞泽GX,Arrizo e,QQ ice cream,QQ冰淇淋,Little ant,小蚂蚁,Chery Fengyun,奇瑞风云,Chery New Energy,奇瑞新能源,Fengyun T9,风云T9,Fengyun A8L,风云A8L,Exeed母公司,Omoda母公司',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Chang'an
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Chang''an', '长安',
    'Changan,Chang''an,长安,Changan CS75,长安CS75,Changan CS75PLUS,长安CS75PLUS,Changan CS75 New Energy,长安CS75新能源,Changan CS35,长安CS35,Changan CS35PLUS,长安CS35PLUS,Changan CS15,长安CS15,Changan CS15EV,长安CS15EV,Changan CS55,长安CS55,Changan CS55PLUS,长安CS55PLUS,Changan CS85,长安CS85,Changan CS95,长安CS95,Changan UNI-T,长安UNI-T,Changan UNI-K,长安UNI-K,Changan UNI-V,长安UNI-V,Changan UNI-Z,长安UNI-Z,Changan UNI-Z New Energy,长安UNI-Z新能源,Yidong,逸动,Yidong DT,逸动DT,Yidong New Energy,逸动新能源,Yuexiang,悦翔,Yuexiang V3,悦翔V3,Changan Benben E-Star,长安奔奔E-Star,Changan Lumin,长安Lumin,Changan Auchan,长安欧尚,Changan Auchan A600,长安欧尚A600,Changan Auchan A800,长安欧尚A800,Changan Auchan A600EV,Changan Auchan Cosai 5,长安欧尚科赛5,Changan Auchan X5,长安欧尚X5,Changan Auchan X7,长安欧尚X7,Changan Auchan X70A,长安欧尚X70A,Changan Auchan Z6,长安欧尚Z6,Changan Qiyuan,长安启源,Changan Qiyuan A05,长安启源A05,Changan Qiyuan A07,长安启源A07,Changan Qiyuan Q07,长安启源Q07,Changan Qiyuan E07,长安启源E07,Changan Kaicheng,长安凯程,Changan Shenqi T30,长安神骐T30,Changan Shenqi T20,长安神骐T20,Changan Shenqi F30,长安神骐F30,Changan Ruixing S50,长安睿行S50,Changan Ruixing M60,长安睿行M60,Changan Ruixing M90,长安睿行M90,Changan Ruixing EM80,长安睿行EM80,Changan X5,长安X5,Changan X7,长安X7,Changan Star 5,长安之星5,长安福特,Changan Ford',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- GAC Trumpchi
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('GAC Trumpchi', '广汽传祺',
    'GAC Trumpchi,GAC Trumpchi,广汽传祺,传祺,Trumpchi GS3,传祺GS3,Trumpchi GS4,传祺GS4,Trumpchi GS4 New Energy,传祺GS4新能源,Trumpchi GS5,传祺GS5,Trumpchi GS8,传祺GS8,Trumpchi GA4,传祺GA4,Trumpchi GA6,传祺GA6,Trumpchi GA8,传祺GA8,Trumpchi M6,传祺M6,Trumpchi M8,传祺M8,Trumpchi E9,传祺E9,Trumpchi ES9,传祺ES9,Trumpchi Yearning for S7,传祺向往S7,GAC Group,广汽集团,广汽本田,广汽丰田',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Dongfeng Fengshen
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Dongfeng Fengshen', '东风风神',
    'Dongfeng Fengshen,Dongfeng Fengshen,东风风神,东风风度,Dongfeng Fengshen AX4,东风风神AX4,Dongfeng Fengshen AX5,东风风神AX5,Dongfeng Fengshen AX7,东风风神AX7,Dongfeng Fengshen E70,东风风神E70,Dongfeng Fengshen L7,东风风神L7,东风奕派,Dongfeng Yipai,eπ007,eπ008,eπ007,eπ008',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Dongfeng popular
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Dongfeng popular', '东风风行',
    'Dongfeng popular,Dongfeng popular,东风风行,Dongfeng Fengshen,东风风行,Scenery,风光,Scenery 330,风光330,Scenery 370,风光370,Scenery 380,风光380,Scenery 500,风光500,Scenery 580,风光580,Scenery 580Pro,风光580Pro,Scenery S560,风光S560,Scenery ix5,风光ix5',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Dongfeng
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Dongfeng', '东风',
    'Dongfeng,东风,东风汽车,东风日产,东风本田,东风悦达起亚,东风小康,Dongfeng Xiaokang,东风小康,Dongfeng Xiaokang K05S,Dongfeng Xiaokang C31,Dongfeng Xiaokang,Dongfeng Nano,东风纳米,Dongfeng Nano EX1,东风纳米EX1,Nano BOX,Nano 01,东风奕派',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Roewe
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Roewe', '荣威',
    'Roewe,荣威,Roewe RX5,荣威RX5,Roewe RX5 New Energy,荣威RX5新能源,Roewe RX8,荣威RX8,Roewe RX3,荣威RX3,Roewe i5,荣威i5,Roewe i6,荣威i6,Roewe i6 New Energy,荣威i6新能源,Roewe iMAX8,荣威iMAX8,Roewe iMAX8 New Energy,荣威iMAX8新能源,Roewe D5X,荣威D5X,Roewe D7,荣威D7,Roewe Ei5,荣威Ei5,Roewe 360,荣威360,Roewe MARVEL,荣威MARVEL,SAIC',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- MG
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('MG', '名爵',
    'MG,名爵,MG6,名爵6,MG 6 New Energy,名爵6新能源,MG5,名爵5,MG5 Scorpio,名爵5天蝎座,MG7,名爵7,MG3,名爵3,MG 3,名爵3,MG 3SW,名爵3SW,MG ZS,名爵ZS,MG HS,名爵HS,MG4,名爵4,SAIC',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Exeed
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Astral Path', '星途',
    'Exeed,Astral Path,星途,Star Way,星途,Star Way TX,星途TX,Xingtu Lanyue,星途揽月,Xingtu Yaoguang,星途瑶光,Star Way Chasing the Wind,星途追风,Star Way Chasing the Wind C-DM,星途追风C-DM,Xingtu Lingyun,星途凌云,Xingtu Lanyue,星途揽月,Chery高端品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Omoda
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Omoda', '欧萌达',
    'Omoda,欧萌达,Ou Mengda,欧萌达,Omoda 5,欧萌达5,Chery品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Zeekr
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Extremely krypton', '极氪',
    'Zeekr,Extremely krypton,极氪,Extreme Krypton 001,极氪001,Extreme Krypton X,极氪X,Extreme Krypton 009,极氪009,Extreme Krypton MIX,极氪MIX,Extreme Krypton 9X,极氪9X,Extreme Krypton 007,极氪007,Extreme Krypton 007GT,极氪007GT,Extreme Krypton 7X,极氪7X,吉利高端电动',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Nio
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Weilai', '蔚来',
    'Nio,Weilai,蔚来,NIO ES8,蔚来ES8,NIO ES6,蔚来ES6,NIO ES7,蔚来ES7,Nio ET5,蔚来ET5,Nio ET5T,蔚来ET5T,Nio ET7,蔚来ET7,Nio ET9,蔚来ET9,Nio EC6,蔚来EC6,电动车,蔚来换电',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Xpeng
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Xiaopeng Motors', '小鹏汽车',
    'Xiaopeng Motors,Xiaopeng Motors,小鹏,Xpeng,Xiaopeng P7,小鹏P7,Xiaopeng P7+,小鹏P7+,Xiaopeng P5,小鹏P5,Xiaopeng G3,小鹏G3,Xiaopeng G6,小鹏G6,Xiaopeng G7,小鹏G7,Xiaopeng G9,小鹏G9,Xiaopeng X9,小鹏X9,Xiaopeng MONA,小鹏MONA,电动车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Li Auto
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Ideal car', '理想汽车',
    'Li Auto,Ideal car,理想,Ideal ONE,理想ONE,Ideal L6,理想L6,Ideal L7,理想L7,Ideal L8,理想L8,Ideal L9,理想L9,Ideal i8,理想i8,Ideal MEGA,理想MEGA,增程式电动车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Red flag
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Red flag', '红旗',
    'Red flag,红旗,Hongqi HS3,红旗HS3,Hongqi HS5,红旗HS5,Hongqi HS7,红旗HS7,Hongqi H5,红旗H5,Hongqi H6,红旗H6,Hongqi H7,红旗H7,Hongqi H9,红旗H9,Hongqi HQ9,红旗HQ9,Hongqi E-QM5,红旗E-QM5,Hongqi E-HS9,红旗E-HS9,Hongqi EH7,红旗EH7,Hongqi Tiangong 08,红旗天工08,一汽',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Wuling Automobile
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Wuling Automobile', '五菱汽车',
    'Wuling Automobile,Wuling Automobile,五菱,Wuling Hongguang,五菱宏光,Wuling Hongguang S3,五菱宏光S3,Wuling Hongguang PLUS,五菱宏光PLUS,Wuling Hongguang New Energy,五菱宏光新能源,Wuling Hongguang V,五菱宏光V,Wuling Rongguang,五菱荣光,Wuling Rongguang New Card,五菱荣光新卡,Wuling Rongguang S,五菱荣光S,Wuling Rongguang V,五菱荣光V,Wuling Rongguang EV,五菱荣光EV,Wuling Rongguang Small Truck,五菱荣光小卡,Wuling Bingguo,五菱缤果,Wuling Bingguo PLUS,五菱缤果PLUS,Wuling Starlight,五菱星光,Wuling Starlight,五菱星光,Wuling Capgemini,五菱凯捷,Wuling Journey,五菱征程,Wuling Jiachen,五菱佳辰,Wuling Air,五菱晴空,Wuling 730,五菱730,Wuling EV50,五菱EV50,SAIC-GM-Wuling',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Baojun
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Baojun', '宝骏',
    'Baojun,宝骏,Baojun 310,宝骏310,Baojun 360,宝骏360,Baojun 510,宝骏510,Baojun 530,宝骏530,Baojun 560,宝骏560,Baojun 730,宝骏730,Baojun Valli,宝骏Valli,Baojun RC-5,宝骏RC-5,Baojun RC-6,宝骏RC-6,Baojun E200,宝骏E200,Baojun E300,宝骏E300,Baojunyue also,宝骏悦也,Baojunyue also Plus,宝骏悦也Plus,SAIC-GM-Wuling',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Brilliance
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Brilliance', '华晨',
    'Brilliance,华晨,Brilliance New Day,华晨新日,华晨汽车,华晨宝马,华晨中华,China,中华,China V3,中华V3,China V5,中华V5,China V6,中华V6,China V7,中华V7',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Haima
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Seahorse', '海马',
    'Haima,Seahorse,海马,Seahorse S5,海马S5,Seahorse 7X,海马7X,Seahorse 8S,海马8S,Seahorse M6,海马M6',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- JAC
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Jiangqi Group', '江汽集团',
    'JAC,Jiangqi Group,江淮,Jianghuai Automobile,江淮汽车,JAC X8,江淮X8,Jiangling,江铃,Jiangling Group,江铃集团,Jiangling Jingma Automobile,江铃晶马汽车,Jiangling E200L,江铃E200L,Jiangling Sojourn RV,江铃旅居房车,Jiangling Fushun,江铃福顺',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Jianghuai Ruifeng
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Jianghuai Ruifeng', '江淮瑞风',
    'Jianghuai Ruifeng,江淮瑞风,Ruifeng,瑞风,Ruifeng S2,瑞风S2,Ruifeng S3,瑞风S3,Ruifeng S4,瑞风S4,Ruifeng S7,瑞风S7,Ruifeng M3,瑞风M3,Ruifeng M4,瑞风M4,Ruifeng M5,瑞风M5,江淮瑞风',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lifan
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lifan', '力帆',
    'Lifan,力帆,Lifan X50,力帆X50,Lifan X60,力帆X60,Lifan X80,力帆X80',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Zotye
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Zotye', '众泰',
    'Zotye,众泰,Zotye T600,众泰T600,Zotye T700,众泰T700,Zotye T800,众泰T800,Zotye T500,众泰T500,Zotye SR7,众泰SR7,Zotye SR9,众泰SR9,Zotye Z300,众泰Z300,Zotye Z560,众泰Z560,Zotye Z700,众泰Z700',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Nezha Automobile
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Nezha Automobile', '哪吒汽车',
    'Nezha Automobile,Nezha Automobile,哪吒,Nezha V,哪吒V,Nezha U,哪吒U,Nezha S,哪吒S,Nezha L,哪吒L,Nezha S hunting Outfit,哪吒S猎装版',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Denza
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Denza', '腾势',
    'Denza,腾势,Denza D9,腾势D9,Denza N7,腾势N7,Denza N8,腾势N8,Denza N8L,腾势N8L,Denza X,腾势X,Denza Z9,腾势Z9,Denza Z9GT,腾势Z9GT,比亚迪奔驰合资',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Euler
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Euler', '欧拉',
    'Euler,欧拉,Euler White Cat,欧拉白猫,Euler Black Cat,欧拉黑猫,Euler good cat,欧拉好猫,Euler Good Cat GT,欧拉好猫GT,Euler Ballet Cat,欧拉芭蕾猫,长城汽车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lynk
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lynk', '领克',
    'Lynk,领克,Lynk 01,领克01,Lynk 02,领克02,Lynk 03,领克03,Lynk 05,领克05,Lynk 06,领克06,Lynk 07,领克07,Lynk 08,领克08,Lynk 09,领克09,Lynk Z10,领克Z10,Lynk Z20,领克Z20,Lynk & Co 900,领克900,吉利沃尔沃合资',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Xiaomi Car
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Xiaomi Car', '小米汽车',
    'Xiaomi Car,小米汽车,Xiaomi SU7,小米SU7,Xiaomi YU7,小米YU7,小米',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- AITO
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('AITO', 'AITO',
    'AITO,AITO,问界,Ask the world M7,问界M7,Ask the world M8,问界M8,Ask the world M9,问界M9,赛力斯华为',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Weima Automobile
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Weima Automobile', '威马汽车',
    'Weima Automobile,威马汽车,Weima EX5,威马EX5',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Zero-running car
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Zero-running car', '零跑汽车',
    'Zero-running car,Zero-running car,零跑,Zero run C01,零跑C01,Zero run C10,零跑C10,Zero run C11,零跑C11,Zero run C16,零跑C16,Zero run T03,零跑T03,Zero run B10,零跑B10',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- SAIC MAXUS
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('SAIC MAXUS', '上汽大通MAXUS',
    'SAIC MAXUS,上汽大通MAXUS,MAXUS,大通,Chase G10,大通G10,Chase G20,大通G20,Chase G50,大通G50,Chase G70,大通G70,Chase G90,大通G90,Chase EV30,大通EV30,Chase G20,大通G20,Chase G90,大通G90,Xintu V80,新途V80,Xintu V90,新途V90,Quanshun T8,全顺T8',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Look up
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Look up', '仰望',
    'Look up,仰望,Look up to U8,仰望U8,比亚迪高端',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Gao He
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Gao He', '高合',
    'Gao He,高合,Gao He HiPhi,高合HiPhi,华人运通',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Happy Road
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Happy Road', '乐道',
    'Happy Road,乐道,Le Dao L60,乐道L60,Le Dao L90,乐道L90,蔚来子品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Enjoy the world
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Enjoy the world', '享界',
    'Enjoy the world,享界,Enjoy domain,享域,Enjoy the world S9,享界S9,华为北汽',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Intellectual world
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Intellectual world', '智界',
    'Intellectual world,智界,Wisdom World S7,智界S7,Wisdom World R7,智界R7,华为奇瑞',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Aion
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Aian', '埃安',
    'AION,Aian,埃安,AION,广汽埃安,GAC Aion',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Dark blue car
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Dark blue car', '深蓝汽车',
    'Dark blue car,深蓝汽车,Dark blue SL03,深蓝SL03,Dark blue G318,深蓝G318,Dark blue S05,深蓝S05,Dark blue L07,深蓝L07,Dark blue S07,深蓝S07,长安深蓝',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Avita
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Avita', '阿维塔',
    'Avita,阿维塔,Avita 06,阿维塔06,Avita 07,阿维塔07,Avita 12,阿维塔12,长安华为宁德',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lan Tu
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lan Tu', '岚图',
    'Lan Tu,岚图,Lan Tu FREE,岚图FREE,Lan Tu Dreamer,岚图梦想家,Lan Tu chasing light,岚图追光,Lan Tu Zhiyin,岚图知音,东风岚图',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Zhiji Automobile
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Zhiji Automobile', '智己汽车',
    'Zhiji Automobile,智己汽车,Zhiji LS7,智己LS7,Zhiji LS6,智己LS6,Zhiji L7,智己L7,Zhiji L6,智己L6,上汽智己',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Qichen
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Qichen', '启辰',
    'Qichen,启辰,Qichen D60,启辰D60,Qichen Big V,启辰大V,Qichen T70,启辰T70,东风启辰',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Pentium
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Pentium', '奔腾',
    'Pentium,奔腾,Pentium B50,奔腾B50,Pentium B70,奔腾B70,Pentium T33,奔腾T33,Pentium T55,奔腾T55,Pentium T77,奔腾T77,Pentium T99,奔腾T99,Pentium X40,奔腾X40,Pentium NAT,奔腾NAT,Pentium pony,奔腾小马,一汽奔腾',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Lu Feng
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lu Feng', '陆风',
    'Lu Feng,陆风,陆风汽车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Beijing off-road
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Beijing off-road', '北京越野',
    'Beijing off-road,北京越野,Beijing off-road BJ40,北京越野BJ40,Beijing off-road BJ60,北京越野BJ60,Beijing off-road BJ80,北京越野BJ80,Beijing off-road BJ90,北京越野BJ90,Beijing off-road BJ30,北京越野BJ30,Beijing off-road BJ40 range extension,北京越野BJ40增程,Beijing off-road BJ60 Thunder,北京越野BJ60雷霆,北京汽车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Beijing Automobile
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Beijing Automobile', '北京汽车',
    'Beijing Automobile,北京汽车,Beijing X3,北京X3,Beijing X7,北京X7,Beijing EU7,北京EU7,Baic New Energy,北汽新能源,Baic New Energy EC5,北汽新能源EC5,Beijing X7,北京X7,Baic Magic Speed,北汽幻速,Baic Magic Speed S3,北汽幻速S3,Baic Magic Speed H2,北汽幻速H2,Baic Weiwang,北汽威旺,Baic Weiwang S50,北汽威旺S50,Beiqi Changhe,北汽昌河,Beiqi Changhe Q35,北汽昌河Q35,Beiqi Changhe M50S,北汽昌河M50S,Beijing Automobile Manufacturing Plant,北京汽车制造厂',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- iCAR
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('iCAR', 'iCAR',
    'iCAR,iCAR,奇瑞iCAR',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- SERES
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('SERES', 'SERES赛力斯',
    'SERES,SERES赛力斯,赛力斯,Sailis SF5,赛力斯SF5,华为赛力斯',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Jietu
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Jietu', '捷途',
    'Jietu,捷途,Jietu X70,捷途X70,Jietu X70M,捷途X70M,Jietu X70S,捷途X70S,Jietu X90,捷途X90,Jietu X95,捷途X95,Jietu Shanhai,捷途山海,Jietu Shanhai T2,捷途山海T2,Jietu Shanhai L7,捷途山海L7,Jietu Shanhai L9,捷途山海L9,Jietu Shanhai,捷途山海,Jietu Vertical and Horizontal,捷途纵横,Great Sage Jietu,捷途大圣,Jet Traveler,捷途旅行者,奇瑞捷途',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Kaiyi
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Kaiyi', '凯翼',
    'Kaiyi,凯翼,Kaiyi X3,凯翼X3,Kaiyi E3,凯翼E3,Kaiyi Kunlun,凯翼昆仑,Kaiyi Kunlun New Energy,凯翼昆仑新能源,奇瑞凯翼',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- King Kong Cannon
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('King Diamond Cannon', '金刚炮',
    'King Diamond Cannon,King Diamond Cannon,金刚炮,长城炮系列',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Baowo
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Baowo', '宝沃',
    'Baowo,宝沃,Baowo BX5,宝沃BX5,Baowo BX7,宝沃BX7',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Remote car
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Remote car', '远程汽车',
    'Remote car,远程汽车,Remote FX,远程FX,Remote E5,远程E5,Remote star enjoy F1E,远程星享F1E,吉利远程',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Zhirui Automobile
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Zhirui Automobile', '智锐汽车',
    'Zhirui Automobile,智锐汽车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Sihao
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Sihao', '思皓',
    'Sihao,思皓,Sihao A5,思皓A5,Sihao X8,思皓X8,Sihao E50A,思皓E50A,江淮大众',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- РОССИЙСКИЕ БРЕНДЫ
-- ============================================

-- Lada
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Lada', '拉达',
    'Lada,拉达,Lada (ВАЗ),ВАЗ,АвтоВАЗ,Lada Granta,Lada Vesta,Lada Niva,Radaniva,拉达尼瓦',
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
VALUES ('Aurus', 'Аурус',
    'Aurus,Аурус,阿鲁斯,Aurus Senat,俄罗斯豪华品牌',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ДРУГИЕ БРЕНДЫ
-- ============================================

-- Iveco
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Iveco', '依维柯',
    'Iveco,依维柯,Iveco proud,依维柯得意,Iveco Ousheng,依维柯欧胜,Iveco Ousheng Sojourn RV,依维柯欧胜旅居房车,Iveco Ousheng RV,依维柯欧胜房车,Iveco Oushenglongcui C-type Rv,依维柯欧胜隆翠C型房车',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Isuzu
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('Isuzu', '五十铃',
    'Isuzu,五十铃,Isuzu D-Max,D-MAX,mu-X Shepherd Ranger,mu-X牧游侠',
    NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ОБНОВЛЕНИЕ СУЩЕСТВУЮЩИХ ЗАПИСЕЙ (если нужно)
-- ============================================

-- Если бренды уже существуют и нужно обновить алиасы, используйте:
-- UPDATE brands SET aliases = 'новые_алиасы', updated_at = NOW() WHERE name = 'Brand Name' OR orig_name = 'Бренд';

-- ============================================
-- ПРОВЕРКА
-- ============================================

-- SELECT name, orig_name, aliases FROM brands WHERE deleted_at IS NULL ORDER BY name;


