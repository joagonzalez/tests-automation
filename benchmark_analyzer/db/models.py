"""Database models for benchmark analyzer."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    JSON,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    CHAR,
    VARCHAR,
    DOUBLE,
    TIMESTAMP,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import CHAR as MYSQL_CHAR, TINYINT

Base = declarative_base()


def generate_uuid() -> str:
    """Generate UUID string."""
    return str(uuid.uuid4())


class Operator(Base):
    """Operator lookup table."""

    __tablename__ = "operators"

    op_id: Mapped[int] = mapped_column(TINYINT, primary_key=True)
    code: Mapped[str] = mapped_column(VARCHAR(8), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(VARCHAR(64), nullable=True)

    # Relationships
    acceptance_criteria = relationship("AcceptanceCriteria", back_populates="operator")

    def __repr__(self) -> str:
        return f"<Operator(op_id={self.op_id}, code='{self.code}')>"


class TestType(Base):
    """Test type definitions."""

    __tablename__ = "test_types"

    test_type_id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(VARCHAR(64), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    test_runs = relationship("TestRun", back_populates="test_type")
    acceptance_criteria = relationship("AcceptanceCriteria", back_populates="test_type")

    def __repr__(self) -> str:
        return f"<TestType(test_type_id='{self.test_type_id}', name='{self.name}')>"


class Environment(Base):
    """Environment definitions."""

    __tablename__ = "environments"

    id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    type: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tools: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    env_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint("JSON_VALID(tools)", name="chk_env_tools_valid"),
        CheckConstraint("JSON_VALID(env_metadata)", name="chk_env_metadata_valid"),
    )

    # Relationships
    test_runs = relationship("TestRun", back_populates="environment")

    def __repr__(self) -> str:
        return f"<Environment(id='{self.id}', name='{self.name}', type='{self.type}')>"


class HardwareBOM(Base):
    """Hardware Bill of Materials."""

    __tablename__ = "hw_bom"

    bom_id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36), primary_key=True, default=generate_uuid
    )
    specs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Constraints
    __table_args__ = (CheckConstraint("JSON_VALID(specs)", name="chk_hw_specs_valid"),)

    # Relationships
    test_runs = relationship("TestRun", back_populates="hw_bom")

    def __repr__(self) -> str:
        return f"<HardwareBOM(bom_id='{self.bom_id}')>"


class SoftwareBOM(Base):
    """Software Bill of Materials."""

    __tablename__ = "sw_bom"

    bom_id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36), primary_key=True, default=generate_uuid
    )
    specs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    kernel_version: Mapped[Optional[str]] = mapped_column(
        VARCHAR(50),
        nullable=True,
        # Generated column based on JSON extract
        server_default=text("(JSON_UNQUOTE(JSON_EXTRACT(specs, '$.kernel_version')))"),
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("JSON_VALID(specs)", name="chk_sw_specs_valid"),
        Index("idx_sw_kernel", "kernel_version"),
    )

    # Relationships
    test_runs = relationship("TestRun", back_populates="sw_bom")

    def __repr__(self) -> str:
        return f"<SoftwareBOM(bom_id='{self.bom_id}', kernel_version='{self.kernel_version}')>"


class TestRun(Base):
    """Test run fact table."""

    __tablename__ = "test_runs"

    test_run_id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36), primary_key=True, default=generate_uuid
    )
    test_type_id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36), ForeignKey("test_types.test_type_id"), nullable=False
    )
    environment_id: Mapped[Optional[str]] = mapped_column(
        MYSQL_CHAR(36), ForeignKey("environments.id"), nullable=True
    )
    hw_bom_id: Mapped[Optional[str]] = mapped_column(
        MYSQL_CHAR(36), ForeignKey("hw_bom.bom_id"), nullable=True
    )
    sw_bom_id: Mapped[Optional[str]] = mapped_column(
        MYSQL_CHAR(36), ForeignKey("sw_bom.bom_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.current_timestamp()
    )
    engineer: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint("JSON_VALID(configuration)", name="chk_test_run_config_valid"),
        Index("idx_test_runs_created", "created_at"),
    )

    # Relationships
    test_type = relationship("TestType", back_populates="test_runs")
    environment = relationship("Environment", back_populates="test_runs")
    hw_bom = relationship("HardwareBOM", back_populates="test_runs")
    sw_bom = relationship("SoftwareBOM", back_populates="test_runs")
    results_cpu_mem = relationship("ResultsCpuMem", back_populates="test_run")

    def __repr__(self) -> str:
        return f"<TestRun(test_run_id='{self.test_run_id}', created_at='{self.created_at}')>"


class ResultsCpuMem(Base):
    """Results for CPU and Memory tests."""

    __tablename__ = "results_cpu_mem"

    test_run_id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36),
        ForeignKey("test_runs.test_run_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Memory metrics
    memory_idle_latency_ns: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    memory_peak_injection_bandwidth_mbs: Mapped[Optional[float]] = mapped_column(
        DOUBLE, nullable=True
    )
    ramspeed_smp_bandwidth_mbs_add: Mapped[Optional[float]] = mapped_column(
        DOUBLE, nullable=True
    )
    ramspeed_smp_bandwidth_mbs_copy: Mapped[Optional[float]] = mapped_column(
        DOUBLE, nullable=True
    )
    sysbench_ram_memory_bandwidth_mibs: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    sysbench_ram_memory_test_duration_sec: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    sysbench_ram_memory_test_mode: Mapped[Optional[str]] = mapped_column(
        VARCHAR(8), nullable=True
    )

    # CPU metrics
    sysbench_cpu_events_per_second: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    sysbench_cpu_duration_sec: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    sysbench_cpu_test_mode: Mapped[Optional[str]] = mapped_column(
        VARCHAR(16), nullable=True
    )

    # Relationships
    test_run = relationship("TestRun", back_populates="results_cpu_mem")

    def __repr__(self) -> str:
        return f"<ResultsCpuMem(test_run_id='{self.test_run_id}')>"


class AcceptanceCriteria(Base):
    """Acceptance criteria for test results."""

    __tablename__ = "acceptance_criteria"

    id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36), primary_key=True, default=generate_uuid
    )
    test_type_id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36), ForeignKey("test_types.test_type_id"), nullable=False
    )
    metric: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    op_id: Mapped[int] = mapped_column(
        TINYINT, ForeignKey("operators.op_id"), nullable=False
    )
    threshold_min: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    threshold_max: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    target_component: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)

    # Relationships
    test_type = relationship("TestType", back_populates="acceptance_criteria")
    operator = relationship("Operator", back_populates="acceptance_criteria")

    def __repr__(self) -> str:
        return f"<AcceptanceCriteria(id='{self.id}', metric='{self.metric}')>"


# View for test runs summary (read-only)
class TestRunsSummaryView(Base):
    """View for test runs summary."""

    __tablename__ = "v_test_runs_summary"

    test_run_id: Mapped[str] = mapped_column(MYSQL_CHAR(36), primary_key=True)
    test_type_id: Mapped[str] = mapped_column(MYSQL_CHAR(36))
    environment_id: Mapped[Optional[str]] = mapped_column(MYSQL_CHAR(36))
    hw_bom_id: Mapped[Optional[str]] = mapped_column(MYSQL_CHAR(36))
    sw_bom_id: Mapped[Optional[str]] = mapped_column(MYSQL_CHAR(36))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    engineer: Mapped[Optional[str]] = mapped_column(VARCHAR(64))
    comments: Mapped[Optional[str]] = mapped_column(Text)
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    kernel_version: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    test_name: Mapped[Optional[str]] = mapped_column(VARCHAR(64))

    # This is a view, so we don't want SQLAlchemy to create it
    __table_args__ = {"info": {"is_view": True}}

    def __repr__(self) -> str:
        return f"<TestRunsSummaryView(test_run_id='{self.test_run_id}', test_name='{self.test_name}')>"


# Model registry for dynamic access
MODEL_REGISTRY = {
    "operators": Operator,
    "test_types": TestType,
    "environments": Environment,
    "hw_bom": HardwareBOM,
    "sw_bom": SoftwareBOM,
    "test_runs": TestRun,
    "results_cpu_mem": ResultsCpuMem,
    "acceptance_criteria": AcceptanceCriteria,
    "v_test_runs_summary": TestRunsSummaryView,
}
