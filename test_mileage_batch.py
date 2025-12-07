from api.dongchedi.parser import DongchediParser
from api.che168.detailed_parser_api import Che168DetailedParserAPI

che168_cases = [
    (56923611, 609019),
    (56973492, 601756),
    (57014796, 656155),
    (57022267, 371720),
    (57026682, 624803),
    (57031967, 540259),
    (57032133, 654841),
    (57032212, 654841),
    (57042408, 524780),
    (57044098, 662036),
]

dongchedi_ids = [
    '35286',
    '37203',
    '46963',
    '77100',
    '78960',
    '88793',
    '96803',
    '253349',
    '5170',
    '6265',
]

print('=== Dongchedi mileage checks ===')
parser = DongchediParser()
for cid in dongchedi_ids:
    car, meta = parser.fetch_car_detail(cid)
    if car:
        print(f"id={cid} mileage={car.mileage} raw={car.car_mileage} city={car.city}")
    else:
        print(f"id={cid} FAILED meta={meta}")

print('\n=== Che168 mileage checks ===')
che = Che168DetailedParserAPI()
for cid, shop in che168_cases:
    car, banned = che.parse_car_details(cid, shop_id=shop)
    if car:
        print(f"id={cid} shop={shop} mileage={car.mileage} banned={banned} image_count={car.image_count}")
    else:
        print(f"id={cid} shop={shop} FAILED banned={banned}")
