"""
Dynamic Tool Budgeting Engine (TASK-P3-07).

Dynamically balances, ranks, and prunes tool declarations for local models (e.g. 8B/3B)
to prevent context window exhaustion, latency spikes, and tool hallucination.
Clamps tool count (max 8-14) and character size (max 9,000 chars) for 8B models,
while delivering full toolsets to capable cloud models (Gemini / GPT-4o).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Standard capacity profiles
BUDGET_PROFILES: Dict[str, Dict[str, Optional[int]]] = {
    "cloud_flagship": {"max_tools": None, "max_chars": None},
    "full": {"max_tools": None, "max_chars": None},
    "gemini": {"max_tools": None, "max_chars": None},
    "gpt-4o": {"max_tools": None, "max_chars": None},
    "8b": {"max_tools": 12, "max_chars": 9000},
    "local_8b": {"max_tools": 12, "max_chars": 9000},
    "3b": {"max_tools": 8, "max_chars": 6000},
    "local_3b": {"max_tools": 8, "max_chars": 6000},
}

# The load-bearing core tools in order of survival priority
CORE_TOOLS_PRIORITY: Tuple[str, ...] = (
    "open_app",
    "computer_settings",
    "computer_control",
    "file_workspace",
    "web_search",
    "screen_process",
    "save_memory",
    "recall_memory",
    "reminder",
    "briefing",
    "system_metrics",
)


class ToolBudgetConfig(BaseModel):
    """Configuration for tool schema budgeting."""
    model_config = ConfigDict(extra="forbid")

    max_tools: Optional[int] = None
    max_chars: Optional[int] = None
    model_capacity: str = "full"


def extract_tool_parts(decl: Any) -> Tuple[str, str, Dict[str, Any]]:
    """Extract (name, description, parameters_dict) from various declaration formats."""
    if isinstance(decl, dict):
        if decl.get("type") == "function" and isinstance(decl.get("function"), dict):
            fn = decl["function"]
            return fn.get("name", ""), fn.get("description", ""), fn.get("parameters", {})
        name = decl.get("name") or decl.get("action_id", "")
        desc = decl.get("description", "")
        params = (
            decl.get("parameters")
            or decl.get("parameters_schema")
            or decl.get("parameters_json_schema")
            or {}
        )
        return str(name), str(desc), params if isinstance(params, dict) else {}

    # ActionDefinition or types.FunctionDeclaration
    name = getattr(decl, "name", None) or getattr(decl, "action_id", "") or ""
    desc = getattr(decl, "description", "") or ""
    params = (
        getattr(decl, "parameters_json_schema", None)
        or getattr(decl, "parameters", None)
        or {}
    )
    if hasattr(params, "model_json_schema"):
        try:
            params = params.model_json_schema()
        except Exception:
            params = {}
    elif hasattr(params, "to_json_dict"):
        try:
            params = params.to_json_dict()
        except Exception:
            params = {}
    if not isinstance(params, dict):
        params = {}
    return str(name), str(desc), params


def payload_size(decls: Iterable[Any]) -> int:
    """Calculate the total character size of a collection of tool declarations."""
    total = 0
    for d in decls:
        name, desc, params = extract_tool_parts(d)
        total += len(name) + len(desc)
        try:
            total += len(json.dumps(params))
        except Exception:
            total += 50
    return total


def budget_tools(
    tools: Sequence[Any],
    capacity_or_config: Union[str, ToolBudgetConfig] = "full",
    user_query: Optional[str] = None,
    usage_stats: Optional[Dict[str, int]] = None,
) -> List[Any]:
    """Dynamically rank, budget, and prune tool schemas based on model capacity and relevance.
    
    If model_capacity is 'full' or 'cloud_flagship', the tools are returned unchanged.
    For constrained models (e.g. '8b', '3b'), tools are ranked by:
      1. Explicit user query keyword relevance
      2. Incurred runtime usage frequency
      3. Core architectural priority
    Tools are pruned when either max_tools or max_chars is exceeded, while maintaining
    original relative declaration ordering among preserved tools.
    """
    if not tools:
        return []

    # Resolve limits
    if isinstance(capacity_or_config, ToolBudgetConfig):
        max_tools = capacity_or_config.max_tools
        max_chars = capacity_or_config.max_chars
    else:
        profile = BUDGET_PROFILES.get(
            capacity_or_config.lower(),
            BUDGET_PROFILES["full"]
        )
        max_tools = profile.get("max_tools")
        max_chars = profile.get("max_chars")

    # If no budget constraints are set, return full tools list unchanged
    if not max_tools and not max_chars:
        return list(tools)

    core_order = {name: i for i, name in enumerate(CORE_TOOLS_PRIORITY)}
    usage_map = usage_stats or {}

    query_tokens: set[str] = set()
    if user_query:
        # Extract alphanumeric words with length >= 3
        words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", user_query.lower())
        query_tokens = set(words)

    # Compute ranking scores
    def score_tool(item: Tuple[int, Any]) -> float:
        idx, decl = item
        name, desc, _ = extract_tool_parts(decl)
        name_lower = name.lower()
        desc_lower = desc.lower()

        score = 0.0

        # Query keyword matching (highest priority when relevant)
        if query_tokens:
            matches = sum(
                1 for token in query_tokens if token in name_lower or token in desc_lower
            )
            score += matches * 100.0

        # Usage frequency boost
        uses = usage_map.get(name, 0)
        score += min(uses * 10.0, 80.0)

        # Core tools priority
        if name in core_order:
            rank = core_order[name]
            score += max(50.0 - rank * 2.0, 10.0)

        # Check explicit tier attribute if present
        if isinstance(decl, dict):
            tier = str(decl.get("tier", "")).lower()
        else:
            tier = str(getattr(decl, "tier", "")).lower()
        if tier == "core":
            score += 40.0
        elif tier == "extra":
            score -= 10.0

        # Secondary tie-breaker: original index preservation
        score -= idx * 0.001
        return score

    # Sort tools descending by score
    indexed_tools = list(enumerate(tools))
    ranked_tools = sorted(indexed_tools, key=score_tool, reverse=True)

    kept_indices: List[int] = []
    accumulated_chars = 0

    for orig_idx, tool in ranked_tools:
        if max_tools is not None and len(kept_indices) >= max_tools:
            break

        cost = payload_size([tool])
        if max_chars is not None and kept_indices and (accumulated_chars + cost > max_chars):
            # Skip this tool if it would breach character budget, but keep checking smaller ones
            continue

        kept_indices.append(orig_idx)
        accumulated_chars += cost

    # Restore original declaration ordering among kept tools
    kept_indices.sort()
    return [tools[i] for i in kept_indices]

