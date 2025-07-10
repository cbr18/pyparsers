from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.dongchedi.parser import DongchediParser
from api.che168.parser import Che168Parser
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
    # Преобразуем в формат для совместимости с фронтендом
    filtered_cars = []
    for car in response.data.search_sh_sku_info_list:
        car_dict = car.dict()
        if car_dict.get('sh_price'):
            car_dict['sh_price'] = decode_sh_price(car_dict['sh_price'])
        filtered_cars.append(car_dict)
    
    return {
        "data": {
            "has_more": response.data.has_more,
            "search_sh_sku_info_list": filtered_cars,
            "total": response.data.total
        },
        "message": response.message,
        "status": response.status
    }

@app.get("/cars/che168fetch")
def get_che168_cars():
    parser = Che168Parser()
    response = parser.fetch_cars()
    # Преобразуем в формат для совместимости с фронтендом
    return {
        "data": {
            "has_more": response.data.has_more,
            "search_sh_sku_info_list": [car.dict() for car in response.data.search_sh_sku_info_list],
            "total": response.data.total
        },
        "message": response.message,
        "status": response.status
    }
