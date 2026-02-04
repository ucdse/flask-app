from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, Boolean, BigInteger, ForeignKey, DateTime
from datetime import datetime

from extensions import db



# 1. 静态信息表 (Station)
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

    def __repr__(self):
        return f'<Station {self.number}: {self.name}>'


# 2. 动态信息表 (Availability)
class Availability(db.Model):
    __tablename__ = "availability"

    # 自增主键，因为每次抓取都是新的一行
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 外键，关联到 Station 表的 number
    number: Mapped[int] = mapped_column(ForeignKey("station.number"), nullable=False)

    available_bikes: Mapped[int] = mapped_column(Integer)
    available_bike_stands: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # 例如 "OPEN"

    # 原始的时间戳 (例如 1770047175000)，存成 BigInt 方便比对
    last_update: Mapped[int] = mapped_column(BigInteger)

    # [推荐] 再加一个转换后的 DateTime 字段，方便你写 SQL 查询 (例如查 "上周三下午的数据")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 数据请求的时间（抓取该条记录时的时间）
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="数据请求的时间")

    # 反向关联
    station = relationship("Station", back_populates="availabilities")

    def __repr__(self):
        return f'<Availability {self.number} @ {self.timestamp}>'
