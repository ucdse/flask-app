from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


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
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 数据请求的时间（抓取该条记录时的时间）
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="数据请求的时间")

    # 反向关联
    station = relationship("Station", back_populates="availabilities")

    def __repr__(self) -> str:
        return f"<Availability {self.number} @ {self.timestamp}>"
