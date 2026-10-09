from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, TypeDecorator, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """SQLite no guarda zona horaria: guardamos UTC y la restauramos al leer."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN201
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN201
        return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    documents: Mapped[list["Document"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    doc_type: Mapped[str] = mapped_column(String(20), default="other")  # tos | privacy | other

    company: Mapped[Company] = relationship(back_populates="documents")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    analyzed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)
    # última vez que se volvió a pedir este análisis y el texto seguía idéntico (cache hit)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    source: Mapped[str] = mapped_column(String(10))  # live | wayback
    snapshot_ts: Mapped[str | None] = mapped_column(String(14), nullable=True)  # YYYYMMDDhhmmss (Wayback)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(100))
    rubric_version: Mapped[str] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    count_green: Mapped[int] = mapped_column(Integer, default=0)
    count_yellow: Mapped[int] = mapped_column(Integer, default=0)
    count_red: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0 (peor) – 100 (mejor)

    document: Mapped[Document] = relationship(back_populates="analyses")
    clauses: Mapped[list["Clause"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="Clause.idx"
    )


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(10))  # green | yellow | red
    category: Mapped[str] = mapped_column(String(50))
    explanation: Mapped[str] = mapped_column(Text)

    analysis: Mapped[Analysis] = relationship(back_populates="clauses")


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    old_analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"))
    new_analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes: Mapped[list] = mapped_column(JSON, default=list)
