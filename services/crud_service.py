from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel

app = FastAPI()

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["iot_db"]
collection = db["sensor_data"]

class SensorData(BaseModel):
    device_id: str
    timestamp: str
    temperature: float
    humidity: float

@app.post("/sensor/")
async def create_sensor_data(data: SensorData):
    collection.insert_one(data.dict())
    return {"message": "Sensor data added successfully"}

@app.get("/sensor/{device_id}")
async def get_sensor_data(device_id: str):
    data = collection.find_one({"device_id": device_id})
    if not data:
        raise HTTPException(status_code=404, detail="Sensor data not found")
    return data

@app.put("/sensor/{device_id}")
async def update_sensor_data(device_id: str, data: SensorData):
    result = collection.update_one({"device_id": device_id}, {"$set": data.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Sensor data not found")
    return {"message": "Sensor data updated successfully"}

@app.delete("/sensor/{device_id}")
async def delete_sensor_data(device_id: str):
    result = collection.delete_one({"device_id": device_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sensor data not found")
    return {"message": "Sensor data deleted successfully"}

