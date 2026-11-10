"""Pure stdlib contracts for profile-driven event extraction.

Profile-driven callers (the event_entity KG builder) supply all domain policy
(entity types, anchor rules, number grounding) explicitly from a validated
event extraction profile. The legacy PMS defaults below are kept only for
direct importers of these pure-stdlib helpers (fork 1.2.x compatibility).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Optional

# Fork compatibility (1.2.x): policy used when a direct importer omits every
# profile argument of parse_extraction_response(). The profile-driven builder
# never relies on these; see the branch in parse_extraction_response().
PMS_ENTITY_TYPES: list[dict] = [
    {"type": "PROJECT", "description": "项目本体，含完整项目编号"},
    {"type": "PERSON", "description": "人员，项目成员或干系人"},
    {"type": "ROLE", "description": "项目内职务或角色"},
    {"type": "ORGANIZATION", "description": "组织、部门、公司或团队"},
    {"type": "PHASE", "description": "项目阶段或状态"},
    {"type": "LOCATION", "description": "地点或区域"},
    {"type": "DATE", "description": "日期或时间"},
    {"type": "METRIC", "description": "数量、比例等指标"},
]
PROJECT_ID_RE = re.compile(r"\b[PI]-\d{6,}\b")

_ALLOWED_EVENT_KEYS = {"title", "content", "entities", "is_valid"}
_ALLOWED_ENTITY_KEYS = {"type", "name", "description"}
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![A-Za-z0-9_.])"
)


def numbers_in(text: str) -> set[str]:
    """Return numeric strings using the deterministic grounding policy."""
    return set(_NUMBER_RE.findall(text or ""))


def event_anchor(content: str, pattern: Optional[str]) -> Optional[str]:
    """Return the first configured anchor match, if any."""
    if pattern is None:
        return None
    match = re.compile(pattern).search(content or "")
    if match is None:
        return None
    if match.lastindex:
        return match.group(1)
    return match.group(0)


def event_node_name(anchor: Optional[str], title: str, content: str, *, legacy: bool = True) -> str:
    """Create a deterministic event node ID.

    ``legacy=True`` (fork 1.2.x default) preserves the anchor-prefixed ID
    scheme for callers that rely on persisted IDs; the profile-driven builder
    always passes ``legacy`` from the event profile explicitly.
    """
    if legacy:
        digest = hashlib.sha256(f"{anchor}\n{title}\n{content}".encode("utf-8")).hexdigest()[:12]
        return f"event:{anchor}:{digest}"
    digest = hashlib.sha256(
        json.dumps([anchor, title, content], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return f"event:{digest}"


def _parse_entity(entity: dict, allowed_types: set[str], dropped: dict) -> Optional[dict]:
    """Validate a single participant entity under the profile policy."""
    if not isinstance(entity, dict):
        dropped["entity_not_object"] += 1
        return None
    if set(entity) - _ALLOWED_ENTITY_KEYS:
        dropped["entity_extra_fields"] += 1
        return None
    etype = str(entity.get("type") or "").strip().upper()
    ename = str(entity.get("name") or "").strip()
    edesc = str(entity.get("description") or "").strip()
    if not etype or not ename or not edesc:
        dropped["entity_blank"] += 1
        return None
    if etype not in allowed_types:
        dropped["entity_type_unknown"] += 1
        return None
    return {"type": etype, "name": ename, "description": edesc}


def _event_rejection_reason(
    item: dict,
    *,
    evidence_numbers: set[str],
    anchor_pattern: Optional[str],
    anchor_required: bool,
    number_grounding: bool,
) -> Optional[str]:
    """Return the first contract violation of an event item, if any."""
    if not isinstance(item, dict):
        return "event_not_object"
    title = str(item.get("title") or "").strip()
    content = str(item.get("content") or "").strip()
    violations = (
        ("event_extra_fields", bool(set(item) - _ALLOWED_EVENT_KEYS)),
        ("event_blank", not title or not content),
        ("event_self_invalid", item.get("is_valid") is False),
        ("event_missing_anchor", anchor_required and event_anchor(content, anchor_pattern) is None),
        (
            "event_number_not_grounded",
            number_grounding
            and any(number not in evidence_numbers for number in numbers_in(f"{title} {content}")),
        ),
        ("event_entities_invalid", not isinstance(item.get("entities") or [], list)),
    )
    for reason, violated in violations:
        if violated:
            return reason
    return None


def _parse_event(
    item: dict,
    *,
    evidence_numbers: set[str],
    allowed_types: set[str],
    anchor_pattern: Optional[str],
    anchor_required: bool,
    number_grounding: bool,
    dropped: dict,
) -> Optional[dict]:
    """Validate a single extracted event under the profile policy."""
    reason = _event_rejection_reason(
        item,
        evidence_numbers=evidence_numbers,
        anchor_pattern=anchor_pattern,
        anchor_required=anchor_required,
        number_grounding=number_grounding,
    )
    if reason:
        dropped[reason] += 1
        return None
    title = str(item.get("title") or "").strip()
    content = str(item.get("content") or "").strip()
    entities = [
        parsed
        for entity in item.get("entities") or []
        if (parsed := _parse_entity(entity, allowed_types, dropped)) is not None
    ]
    return {
        "title": title,
        "content": content,
        "anchor": event_anchor(content, anchor_pattern),
        "entities": entities,
    }


def parse_extraction_response(
    response: str,
    *,
    chunk_content: str,
    entity_types: Optional[list[dict]] = None,
    anchor_pattern: Optional[str] = None,
    anchor_required: Optional[bool] = None,
    number_grounding: bool = True,
) -> tuple[list[dict], dict[str, int]]:
    """Parse the strict event response contract under an explicit profile policy.

    Omitted policy arguments retain the historical PMS behavior for callers
    that import this pure-stdlib helper directly (fork 1.2.x compatibility);
    the profile-driven builder always passes the full policy explicitly.

    :param response: raw LLM response
    :param chunk_content: source chunk text used for number grounding
    :param entity_types: allowed entity types from the event profile
    :param anchor_pattern: optional regex applied to the event content
    :param anchor_required: whether an event without an anchor is dropped
    :param number_grounding: whether numbers must appear in the chunk content
    :return: (valid_events, dropped_counters)
    """
    dropped: dict[str, int] = defaultdict(int)
    text = (response or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        dropped["response_not_json"] += 1
        return [], dict(dropped)
    if not isinstance(payload, dict) or set(payload) != {"type", "data"}:
        dropped["response_contract_invalid"] += 1
        return [], dict(dropped)
    data = payload.get("data")
    if not isinstance(data, dict) or set(data) != {"items"} or not isinstance(data["items"], list):
        dropped["response_contract_invalid"] += 1
        return [], dict(dropped)

    profile_policy = (
        entity_types is not None
        or anchor_pattern is not None
        or anchor_required is not None
    )
    if profile_policy:
        allowed_types = {str(item["type"]).strip().upper() for item in (entity_types or [])}
        if anchor_required is None:
            anchor_required = True
    else:
        # Fork compatibility: legacy PMS policy (see module docstring).
        allowed_types = {item["type"] for item in PMS_ENTITY_TYPES}
        anchor_pattern = PROJECT_ID_RE.pattern
        anchor_required = True
    evidence_numbers = numbers_in(chunk_content) if number_grounding else set()
    valid_events = [
        event
        for item in data["items"]
        if (
            event := _parse_event(
                item,
                evidence_numbers=evidence_numbers,
                allowed_types=allowed_types,
                anchor_pattern=anchor_pattern,
                anchor_required=anchor_required,
                number_grounding=number_grounding,
                dropped=dropped,
            )
        )
        is not None
    ]
    return valid_events, dict(dropped)
