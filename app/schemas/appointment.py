from pydantic import BaseModel, Field, StrictStr
from datetime import date, time
from app.schemas.update_payload import UpdatePayload


class AppointmentCreate(BaseModel):

    patient_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f123456789abcdef123456"]
    )

    doctor_id: StrictStr = Field(
        ...,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$",
        examples=["66f987654321abcdef654321"]
    )

    appointment_date: date = Field(
        ...,
        examples=["2026-10-01"]
    )

    appointment_time: time = Field(
        ...,
        examples=["10:30"]
    )

    reason: StrictStr = Field(
        ...,
        min_length=3,
        max_length=300,
        examples=["Regular consultation"]
    )


class AppointmentUpdate(UpdatePayload):

    patient_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    doctor_id: StrictStr | None = Field(
        default=None,
        min_length=24,
        max_length=24,
        pattern=r"^[0-9a-fA-F]{24}$"
    )

    appointment_date: date | None = None

    appointment_time: time | None = None

    reason: StrictStr | None = Field(
        default=None,
        min_length=3,
        max_length=300
    )

    status: StrictStr | None = Field(
        default=None,
        examples=["scheduled"]
    )
