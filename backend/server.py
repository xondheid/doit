from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT and password hashing setup
JWT_SECRET = "your-super-secret-jwt-key-change-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# User Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    role: str  # "patient", "doctor", "admin"
    phone: Optional[str] = None
    specialization: Optional[str] = None  # for doctors
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str
    phone: Optional[str] = None
    specialization: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# Medical Service Models
class MedicalService(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    duration_minutes: int
    price: float
    category: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MedicalServiceCreate(BaseModel):
    name: str
    description: str
    duration_minutes: int
    price: float
    category: str

# Appointment Models
class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    doctor_id: str
    service_id: str
    appointment_date: datetime
    status: str  # "scheduled", "completed", "cancelled"
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AppointmentCreate(BaseModel):
    doctor_id: str
    service_id: str
    appointment_date: datetime
    notes: Optional[str] = None

# Time Slot Model
class TimeSlot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doctor_id: str
    date: str  # YYYY-MM-DD format
    start_time: str  # HH:MM format
    end_time: str  # HH:MM format
    is_available: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TimeSlotCreate(BaseModel):
    date: str
    start_time: str
    end_time: str

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = await db.users.find_one({"email": email})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Remove MongoDB's _id field to avoid serialization issues
        if '_id' in user:
            del user['_id']
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Auth routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and create user
    hashed_password = hash_password(user_data.password)
    user_dict = user_data.dict()
    del user_dict["password"]
    user_dict["hashed_password"] = hashed_password
    
    user = User(**user_dict)
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    user_doc = await db.users.find_one({"email": user_credentials.email})
    if not user_doc or not verify_password(user_credentials.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Remove MongoDB's _id field to avoid serialization issues
    if '_id' in user_doc:
        del user_doc['_id']
    user = User(**user_doc)
    access_token = create_access_token(data={"sub": user.email})
    
    return Token(access_token=access_token, token_type="bearer", user=user)

# User routes
@api_router.get("/users/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.get("/users/doctors", response_model=List[User])
async def get_doctors():
    doctors = await db.users.find({"role": "doctor"}).to_list(100)
    # Remove MongoDB's _id field to avoid serialization issues
    for doctor in doctors:
        if '_id' in doctor:
            del doctor['_id']
    return [User(**doctor) for doctor in doctors]

# Medical Service routes
@api_router.post("/services", response_model=MedicalService)
async def create_service(service_data: MedicalServiceCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create services")
    
    service = MedicalService(**service_data.dict())
    await db.medical_services.insert_one(service.dict())
    return service

@api_router.get("/services", response_model=List[MedicalService])
async def get_services():
    services = await db.medical_services.find({"is_active": True}).to_list(100)
    return [MedicalService(**service) for service in services]

@api_router.put("/services/{service_id}", response_model=MedicalService)
async def update_service(service_id: str, service_data: MedicalServiceCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update services")
    
    result = await db.medical_services.update_one(
        {"id": service_id}, 
        {"$set": service_data.dict()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service not found")
    
    updated_service = await db.medical_services.find_one({"id": service_id})
    return MedicalService(**updated_service)

# Time Slot routes
@api_router.post("/time-slots", response_model=TimeSlot)
async def create_time_slot(slot_data: TimeSlotCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can create time slots")
    
    slot_dict = slot_data.dict()
    slot_dict["doctor_id"] = current_user.id
    slot = TimeSlot(**slot_dict)
    await db.time_slots.insert_one(slot.dict())
    return slot

@api_router.get("/time-slots/{doctor_id}", response_model=List[TimeSlot])
async def get_doctor_time_slots(doctor_id: str, date: Optional[str] = None):
    query = {"doctor_id": doctor_id, "is_available": True}
    if date:
        query["date"] = date
    
    slots = await db.time_slots.find(query).to_list(100)
    return [TimeSlot(**slot) for slot in slots]

# Appointment routes
@api_router.post("/appointments", response_model=Appointment)
async def book_appointment(appointment_data: AppointmentCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can book appointments")
    
    # Check if the requested time slot is available
    appointment_date = appointment_data.appointment_date
    existing_appointment = await db.appointments.find_one({
        "doctor_id": appointment_data.doctor_id,
        "appointment_date": appointment_date,
        "status": {"$ne": "cancelled"}
    })
    
    if existing_appointment:
        raise HTTPException(status_code=400, detail="Time slot not available")
    
    appointment_dict = appointment_data.dict()
    appointment_dict["patient_id"] = current_user.id
    appointment_dict["status"] = "scheduled"
    appointment = Appointment(**appointment_dict)
    await db.appointments.insert_one(appointment.dict())
    
    return appointment

@api_router.get("/appointments/my", response_model=List[dict])
async def get_my_appointments(current_user: User = Depends(get_current_user)):
    if current_user.role == "patient":
        query = {"patient_id": current_user.id}
    elif current_user.role == "doctor":
        query = {"doctor_id": current_user.id}
    else:
        query = {}
    
    appointments = await db.appointments.find(query).to_list(100)
    
    # Enrich with user and service details
    enriched_appointments = []
    for apt in appointments:
        # Remove MongoDB's _id field to avoid serialization issues
        if '_id' in apt:
            del apt['_id']
            
        # Get patient info
        if current_user.role != "patient":
            patient = await db.users.find_one({"id": apt["patient_id"]})
            apt["patient_name"] = patient["name"] if patient else "Unknown"
        
        # Get doctor info
        if current_user.role != "doctor":
            doctor = await db.users.find_one({"id": apt["doctor_id"]})
            apt["doctor_name"] = doctor["name"] if doctor else "Unknown"
        
        # Get service info
        service = await db.medical_services.find_one({"id": apt["service_id"]})
        apt["service_name"] = service["name"] if service else "Unknown"
        apt["service_price"] = service["price"] if service else 0
        
        enriched_appointments.append(apt)
    
    return enriched_appointments

@api_router.put("/appointments/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str, current_user: User = Depends(get_current_user)):
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check permissions
    if (current_user.role == "patient" and appointment["patient_id"] != current_user.id) or \
       (current_user.role == "doctor" and appointment["doctor_id"] != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to cancel this appointment")
    
    await db.appointments.update_one(
        {"id": appointment_id}, 
        {"$set": {"status": "cancelled"}}
    )
    
    return {"message": "Appointment cancelled successfully"}

# Initialize default data
@api_router.post("/init-data")
async def initialize_default_data():
    # Check if admin exists
    admin = await db.users.find_one({"email": "admin@medical.com"})
    if not admin:
        admin_data = {
            "email": "admin@medical.com",
            "hashed_password": hash_password("admin123"),
            "name": "System Admin",
            "role": "admin",
            "id": str(uuid.uuid4()),
            "created_at": datetime.utcnow()
        }
        await db.users.insert_one(admin_data)
    
    # Check if services exist
    services_count = await db.medical_services.count_documents({})
    if services_count == 0:
        default_services = [
            {
                "id": str(uuid.uuid4()),
                "name": "Recipe Consultation",
                "description": "Get medical prescriptions and recipes",
                "duration_minutes": 15,
                "price": 25.00,
                "category": "consultation",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Sick Note",
                "description": "Medical certificate for sick leave",
                "duration_minutes": 10,
                "price": 15.00,
                "category": "documentation",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Vaccination",
                "description": "Various vaccination services",
                "duration_minutes": 20,
                "price": 35.00,
                "category": "treatment",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Wound Dressing",
                "description": "Professional wound care and dressing",
                "duration_minutes": 30,
                "price": 40.00,
                "category": "treatment",
                "is_active": True,
                "created_at": datetime.utcnow()
            }
        ]
        await db.medical_services.insert_many(default_services)
    
    return {"message": "Default data initialized"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()