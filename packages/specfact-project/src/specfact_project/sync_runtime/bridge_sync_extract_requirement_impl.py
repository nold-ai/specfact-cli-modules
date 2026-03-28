"""Extract requirement text from proposal (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import re
from typing import Any


ERFP_SKIP_TITLES = frozenset(
    {
        "architecture overview",
        "purpose",
        "introduction",
        "overview",
        "documentation",
        "testing",
        "security & quality",
        "security and quality",
        "non-functional requirements",
        "three-phase delivery",
        "additional context",
        "platform roadmap",
        "similar implementations",
        "required python packages",
        "optional packages",
        "known limitations & mitigations",
        "known limitations and mitigations",
        "security model",
        "update required",
    }
)

ERFP_VERBS_THIRD_PERSON = {
    "support": "supports",
    "store": "stores",
    "manage": "manages",
    "provide": "provides",
    "implement": "implements",
    "enable": "enables",
    "allow": "allows",
    "use": "uses",
    "create": "creates",
    "handle": "handles",
    "follow": "follows",
}

ERFP_VERBS_LOWER_FIRST = frozenset(
    {
        "uses",
        "use",
        "provides",
        "provide",
        "stores",
        "store",
        "supports",
        "support",
        "enforces",
        "enforce",
        "allows",
        "allow",
        "leverages",
        "leverage",
        "adds",
        "add",
        "can",
        "custom",
        "supported",
        "zero-configuration",
    }
)


def erfp_extract_section_details(section_content: str | None) -> list[str]:
    if not section_content:
        return []
    details: list[str] = []
    in_code_block = False
    for raw_line in section_content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not stripped:
            continue
        if in_code_block:
            cleaned = re.sub(r"^[-*]\s*", "", stripped).strip()
            if cleaned.startswith("#") or not cleaned:
                continue
            cleaned = re.sub(r"^\[\s*[xX]?\s*\]\s*", "", cleaned).strip()
            details.append(cleaned)
            continue
        if stripped.startswith(("#", "---")):
            continue
        cleaned = re.sub(r"^[-*]\s*", "", stripped)
        cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
        cleaned = cleaned.strip()
        cleaned = re.sub(r"^\[\s*[xX]?\s*\]\s*", "", cleaned).strip()
        if cleaned:
            details.append(cleaned)
    return details


def _nd_apply_labeled_prefix(cleaned: str, lower: str) -> tuple[str, str, bool]:
    if lower.startswith("new command group"):
        rest = re.sub(r"^new\s+command\s+group\s*:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = f"provides command group {rest}".strip()
        return cleaned, cleaned.lower(), True
    if lower.startswith("location:"):
        rest = re.sub(r"^location\s*:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = f"stores tokens at {rest}".strip()
        return cleaned, cleaned.lower(), True
    if lower.startswith("format:"):
        rest = re.sub(r"^format\s*:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = f"uses format {rest}".strip()
        return cleaned, cleaned.lower(), True
    if lower.startswith("permissions:"):
        rest = re.sub(r"^permissions\s*:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = f"enforces permissions {rest}".strip()
        return cleaned, cleaned.lower(), True
    return cleaned, lower, False


def _nd_apply_colon_suffix(cleaned: str, lower: str) -> tuple[str, str]:
    if ":" not in cleaned:
        return cleaned, lower
    _prefix, rest = cleaned.split(":", 1)
    if not rest.strip():
        return cleaned, lower
    cleaned = rest.strip()
    return cleaned, cleaned.lower()


def _nd_apply_user_specfact_rules(cleaned: str, lower: str) -> tuple[str, str]:
    if lower.startswith("users can"):
        cleaned = f"allows users to {cleaned[10:].lstrip()}".strip()
        return cleaned, cleaned.lower()
    if re.match(r"^specfact\s+", cleaned):
        cleaned = f"supports `{cleaned}` command"
        return cleaned, cleaned.lower()
    return cleaned, lower


def _nd_maybe_lowercase_first_verb(cleaned: str) -> str:
    if not cleaned:
        return cleaned
    first_word = cleaned.split()[0].rstrip(".,;:!?")
    if first_word.lower() in ERFP_VERBS_LOWER_FIRST and cleaned[0].isupper():
        return cleaned[0].lower() + cleaned[1:]
    return cleaned


def erfp_normalize_detail_for_and(detail: str) -> str:
    cleaned = detail.strip()
    if not cleaned:
        return ""
    cleaned = cleaned.replace("**", "").strip()
    cleaned = cleaned.lstrip("*").strip()
    if cleaned.lower() in {"commands:", "commands"}:
        return ""
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned).strip()
    cleaned = re.sub(r"^\[\s*[xX]?\s*\]\s*", "", cleaned).strip()
    lower = cleaned.lower()
    cleaned, lower, labeled = _nd_apply_labeled_prefix(cleaned, lower)
    if not labeled:
        cleaned, lower = _nd_apply_colon_suffix(cleaned, lower)
    cleaned, lower = _nd_apply_user_specfact_rules(cleaned, lower)
    cleaned = _nd_maybe_lowercase_first_verb(cleaned)
    if cleaned and not cleaned.endswith("."):
        cleaned += "."
    return cleaned


def erfp_parse_formatted_sections(text: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current: dict[str, Any] | None = None
    marker_pattern = re.compile(
        r"^-\s*\*\*(NEW|EXTEND|FIX|ADD|MODIFY|UPDATE|REMOVE|REFACTOR)\*\*:\s*(.+)$",
        re.IGNORECASE,
    )
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        marker_match = marker_pattern.match(stripped)
        if marker_match:
            if current:
                sections.append(
                    {
                        "title": current["title"],
                        "content": "\n".join(current["content"]).strip(),
                    }
                )
            current = {"title": marker_match.group(2).strip(), "content": []}
            continue
        if current is not None:
            current["content"].append(raw_line)
    if current:
        sections.append(
            {
                "title": current["title"],
                "content": "\n".join(current["content"]).strip(),
            }
        )
    return sections


def erfp_normalize_section_key(section_title_lower: str) -> str:
    normalized = re.sub(r"\([^)]*\)", "", section_title_lower).strip()
    return re.sub(r"^\d+\.\s*", "", normalized).strip()


def _change_desc_devops_device_code(title_lower: str, section_title: str) -> str:
    if "azure" in title_lower or "devops" in title_lower:
        return "use Azure DevOps device code authentication for sync operations with Azure DevOps"
    if "github" in title_lower:
        return "use GitHub device code authentication for sync operations with GitHub"
    return f"use device code authentication for {section_title.lower()} sync operations"


def _change_desc_devops(title_lower: str, section_title: str) -> str:
    if "device code" in title_lower:
        return _change_desc_devops_device_code(title_lower, section_title)
    if "token" in title_lower or "storage" in title_lower or "management" in title_lower:
        return "use stored authentication tokens for DevOps sync operations when available"
    if "cli" in title_lower or "command" in title_lower or "integration" in title_lower:
        return "provide CLI authentication commands for DevOps sync operations"
    if "architectural" in title_lower or "decision" in title_lower:
        return "follow documented authentication architecture decisions for DevOps sync operations"
    return f"support {section_title.lower()} for DevOps sync operations"


def _change_desc_auth_mgmt(title_lower: str, section_title: str) -> str:
    if "device code" in title_lower:
        if "azure" in title_lower or "devops" in title_lower:
            return "support Azure DevOps device code authentication using Entra ID"
        if "github" in title_lower:
            return "support GitHub device code authentication using RFC 8628 OAuth device authorization flow"
        return f"support device code authentication for {section_title.lower()}"
    if "token" in title_lower or "storage" in title_lower or "management" in title_lower:
        return "store and manage authentication tokens securely with appropriate file permissions"
    if "cli" in title_lower or "command" in title_lower:
        return "provide CLI commands for authentication operations"
    return f"support {section_title.lower()}"


def _change_desc_default(title_lower: str, section_title: str) -> str:
    if "device code" in title_lower:
        return f"support {section_title.lower()} authentication"
    if "token" in title_lower or "storage" in title_lower:
        return "store and manage authentication tokens securely"
    if "architectural" in title_lower or "decision" in title_lower:
        return "follow documented architecture decisions"
    return f"support {section_title.lower()}"


def erfp_resolve_change_desc(spec_id: str, title_lower: str, section_title: str) -> str:
    if spec_id == "devops-sync":
        return _change_desc_devops(title_lower, section_title)
    if spec_id == "auth-management":
        return _change_desc_auth_mgmt(title_lower, section_title)
    return _change_desc_default(title_lower, section_title)


def erfp_finalize_change_desc_sentence(change_desc: str) -> str:
    if not change_desc.endswith("."):
        change_desc = change_desc + "."
    if change_desc and change_desc[0].isupper():
        change_desc = change_desc[0].lower() + change_desc[1:]
    return change_desc


def erfp_build_req_name(
    section_title: str,
    bridge: Any,
    proposal: Any,
    requirement_index: int,
) -> str:
    req_name = section_title.strip()
    req_name = re.sub(r"^(new|add|implement|support|provide|enable)\s+", "", req_name, flags=re.IGNORECASE)
    req_name = re.sub(r"\([^)]*\)", "", req_name, flags=re.IGNORECASE).strip()
    req_name = re.sub(r"^\d+\.\s*", "", req_name).strip()
    req_name = re.sub(r"\s+", " ", req_name)[:60].strip()
    if req_name and len(req_name) >= 8:
        return req_name
    req_name = bridge._format_proposal_title(proposal.title)
    req_name = re.sub(r"^(feat|fix|add|update|remove|refactor):\s*", "", req_name, flags=re.IGNORECASE)
    req_name = req_name.replace("[Change]", "").strip()
    if requirement_index > 0:
        req_name = f"{req_name} ({requirement_index + 1})"
    return req_name


def erfp_then_response_from_change_desc(change_desc: str) -> str:
    then_response = change_desc
    words = then_response.split()
    if not words:
        return then_response
    first_word = words[0].rstrip(".,;:!?")
    if first_word.lower() in ERFP_VERBS_THIRD_PERSON:
        words[0] = ERFP_VERBS_THIRD_PERSON[first_word.lower()] + words[0][len(first_word) :]
    for i in range(1, len(words) - 1):
        if words[i].lower() == "and" and i + 1 < len(words):
            next_word = words[i + 1].rstrip(".,;:!?")
            if next_word.lower() in ERFP_VERBS_THIRD_PERSON:
                words[i + 1] = ERFP_VERBS_THIRD_PERSON[next_word.lower()] + words[i + 1][len(next_word) :]
    return " ".join(words)


def erfp_append_requirement_block(
    requirement_lines: list[str],
    req_name: str,
    change_desc: str,
    section_details: list[str],
    title_lower: str,
) -> None:
    requirement_lines.append(f"### Requirement: {req_name}")
    requirement_lines.append("")
    requirement_lines.append(f"The system SHALL {change_desc}")
    requirement_lines.append("")
    scenario_name = (
        req_name.split(":")[0] if ":" in req_name else req_name.split()[0] if req_name.split() else "Implementation"
    )
    requirement_lines.append(f"#### Scenario: {scenario_name}")
    requirement_lines.append("")
    when_action = req_name.lower().replace("device code", "device code authentication")
    when_clause = f"a user requests {when_action}"
    if "architectural" in title_lower or "decision" in title_lower:
        when_clause = "the system performs authentication operations"
    requirement_lines.append(f"- **WHEN** {when_clause}")
    then_response = erfp_then_response_from_change_desc(change_desc)
    requirement_lines.append(f"- **THEN** the system {then_response}")
    for detail in section_details:
        normalized_detail = erfp_normalize_detail_for_and(detail)
        if normalized_detail:
            requirement_lines.append(f"- **AND** {normalized_detail}")
    requirement_lines.append("")


def erfp_process_one_section(
    bridge: Any,
    proposal: Any,
    spec_id: str,
    section_title: str,
    section_content: str | None,
    seen_sections: set[str],
    requirement_lines: list[str],
    requirement_index: int,
) -> int:
    section_title_lower = section_title.lower()
    normalized_title = erfp_normalize_section_key(section_title_lower)
    if normalized_title in seen_sections:
        return requirement_index
    if normalized_title in ERFP_SKIP_TITLES:
        return requirement_index
    seen_sections.add(normalized_title)
    section_details = erfp_extract_section_details(section_content)
    req_name = erfp_build_req_name(section_title, bridge, proposal, requirement_index)
    title_lower = section_title_lower
    change_desc = erfp_resolve_change_desc(spec_id, title_lower, section_title)
    change_desc = erfp_finalize_change_desc_sentence(change_desc)
    erfp_append_requirement_block(requirement_lines, req_name, change_desc, section_details, title_lower)
    return requirement_index + 1


def erfp_try_subsection_fallback(
    bridge: Any,
    proposal: Any,
    description: str,
    requirement_lines: list[str],
) -> None:
    subsection_match = re.search(r"-\s*###\s*([^\n]+)\s*\n\s*-\s*([^\n]+)", description, re.MULTILINE)
    if not subsection_match:
        return
    subsection_title = subsection_match.group(1).strip()
    first_line = subsection_match.group(2).strip()
    if first_line.startswith("- "):
        first_line = first_line[2:].strip()
    if first_line.lower() == subsection_title.lower() or len(first_line) <= 10:
        return
    if "." in first_line:
        first_line = first_line.split(".")[0].strip() + "."
    if len(first_line) > 200:
        first_line = first_line[:200] + "..."
    req_name = bridge._format_proposal_title(proposal.title)
    req_name = re.sub(r"^(feat|fix|add|update|remove|refactor):\s*", "", req_name, flags=re.IGNORECASE)
    req_name = req_name.replace("[Change]", "").strip()
    requirement_lines.append(f"### Requirement: {req_name}")
    requirement_lines.append("")
    requirement_lines.append(f"The system SHALL {first_line}")
    requirement_lines.append("")
    requirement_lines.append(f"#### Scenario: {subsection_title}")
    requirement_lines.append("")
    requirement_lines.append("- **WHEN** the system processes the change")
    requirement_lines.append(f"- **THEN** {first_line.lower()}")
    requirement_lines.append("")


def erfp_try_title_description_fallback(
    bridge: Any,
    proposal: Any,
    description: str,
    rationale: str,
    requirement_lines: list[str],
) -> None:
    first_sentence = (
        description.split(".")[0].strip()
        if description
        else rationale.split(".")[0].strip()
        if rationale
        else "implement the change"
    )
    first_sentence = re.sub(r"^[-#\s]+", "", first_sentence).strip()
    if len(first_sentence) > 200:
        first_sentence = first_sentence[:200] + "..."
    req_name = bridge._format_proposal_title(proposal.title)
    req_name = re.sub(r"^(feat|fix|add|update|remove|refactor):\s*", "", req_name, flags=re.IGNORECASE)
    req_name = req_name.replace("[Change]", "").strip()
    requirement_lines.append(f"### Requirement: {req_name}")
    requirement_lines.append("")
    requirement_lines.append(f"The system SHALL {first_sentence}")
    requirement_lines.append("")
    requirement_lines.append(f"#### Scenario: {req_name}")
    requirement_lines.append("")
    requirement_lines.append("- **WHEN** the change is applied")
    requirement_lines.append(f"- **THEN** {first_sentence.lower()}")
    requirement_lines.append("")


def _erfp_fill_from_formatted_sections(
    bridge: Any,
    proposal: Any,
    spec_id: str,
    formatted_sections: list[dict[str, str]],
    seen_sections: set[str],
    requirement_lines: list[str],
    requirement_index: int,
) -> int:
    for section in formatted_sections:
        requirement_index = erfp_process_one_section(
            bridge,
            proposal,
            spec_id,
            section["title"],
            section["content"] or None,
            seen_sections,
            requirement_lines,
            requirement_index,
        )
    return requirement_index


def _erfp_fill_from_change_patterns(
    bridge: Any,
    proposal: Any,
    spec_id: str,
    description: str,
    seen_sections: set[str],
    requirement_lines: list[str],
    requirement_index: int,
) -> int:
    change_patterns = re.finditer(
        r"(?i)(?:^|\n)(?:-\s*)?###\s*([^\n]+)\s*\n(.*?)(?=\n(?:-\s*)?###\s+|\n(?:-\s*)?##\s+|\Z)",
        description,
        re.MULTILINE | re.DOTALL,
    )
    for match in change_patterns:
        requirement_index = erfp_process_one_section(
            bridge,
            proposal,
            spec_id,
            match.group(1).strip(),
            match.group(2).strip(),
            seen_sections,
            requirement_lines,
            requirement_index,
        )
    return requirement_index


def run_extract_requirement_from_proposal(bridge: Any, proposal: Any, spec_id: str) -> str:
    description = proposal.description or ""
    rationale = proposal.rationale or ""
    requirement_lines: list[str] = []
    seen_sections: set[str] = set()
    requirement_index = 0
    formatted_sections = erfp_parse_formatted_sections(description)
    if formatted_sections:
        _erfp_fill_from_formatted_sections(
            bridge, proposal, spec_id, formatted_sections, seen_sections, requirement_lines, requirement_index
        )
    else:
        _erfp_fill_from_change_patterns(
            bridge, proposal, spec_id, description, seen_sections, requirement_lines, requirement_index
        )
    if not requirement_lines and description:
        erfp_try_subsection_fallback(bridge, proposal, description, requirement_lines)
    if not requirement_lines and (description or rationale):
        erfp_try_title_description_fallback(bridge, proposal, description, rationale, requirement_lines)
    return "\n".join(requirement_lines) if requirement_lines else ""
