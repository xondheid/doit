#!/usr/bin/env python3
"""
Debug appointment booking issue
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "https://d28dd0c4-9f9d-436c-a782-395e80651953.preview.emergentagent.com/api"

def debug_appointment_booking():
    # Login as admin first
    admin_login = {
        "email": "admin@medical.com",
        "password": "admin123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=admin_login)
    if response.status_code != 200:
        print(f"Admin login failed: {response.status_code}")
        return
    
    admin_token = response.json()["access_token"]
    
    # Get doctors list
    response = requests.get(f"{BASE_URL}/users/doctors")
    if response.status_code != 200:
        print(f"Failed to get doctors: {response.status_code}")
        return
    
    doctors = response.json()
    if not doctors:
        print("No doctors found")
        return
    
    doctor_id = doctors[0]["id"]
    print(f"Using doctor ID: {doctor_id}")
    
    # Get services
    response = requests.get(f"{BASE_URL}/services")
    if response.status_code != 200:
        print(f"Failed to get services: {response.status_code}")
        return
    
    services = response.json()
    if not services:
        print("No services found")
        return
    
    service_id = services[0]["id"]
    print(f"Using service: {services[0]['name']} ({services[0]['duration_minutes']} min)")
    
    # Check available slots for tomorrow
    tomorrow = (datetime.utcnow() + timedelta(days=1)).date().isoformat()
    response = requests.get(f"{BASE_URL}/time-slots/{doctor_id}/available", 
                          params={"date": tomorrow, "service_id": service_id})
    
    if response.status_code != 200:
        print(f"Failed to get available slots: {response.status_code}")
        print(response.text)
        return
    
    slots = response.json()
    print(f"Available slots for {tomorrow}: {len(slots)}")
    
    if slots:
        print("First few slots:")
        for i, slot in enumerate(slots[:3]):
            print(f"  {i+1}. {slot['time']} - {slot['datetime']}")
        
        # Try to book the first available slot
        first_slot = slots[0]
        appointment_time = datetime.fromisoformat(first_slot["datetime"])
        
        # Create a patient account for testing
        import time
        timestamp = str(int(time.time()))
        patient_data = {
            "email": f"testpatient{timestamp}@test.com",
            "password": "test123",
            "name": "Test Patient",
            "role": "patient"
        }
        
        response = requests.post(f"{BASE_URL}/auth/register", json=patient_data)
        if response.status_code != 200:
            print(f"Failed to create patient: {response.status_code}")
            print(response.text)
            return
        
        patient_token = response.json()["access_token"]
        print(f"Created patient: {patient_data['name']}")
        
        # Try to book appointment
        headers = {"Authorization": f"Bearer {patient_token}"}
        appointment_data = {
            "doctor_id": doctor_id,
            "service_id": service_id,
            "appointment_date": appointment_time.isoformat(),
            "notes": "Debug test appointment"
        }
        
        print(f"Trying to book appointment at: {appointment_time.isoformat()}")
        response = requests.post(f"{BASE_URL}/appointments", json=appointment_data, headers=headers)
        
        if response.status_code == 200:
            print("✅ Appointment booked successfully!")
            print(response.json())
        else:
            print(f"❌ Appointment booking failed: {response.status_code}")
            print(response.text)
            
            # Check if doctor has time slots defined
            response = requests.get(f"{BASE_URL}/time-slots/{doctor_id}", params={"date": tomorrow})
            if response.status_code == 200:
                doctor_slots = response.json()
                print(f"Doctor has {len(doctor_slots)} defined time slots for {tomorrow}")
                if doctor_slots:
                    print("Doctor's time slots:")
                    for slot in doctor_slots[:3]:
                        print(f"  {slot['start_time']} - {slot['end_time']} (available: {slot['is_available']})")
            else:
                print(f"Failed to get doctor's time slots: {response.status_code}")
    else:
        print("No available slots found")

if __name__ == "__main__":
    debug_appointment_booking()