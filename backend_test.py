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

        # Test booking appointment as patient
        try:
            headers = {"Authorization": f"Bearer {self.patient_token}"}
            appointment_date = datetime.utcnow() + timedelta(days=1)
            appointment_data = {
                "doctor_id": self.doctor_id,
                "service_id": service_id,
                "appointment_date": appointment_date.isoformat(),
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
        
        # Appointment system tests
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