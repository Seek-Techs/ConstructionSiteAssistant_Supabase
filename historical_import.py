"""Preview-only analysis of historical WhatsApp site reports.

This module is pure: it performs no database, network or file access.
It reuses ``whatsapp_parser`` and ``whatsapp_digest`` and turns parsed
messages into *proposed* site-observation candidates for human review.

Design rules
------------
* Nothing is invented. Every proposed field is either copied verbatim
  from the message text or left as ``None`` for the reviewer to fill in.
* Nothing is ever proposed as ``Closed``. Status is always ``Open``.
* Original text, sender, timestamp and source-line numbers are kept so
  every candidate can be traced back to the export.
* Classification is a conservative heuristic. Each decision carries the
  cue words that triggered it so the reviewer can see why.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from whatsapp_digest import filter_messages_by_date
from whatsapp_parser import WhatsAppMessage, parse_whatsapp_text


# ---------------------------------------------------------------------
# Message kinds
# ---------------------------------------------------------------------

KIND_OBSERVATION = "Observation"
KIND_FOLLOW_UP = "Rectification / follow-up"
KIND_PROGRESS = "Progress update"
KIND_INSTRUCTION = "Instruction"
KIND_ACK = "Acknowledgement"
KIND_MEDIA = "Media only"
KIND_SYSTEM = "System / deleted"
KIND_OTHER = "Other"

ALL_KINDS = (
    KIND_OBSERVATION,
    KIND_FOLLOW_UP,
    KIND_PROGRESS,
    KIND_INSTRUCTION,
    KIND_ACK,
    KIND_MEDIA,
    KIND_SYSTEM,
    KIND_OTHER,
)

# Kinds that can produce candidate observations.
CANDIDATE_KINDS = (KIND_OBSERVATION, KIND_FOLLOW_UP)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MEDIA_LINK_WINDOW = timedelta(minutes=10)
FOLLOW_UP_LINK_WINDOW = timedelta(days=45)


# ---------------------------------------------------------------------
# Cue patterns
# ---------------------------------------------------------------------

MEDIA_PREFIX = re.compile(
    r"^\s*(?:\[forwarded\]\s*)?"
    r"<(?:image|video|audio|sticker|document|gif|album message|"
    r"unknown message)[^>]*>",
    re.IGNORECASE,
)

DELETED = re.compile(
    r"^\s*(?:this message was deleted|you deleted this message)\.?\s*$",
    re.IGNORECASE,
)

ACK_TEXT = re.compile(
    r"^\s*(?:ok(?:ay)?|noted|alright|yes|yep|well noted|thanks?|"
    r"thank you|received|copy|seen|done|good)"
    r"(?:[\s,.!]+(?:sir|ma|ma'am|noted|please|thanks?|"
    r"thank you|ok))*[\s.!]*$",
    re.IGNORECASE,
)

# Strong cues describe a problem (defect, non-compliance, hazard).
ISSUE_CUES = re.compile(
    r"\b(?:defect\w*|crack\w*|honeycomb\w*|segregat\w*|poor|"
    r"broken|damag\w*|displac\w*|not conform\w*|non-?conform\w*|"
    r"non-?complian\w*|without (?:the )?(?:required )?ppe|unsafe|"
    r"debris|housekeeping|organic|contaminat\w*|difference in level|"
    r"inadequate|improper\w*|incorrect\w*|failed|failure|missing|"
    r"stagnant|standing water|obstruct\w*|substandard|unsuitable|"
    r"deficien\w*|unauthori[sz]ed|not (?:in )?accordance)\b",
    re.IGNORECASE,
)

# A weak cue only says something was seen. On its own it does not make a
# defect, so such messages are kept as progress/site updates.
WEAK_OBSERVATION_CUES = re.compile(
    r"\b(?:observed|site observation|noted that|inspection)\b",
    re.IGNORECASE,
)

# Follow-up cues refer back to an earlier finding. Future-tense plans
# ("follow-up inspection to verify ...") and action headings such as
# "Rectification of ..." are deliberately not treated as follow-ups.
FOLLOW_UP_CUES = re.compile(
    r"\b(?:during (?:the )?follow-?\s?up inspection|"
    r"follow-?\s?up inspection (?:on|was|carried out|conducted)|"
    r"follow-?\s?up/repeat observation|re-?inspection (?:on|was)|"
    r"previously (?:observed|instructed|noted|reported)|"
    r"has been (?:corrected|rectified|addressed|repaired)|"
    r"had been (?:corrected|rectified|addressed|repaired)|"
    r"repeat observation|despite the previous instruction|"
    r"re-?observed)\b",
    re.IGNORECASE,
)

INSTRUCTION_CUES = re.compile(
    r"\b(?:please|kindly|ensure|you (?:are|should|must)|instruct\w*|"
    r"advis\w+|make sure|should be|must be|stop work|remove|submit)\b",
    re.IGNORECASE,
)

PROGRESS_CUES = re.compile(
    r"\b(?:work ?plan|work ?done|work achieved|progress|update|ongoing|"
    r"in progress|completed|activity|activities|resources|manpower|"
    r"equipment|planned|quantity)\b",
    re.IGNORECASE,
)

ACTION_CLAUSE = re.compile(
    r"\b(?:instructed|advised|requested|directed|asked)\s+to\s+"
    r"(?P<clause>[^.;\n]+)",
    re.IGNORECASE,
)

HSE_WORDS = re.compile(
    r"\b(?:ppe|safety|hse|hazard\w*|unsafe|housekeeping|barricad\w*|"
    r"helmet|harness|fire|injur\w*|debris)\b",
    re.IGNORECASE,
)
TRAFFIC_WORDS = re.compile(
    r"\b(?:traffic|haulage|truck|trucks|vehicle|vehicles|"
    r"speed|flagman|diversion)\b",
    re.IGNORECASE,
)
QUALITY_WORDS = re.compile(
    r"\b(?:level|alignment|reinforcement|concrete|mortar|material\w*|"
    r"workmanship|thickness|compaction|crack\w*|honeycomb\w*|joint\w*|"
    r"invert|organic|contaminat\w*|kerb\w*|paving|screed|formwork|"
    r"blinding|specification|specified)\b",
    re.IGNORECASE,
)

DIRECT_CUES = re.compile(
    r"\b(?:was observed|were observed|i observed|observed during|"
    r"during (?:the )?(?:site )?(?:inspection|visit|reconnaissance)|"
    r"was inspected|were inspected|site inspection|noted during)\b",
    re.IGNORECASE,
)
REPORTED_CUES = re.compile(
    r"\b(?:contractor (?:reported|informed|confirmed|stated|said)|"
    r"according to the contractor|based on the contractor|"
    r"reported by the contractor|contractor'?s representative)\b",
    re.IGNORECASE,
)

CONTRACTOR_LINE = re.compile(
    r"^\s*contractor(?:'s)?\s*[:\-–]\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
LOCATION_LINE = re.compile(
    r"^\s*location\s*[:\-–]\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
LOCATION_FALLBACK = re.compile(
    r"\b(?:[EN]\d+[A-Za-z]?\s+(?:road|channel)|"
    r"[EN]\d+[A-Za-z]?\s*\([^)]*\))",
    re.IGNORECASE,
)
DATE_LINE = re.compile(
    r"^\s*(?:work update|date(?: of contractor.s report)?|report date)"
    r"\s*[:\-–]?\s*(?P<d>\d{1,2})[/.\-](?P<m>\d{1,2})[/.\-]"
    r"(?P<y>\d{4})\s*$",
    re.IGNORECASE,
)

BULLET = re.compile(r"^\s*(?:[*•\-–.]|\d{1,2}[.)])\s+(?P<body>\S.*)$")
FINDING_SECTION = re.compile(
    r"observation|inspection|finding|issue|non-?conform|qc|hse|safety|"
    r"quality|remark",
    re.IGNORECASE,
)
ACTION_SECTION = re.compile(
    r"outstanding action|action required|required action|"
    r"recommendation|next step|corrective action",
    re.IGNORECASE,
)
IGNORED_SECTION = re.compile(
    r"constraint|resource|manpower|equipment|work plan|work ?done|"
    r"planned|picture|pictures|photo",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class ClassifiedMessage:
    """One export message with its heuristic classification."""

    timestamp: datetime
    sender: str | None
    text: str
    source_line: int
    end_line: int
    kind: str
    reasons: tuple[str, ...]
    media_count: int = 0


@dataclass
class CandidateObservation:
    """A *proposed* observation. Nothing here has been saved or verified."""

    candidate_id: str
    kind: str
    message_timestamp: datetime
    sender: str | None
    message_source_line: int
    finding_source_line: int
    original_message_text: str
    finding_text: str
    contractor: str | None
    contractor_options: tuple[str, ...]
    location: str | None
    report_date: date
    report_date_note: str | None
    category: str
    information_source: str | None
    required_action: str | None
    message_actions: tuple[str, ...]
    status: str = "Open"
    reasons: tuple[str, ...] = ()
    media_count: int = 0
    possible_links: tuple[int, ...] = ()
    fingerprint: str = ""


@dataclass
class ImportPreview:
    """Everything the preview screen needs. Never persisted."""

    total_messages: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    senders: dict[str, int]
    messages: list[ClassifiedMessage] = field(default_factory=list)
    candidates: list[CandidateObservation] = field(default_factory=list)
    kind_counts: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------
# Reading uploads
# ---------------------------------------------------------------------

def decode_export(raw: bytes) -> str:
    """Decode a WhatsApp export, rejecting oversized or non-text input."""
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("The file is larger than the 20 MB import limit.")

    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeError:
            continue

    raise ValueError("The file could not be read as UTF-8 text.")


def extract_chat_text(filename: str, raw: bytes) -> str:
    """Return chat text from a ``.txt`` file or a WhatsApp ``.zip`` export.

    Zip files are read in memory only. Nothing is extracted to disk, and
    only a single ``.txt`` member is considered.
    """
    import io
    import zipfile

    name = (filename or "").lower()

    if name.endswith(".txt"):
        return decode_export(raw)

    if name.endswith(".zip"):
        try:
            archive = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile:
            raise ValueError("The zip file is not valid.") from None

        members = [
            info
            for info in archive.infolist()
            if info.filename.lower().endswith(".txt")
            and not info.is_dir()
        ]
        if not members:
            raise ValueError("The zip file contains no .txt chat export.")

        # Prefer the conventional WhatsApp name, otherwise the largest.
        members.sort(
            key=lambda info: (
                "chat" not in info.filename.lower(),
                -info.file_size,
            )
        )
        member = members[0]
        if member.file_size > MAX_UPLOAD_BYTES:
            raise ValueError(
                "The chat file in the zip is larger than the 20 MB limit."
            )
        return decode_export(archive.read(member))

    raise ValueError("Upload a WhatsApp export as a .txt or .zip file.")


# ---------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------

def split_media_prefix(text: str) -> tuple[int, str]:
    """Return (1 if text starts with a media placeholder, remaining text)."""
    match = MEDIA_PREFIX.match(text)
    if not match:
        return 0, text.strip()
    return 1, text[match.end():].strip()


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text)


def _matches(pattern: re.Pattern, text: str, limit: int = 4) -> list[str]:
    found: list[str] = []
    for match in pattern.finditer(text):
        value = match.group(0).strip().lower()
        if value not in found:
            found.append(value)
        if len(found) >= limit:
            break
    return found


def classify_text(
    sender: str | None,
    text: str,
) -> tuple[str, tuple[str, ...], int]:
    """Classify one message. Returns (kind, reasons, media_in_message)."""
    if sender is None:
        return KIND_SYSTEM, ("no sender (group notification)",), 0

    if DELETED.match(text):
        return KIND_SYSTEM, ("deleted message",), 0

    media, body = split_media_prefix(text)

    if not body or re.fullmatch(r"(?:<[^>]*>\s*)+", body):
        return KIND_MEDIA, ("media placeholder with no text",), media

    if len(_words(body)) <= 6 and ACK_TEXT.match(body):
        return KIND_ACK, ("short acknowledgement",), media

    issues = _matches(ISSUE_CUES, body)
    follow = _matches(FOLLOW_UP_CUES, body)
    progress = _matches(PROGRESS_CUES, body)
    instruct = _matches(INSTRUCTION_CUES, body)
    long_enough = len(_words(body)) >= 12

    if follow and long_enough:
        return (
            KIND_FOLLOW_UP,
            tuple(f"follow-up cue: {cue}" for cue in follow),
            media,
        )

    if issues and long_enough:
        return (
            KIND_OBSERVATION,
            tuple(f"issue cue: {cue}" for cue in issues),
            media,
        )

    weak = _matches(WEAK_OBSERVATION_CUES, body)

    if (progress or weak) and long_enough:
        reasons = [f"progress cue: {cue}" for cue in progress]
        if weak and not issues:
            reasons.append(
                "observation wording without a defect or "
                "non-compliance cue"
            )
        return KIND_PROGRESS, tuple(reasons), media

    if instruct:
        return (
            KIND_INSTRUCTION,
            tuple(f"instruction cue: {cue}" for cue in instruct),
            media,
        )

    return KIND_OTHER, ("no recognised cue",), media


def message_line_spans(
    messages: list[WhatsAppMessage],
    total_lines: int,
) -> dict[int, int]:
    """Map each message's start line to its last line in the export."""
    ordered = sorted(messages, key=lambda m: m.source_line)
    spans: dict[int, int] = {}
    for index, message in enumerate(ordered):
        if index + 1 < len(ordered):
            spans[message.source_line] = ordered[index + 1].source_line - 1
        else:
            spans[message.source_line] = total_lines
    return spans


