from datetime import date, datetime, time

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utcnow


class BusinessHours(Base):
    """Franja hábil en hora local del centro. `area_id` NULL = horario por defecto.

    Un área sin franjas propias usa el horario por defecto. Puede haber varias franjas por día
    (turno partido). Sin ninguna franja en la tabla, los minutos hábiles son minutos de reloj.
    """

    __tablename__ = "business_hours"
    __table_args__ = (Index("ix_business_hours_area_weekday", "area_id", "weekday"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))
    weekday: Mapped[int] = mapped_column(Integer)  # 0 = lunes … 6 = domingo
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)


class Holiday(Base):
    """Día no hábil. `area_id` NULL = aplica a todas las áreas."""

    __tablename__ = "holidays"
    __table_args__ = (
        UniqueConstraint(
            "day", "area_id", name="uq_holidays_day_area", postgresql_nulls_not_distinct=True
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(120))
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
