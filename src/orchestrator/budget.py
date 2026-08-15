"""Hard cost ceiling for a run, enforced by code — not a suggestion to an agent.

The Adviser Hunter's lateral search and the two-round Verifier loop are the
main cost drivers. Under budget pressure the orchestrator stops issuing new
agent calls and finishes the run with what it has: more NOT_FOUND fields,
never exceeded spend.
"""

from dataclasses import dataclass, field


class BudgetExceeded(Exception):
    """Raised by utils.llm.run_agent before spawning a new agent call once
    the ceiling is spent. The orchestrator catches it, stops issuing work,
    and finishes the run with what it has.
    """

    def __init__(self, ceiling_usd: float, spent_usd: float):
        self.ceiling_usd = ceiling_usd
        self.spent_usd = spent_usd
        super().__init__(f"run budget exhausted: ${spent_usd:.2f} spent of ${ceiling_usd:.2f}")


@dataclass
class RunBudget:
    ceiling_usd: float
    spent_usd: float = field(default=0.0, init=False)

    def remaining(self) -> float:
        return max(0.0, self.ceiling_usd - self.spent_usd)

    def record_spend(self, actual_cost_usd: float) -> None:
        self.spent_usd += actual_cost_usd

    def check(self) -> None:
        if self.remaining() <= 0:
            raise BudgetExceeded(self.ceiling_usd, self.spent_usd)
