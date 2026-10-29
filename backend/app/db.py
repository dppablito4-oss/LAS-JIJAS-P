import json
from pathlib import Path
from sqlalchemy import create_engine, String, Text, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings
from .schemas import now

Path('data').mkdir(exist_ok=True)
engine = create_engine(settings.database_url, connect_args={'check_same_thread': False})
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase): pass


class Job(Base):
    __tablename__ = 'analyses'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True)
    digest: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    request: Mapped[str] = mapped_column(Text)
    report: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Cache(Base):
    __tablename__ = 'cache'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    expires: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)


class Usage(Base):
    __tablename__ = 'api_usage'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    scope: Mapped[str] = mapped_column(String, index=True)
    provider: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    retrieved_at: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)


def record_usage(scope, provider, model, value):
    import uuid
    with Session.begin() as db:
        db.add(Usage(id=str(uuid.uuid4()),scope=scope,provider=provider,model=model,
                     retrieved_at=now().isoformat(),value=json.dumps(value)))


def init():
    Base.metadata.create_all(engine)
    with Session.begin() as db:
        db.execute(update(Job).where(Job.status.in_(['queued','running'])).values(
            status='interrupted', error='El proceso se reinició. Crea una revisión para continuar; no se repiten cargos automáticamente.'))


def serial(job):
    with Session() as db:
        usage=[{'provider':u.provider,'model':u.model,'retrieved_at':u.retrieved_at,'usage':json.loads(u.value)}
               for u in db.scalars(select(Usage).where(Usage.scope==job.id))]
    return {'id':job.id, 'created_at':job.created_at, 'status':job.status,
            'request':json.loads(job.request), 'report':json.loads(job.report) if job.report else None,
            'error':job.error,'api_usage':usage}
