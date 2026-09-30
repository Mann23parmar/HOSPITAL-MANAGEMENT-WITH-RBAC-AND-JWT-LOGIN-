# 🏥 Hospital Management System

A backend Hospital Management System built with **FastAPI** and **MongoDB**.

## 🚀 Tech Stack

- Python
- FastAPI
- MongoDB
- Pydantic
- JWT Authentication
- bcrypt
- RBAC
- PyMongo

## ✨ Features

- 🔐 JWT Authentication
- 👥 Role-Based Access Control (RBAC)
- 👨‍⚕️ Doctor Management
- 👩‍⚕️ Nurse Management
- 🧑‍💼 User Management
- 🧑‍🤝‍🧑 Patient Management
- 📅 Appointment Management
- 📝 Medical Records
- 💊 Prescription Management
- 💉 Patient Vitals
- 🏥 Department Management
- 💊 Medicine Management
- ✅ Data & Business Validation
- 🔄 Partial Update Support

## 👤 User Roles

| Role | Responsibilities |
|------|------------------|
| **Admin** | Manage users and overall system |
| **Doctor** | Medical records and prescriptions |
| **Nurse** | Patient vitals and patient care |
| **Receptionist** | Patients and appointments |

## 🔐 Authentication & Authorization

```text
Admin creates user
       ↓
User Login
       ↓
JWT Token
       ↓
Swagger Authorize
       ↓
RBAC checks user role
       ↓
Access allowed / denied