# ---------------------------------------------------------------------
# Field proposals (verbatim or None)
# ---------------------------------------------------------------------

COMPANY_ENTITY = re.compile(
    r"(?:[A-Z][\w&'-]*\.?\s+){0,3}[A-Z][\w&'-]*\s+"
    r"(?:Nig\.?\s+)?(?:Ltd\.?|Limited|FZE|FZC)"
)


def _entities(text: str) -> list[str]:
    """Company-style names found in a piece of text, cleaned."""
    found = []
    for match in COMPANY_ENTITY.finditer(text):
        name = re.sub(r"\s+", " ", match.group(0)).strip(" .,*_")
        if name not in found:
            found.append(name)
    return found


def learn_contractor_names(messages: list[WhatsAppMessage]) -> list[str]:
    """Collect contractor names that the export itself mentions.

    Names come from ``Contractor:`` lines and the first lines of reports,
    so proposals are limited to names the group has actually used.
    Names are ordered from most to least frequent.
    """
    counts: Counter[str] = Counter()

    for message in messages:
        _, body = split_media_prefix(message.text)
        lines = [line for line in body.splitlines() if line.strip()]

        for line in lines:
            match = CONTRACTOR_LINE.match(line)
            if match:
                for name in _entities(match.group("value")):
                    counts[name] += 1

        for line in lines[:2]:
            for name in _entities(line):
                counts[name] += 1

    return [name for name, _ in counts.most_common()]


