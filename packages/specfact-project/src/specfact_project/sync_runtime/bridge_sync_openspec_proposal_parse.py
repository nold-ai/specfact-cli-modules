"""OpenSpec proposal.md section parsing (cyclomatic complexity extraction)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProposalSectionState:
    title: str = ""
    description: str = ""
    rationale: str = ""
    impact: str = ""
    in_why: bool = False
    in_what: bool = False
    in_impact: bool = False
    in_source_tracking: bool = False


class ProposalSectionParser:
    """Parses Why / What Changes / Impact sections from proposal.md lines."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.st = ProposalSectionState()

    def parse(self) -> None:
        for line_idx, line in enumerate(self._lines):
            self._step(line_idx, line)

    def _set_mode(self, *, why: bool, what: bool, impact: bool, st: bool) -> None:
        self.st.in_why = why
        self.st.in_what = what
        self.st.in_impact = impact
        self.st.in_source_tracking = st

    @staticmethod
    def _separator_targets_source_tracking(lines: list[str], line_idx: int) -> bool:
        remaining = lines[line_idx + 1 : line_idx + 5]
        return any("## Source Tracking" in ln for ln in remaining)

    def _step(self, line_idx: int, line: str) -> None:
        ls = line.strip()
        if ls.startswith("# Change:"):
            self.st.title = ls.replace("# Change:", "").strip()
            return
        if ls == "## Why":
            self._set_mode(why=True, what=False, impact=False, st=False)
            return
        if ls == "## What Changes":
            self._set_mode(why=False, what=True, impact=False, st=False)
            return
        if ls == "## Impact":
            self._set_mode(why=False, what=False, impact=True, st=False)
            return
        if ls == "## Source Tracking":
            self._set_mode(why=False, what=False, impact=False, st=True)
            return
        if self.st.in_source_tracking:
            return
        if self.st.in_why:
            self._in_why(line_idx, line, ls)
        elif self.st.in_what:
            self._in_what(line_idx, line, ls)
        elif self.st.in_impact:
            self._in_impact(line_idx, line, ls)

    def _in_why(self, line_idx: int, line: str, ls: str) -> None:
        if ls == "## What Changes":
            self._set_mode(why=False, what=True, impact=False, st=False)
            return
        if ls == "## Impact":
            self._set_mode(why=False, what=False, impact=True, st=False)
            return
        if ls == "## Source Tracking":
            self._set_mode(why=False, what=False, impact=False, st=True)
            return
        if ls == "---" and self._separator_targets_source_tracking(self._lines, line_idx):
            self._set_mode(why=False, what=False, impact=False, st=True)
            return
        if self.st.rationale and not self.st.rationale.endswith("\n"):
            self.st.rationale += "\n"
        self.st.rationale += line + "\n"

    def _in_what(self, line_idx: int, line: str, ls: str) -> None:
        if ls == "## Why":
            self._set_mode(why=True, what=False, impact=False, st=False)
            return
        if ls == "## Impact":
            self._set_mode(why=False, what=False, impact=True, st=False)
            return
        if ls == "## Source Tracking":
            self._set_mode(why=False, what=False, impact=False, st=True)
            return
        if ls == "---" and self._separator_targets_source_tracking(self._lines, line_idx):
            self._set_mode(why=False, what=False, impact=False, st=True)
            return
        if self.st.description and not self.st.description.endswith("\n"):
            self.st.description += "\n"
        self.st.description += line + "\n"

    def _in_impact(self, line_idx: int, line: str, ls: str) -> None:
        if ls == "## Why":
            self._set_mode(why=True, what=False, impact=False, st=False)
            return
        if ls == "## What Changes":
            self._set_mode(why=False, what=True, impact=False, st=False)
            return
        if ls == "## Source Tracking":
            self._set_mode(why=False, what=False, impact=False, st=True)
            return
        if ls == "---" and self._separator_targets_source_tracking(self._lines, line_idx):
            self._set_mode(why=False, what=False, impact=False, st=True)
            return
        if self.st.impact and not self.st.impact.endswith("\n"):
            self.st.impact += "\n"
        self.st.impact += line + "\n"
