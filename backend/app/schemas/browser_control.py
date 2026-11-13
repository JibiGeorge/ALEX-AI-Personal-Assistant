"""
Schemas for Browser Automation (TASK-GAP-01 / GAP-01).

Supports web navigation, search, and Playwright DOM interaction.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class BrowserControlParameters(BaseModel):
    """Parameters for browser automation actions."""
    model_config = ConfigDict(extra="ignore")

    action: str = Field(
        ...,
        description="The browser operation to perform: go_to | search | click | type | scroll | fill_form | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all",
    )
    browser: Optional[str] = Field(
        default=None,
        description="Target browser: chrome | edge | firefox | opera | operagx | brave | vivaldi | safari. Omit to use the currently active or default browser.",
    )
    url: Optional[str] = Field(
        default=None,
        description="Target URL for go_to or new_tab action.",
    )
    query: Optional[str] = Field(
        default=None,
        description="Search query string for search action.",
    )
    engine: Optional[str] = Field(
        default="google",
        description="Search engine for search action: google | bing | duckduckgo | yandex.",
    )
    selector: Optional[str] = Field(
        default=None,
        description="CSS or text selector for click or type actions.",
    )
    text: Optional[str] = Field(
        default=None,
        description="Text content for type action.",
    )
    direction: Optional[str] = Field(
        default="down",
        description="Scroll direction: down | up.",
    )
    amount: Optional[int] = Field(
        default=500,
        description="Scroll amount in pixels.",
    )
    fields: Optional[Dict[str, str]] = Field(
        default=None,
        description="Key-value mapping of selectors and values for fill_form action.",
    )
    key: Optional[str] = Field(
        default="Enter",
        description="Keyboard key to press for press action.",
    )
    clear_first: Optional[bool] = Field(
        default=True,
        description="Whether to clear input field before typing.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Semantic description of the target element for smart interaction.",
    )
    target: Optional[str] = Field(
        default=None,
        description="Target browser name for switch action.",
    )