def find_contractor(
    text: str,
    names: list[str],
) -> tuple[str | None, tuple[str, ...]]:
    """Return (proposed contractor, all known names mentioned).

    A contractor is proposed only when the text identifies one clearly:
    an explicit ``Contractor:`` line, the report heading, or exactly one
    known name in the whole text. Otherwise the proposal is None and the
    reviewer chooses from the names that were mentioned.
    """
    lowered = text.lower()
    mentioned = tuple(
        name for name in names if name.lower() in lowered
    )

    lines = [line for line in text.splitlines() if line.strip()]

    for line in lines:
        match = CONTRACTOR_LINE.match(line)
        if match:
            for name in _entities(match.group("value")):
                return name, mentioned

    for line in lines[:2]:
        entities = _entities(line)
        if len(entities) == 1:
            return entities[0], mentioned

    if len(mentioned) == 1:
        return mentioned[0], mentioned

    return None, mentioned


def find_location(text: str) -> str | None:
    """Return a location stated in the text, or None."""
    for line in text.splitlines():
        match = LOCATION_LINE.match(line)
        if match:
            return match.group("value").strip(" .*_")

    match = LOCATION_FALLBACK.search(text)
    return match.group(0).strip() if match else None


def find_report_date(
    text: str,
    message_date: date,
) -> tuple[date, str | None]:
    """Return (report date, note). Text dates are day-first (DD/MM/YYYY).

    The export's own timestamps are month-first, so the two formats are
    parsed separately and never confused.
    """
    for line in text.splitlines():
        match = DATE_LINE.match(line)
        if not match:
            continue
        try:
            stated = date(
                int(match.group("y")),
                int(match.group("m")),
                int(match.group("d")),
            )
        except ValueError:
            continue

        if stated == message_date:
            return stated, None

        gap = abs((stated - message_date).days)
        if gap <= 7:
            return stated, (
                f"Date stated in the report ({stated.isoformat()}) "
                f"differs from the message date "
                f"({message_date.isoformat()})."
            )
        return message_date, (
            f"Report states {stated.isoformat()}, more than a week from "
            f"the message date; message date used. Please check."
        )

    return message_date, None


