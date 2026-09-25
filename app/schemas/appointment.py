from pydantic import BaseModel, Field

#this schema is for to create appointment
class AppointmentCreate(BaseModel):

    patient_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        description="MongoDB patient ID",
        examples=["6ab4bf465142012b9d33db70"]
    )

    doctor: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Doctor name",
        examples=["Dr. Patel"]
    )

    date: str = Field(
        ...,
        description="Appointment date in YYYY-MM-DD format",
        examples=["2026-09-25"]
    )

    time: str = Field(
        ...,
        description="Appointment time in HH:MM format",
        examples=["10:30"]
    )

    reason: str = Field(
        ...,
        min_length=2,
        max_length=300,
        description="Reason for appointment",
        examples=["Regular checkup"]
    )


#this schema is to update appointment

class AppointmentUpdate(BaseModel):

    patient_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["6ab4bf465142012b9d33db70"]
    )

    doctor: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Dr. Patel"]
    )

    date: str = Field(
        ...,
        examples=["2026-09-25"]
    )

    time: str = Field(
        ...,
        examples=["10:30"]
    )

    reason: str = Field(
        ...,
        min_length=2,
        max_length=300,
        examples=["Regular checkup"]
    )