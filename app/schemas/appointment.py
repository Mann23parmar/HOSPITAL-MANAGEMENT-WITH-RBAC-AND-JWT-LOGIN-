from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):

    patient_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["66f123456789abcdef123456"]
    )

    doctor_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["66f987654321abcdef654321"]
    )

    appointment_date: str = Field(
        ...,
        examples=["2026-10-01"]
    )

    appointment_time: str = Field(
        ...,
        examples=["10:30"]
    )

    reason: str = Field(
        ...,
        min_length=3,
        max_length=300,
        examples=["Regular consultation"]
    )


class AppointmentUpdate(BaseModel):

    patient_id: str = Field(
        ...,
        min_length=24,
        max_length=24
    )

    doctor_id: str = Field(
        ...,
        min_length=24,
        max_length=24
    )

    appointment_date: str

    appointment_time: str

    reason: str = Field(
        ...,
        min_length=3,
        max_length=300
    )

    status: str = Field(
        ...,
        examples=["scheduled"]
    )