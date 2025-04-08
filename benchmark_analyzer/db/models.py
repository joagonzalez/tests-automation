# db/models.py
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class TestRun(Base):
    """Model for test run metadata."""
    __tablename__ = "test_runs"

    test_run_id = Column(Integer, primary_key=True)
    test_type_id = Column(Integer, ForeignKey("test_types.test_type_id"))
    environment_id = Column(Integer, ForeignKey("environments.environment_id"))
    hw_bom_id = Column(Integer, ForeignKey("hw_bom.bom_id"))
    sw_bom_id = Column(Integer, ForeignKey("sw_bom.bom_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    engineer = Column(String)
    comments = Column(String)
    configuration = Column(JSON)

    # Relationships
    test_type = relationship("TestType", back_populates="test_runs")
    environment = relationship("Environment", back_populates="test_runs")
    hw_bom = relationship("HardwareBOM")
    sw_bom = relationship("SoftwareBOM")

class TestType(Base):
    """Model for test types."""
    __tablename__ = "test_types"

    test_type_id = Column(Integer, primary_key=True)
    test_type = Column(String, unique=True)
    description = Column(String)
    schema_version = Column(String)

    test_runs = relationship("TestRun", back_populates="test_type")

class ResultsMemoryBandwidth(Base):
    """Model for memory bandwidth test results."""
    __tablename__ = "results_memory_bandwidth"

    result_id = Column(Integer, primary_key=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.test_run_id"))
    test_name = Column(String)
    read_bw = Column(Float)
    write_bw = Column(Float)
    timestamp = Column(DateTime)

class ResultsCpuLatency(Base):
    """Model for CPU latency test results."""
    __tablename__ = "results_cpu_latency"

    result_id = Column(Integer, primary_key=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.test_run_id"))
    test_name = Column(String)
    average_ns = Column(Float)
    latencies_ns = Column(JSON)
    timestamp = Column(DateTime)

class HardwareBOM(Base):
    """Model for hardware Bill of Materials."""
    __tablename__ = "hw_bom"

    bom_id = Column(Integer, primary_key=True)
    name = Column(String)
    version = Column(String)
    specs = Column(JSON)

class SoftwareBOM(Base):
    """Model for software Bill of Materials."""
    __tablename__ = "sw_bom"

    bom_id = Column(Integer, primary_key=True)
    name = Column(String)
    version = Column(String)
    specs = Column(JSON)

class Environment(Base):
    """Model for test environments."""
    __tablename__ = "environments"

    environment_id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    type = Column(String)
    comments = Column(String)
    tools = Column(JSON)
    # Change 'metadata' to 'env_metadata' or another name
    env_metadata = Column(JSON)  # Changed from metadata to env_metadata

    test_runs = relationship("TestRun", back_populates="environment")

class AcceptanceCriteria(Base):
    """Model for test acceptance criteria."""
    __tablename__ = "acceptance_criteria"

    criteria_id = Column(Integer, primary_key=True)
    test_type_id = Column(Integer, ForeignKey("test_types.test_type_id"))
    metric = Column(String)
    threshold = Column(Float)
    operator = Column(String)
    target_component = Column(String)
