"""Hard cost ceiling for a run, enforced by code — not a suggestion to an agent.

The Adviser Hunter's lateral search and the two-round Verifier loop are the
main cost drivers. Under budget pressure the orchestrator stops issuing new
agent calls and finishes the run with what it has: more NOT_FOUND fields,
never exceeded spend.
"""

from dataclasses import dataclass, field


@dataclass
class RunBudget:
    ceiling_usd: float
    spent_usd: float = field(default=0.0, init=False)

    def remaining(self) -> float:
        return max(0.0, self.ceiling_usd - self.spent_usd)

    def can_afford(self, estimated_cost_usd: float) -> bool:
        return self.remaining() >= estimated_cost_usd

    def record_spend(self, actual_cost_usd: float) -> None:
        self.spent_usd += actual_cost_usd
