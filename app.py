import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, date

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Excuse Absence Portal | Course 011101",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
COURSE_ID = "011101"
DATA_FILE = "requests.json"
EXCUSE_TYPES = [
    "Medical / Illness",
    "Family Emergency",
    "Transportation Issue",
    "Academic Conflict",
    "Religious Observance",
    "Other"
]

STATUS_COLORS = {
    "Pending":  "#FFA500",
    "Approved": "#28a745",
    "Denied":   "#dc3545",
}

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1a1f36;
    }
    [data-testid="stSidebar"] * {
        color: #e0e4f0 !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #2d3561;
        color: #ffffff !important;
        border: 1px solid #4a5080;
        border-radius: 8px;
        font-weight: 500;
        transition: background-color 0.2s;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #4a5080;
    }

    /* Main area card style */
    .detail-card {
        background-color: #f8f9fc;
        border: 1px solid #e0e4ef;
        border-radius: 10px;
        padding: 20px 24px;
        margin-top: 12px;
    }

    /* Status badge */
    .badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.82em;
        font-weight: 600;
        color: #fff;
    }
    .badge-pending  { background-color: #e08c00; }
    .badge-approved { background-color: #28a745; }
    .badge-denied   { background-color: #dc3545; }

    /* Section header accent */
    .section-label {
        font-size: 0.75em;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #7a86a5;
        margin-bottom: 2px;
    }
    .section-value {
        font-size: 1em;
        color: #1a1f36;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ─── JSON LOADING ─────────────────────────────────────────────────────────────
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        all_requests = json.load(f)
else:
    all_requests = []

# ─── SESSION STATE INITIALIZATION ─────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Dashboard"

if "selected_request_index" not in st.session_state:
    st.session_state["selected_request_index"] = None

if "submit_success" not in st.session_state:
    st.session_state["submit_success"] = False

# ─── SIDEBAR NAVIGATION ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📋 Excuse Portal")
    st.markdown(f"**Course ID:** `{COURSE_ID}`")
    st.divider()

    st.markdown("### 🗂️ Navigation")

    if st.button(
        "📊  Excuse Absence Dashboard",
        key="nav_dashboard_btn",
        use_container_width=True
    ):
        st.session_state["current_page"] = "Dashboard"
        st.session_state["submit_success"] = False
        st.rerun()

    if st.button(
        "📝  Submit Excuse Request",
        key="nav_request_btn",
        use_container_width=True
    ):
        st.session_state["current_page"] = "Request"
        st.session_state["submit_success"] = False
        st.rerun()

    st.divider()
    total = len(all_requests)
    pending_count = sum(1 for r in all_requests if r.get("status") == "Pending")
    st.markdown(f"**Total Requests:** {total}")
    st.markdown(f"**Pending Review:** {pending_count}")
    st.caption("Use the buttons above to navigate between pages.")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["current_page"] == "Dashboard":

    st.title("📊 Excuse Absence Dashboard")
    st.markdown(f"*Course **{COURSE_ID}** — Review all submitted absence excuse requests.*")
    st.divider()

    # ── Success banner (shown after a fresh submission) ──
    if st.session_state.get("submit_success"):
        st.success("✅ New request submitted successfully! It is highlighted below.")
        st.session_state["submit_success"] = False

    # ── No requests yet ──
    if len(all_requests) == 0:
        st.info(
            "📭 No excuse requests have been submitted yet. "
            "Click **Submit Excuse Request** in the sidebar to add one."
        )

    else:
        # ── Summary table ──
        st.subheader("All Requests")

        display_rows = []
        for i, req in enumerate(all_requests):
            display_rows.append({
                "#": i + 1,
                "Student Email":  req.get("student_email", ""),
                "Absence Date":   req.get("absence_date", ""),
                "Excuse Type":    req.get("excuse_type", ""),
                "Status":         req.get("status", "Pending"),
                "Submitted":      req.get("submitted_timestamp", "")[:10]
                                  if req.get("submitted_timestamp") else "",
            })

        df = pd.DataFrame(display_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()

        # ── Request selector ──
        st.subheader("🔍 Request Details")
        st.markdown("Select a request from the list below to view its full details.")

        selector_options = [
            f"#{i + 1}  —  {req.get('student_email', '?')}  —  {req.get('absence_date', '?')}"
            for i, req in enumerate(all_requests)
        ]

        # Restore previously selected index so it persists across reruns
        if (
            st.session_state["selected_request_index"] is not None
            and st.session_state["selected_request_index"] < len(all_requests)
        ):
            default_selector_idx = st.session_state["selected_request_index"] + 1
        else:
            default_selector_idx = 0

        selected_label = st.selectbox(
            "Choose a request:",
            options=["— Select a request to inspect —"] + selector_options,
            index=default_selector_idx,
            key="dash_request_selector"
        )

        # Update session state based on selection
        if selected_label == "— Select a request to inspect —":
            st.session_state["selected_request_index"] = None
        else:
            st.session_state["selected_request_index"] = selector_options.index(selected_label)

        # ── Detail view ──
        if st.session_state["selected_request_index"] is not None:
            idx = st.session_state["selected_request_index"]
            req = all_requests[idx]
            status = req.get("status", "Pending")
            badge_class = f"badge-{status.lower()}"

            st.markdown(
                f"<div class='detail-card'>",
                unsafe_allow_html=True
            )

            # Header row
            header_col, badge_col = st.columns([4, 1])
            with header_col:
                st.markdown(f"#### Request #{idx + 1}")
            with badge_col:
                st.markdown(
                    f"<span class='badge {badge_class}'>{status}</span>",
                    unsafe_allow_html=True
                )

            st.divider()

            # Two-column layout for details
            left_col, right_col = st.columns(2)

            with left_col:
                st.markdown("<p class='section-label'>Student Email</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='section-value'>{req.get('student_email', 'N/A')}</p>", unsafe_allow_html=True)

                st.markdown("<p class='section-label'>Absence Date</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='section-value'>{req.get('absence_date', 'N/A')}</p>", unsafe_allow_html=True)

                st.markdown("<p class='section-label'>Excuse Type</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='section-value'>{req.get('excuse_type', 'N/A')}</p>", unsafe_allow_html=True)

            with right_col:
                st.markdown("<p class='section-label'>Course ID</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='section-value'>{req.get('course_id', 'N/A')}</p>", unsafe_allow_html=True)

                st.markdown("<p class='section-label'>Submitted At</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='section-value'>{req.get('submitted_timestamp', 'N/A')}</p>", unsafe_allow_html=True)

                instructor_note = req.get("instructor_note", "").strip()
                st.markdown("<p class='section-label'>Instructor Note</p>", unsafe_allow_html=True)
                st.markdown(
                    f"<p class='section-value'>{instructor_note if instructor_note else '(none)'}</p>",
                    unsafe_allow_html=True
                )

            st.markdown("<p class='section-label'>Explanation</p>", unsafe_allow_html=True)
            st.info(req.get("explanation", "No explanation provided."))

            st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# REQUEST PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["current_page"] == "Request":

    st.title("📝 Excuse Absence Request")
    st.markdown(f"*Course **{COURSE_ID}** — Submit a new absence excuse request below.*")
    st.divider()

    with st.container():
        st.subheader("Student Information")

        info_col1, info_col2 = st.columns(2)

        with info_col1:
            form_student_email = st.text_input(
                "Student Email *",
                placeholder="yourname@university.edu",
                key="form_student_email"
            )

        with info_col2:
            form_absence_date = st.date_input(
                "Absence Date *",
                value=date.today(),
                key="form_absence_date"
            )

        st.divider()
        st.subheader("Absence Details")

        form_excuse_type = st.selectbox(
            "Excuse Type *",
            options=["— Select excuse type —"] + EXCUSE_TYPES,
            key="form_excuse_type"
        )

        form_explanation = st.text_area(
            "Explanation *",
            placeholder="Please describe in detail why you were absent and provide any relevant context...",
            height=160,
            key="form_explanation"
        )

        st.divider()

        # ── Submission row ──
        submit_col, note_col = st.columns([1, 3])
        with submit_col:
            form_submit_clicked = st.button(
                "Submit Request",
                key="form_submit_btn",
                type="primary",
                use_container_width=True
            )
        with note_col:
            st.caption("Fields marked with * are required. Your request will default to **Pending** status.")

        # ── Validation & Save ──
        if form_submit_clicked:
            validation_errors = []

            if not form_student_email.strip():
                validation_errors.append("Student Email is required.")
            elif "@" not in form_student_email or "." not in form_student_email.split("@")[-1]:
                validation_errors.append("Please enter a valid email address (e.g. name@university.edu).")

            if form_excuse_type == "— Select excuse type —":
                validation_errors.append("Excuse Type is required — please select one from the dropdown.")

            if not form_explanation.strip():
                validation_errors.append("Explanation is required — please describe your absence.")
            elif len(form_explanation.strip()) < 10:
                validation_errors.append("Explanation is too short — please provide more detail.")

            if validation_errors:
                for err in validation_errors:
                    st.warning(f"⚠️  {err}")
            else:
                # ── Build and save the new request ──
                new_request = {
                    "status":              "Pending",
                    "course_id":           COURSE_ID,
                    "student_email":       form_student_email.strip(),
                    "absence_date":        str(form_absence_date),
                    "submitted_timestamp": datetime.now().isoformat(),
                    "excuse_type":         form_excuse_type,
                    "explanation":         form_explanation.strip(),
                    "instructor_note":     ""
                }

                all_requests.append(new_request)

                with open(DATA_FILE, "w") as f:
                    json.dump(all_requests, f, indent=2)

                # Navigate to Dashboard, pre-select the new record, show banner
                st.session_state["current_page"] = "Dashboard"
                st.session_state["selected_request_index"] = len(all_requests) - 1
                st.session_state["submit_success"] = True
                st.rerun()
