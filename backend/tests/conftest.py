from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.common.models  # noqa: F401
import app.modules.attendance.models  # noqa: F401
import app.modules.auth.models  # noqa: F401
import app.modules.employees.models  # noqa: F401
import app.modules.evaluations.models  # noqa: F401
import app.modules.incentives.models  # noqa: F401
import app.modules.kpi_templates.models  # noqa: F401
import app.modules.org.models  # noqa: F401
import app.modules.transfers.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

settings = get_settings()
_base_url, _, _db_name = settings.database_url.rpartition("/")
TEST_DATABASE_URL = f"{_base_url}/ems_test"
_ADMIN_DATABASE_URL = f"{_base_url}/postgres"


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    admin_engine = create_engine(_ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'ems_test'")).first()
        if exists is None:
            conn.execute(text("CREATE DATABASE ems_test"))
    admin_engine.dispose()

    test_engine = create_engine(TEST_DATABASE_URL)
    with test_engine.begin() as conn:
        # Required by position_rates/employee_salaries EXCLUDE constraints + employees
        # trigram name indexes — mirrors the Phase 2 migration since this fixture builds
        # the schema from ORM metadata (create_all) rather than running alembic.
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.create_all(test_engine)
    with test_engine.begin() as conn:
        # The ems_test database persists across local pytest runs (only row data is
        # truncated between tests), so these ADD CONSTRAINT calls must be idempotent
        # too, same as create_all above.
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'ck_position_rates_no_overlap'
                    ) THEN
                        ALTER TABLE position_rates
                        ADD CONSTRAINT ck_position_rates_no_overlap
                        EXCLUDE USING gist (
                            position_id WITH =,
                            daterange(effective_from, effective_to, '[)') WITH &&
                        );
                    END IF;
                END $$;
                """
            )
        )
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'ck_employee_salaries_no_overlap'
                    ) THEN
                        ALTER TABLE employee_salaries
                        ADD CONSTRAINT ck_employee_salaries_no_overlap
                        EXCLUDE USING gist (
                            employee_id WITH =,
                            daterange(effective_from, effective_to, '[)') WITH &&
                        );
                    END IF;
                END $$;
                """
            )
        )
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'ck_kpi_template_assignments_no_overlap'
                    ) THEN
                        ALTER TABLE kpi_template_assignments
                        ADD CONSTRAINT ck_kpi_template_assignments_no_overlap
                        EXCLUDE USING gist (
                            position_id WITH =,
                            daterange(effective_from, effective_to, '[)') WITH &&
                        );
                    END IF;
                END $$;
                """
            )
        )
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    with engine.begin() as conn:
        table_names = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
