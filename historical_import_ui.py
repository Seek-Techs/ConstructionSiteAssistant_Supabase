"""Streamlit screen for the preview-only historical WhatsApp import.

This screen never writes anything. It does not import the Supabase
client, the data service or any storage module, so it cannot change
cloud records. Saving is a separate, later step.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from historical_import import (
    ALL_KINDS,
    CANDIDATE_KINDS,
    CandidateObservation,
    ImportPreview,
    analyze_export,
    extract_chat_text,
)
from whatsapp_parser import parse_whatsapp_text


KEY = "hist_import"
PREVIEW_CHARS = 140


def _short(text: str, limit: int = PREVIEW_CHARS) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def candidate_rows(
    candidates: list[CandidateObservation],
) -> list[dict]:
    """Flatten candidates into plain rows for display."""
    return [
        {
            "ID": item.candidate_id,
            "Type": item.kind,
            "Report date": item.report_date.isoformat(),
            "Sender": item.sender or "",
            "Contractor": item.contractor or "— choose in review —",
            "Location": item.location or "— choose in review —",
            "Category": item.category,
            "Source": item.information_source or "— choose in review —",
            "Finding (verbatim)": _short(item.finding_text),
            "Source line": item.finding_source_line,
            "Photos/videos nearby": item.media_count,
            "Possible earlier lines": ", ".join(
                str(line) for line in item.possible_links
            ),
            "Date note": item.report_date_note or "",
        }
        for item in candidates
    ]


def message_rows(preview: ImportPreview) -> list[dict]:
    """Flatten classified messages into plain rows for display."""
    return [
        {
            "Line": item.source_line,
            "Time": item.timestamp.strftime("%Y-%m-%d %H:%M"),
            "Sender": item.sender or "(system)",
            "Classified as": item.kind,
            "Why": "; ".join(item.reasons),
            "Text": _short(item.text),
        }
        for item in preview.messages
    ]


def _read_upload(uploaded) -> str | None:
    try:
        return extract_chat_text(uploaded.name, uploaded.getvalue())
    except ValueError as error:
        st.error(str(error))
        return None


def _date_bounds(content: str) -> tuple[date, date] | None:
    messages = parse_whatsapp_text(content)
    if not messages:
        return None
    return (
        messages[0].timestamp.date(),
        messages[-1].timestamp.date(),
    )


def render_historical_import_preview() -> None:
    """Render the preview-only import screen."""
    st.subheader("Historical WhatsApp import — preview only")
    st.info(
        "Nothing on this screen is saved. It reads the file you upload, "
        "proposes possible site observations and shows where each one "
        "came from. Proposals are suggestions: fields the messages do "
        "not state are left blank, and nothing is marked Closed."
    )

    uploaded = st.file_uploader(
        "WhatsApp chat export (.txt, or the .zip WhatsApp produces)",
        type=["txt", "zip"],
        key=f"{KEY}_upload",
        help="Photos and videos are not part of the export, so only "
        "their placeholders appear in the chat.",
    )

    if uploaded is None:
        st.caption("Upload an export to begin.")
        return

    content = _read_upload(uploaded)
    if content is None:
        return

    bounds = _date_bounds(content)
    if bounds is None:
        st.error(
            "No messages were recognised. Check that this is a WhatsApp "
            "text export (for example '8/4/26, 11:24 AM - Name: text')."
        )
        return

    first_day, last_day = bounds

    full = analyze_export(content)

    sender_options = list(full.senders)
    default_senders = ["You"] if "You" in sender_options else sender_options

    filter_cols = st.columns([2, 3])
    with filter_cols[0]:
        chosen_range = st.date_input(
            "Dates to preview",
            value=(first_day, last_day),
            min_value=first_day,
            max_value=last_day,
            key=f"{KEY}_dates",
        )
    with filter_cols[1]:
        chosen_senders = st.multiselect(
            "Senders",
            options=sender_options,
            default=default_senders,
            key=f"{KEY}_senders",
            help="Defaults to your own posts ('You').",
        )

    if isinstance(chosen_range, (tuple, list)):
        if len(chosen_range) != 2:
            st.caption("Select both a start and an end date.")
            return
        start, end = chosen_range
    else:
        start = end = chosen_range

    if not chosen_senders:
        st.caption("Select at least one sender.")
        return

    preview = analyze_export(
        content,
        start_date=start,
        end_date=end,
        senders=set(chosen_senders),
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Messages in file", full.total_messages)
    metric_cols[1].metric("Messages selected", len(preview.messages))
    metric_cols[2].metric(
        "Proposed observations",
        sum(1 for c in preview.candidates if c.kind == "Observation"),
    )
    metric_cols[3].metric(
        "Follow-up reports",
        sum(
            1
            for c in preview.candidates
            if c.kind != "Observation"
        ),
    )
    st.caption(
        f"File covers {first_day.isoformat()} to {last_day.isoformat()}; "
        f"{len(full.senders)} senders."
    )

    candidates_tab, messages_tab, summary_tab = st.tabs(
        ["Proposed observations", "All selected messages", "Summary"]
    )

    with candidates_tab:
        shown_kinds = st.multiselect(
            "Show",
            options=list(CANDIDATE_KINDS),
            default=list(CANDIDATE_KINDS),
            key=f"{KEY}_kinds",
        )
        shown = [c for c in preview.candidates if c.kind in shown_kinds]

        if not shown:
            st.info("No proposed observations for this selection.")
        else:
            st.dataframe(
                candidate_rows(shown),
                use_container_width=True,
                hide_index=True,
            )

            options = {
                f"{c.candidate_id} · {c.report_date.isoformat()} · "
                f"{_short(c.finding_text, 60)}": c
                for c in shown
            }
            label = st.selectbox(
                "Inspect one proposal",
                options=list(options),
                key=f"{KEY}_inspect",
            )
            item = options[label]

            st.markdown(
                f"**Sender:** {item.sender}  \n"
                f"**Message time:** "
                f"{item.message_timestamp:%Y-%m-%d %H:%M:%S}  \n"
                f"**Message starts at line** {item.message_source_line}; "
                f"**finding at line** {item.finding_source_line}  \n"
                f"**Classified as:** {item.kind} — "
                f"{'; '.join(item.reasons)}"
            )
            if item.report_date_note:
                st.warning(item.report_date_note)
            if item.contractor_options and not item.contractor:
                st.caption(
                    "Contractors named in the text (choose one in "
                    "review): " + ", ".join(item.contractor_options)
                )
            if item.required_action:
                st.markdown("**Required action stated in the finding:**")
                st.text(item.required_action)
            if item.message_actions:
                st.markdown("**Outstanding actions listed in the report:**")
                for action in item.message_actions:
                    st.text(f"• {action}")

            st.markdown("**Finding (verbatim):**")
            st.text(item.finding_text)
            with st.expander("Full original message"):
                st.text(item.original_message_text)
            st.caption(f"Provenance fingerprint: {item.fingerprint}")

    with messages_tab:
        kinds = st.multiselect(
            "Classified as",
            options=list(ALL_KINDS),
            default=[
                kind
                for kind in ALL_KINDS
                if kind not in ("Media only", "System / deleted")
            ],
            key=f"{KEY}_message_kinds",
        )
        rows = [
            row
            for row in message_rows(preview)
            if row["Classified as"] in kinds
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with summary_tab:
        st.markdown("**Messages by classification (selected range):**")
        st.dataframe(
            [
                {"Classified as": kind, "Messages": count}
                for kind, count in preview.kind_counts.items()
            ],
            hide_index=True,
        )
        st.markdown("**Messages by sender (whole file):**")
        st.dataframe(
            [
                {"Sender": sender, "Messages": count}
                for sender, count in full.senders.items()
            ],
            hide_index=True,
        )
