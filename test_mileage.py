from api.dongchedi.parser import DongchediParser
from api.che168.detailed_parser_api import Che168DetailedParserAPI


dongchedi_ids = ['55406760','54006634','55340279']
che168_ids = [55406760,54006634,55340279]

print('=== Dongchedi mileage checks ===')
parser = DongchediParser()
for cid in dongchedi_ids:
    car, meta = parser.fetch_car_detail(cid)
    if car:
        print(f"id={cid} mileage={car.mileage} raw={car.car_mileage}")
    else:
        print(f"id={cid} FAILED meta={meta}")

print('\n=== Che168 mileage checks ===')
che = Che168DetailedParserAPI()
for cid in che168_ids:
    car, banned = che.parse_car_details(cid)
    if car:
        print(f"id={cid} mileage={car.mileage} banned={banned}")
    else:
        print(f"id={cid} FAILED banned={banned}")
