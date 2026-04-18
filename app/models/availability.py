from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Availability(db.Model):
    __tablename__ = "availability"

    # Auto-incrementing primary key because each scrape creates a new row
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key, references Station table's number
    number: Mapped[int] = mapped_column(ForeignKey("station.number"), nullable=False)

    available_bikes: Mapped[int] = mapped_column(Integer)
    available_bike_stands: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # e.g. "OPEN"

    # Raw timestamp (e.g. 1770047175000), stored as BigInt for easy comparison
    last_update: Mapped[int] = mapped_column(BigInteger)

    # [Recommended] Add a converted DateTime field for easier SQL queries (e.g. querying "Wednesday afternoon data last week")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Time when the data was requested (time when this record was scraped)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="Time when the data was requested")

    # Reverse relationship
    station = relationship("Station", back_populates="availabilities")

    def __repr__(self) -> str:
        return f"<Availability {self.number} @ {self.timestamp}>"
