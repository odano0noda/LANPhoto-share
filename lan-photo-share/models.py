from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime
class Base(DeclarativeBase):
    pass
class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    mime: Mapped[str] = mapped_column(String(100), default="image/jpeg")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# 初期化：
# python -c "from models import Base; from sqlalchemy import create_engine;
# engine=create_engine('sqlite:///app.db'); Base.metadata.create_all(engine)"