from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from typing_extensions import Annotated

SearchMode = Literal["search", "news", "research", "price", "compare"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WebSearchRequest(StrictModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    mode: SearchMode = "search"
    items: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]] = Field(
        default_factory=list,
        max_length=8,
    )
    aspect: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] = "general"

    @field_validator("items")
    @classmethod
    def require_distinct_items(cls, items: list[str]) -> list[str]:
        if len(set(item.casefold() for item in items)) != len(items):
            raise ValueError("Comparison items must be unique")
        return items


class WebSearchSource(StrictModel):
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_public_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in ("https", "http") or not parsed.hostname:
            raise ValueError("Source URL must be an HTTP or HTTPS address")
        return value


class WebSearchResponse(StrictModel):
    query: str = Field(min_length=1, max_length=4000)
    mode: SearchMode
    answer: str = Field(min_length=1, max_length=20000)
    sources: list[WebSearchSource] = Field(max_length=30)
