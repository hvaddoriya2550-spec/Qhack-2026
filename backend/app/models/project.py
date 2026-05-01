import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)

    # Customer & property
    customer_name = Column(String(255), nullable=True)
    date_of_birth = Column(String(10), nullable=True)  # ISO YYYY-MM-DD
    postal_code = Column(String(10), nullable=True)
    city = Column(String(255), nullable=True)
    product_interest = Column(String(255), nullable=True)
    household_size = Column(Integer, nullable=True)
    house_type = Column(String(100), nullable=True)
    build_year = Column(Integer, nullable=True)
    roof_orientation = Column(String(50), nullable=True)
    electricity_kwh_year = Column(Integer, nullable=True)
    heating_type = Column(String(100), nullable=True)
    monthly_energy_bill_eur = Column(Integer, nullable=True)
    existing_assets = Column(String(255), nullable=True)
    financial_profile = Column(String(255), nullable=True)
    notes = Column(String, nullable=True)

    # Agent-generated data
    recommendations = Column(JSON, default=list)
    competitors = Column(JSON, default=list)
    research_data = Column(JSON, default=dict)
    strategy_notes = Column(JSON, default=dict)

    # Uploaded documents — list of {filename, text, uploaded_at}
    documents = Column(JSON, default=list)

    status = Column(String(50), default="data_gathering")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="project")