def propose_category(text: str) -> str:
    """Suggest Quality / HSE / Traffic / Other from cue words."""
    scores = {
        "HSE": len(HSE_WORDS.findall(text)),
        "Traffic": len(TRAFFIC_WORDS.findall(text)),
        "Quality": len(QUALITY_WORDS.findall(text)),
    }
    best = max(scores, key=lambda key: scores[key])
    if scores[best] == 0:
        return "Other"
    # Prefer HSE on ties because safety issues should not be understated.
    ties = [key for key, value in scores.items() if value == scores[best]]
    return "HSE" if "HSE" in ties else ties[0]


def propose_information_source(text: str) -> str | None:
    """Return a supported source only when the wording clearly shows one."""
    direct = bool(DIRECT_CUES.search(text))
    reported = bool(REPORTED_CUES.search(text))
    if direct and not reported:
        return "Direct observation"
    if reported and not direct:
        return "Contractor-reported"
    return None


def extract_required_action(text: str) -> str | None:
    """Copy an 'instructed to ...' clause verbatim, if the text has one."""
    match = ACTION_CLAUSE.search(text)
    if not match:
        return None
    clause = match.group(0).strip()
    return clause[0].upper() + clause[1:]


def make_fingerprint(message: WhatsAppMessage, finding_text: str) -> str:
    """Stable provenance hash used later for duplicate protection."""
    normalized = re.sub(r"\s+", " ", finding_text).strip().lower()
    material = (
        f"{message.timestamp.isoformat()}|{message.sender}|{normalized}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


# ---------------------------------------------------------------------
# Splitting one message into findings
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class _Finding:
    text: str
    line: int


def split_findings(
    message: WhatsAppMessage,
    end_line: int,
    raw_lines: list[str],
) -> tuple[list[_Finding], list[str]]:
    """Split a report into separate findings plus message-level actions.

    Bullets under observation-type headings that contain issue or
    follow-up wording become one finding each. Bullets under action
    headings are returned as verbatim message-level actions. If no
    qualifying bullets exist, the whole message is one finding.
    """
    findings: list[_Finding] = []
    actions: list[str] = []
    section = ""

    first = message.source_line
    last = min(end_line, len(raw_lines))

    for line_number in range(first, last + 1):
        line = raw_lines[line_number - 1]
        bullet = BULLET.match(line)

        if bullet:
            body = bullet.group("body").strip()
            if ACTION_SECTION.search(section):
                actions.append(body)
            elif IGNORED_SECTION.search(section):
                continue
            elif ISSUE_CUES.search(body) or FOLLOW_UP_CUES.search(body):
                if not section or FINDING_SECTION.search(section):
                    findings.append(_Finding(body, line_number))
            continue

        stripped = line.strip(" *_#:")
        if stripped and len(stripped) <= 80 and not re.match(
            r"^\[\d", line
        ):
            # A short non-bullet line is treated as a section heading.
            section = stripped

    if not findings:
        _, body = split_media_prefix(message.text)
        findings.append(_Finding(body.strip(), first))

    return findings, actions


# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------

def analyze_export(
    content: str,
    start_date: date | None = None,
    end_date: date | None = None,
    senders: set[str] | None = None,
) -> ImportPreview:
    """Parse an export and propose candidates. Writes nothing anywhere."""
    all_messages = parse_whatsapp_text(content)
    raw_lines = content.splitlines()

    sender_counts = Counter(
        m.sender for m in all_messages if m.sender is not None
    )

    if not all_messages:
        return ImportPreview(
            total_messages=0,
            first_timestamp=None,
            last_timestamp=None,
            senders={},
        )

    spans = message_line_spans(all_messages, len(raw_lines))
    names = learn_contractor_names(all_messages)

    first_day = start_date or all_messages[0].timestamp.date()
    last_day = end_date or all_messages[-1].timestamp.date()
    selected = filter_messages_by_date(all_messages, first_day, last_day)

    if senders is not None:
        selected = [m for m in selected if m.sender in senders]

    # Count media posts per sender so text reports can reference them.
    media_posts = [
        (m.timestamp, m.sender)
        for m in all_messages
        if m.sender is not None and split_media_prefix(m.text)[0]
        and not DELETED.match(m.text)
    ]

    classified: list[ClassifiedMessage] = []
    candidates: list[CandidateObservation] = []

    for message in selected:
        kind, reasons, own_media = classify_text(message.sender, message.text)

        nearby = sum(
            1
            for when, who in media_posts
            if who == message.sender
            and abs(when - message.timestamp) <= MEDIA_LINK_WINDOW
        )

        classified.append(
            ClassifiedMessage(
                timestamp=message.timestamp,
                sender=message.sender,
                text=message.text,
                source_line=message.source_line,
                end_line=spans[message.source_line],
                kind=kind,
                reasons=reasons,
                media_count=max(own_media, nearby),
            )
        )

        if kind not in CANDIDATE_KINDS:
            continue

        _, body = split_media_prefix(message.text)
        findings, actions = split_findings(
            message,
            spans[message.source_line],
            raw_lines,
        )

        report_date, date_note = find_report_date(
            body,
            message.timestamp.date(),
        )
        message_contractor, contractor_options = find_contractor(
            body,
            names,
        )
        message_location = find_location(body)

        for index, finding in enumerate(findings, start=1):
            combined = f"{finding.text}\n{body}" if len(findings) > 1 \
                else finding.text
            candidates.append(
                CandidateObservation(
                    candidate_id=(
                        f"L{message.source_line}-{index}"
                    ),
                    kind=kind,
                    message_timestamp=message.timestamp,
                    sender=message.sender,
                    message_source_line=message.source_line,
                    finding_source_line=finding.line,
                    original_message_text=message.text,
                    finding_text=finding.text,
                    contractor=message_contractor,
                    contractor_options=contractor_options,
                    location=message_location,
                    report_date=report_date,
                    report_date_note=date_note,
                    category=propose_category(finding.text or combined),
                    information_source=propose_information_source(
                        finding.text
                    )
                    or propose_information_source(body),
                    required_action=extract_required_action(finding.text),
                    message_actions=tuple(actions),
                    reasons=reasons,
                    media_count=max(own_media, nearby),
                    fingerprint=make_fingerprint(message, finding.text),
                )
            )

    attach_possible_links(candidates)

    kind_counts = Counter(item.kind for item in classified)

    return ImportPreview(
        total_messages=len(all_messages),
        first_timestamp=all_messages[0].timestamp,
        last_timestamp=all_messages[-1].timestamp,
        senders=dict(sender_counts.most_common()),
        messages=classified,
        candidates=candidates,
        kind_counts={kind: kind_counts.get(kind, 0) for kind in ALL_KINDS},
    )


def _tokens(text: str) -> set[str]:
    return {
        word.lower()
        for word in _words(text)
        if len(word) > 3
    }


def attach_possible_links(candidates: list[CandidateObservation]) -> None:
    """Suggest earlier observations that a follow-up may relate to.

    Suggestions only: same contractor, earlier in time, within 45 days,
    ranked by shared wording. The reviewer decides in a later phase.
    """
    for candidate in candidates:
        if candidate.kind != KIND_FOLLOW_UP or not candidate.contractor:
            continue

        mine = _tokens(candidate.finding_text)
        scored: list[tuple[int, int]] = []

        for other in candidates:
            if other is candidate or other.kind != KIND_OBSERVATION:
                continue
            if other.contractor != candidate.contractor:
                continue
            if other.message_timestamp >= candidate.message_timestamp:
                continue
            if (
                candidate.message_timestamp - other.message_timestamp
                > FOLLOW_UP_LINK_WINDOW
            ):
                continue

            overlap = len(mine & _tokens(other.finding_text))
            if overlap >= 2:
                scored.append((overlap, other.finding_source_line))

        scored.sort(reverse=True)
        candidate.possible_links = tuple(line for _, line in scored[:3])
