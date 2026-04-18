from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Station(db.Model):
    __tablename__ = "station"

    # Use the number from the API (e.g. 42) as primary key since it is already unique
    number: Mapped[int] = mapped_column(Integer, primary_key=True)

    contract_name: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(200))

    # Split the position: {lat, lng} from JSON into two fields
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    # Whether on-site card/credit card payment is supported (JCDecaux API: banking). 0=not supported, 1=supported
    banking: Mapped[bool] = mapped_column(Boolean, comment="Whether on-site card/credit card payment is supported; 0=not supported, 1=supported")
    # Whether it is a bonus station, e.g. returning bikes grants extra duration (JCDecaux API: bonus). 0=no, 1=yes
    bonus: Mapped[bool] = mapped_column(Boolean, comment="Whether it is a bonus station (returning bikes grants extra duration, etc.); 0=no, 1=yes")
    bike_stands: Mapped[int] = mapped_column(Integer)  # Total number of bike stands

    # Establish relationship for easy access to historical data via Station.availabilities
    availabilities = relationship("Availability", back_populates="station", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<Station {self.number}: {self.name}>"
