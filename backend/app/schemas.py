from datetime import datetime, timezone
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, field_validator


class LoginInput(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str = Field(min_length=8)


class SeriesInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    minValue: float = Field(strict=True, allow_inf_nan=False)
    maxValue: float = Field(strict=True, allow_inf_nan=False)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = None
    unit: str | None = Field(default=None, max_length=20)


class SensorInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    seriesId: UUID


class MeasurementInput(BaseModel):
    value: float = Field(strict=True, allow_inf_nan=False)
    timestamp: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("timestamp", mode="before")
    @classmethod
    def require_timestamp_string(cls, value):
        # Pydantic otherwise accepts numbers as Unix timestamps.
        if not isinstance(value, str):
            raise ValueError("timestamp must be an ISO 8601 string with a timezone")
        return value
