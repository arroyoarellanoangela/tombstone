"""Core data model. No framework imports — testable in isolation.

The central design constraint (see docs/ARCHITECTURE_NOTE.html, section 2):
a fabricated value is an automatic fail, a well-handled "undisclosed" is a
pass. Claim is the primitive that makes that distinction structural rather
than a prompt convention.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ClaimStatus(StrEnum):
    VERIFIED = "verified"
    EXPLICITLY_UNDISCLOSED = "explicitly_undisclosed"
    NOT_FOUND = "not_found"


class Claim(BaseModel):
    """A single field's value, always paired with the source that grounds it.

    A `verbatim_quote` is mandatory for every status except NOT_FOUND — this
    is enforced below, not left as a prompt instruction an agent can drop.
    """

    field: str
    status: ClaimStatus
    value: str | None = None
    source_url: str | None = None
    verbatim_quote: str | None = None
    source_language: str | None = None
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    verified: bool = False

    @model_validator(mode="after")
    def _quote_required_unless_not_found(self) -> "Claim":
        if self.status != ClaimStatus.NOT_FOUND and not self.verbatim_quote:
            raise ValueError(
                f"Claim for '{self.field}' has status={self.status} but no "
                "verbatim_quote — every non-empty claim must cite its source text."
            )
        return self


class AcquirerProfile(BaseModel):
    """Declarative Discovery config for one acquirer — no logic, just scope."""

    name: str
    slug: str
    allowed_domains: list[str]
    primary_language: str = "en"
    source_type: str = "press_room"  # e.g. "press_room" | "regulatory_filing"
    notes: str | None = None


class DealCandidate(BaseModel):
    """Discovery's raw, uninterpreted output — never a deal, just a lead."""

    acquirer_slug: str
    url: str
    published_at: datetime | None = None
    snippet: str


class DealRecord(BaseModel):
    """A researched acquisition. Every field below is a Claim, not a bare value."""

    deal_id: str
    acquirer: Claim
    target: Claim
    date_announced: Claim
    target_description: Claim
    geography: Claim
    adviser: Claim
    purchase_price: Claim
    confidence: float | None = None  # set by the Scorer, never by an agent
    source_urls: list[str] = Field(default_factory=list)
    # Every claim the Verifier rejected, and why. Carried on the record
    # itself so a rejection is visible in the snapshot and the dashboard —
    # the system under-claiming is the feature being demonstrated, and a
    # downgrade that only ever reached a server log would be invisible
    # exactly where it matters most.
    conflicts: list[str] = Field(default_factory=list)


class Omission(BaseModel):
    """A candidate or source excluded on purpose — rendered in the dashboard's
    Omissions tab, not just noted in a README. "If in doubt, leave it out and
    say so" as a UI artifact, not a line of prose.
    """

    url: str
    reason: str
    stage: str  # e.g. "allowlist" | "deal_definition" | "window"
