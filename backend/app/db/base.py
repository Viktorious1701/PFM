"""Declarative base. Import models here so Alembic autogenerate sees them."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
