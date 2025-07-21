#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Universal Medical Platform
Tests all API endpoints with proper authentication and role-based access control
"""

import requests
import json
from datetime import datetime, timedelta
import uuid

# Backend URL from frontend/.env
BASE_URL = "https://d28dd0c4-9f9d-436c-a782-395e80651953.preview.emergentagent.com/api"

class MedicalPlatformTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.admin_token = None
        self.doctor_token = None
        self.patient_token = None
        self.doctor_email = None
        self.patient_email = None
        self.test_results = []
        self.created_service_id = None
        self.created_appointment_id = None
        self.doctor_id = None
        
    def log_test(self, test_name, success, message="", details=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        if not success and details:
            print(f"   Details: {details}")
        print()

    def test_init_data(self):
        """Test initialization of default data"""
        try:
            response = requests.post(f"{self.base_url}/init-data")
            if response.status_code == 200:
                self.log_test("Initialize Default Data", True, "Default admin and services created successfully")
                return True
            else:
                self.log_test("Initialize Default Data", False, f"Status: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Initialize Default Data", False, f"Connection error: {str(e)}")
            return False

    def test_user_registration(self):
        """Test user registration for all roles"""
        import time
        timestamp = str(int(time.time()))
        
        users_to_create = [
            {
                "email": f"patient{timestamp}@test.com",
                "password": "patient123",
                "name": "Jane Patient",
                "role": "patient",
                "phone": "+1234567892"
            },
            {
                "email": f"doctor{timestamp}@test.com", 
                "password": "doctor123",
                "name": "Dr. Michael Smith",
                "role": "doctor",
                "phone": "+1234567893",
                "specialization": "General Practice"
            }
        ]
        
        for user_data in users_to_create:
            try:
                response = requests.post(f"{self.base_url}/auth/register", json=user_data)
                if response.status_code == 200:
                    data = response.json()
                    if user_data["role"] == "doctor":
                        self.doctor_token = data["access_token"]
                        self.doctor_id = data["user"]["id"]
                        self.doctor_email = user_data["email"]
                    elif user_data["role"] == "patient":
                        self.patient_token = data["access_token"]
                        self.patient_email = user_data["email"]
                    
                    self.log_test(f"Register {user_data['role'].title()}", True, 
                                f"User {user_data['name']} registered successfully")
                else:
                    self.log_test(f"Register {user_data['role'].title()}", False, 
                                f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test(f"Register {user_data['role'].title()}", False, f"Error: {str(e)}")

    def test_admin_login(self):
        """Test admin login with default credentials"""
        try:
            login_data = {
                "email": "admin@medical.com",
                "password": "admin123"
            }
            response = requests.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                self.log_test("Admin Login", True, "Admin logged in successfully")
                return True
            else:
                self.log_test("Admin Login", False, f"Status: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Admin Login", False, f"Error: {str(e)}")
            return False

    def test_user_login(self):
        """Test user login for created users"""
        if not self.patient_email or not self.doctor_email:
            self.log_test("Login Setup", False, "Missing user emails from registration")
            return
            
        login_tests = [
            {"email": self.patient_email, "password": "patient123", "role": "patient"},
            {"email": self.doctor_email, "password": "doctor123", "role": "doctor"}
        ]
        
        for login_data in login_tests:
            try:
                response = requests.post(f"{self.base_url}/auth/login", json={
                    "email": login_data["email"],
                    "password": login_data["password"]
                })
                if response.status_code == 200:
                    data = response.json()
                    if login_data["role"] == "doctor" and not self.doctor_token:
                        self.doctor_token = data["access_token"]
                        self.doctor_id = data["user"]["id"]
                    elif login_data["role"] == "patient" and not self.patient_token:
                        self.patient_token = data["access_token"]
                    
                    self.log_test(f"Login {login_data['role'].title()}", True, 
                                f"{login_data['role'].title()} logged in successfully")
                else:
                    self.log_test(f"Login {login_data['role'].title()}", False, 
                                f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test(f"Login {login_data['role'].title()}", False, f"Error: {str(e)}")

    def test_jwt_token_validation(self):
        """Test JWT token validation on protected endpoints"""
        # Test with valid token
        if self.patient_token:
            try:
                headers = {"Authorization": f"Bearer {self.patient_token}"}
                response = requests.get(f"{self.base_url}/users/me", headers=headers)
                if response.status_code == 200:
                    self.log_test("JWT Token Validation (Valid)", True, "Valid token accepted")
                else:
                    self.log_test("JWT Token Validation (Valid)", False, 
                                f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("JWT Token Validation (Valid)", False, f"Error: {str(e)}")
        
        # Test with invalid token
        try:
            headers = {"Authorization": "Bearer invalid_token"}
            response = requests.get(f"{self.base_url}/users/me", headers=headers)
            if response.status_code == 401:
                self.log_test("JWT Token Validation (Invalid)", True, "Invalid token properly rejected")
            else:
                self.log_test("JWT Token Validation (Invalid)", False, 
                            f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_test("JWT Token Validation (Invalid)", False, f"Error: {str(e)}")

    def test_get_current_user(self):
        """Test getting current user info"""
        tokens = [
            (self.admin_token, "Admin"),
            (self.doctor_token, "Doctor"), 
            (self.patient_token, "Patient")
        ]
        
        for token, role in tokens:
            if token:
                try:
                    headers = {"Authorization": f"Bearer {token}"}
                    response = requests.get(f"{self.base_url}/users/me", headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        self.log_test(f"Get Current User ({role})", True, 
                                    f"Retrieved user info for {data.get('name', 'Unknown')}")
                    else:
                        self.log_test(f"Get Current User ({role})", False, 
                                    f"Status: {response.status_code}", response.text)
                except Exception as e:
                    self.log_test(f"Get Current User ({role})", False, f"Error: {str(e)}")

    def test_get_doctors_list(self):
        """Test fetching doctors list for appointment booking"""
        try:
            response = requests.get(f"{self.base_url}/users/doctors")
            if response.status_code == 200:
                doctors = response.json()
                self.log_test("Get Doctors List", True, f"Retrieved {len(doctors)} doctors")
                if doctors and not self.doctor_id:
                    self.doctor_id = doctors[0]["id"]
            else:
                self.log_test("Get Doctors List", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Get Doctors List", False, f"Error: {str(e)}")

    def test_medical_services_crud(self):
        """Test CRUD operations for medical services"""
        # Test getting services (public endpoint)
        try:
            response = requests.get(f"{self.base_url}/services")
            if response.status_code == 200:
                services = response.json()
                self.log_test("Get Medical Services", True, f"Retrieved {len(services)} services")
            else:
                self.log_test("Get Medical Services", False, f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Get Medical Services", False, f"Error: {str(e)}")

        # Test creating service (admin only)
        if self.admin_token:
            try:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                service_data = {
                    "name": "Test Consultation",
                    "description": "Test medical consultation service",
                    "duration_minutes": 30,
                    "price": 50.0,
                    "category": "consultation"
                }
                response = requests.post(f"{self.base_url}/services", json=service_data, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    self.created_service_id = data["id"]
                    self.log_test("Create Medical Service (Admin)", True, "Service created successfully")
                else:
                    self.log_test("Create Medical Service (Admin)", False, 
                                f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Create Medical Service (Admin)", False, f"Error: {str(e)}")

        # Test creating service as patient (should fail)
        if self.patient_token:
            try:
                headers = {"Authorization": f"Bearer {self.patient_token}"}
                service_data = {
                    "name": "Unauthorized Service",
                    "description": "This should fail",
                    "duration_minutes": 15,
                    "price": 25.0,
                    "category": "test"
                }
                response = requests.post(f"{self.base_url}/services", json=service_data, headers=headers)
                if response.status_code == 403:
                    self.log_test("Create Medical Service (Patient - Should Fail)", True, 
                                "Properly rejected non-admin user")
                else:
                    self.log_test("Create Medical Service (Patient - Should Fail)", False, 
                                f"Expected 403, got {response.status_code}")
            except Exception as e:
                self.log_test("Create Medical Service (Patient - Should Fail)", False, f"Error: {str(e)}")

        # Test updating service (admin only)
        if self.admin_token and self.created_service_id:
            try:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                update_data = {
                    "name": "Updated Test Consultation",
                    "description": "Updated test medical consultation service",
                    "duration_minutes": 45,
                    "price": 60.0,
                    "category": "consultation"
                }
                response = requests.put(f"{self.base_url}/services/{self.created_service_id}", 
                                      json=update_data, headers=headers)
                if response.status_code == 200:
                    self.log_test("Update Medical Service (Admin)", True, "Service updated successfully")
                else:
                    self.log_test("Update Medical Service (Admin)", False, 
                                f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Update Medical Service (Admin)", False, f"Error: {str(e)}")

    def test_appointment_booking_system(self):
        """Test appointment booking with conflict detection"""
        if not self.patient_token or not self.doctor_id:
            self.log_test("Appointment Booking Setup", False, "Missing patient token or doctor ID")
            return

        # Get services first to book an appointment
        try:
            response = requests.get(f"{self.base_url}/services")
            if response.status_code != 200:
                self.log_test("Get Services for Booking", False, "Could not retrieve services")
                return
            
            services = response.json()
            if not services:
                self.log_test("Get Services for Booking", False, "No services available")
                return
            
            service_id = services[0]["id"]
        except Exception as e:
            self.log_test("Get Services for Booking", False, f"Error: {str(e)}")
            return

        # Get available time slots first
        try:
            tomorrow = (datetime.utcnow() + timedelta(days=1)).date().isoformat()
            response = requests.get(f"{self.base_url}/time-slots/{self.doctor_id}/available", 
                                  params={"date": tomorrow, "service_id": service_id})
            
            if response.status_code != 200:
                self.log_test("Get Available Slots for Booking", False, f"Status: {response.status_code}")
                return
            
            available_slots = response.json()
            if not available_slots:
                self.log_test("Get Available Slots for Booking", False, "No available slots")
                return
            
            # Use the first available slot
            first_slot = available_slots[0]
            appointment_datetime = datetime.fromisoformat(first_slot["datetime"])
            
        except Exception as e:
            self.log_test("Get Available Slots for Booking", False, f"Error: {str(e)}")
            return

        # Test booking appointment as patient
        try:
            headers = {"Authorization": f"Bearer {self.patient_token}"}
            appointment_data = {
                "doctor_id": self.doctor_id,
                "service_id": service_id,
                "appointment_date": appointment_datetime.isoformat(),
                "notes": "Test appointment booking"
            }
            
            response = requests.post(f"{self.base_url}/appointments", json=appointment_data, headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.created_appointment_id = data["id"]
                self.log_test("Book Appointment (Patient)", True, "Appointment booked successfully")
                
                # Test conflict detection - try to book same time slot
                response2 = requests.post(f"{self.base_url}/appointments", json=appointment_data, headers=headers)
                if response2.status_code == 400:
                    self.log_test("Appointment Conflict Detection", True, "Duplicate booking properly rejected")
                else:
                    self.log_test("Appointment Conflict Detection", False, 
                                f"Expected 400, got {response2.status_code}")
            else:
                self.log_test("Book Appointment (Patient)", False, 
                            f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Book Appointment (Patient)", False, f"Error: {str(e)}")

        # Test booking appointment as doctor (should fail)
        if self.doctor_token:
            try:
                headers = {"Authorization": f"Bearer {self.doctor_token}"}
                appointment_date = datetime.utcnow() + timedelta(days=2)
                appointment_data = {
                    "doctor_id": self.doctor_id,
                    "service_id": service_id,
                    "appointment_date": appointment_date.isoformat(),
                    "notes": "This should fail"
                }
                
                response = requests.post(f"{self.base_url}/appointments", json=appointment_data, headers=headers)
                if response.status_code == 403:
                    self.log_test("Book Appointment (Doctor - Should Fail)", True, 
                                "Properly rejected non-patient user")
                else:
                    self.log_test("Book Appointment (Doctor - Should Fail)", False, 
                                f"Expected 403, got {response.status_code}")
            except Exception as e:
                self.log_test("Book Appointment (Doctor - Should Fail)", False, f"Error: {str(e)}")

    def test_view_appointments(self):
        """Test viewing appointments by role"""
        tokens_roles = [
            (self.patient_token, "Patient"),
            (self.doctor_token, "Doctor"),
            (self.admin_token, "Admin")
        ]
        
        for token, role in tokens_roles:
            if token:
                try:
                    headers = {"Authorization": f"Bearer {token}"}
                    response = requests.get(f"{self.base_url}/appointments/my", headers=headers)
                    if response.status_code == 200:
                        appointments = response.json()
                        self.log_test(f"View Appointments ({role})", True, 
                                    f"Retrieved {len(appointments)} appointments")
                    else:
                        self.log_test(f"View Appointments ({role})", False, 
                                    f"Status: {response.status_code}", response.text)
                except Exception as e:
                    self.log_test(f"View Appointments ({role})", False, f"Error: {str(e)}")

    def test_appointment_cancellation(self):
        """Test appointment cancellation by patient and doctor"""
        if not self.created_appointment_id:
            self.log_test("Appointment Cancellation Setup", False, "No appointment to cancel")
            return

        # Test cancellation by patient (should work)
        if self.patient_token:
            try:
                headers = {"Authorization": f"Bearer {self.patient_token}"}
                response = requests.put(f"{self.base_url}/appointments/{self.created_appointment_id}/cancel", 
                                      headers=headers)
                if response.status_code == 200:
                    self.log_test("Cancel Appointment (Patient)", True, "Appointment cancelled successfully")
                else:
                    self.log_test("Cancel Appointment (Patient)", False, 
                                f"Status: {response.status_code}", response.text)
            except Exception as e:
                self.log_test("Cancel Appointment (Patient)", False, f"Error: {str(e)}")

        # Test unauthorized cancellation
        if self.admin_token:
            try:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                response = requests.put(f"{self.base_url}/appointments/{self.created_appointment_id}/cancel", 
                                      headers=headers)
                if response.status_code == 403:
                    self.log_test("Cancel Appointment (Unauthorized)", True, 
                                "Properly rejected unauthorized cancellation")
                else:
                    self.log_test("Cancel Appointment (Unauthorized)", False, 
                                f"Expected 403, got {response.status_code}")
            except Exception as e:
                self.log_test("Cancel Appointment (Unauthorized)", False, f"Error: {str(e)}")

    def test_doctor_working_hours_management(self):
        """Test doctor working hours management system"""
        if not self.doctor_token or not self.doctor_id:
            self.log_test("Working Hours Setup", False, "Missing doctor token or ID")
            return

        # Test setting working hours as doctor
        try:
            headers = {"Authorization": f"Bearer {self.doctor_token}"}
            working_hours = {
                "monday": {"available": True, "start": "09:00", "end": "17:00"},
                "tuesday": {"available": True, "start": "09:00", "end": "17:00"},
                "wednesday": {"available": True, "start": "09:00", "end": "17:00"},
                "thursday": {"available": True, "start": "09:00", "end": "17:00"},
                "friday": {"available": True, "start": "09:00", "end": "17:00"},
                "saturday": {"available": False, "start": "", "end": ""},
                "sunday": {"available": False, "start": "", "end": ""}
            }
            
            response = requests.post(f"{self.base_url}/doctors/{self.doctor_id}/working-hours", 
                                   json=working_hours, headers=headers)
            if response.status_code == 200:
                self.log_test("Set Doctor Working Hours", True, "Working hours set successfully")
            else:
                self.log_test("Set Doctor Working Hours", False, 
                            f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Set Doctor Working Hours", False, f"Error: {str(e)}")

        # Test unauthorized working hours setting (patient trying to set doctor's hours)
        if self.patient_token:
            try:
                headers = {"Authorization": f"Bearer {self.patient_token}"}
                working_hours = {
                    "monday": {"available": True, "start": "10:00", "end": "16:00"}
                }
                
                response = requests.post(f"{self.base_url}/doctors/{self.doctor_id}/working-hours", 
                                       json=working_hours, headers=headers)
                if response.status_code == 403:
                    self.log_test("Set Working Hours (Unauthorized)", True, 
                                "Properly rejected unauthorized access")
                else:
                    self.log_test("Set Working Hours (Unauthorized)", False, 
                                f"Expected 403, got {response.status_code}")
            except Exception as e:
                self.log_test("Set Working Hours (Unauthorized)", False, f"Error: {str(e)}")

    def test_available_time_slots_api(self):
        """Test available time slots API with service duration consideration"""
        if not self.doctor_id:
            self.log_test("Available Time Slots Setup", False, "Missing doctor ID")
            return

        # Get services first
        try:
            response = requests.get(f"{self.base_url}/services")
            if response.status_code != 200:
                self.log_test("Get Services for Time Slots", False, "Could not retrieve services")
                return
            
            services = response.json()
            if not services:
                self.log_test("Get Services for Time Slots", False, "No services available")
                return
            
            service_id = services[0]["id"]
            service_duration = services[0]["duration_minutes"]
        except Exception as e:
            self.log_test("Get Services for Time Slots", False, f"Error: {str(e)}")
            return

        # Test getting available time slots for tomorrow
        try:
            tomorrow = (datetime.utcnow() + timedelta(days=1)).date().isoformat()
            response = requests.get(f"{self.base_url}/time-slots/{self.doctor_id}/available", 
                                  params={"date": tomorrow, "service_id": service_id})
            
            if response.status_code == 200:
                slots = response.json()
                self.log_test("Get Available Time Slots", True, 
                            f"Retrieved {len(slots)} available slots for {service_duration}min service")
                
                # Verify slot structure
                if slots:
                    slot = slots[0]
                    required_fields = ["datetime", "time", "duration_minutes", "available"]
                    if all(field in slot for field in required_fields):
                        self.log_test("Time Slot Structure Validation", True, 
                                    "Slots contain all required fields")
                    else:
                        self.log_test("Time Slot Structure Validation", False, 
                                    f"Missing fields in slot: {slot}")
                        
                    # Verify duration matches service
                    if slot["duration_minutes"] == service_duration:
                        self.log_test("Service Duration Integration", True, 
                                    "Slot duration matches service duration")
                    else:
                        self.log_test("Service Duration Integration", False, 
                                    f"Expected {service_duration}min, got {slot['duration_minutes']}min")
            else:
                self.log_test("Get Available Time Slots", False, 
                            f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Get Available Time Slots", False, f"Error: {str(e)}")

        # Test with invalid service ID
        try:
            tomorrow = (datetime.utcnow() + timedelta(days=1)).date().isoformat()
            response = requests.get(f"{self.base_url}/time-slots/{self.doctor_id}/available", 
                                  params={"date": tomorrow, "service_id": "invalid-service-id"})
            
            if response.status_code == 404:
                self.log_test("Available Slots Invalid Service", True, 
                            "Properly rejected invalid service ID")
            else:
                self.log_test("Available Slots Invalid Service", False, 
                            f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.log_test("Available Slots Invalid Service", False, f"Error: {str(e)}")

    def test_enhanced_appointment_conflict_detection(self):
        """Test enhanced appointment booking with duration-aware conflict detection"""
        if not self.patient_token or not self.doctor_id:
            self.log_test("Enhanced Conflict Detection Setup", False, "Missing patient token or doctor ID")
            return

        # Get services with different durations
        try:
            response = requests.get(f"{self.base_url}/services")
            if response.status_code != 200:
                self.log_test("Get Services for Conflict Test", False, "Could not retrieve services")
                return
            
            services = response.json()
            if len(services) < 2:
                self.log_test("Get Services for Conflict Test", False, "Need at least 2 services for testing")
                return
            
            # Sort services by duration to get different durations
            services.sort(key=lambda x: x["duration_minutes"])
            short_service = services[0]  # Shortest duration
            long_service = services[-1]  # Longest duration
            
        except Exception as e:
            self.log_test("Get Services for Conflict Test", False, f"Error: {str(e)}")
            return

        headers = {"Authorization": f"Bearer {self.patient_token}"}
        base_time = datetime.utcnow() + timedelta(days=2)
        base_time = base_time.replace(hour=10, minute=0, second=0, microsecond=0)

        # Test 1: Book a long appointment
        try:
            appointment_data = {
                "doctor_id": self.doctor_id,
                "service_id": long_service["id"],
                "appointment_date": base_time.isoformat(),
                "notes": "Long duration appointment for conflict testing"
            }
            
            response = requests.post(f"{self.base_url}/appointments", json=appointment_data, headers=headers)
            if response.status_code == 200:
                long_appointment_id = response.json()["id"]
                self.log_test("Book Long Duration Appointment", True, 
                            f"Booked {long_service['duration_minutes']}min appointment")
                
                # Test 2: Try to book overlapping short appointment (should fail)
                overlap_time = base_time + timedelta(minutes=10)  # 10 minutes into the long appointment
                overlap_data = {
                    "doctor_id": self.doctor_id,
                    "service_id": short_service["id"],
                    "appointment_date": overlap_time.isoformat(),
                    "notes": "This should conflict"
                }
                
                response2 = requests.post(f"{self.base_url}/appointments", json=overlap_data, headers=headers)
                if response2.status_code == 400:
                    self.log_test("Duration-Aware Conflict Detection", True, 
                                "Properly detected overlapping appointment conflict")
                else:
                    self.log_test("Duration-Aware Conflict Detection", False, 
                                f"Expected 400, got {response2.status_code}")
                
                # Test 3: Book non-overlapping appointment after the long one
                after_time = base_time + timedelta(minutes=long_service["duration_minutes"] + 5)
                after_data = {
                    "doctor_id": self.doctor_id,
                    "service_id": short_service["id"],
                    "appointment_date": after_time.isoformat(),
                    "notes": "Non-overlapping appointment"
                }
                
                response3 = requests.post(f"{self.base_url}/appointments", json=after_data, headers=headers)
                if response3.status_code == 200:
                    self.log_test("Non-Overlapping Appointment Booking", True, 
                                "Successfully booked non-overlapping appointment")
                else:
                    self.log_test("Non-Overlapping Appointment Booking", False, 
                                f"Status: {response3.status_code}", response3.text)
                
            else:
                self.log_test("Book Long Duration Appointment", False, 
                            f"Status: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Enhanced Conflict Detection", False, f"Error: {str(e)}")

    def test_default_working_hours_behavior(self):
        """Test default working hours (9 AM - 5 PM) when no custom slots exist"""
        if not self.doctor_id:
            self.log_test("Default Working Hours Setup", False, "Missing doctor ID")
            return

        # Get services first
        try:
            response = requests.get(f"{self.base_url}/services")
            services = response.json()
            service_id = services[0]["id"] if services else None
            if not service_id:
                self.log_test("Get Service for Default Hours Test", False, "No services available")
                return
        except Exception as e:
            self.log_test("Get Service for Default Hours Test", False, f"Error: {str(e)}")
            return

        # Test getting available slots for a doctor without custom working hours
        try:
            # Use a date far in the future to avoid conflicts with existing appointments
            future_date = (datetime.utcnow() + timedelta(days=10)).date().isoformat()
            response = requests.get(f"{self.base_url}/time-slots/{self.doctor_id}/available", 
                                  params={"date": future_date, "service_id": service_id})
            
            if response.status_code == 200:
                slots = response.json()
                if slots:
                    # Check if slots are within default working hours (9 AM - 5 PM)
                    first_slot_time = slots[0]["time"]
                    last_slot_time = slots[-1]["time"]
                    
                    # Parse times
                    first_hour = int(first_slot_time.split(":")[0])
                    last_hour = int(last_slot_time.split(":")[0])
                    
                    if first_hour >= 9 and last_hour < 17:
                        self.log_test("Default Working Hours (9 AM - 5 PM)", True, 
                                    f"Slots available from {first_slot_time} to {last_slot_time}")
                    else:
                        self.log_test("Default Working Hours (9 AM - 5 PM)", False, 
                                    f"Slots outside expected hours: {first_slot_time} to {last_slot_time}")
                else:
                    self.log_test("Default Working Hours (9 AM - 5 PM)", False, 
                                "No slots returned for default working hours")
            else:
                self.log_test("Default Working Hours (9 AM - 5 PM)", False, 
                            f"Status: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Default Working Hours (9 AM - 5 PM)", False, f"Error: {str(e)}")

    def test_time_slots_update_after_bookings(self):
        """Test that available slots update correctly after appointments are booked"""
        if not self.patient_token or not self.doctor_id:
            self.log_test("Time Slots Update Setup", False, "Missing patient token or doctor ID")
            return

        # Get services
        try:
            response = requests.get(f"{self.base_url}/services")
            services = response.json()
            service_id = services[0]["id"] if services else None
            if not service_id:
                self.log_test("Get Service for Slots Update Test", False, "No services available")
                return
        except Exception as e:
            self.log_test("Get Service for Slots Update Test", False, f"Error: {str(e)}")
            return

        # Use a date far in the future to avoid conflicts
        test_date = (datetime.utcnow() + timedelta(days=15)).date().isoformat()
        
        # Get initial available slots
        try:
            response = requests.get(f"{self.base_url}/time-slots/{self.doctor_id}/available", 
                                  params={"date": test_date, "service_id": service_id})
            
            if response.status_code == 200:
                initial_slots = response.json()
                initial_count = len(initial_slots)
                
                if initial_count > 0:
                    # Book an appointment at the first available slot
                    first_slot = initial_slots[0]
                    appointment_time = datetime.fromisoformat(first_slot["datetime"])
                    
                    headers = {"Authorization": f"Bearer {self.patient_token}"}
                    appointment_data = {
                        "doctor_id": self.doctor_id,
                        "service_id": service_id,
                        "appointment_date": appointment_time.isoformat(),
                        "notes": "Testing slot availability update"
                    }
                    
                    booking_response = requests.post(f"{self.base_url}/appointments", 
                                                   json=appointment_data, headers=headers)
                    
                    if booking_response.status_code == 200:
                        # Get available slots again after booking
                        response2 = requests.get(f"{self.base_url}/time-slots/{self.doctor_id}/available", 
                                               params={"date": test_date, "service_id": service_id})
                        
                        if response2.status_code == 200:
                            updated_slots = response2.json()
                            updated_count = len(updated_slots)
                            
                            # Check if the booked slot is no longer available
                            booked_slot_still_available = any(
                                slot["datetime"] == first_slot["datetime"] 
                                for slot in updated_slots
                            )
                            
                            if not booked_slot_still_available and updated_count < initial_count:
                                self.log_test("Available Slots Update After Booking", True, 
                                            f"Slots reduced from {initial_count} to {updated_count}")
                            else:
                                self.log_test("Available Slots Update After Booking", False, 
                                            f"Booked slot still available or count unchanged: {initial_count} -> {updated_count}")
                        else:
                            self.log_test("Available Slots Update After Booking", False, 
                                        f"Failed to get updated slots: {response2.status_code}")
                    else:
                        self.log_test("Available Slots Update After Booking", False, 
                                    f"Failed to book appointment: {booking_response.status_code}")
                else:
                    self.log_test("Available Slots Update After Booking", False, 
                                "No initial slots available for testing")
            else:
                self.log_test("Available Slots Update After Booking", False, 
                            f"Failed to get initial slots: {response.status_code}")
        except Exception as e:
            self.log_test("Available Slots Update After Booking", False, f"Error: {str(e)}")

    def test_role_based_access_control(self):
        """Test role-based permissions across the system"""
        # Already tested in individual functions, but let's do a summary test
        
        # Test admin-only endpoints
        if self.admin_token and self.patient_token:
            # Admin should be able to create services
            try:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                service_data = {
                    "name": "RBAC Test Service",
                    "description": "Testing role-based access",
                    "duration_minutes": 20,
                    "price": 30.0,
                    "category": "test"
                }
                response = requests.post(f"{self.base_url}/services", json=service_data, headers=headers)
                admin_can_create = response.status_code == 200
                
                # Patient should not be able to create services
                headers = {"Authorization": f"Bearer {self.patient_token}"}
                response = requests.post(f"{self.base_url}/services", json=service_data, headers=headers)
                patient_cannot_create = response.status_code == 403
                
                if admin_can_create and patient_cannot_create:
                    self.log_test("Role-Based Access Control", True, 
                                "Admin permissions working correctly")
                else:
                    self.log_test("Role-Based Access Control", False, 
                                f"Admin create: {admin_can_create}, Patient blocked: {patient_cannot_create}")
            except Exception as e:
                self.log_test("Role-Based Access Control", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🏥 Universal Medical Platform Backend Testing")
        print("=" * 50)
        print()
        
        # Initialize system
        if not self.test_init_data():
            print("❌ Failed to initialize system. Stopping tests.")
            return
        
        # Authentication tests
        self.test_admin_login()
        self.test_user_registration()
        self.test_user_login()
        self.test_jwt_token_validation()
        self.test_get_current_user()
        
        # User management tests
        self.test_get_doctors_list()
        
        # Medical services tests
        self.test_medical_services_crud()
        
        # Enhanced appointment system tests (NEW FEATURES)
        print("\n🔥 TESTING ENHANCED APPOINTMENT BOOKING FEATURES")
        print("-" * 50)
        self.test_doctor_working_hours_management()
        self.test_available_time_slots_api()
        self.test_default_working_hours_behavior()
        self.test_enhanced_appointment_conflict_detection()
        self.test_time_slots_update_after_bookings()
        
        # Original appointment system tests
        print("\n📅 TESTING CORE APPOINTMENT FEATURES")
        print("-" * 50)
        self.test_appointment_booking_system()
        self.test_view_appointments()
        self.test_appointment_cancellation()
        
        # Role-based access control
        self.test_role_based_access_control()
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if "✅ PASS" in result["status"])
        failed = sum(1 for result in self.test_results if "❌ FAIL" in result["status"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if "❌ FAIL" in result["status"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n🎯 CRITICAL FUNCTIONALITY STATUS:")
        critical_tests = [
            "Initialize Default Data",
            "Admin Login", 
            "Register Patient",
            "Register Doctor",
            "JWT Token Validation (Valid)",
            "Get Medical Services",
            "Set Doctor Working Hours",
            "Get Available Time Slots",
            "Duration-Aware Conflict Detection",
            "Default Working Hours (9 AM - 5 PM)",
            "Book Appointment (Patient)",
            "Role-Based Access Control"
        ]
        
        for test_name in critical_tests:
            result = next((r for r in self.test_results if r["test"] == test_name), None)
            if result:
                print(f"  {result['status']}: {test_name}")
            else:
                print(f"  ⚠️  SKIP: {test_name}")

if __name__ == "__main__":
    tester = MedicalPlatformTester()
    tester.run_all_tests()