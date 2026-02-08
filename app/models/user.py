from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class User(db.Model):
    __tablename__ = "user"

    # 自增主键 ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 用户名：唯一且建立索引，方便快速查找
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # 邮箱：唯一且建立索引，用于登录或找回密码
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    # 密码哈希值：注意永远不要存储明文密码，预留足够的长度 (如 128 或 256) 存储 hash 字符串
    password_hash: Mapped[str] = mapped_column(String(256))

    # 头像 URL (可选)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 账户状态：是否激活 (例如邮箱验证后为 True)；新注册用户默认为未激活
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="账户是否激活；0=禁用，1=激活")

    # 邮箱验证码：注册/重发时生成 6 位数字，激活后清空；仅最新一次有效；暂不发邮件，仅输出到控制台
    email_verification_code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    # 验证码过期时间（如 5 分钟后）；激活时校验
    email_verification_code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # 最近一次发送验证码的时间，用于限频（如每分钟最多请求一次）
    email_verification_code_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # 激活链接用 Token：邮件中带 /activate/:token，点击即激活；与验证码同效、同过期
    activation_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    # 令牌版本号：logout 时递增，使旧 access/refresh token 立即失效
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 创建时间：使用数据库层面的默认值 (server_default)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 更新时间：每次更新记录时自动刷新时间
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<User {self.id}: {self.username}>"
