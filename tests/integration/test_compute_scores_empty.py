from __future__ import annotations

import pytest
import sqlalchemy as sa

from climate_esg.config import get_settings

EMPTY_SCENARIO = "__test_empty_scenario__"


def _postgres_available() -> bool:
    try:
        engine = sa.create_engine(
            get_settings().sqlalchemy_url, connect_args={"connect_timeout": 3}
        )
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _postgres_available(), reason="Postgres indisponível"),
]


@pytest.fixture()
def empty_scenario():
    from climate_esg.db.base import session_scope
    from climate_esg.db.models import DimModelRun, DimScenario, FactClimateIndicator

    with session_scope() as session:
        session.execute(sa.delete(DimScenario).where(DimScenario.name == EMPTY_SCENARIO))
        max_sk = session.scalar(sa.select(sa.func.max(DimScenario.scenario_sk))) or 0
        max_run = session.scalar(sa.select(sa.func.max(DimModelRun.run_sk))) or 0
        session.add(DimScenario(scenario_sk=max_sk + 101, framework="TEST", name=EMPTY_SCENARIO))

    yield EMPTY_SCENARIO

    with session_scope() as session:
        scenario_sk = session.scalar(
            sa.select(DimScenario.scenario_sk).where(DimScenario.name == EMPTY_SCENARIO)
        )
        if scenario_sk is not None:
            session.execute(
                sa.delete(FactClimateIndicator).where(
                    FactClimateIndicator.scenario_sk == scenario_sk
                )
            )
            session.execute(sa.delete(DimScenario).where(DimScenario.scenario_sk == scenario_sk))
        session.execute(sa.delete(DimModelRun).where(DimModelRun.run_sk > max_run))


def test_flow_falha_sem_fact_climate_indicator(empty_scenario):
    from pipelines.flows.compute_scores import compute_all

    from climate_esg.db.base import session_scope
    from climate_esg.db.models import DimModelRun, DimScenario, FactClimateIndicator
    from climate_esg.modeling.physical_config import PHYSICAL_MODEL_NAME

    with session_scope() as session:
        scenario_sk = session.scalar(
            sa.select(DimScenario.scenario_sk).where(DimScenario.name == empty_scenario)
        )
        indicators = session.scalar(
            sa.select(sa.func.count())
            .select_from(FactClimateIndicator)
            .where(FactClimateIndicator.scenario_sk == scenario_sk)
        )
        assert indicators == 0

    with pytest.raises(RuntimeError, match="min_companies_scored"):
        compute_all(empty_scenario, (2030,))

    with session_scope() as session:
        status = session.scalar(
            sa.select(DimModelRun.status)
            .where(DimModelRun.model_name == PHYSICAL_MODEL_NAME)
            .order_by(DimModelRun.run_sk.desc())
            .limit(1)
        )
        assert status in ("empty", "failed")
        assert status != "success"


def test_score_physical_falha_cenario_inexistente():
    from pipelines.flows.compute_scores import score_physical

    with pytest.raises(RuntimeError, match="não existe"):
        score_physical.fn("__cenario_que_nao_existe__", 2030)
