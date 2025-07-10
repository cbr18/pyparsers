from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.dongchedifetch import DongchediParser
from api.che168fetch import Che168Parser
from converters import decode_sh_price

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/cars/dongchedifetch")
def get_dongchedi_cars():
    parser = DongchediParser()
    response = parser.fetch_cars()
    # Оставляем только нужные поля для каждого авто
    allowed_fields = [
        "title", "sh_price", "image", "car_year", "car_mileage", "car_source_city_name",
        "brand_name", "series_name", "car_name", "car_source_type", "transfer_cnt"
    ]
    filtered_cars = []
    for car in response.data.search_sh_sku_info_list:
        if car.sh_price:
            car.sh_price = decode_sh_price(car.sh_price)
        filtered_car = {field: getattr(car, field, None) for field in allowed_fields}
        filtered_cars.append(filtered_car)
    return {
        "data": {
            "has_more": response.data.has_more,
            "search_sh_sku_info_list": filtered_cars,
            "total": response.data.total
        },
        "message": "Success",
        "status": 200
    }

@app.get("/cars/che168fetch")
def get_che168_cars():
    parser = Che168Parser()
    response = parser.fetch_cars()
    return response
