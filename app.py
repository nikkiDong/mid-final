import streamlit as st
import json
from pathlib import Path
from datetime import datetime, date
import time

st.set_page_config("Excuse Absence Portal | Course 011101", layout="wide", initial_sidebar_state="expanded")

COURSE_ID = "011101"
EXCUSE_TYPES = [
    "Medical / Illness",
    "Family Emergency",
    "Transportation Issue",
    "Academic Conflict",
    "Religious Observance",
    "Other",
]

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"

if "selected_request_index" not in st.session_state:
    st.session_state["selected_request_index"] = None

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hi! I can help you with the absence excuse process. How can I assist?",
        }
    ]

# ─── SIDEBAR NAVIGATION ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Excuse Absence Portal")
    st.markdown(f"**Course ID:** `{COURSE_ID}`")
    st.divider()

    if st.button("Excuse Absence Dashboard", key="nav_dashboard_btn", type="primary", use_container_width=True):
        st.session_state["page"] = "dashboard"
        st.rerun()

    if st.button("Excuse Absence Request", key="nav_request_btn", type="primary", use_container_width=True):
        st.session_state["page"] = "request"
        st.rerun()

# ─── JSON LOADING ──────────────────────────────────────────────────────────────
json_path = Path("requests.json")
if json_path.exists():
    with open(json_path, "r") as f:
        all_requests = json.load(f)
else:
    all_requests = []

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["page"] == "dashboard":
    st.title("Excuse Absence Dashboard")
    st.markdown(f"*Course **{COURSE_ID}** — Review all submitted absence excuse requests.*")
    st.divider()

    col1, col2 = st.columns([4, 2])

    with col1:
        st.markdown("## All Requests")
        if len(all_requests) > 0:
            st.dataframe(all_requests, use_container_width=True)
        else:
            st.warning("No excuse requests have been submitted yet.")

    with col2:
        pending_count  = sum(1 for r in all_requests if r.get("status") == "Pending")
        approved_count = sum(1 for r in all_requests if r.get("status") == "Approved")
        denied_count   = sum(1 for r in all_requests if r.get("status") == "Denied")

        st.metric("Total Requests", f"{len(all_requests)}")
        st.metric("Pending",        f"{pending_count}")
        st.metric("Approved",       f"{approved_count}")
        st.metric("Denied",         f"{denied_count}")

    st.divider()

    # ── Request detail selector ──
    if len(all_requests) > 0:
        st.subheader("Request Details")

        selector_options = [
            f"#{i + 1}  —  {req.get('student_email', '?')}  —  {req.get('absence_date', '?')}"
            for i, req in enumerate(all_requests)
        ]

        if (
            st.session_state["selected_request_index"] is not None
            and st.session_state["selected_request_index"] < len(all_requests)
        ):
            default_idx = st.session_state["selected_request_index"] + 1
        else:
            default_idx = 0

        selected_label = st.selectbox(
            "Choose a request to inspect:",
            options=["— Select a request —"] + selector_options,
            index=default_idx,
            key="dash_request_selector",
        )

        if selected_label == "— Select a request —":
            st.session_state["selected_request_index"] = None
        else:
            st.session_state["selected_request_index"] = selector_options.index(selected_label)

        if st.session_state["selected_request_index"] is not None:
            idx = st.session_state["selected_request_index"]
            req = all_requests[idx]

            with st.container(border=True):
                col_a, col_b = st.columns(2)

                with col_a:
                    st.markdown(f"**Student Email:** {req.get('student_email', 'N/A')}")
                    st.markdown(f"**Absence Date:** {req.get('absence_date', 'N/A')}")
                    st.markdown(f"**Excuse Type:** {req.get('excuse_type', 'N/A')}")
                    st.markdown(f"**Status:** {req.get('status', 'N/A')}")

                with col_b:
                    st.markdown(f"**Course ID:** {req.get('course_id', 'N/A')}")
                    st.markdown(f"**Submitted:** {req.get('submitted_timestamp', 'N/A')}")
                    instructor_note = req.get("instructor_note", "").strip()
                    st.markdown(f"**Instructor Note:** {instructor_note if instructor_note else '(none)'}")

                st.markdown("**Explanation:**")
                st.info(req.get("explanation", "No explanation provided."))

