import pytest

from src.orchestrator.budget import BudgetExceeded, RunBudget
from src.utils.llm import run_agent


def test_remaining_decreases_with_spend():
    budget = RunBudget(ceiling_usd=1.00)
    budget.record_spend(0.30)
    budget.record_spend(0.30)
    assert budget.remaining() == pytest.approx(0.40)


def test_remaining_never_negative():
    budget = RunBudget(ceiling_usd=0.10)
    budget.record_spend(5.00)
    assert budget.remaining() == 0.0


def test_check_passes_under_ceiling():
    budget = RunBudget(ceiling_usd=1.00)
    budget.record_spend(0.50)
    budget.check()  # must not raise


def test_check_raises_once_exhausted():
    budget = RunBudget(ceiling_usd=0.10)
    budget.record_spend(0.10)
    with pytest.raises(BudgetExceeded):
        budget.check()


@pytest.mark.asyncio
async def test_run_agent_refuses_to_spawn_over_budget():
    # The ceiling check happens before the SDK subprocess is created, so an
    # exhausted budget raises immediately — no network, no key, no cost.
    budget = RunBudget(ceiling_usd=0.01)
    budget.record_spend(0.01)

    with pytest.raises(BudgetExceeded):
        await run_agent(prompt="x", system_prompt="x", budget=budget)
