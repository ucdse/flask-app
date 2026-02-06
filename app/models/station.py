from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Station(db.Model):
    __tablename__ = "station"

    # 使用 API 里的 number (例如 42) 作为主键，因为它本身就是唯一的
    number: Mapped[int] = mapped_column(Integer, primary_key=True)

    contract_name: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(200))

    # 把 JSON 里的 position: {lat, lng} 拆成两个字段
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    # 是否支持现场银行卡/信用卡支付 (JCDecaux API: banking)。0=不支持，1=支持
    banking: Mapped[bool] = mapped_column(Boolean, comment="是否支持现场银行卡/信用卡支付；0=不支持，1=支持")
    # 是否为奖励站点，如还车可获额外时长等 (JCDecaux API: bonus)。0=否，1=是
    bonus: Mapped[bool] = mapped_column(Boolean, comment="是否为奖励站点（还车可获额外时长等）；0=否，1=是")
    bike_stands: Mapped[int] = mapped_column(Integer)  # 总车桩数量

    # 建立关系，方便通过 Station.availabilities 查历史数据
    availabilities = relationship("Availability", back_populates="station", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<Station {self.number}: {self.name}>"