# ══════════════════════════════════════════════════════════════════════════════
# REQUEST PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "request":
    st.title("Excuse Absence Request")
    st.markdown(f"*Course **{COURSE_ID}** — Submit a new absence excuse request below.*")
    st.divider()

    col1, col2 = st.columns([3, 3])

    with col1:
        st.subheader("Student Information")

        form_student_email = st.text_input(
            "Student Email *",
            placeholder="yourname@university.edu",
            key="form_student_email",
        )
        form_absence_date = st.date_input(
            "Absence Date *",
            value=date.today(),
            key="form_absence_date",
        )
        form_excuse_type = st.selectbox(
            "Excuse Type *",
            options=["— Select excuse type —"] + EXCUSE_TYPES,
            key="form_excuse_type",
        )
        form_explanation = st.text_area(
            "Explanation *",
            placeholder="Please describe in detail why you were absent...",
            height=150,
            key="form_explanation",
        )

        submit_col, note_col = st.columns([1, 2])
        with submit_col:
            form_submit_clicked = st.button(
                "Submit Request",
                key="form_submit_btn",
                type="primary",
                use_container_width=True,
            )
        with note_col:
            st.caption("Fields marked * are required. Status defaults to **Pending**.")

        # ── Validation & save ──
        if form_submit_clicked:
            validation_errors = []

            if not form_student_email.strip():
                validation_errors.append("Student Email is required.")
            elif "@" not in form_student_email or "." not in form_student_email.split("@")[-1]:
                validation_errors.append("Please enter a valid email address.")

            if form_excuse_type == "— Select excuse type —":
                validation_errors.append("Excuse Type is required.")

            if not form_explanation.strip():
                validation_errors.append("Explanation is required.")
            elif len(form_explanation.strip()) < 10:
                validation_errors.append("Explanation is too short — please provide more detail.")

            if validation_errors:
                for err in validation_errors:
                    st.warning(f"⚠️  {err}")
            else:
                with st.spinner("Submitting your request..."):
                    new_request = {
                        "status":              "Pending",
                        "course_id":           COURSE_ID,
                        "student_email":       form_student_email.strip(),
                        "absence_date":        str(form_absence_date),
                        "submitted_timestamp": datetime.now().isoformat(),
                        "excuse_type":         form_excuse_type,
                        "explanation":         form_explanation.strip(),
                        "instructor_note":     "",
                    }

                    all_requests.append(new_request)

                    with open(json_path, "w") as f:
                        json.dump(all_requests, f, indent=2)

                    st.session_state["selected_request_index"] = len(all_requests) - 1

                    st.balloons()
                    time.sleep(8)
                    st.session_state["page"] = "dashboard"
                    st.rerun()

    with col2:
        st.subheader("AI Assistant")
        col11, col22 = st.columns([3, 1])
        with col11:
            st.caption("Try asking: How do I submit an excuse request?")
        with col22:
            if st.button("Clear Messages", key="clear_messages_btn"):
                st.session_state["messages"] = [{"role": "assistant", "content": "Hi! I can help you with the absence excuse process. How can I assist?"}]
                st.rerun()

        with st.container(border=True, height=250):
            for message in st.session_state["messages"]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        user_input = st.chat_input("Ask a question....")
        if user_input:
            with st.spinner("Thinking..."):
                st.session_state["messages"].append(
                    {
                        "role": "user",
                        "content": user_input,
                    }
                )

                user_lower = user_input.lower()
                if "submit" in user_lower or "how" in user_lower or "request" in user_lower:
                    ai_response = "To submit an excuse request: fill in your student email, select the absence date, choose an excuse type, and write a detailed explanation. Then click Submit Request."
                elif "status" in user_lower or "check" in user_lower or "view" in user_lower:
                    ai_response = "To check your request status, go to the Excuse Absence Dashboard using the sidebar. Find your submission in the table or select it from the dropdown to see full details."
                elif "excuse type" in user_lower or "type" in user_lower:
                    ai_response = "Available excuse types: Medical / Illness, Family Emergency, Transportation Issue, Academic Conflict, Religious Observance, and Other."
                elif "approved" in user_lower or "denied" in user_lower or "pending" in user_lower:
                    ai_response = "Request statuses — Pending: under review. Approved: excuse accepted. Denied: excuse not accepted. Check the Instructor Note field for details."
                elif "date" in user_lower or "absence" in user_lower:
                    ai_response = "Select the exact date you were absent using the date picker on the form. Absence date is saved in YYYY-MM-DD format."
                else:
                    ai_response = "I can help with: submitting a request, checking status, understanding excuse types, and navigating the portal. What would you like to know?"

                st.session_state["messages"].append(
                    {
                        "role": "assistant",
                        "content": ai_response,
                    }
                )
                time.sleep(2)
                st.rerun()
