import streamlit as st
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
import uuid

st.set_page_config("ClearVision Clinic", layout="wide", initial_sidebar_state="expanded")

# ─── CUSTOM STYLING ────────────────────────────────────────────────────────────────
def inject_custom_css():
    """Inject custom CSS for polished UI."""
    st.markdown("""
    <style>
    /* Typography and headers */
    .section-header {
        font-size: 1.4rem;
        font-weight: 600;
        color: #1f77b4;
        border-bottom: 3px solid #1f77b4;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }

    /* Status badges */
    .status-scheduled {
        background-color: #d4edda;
        color: #155724;
        padding: 0.3rem 0.6rem;
        border-radius: 0.25rem;
        font-weight: 500;
        font-size: 0.9rem;
    }
    .status-completed {
        background-color: #cfe2ff;
        color: #084298;
        padding: 0.3rem 0.6rem;
        border-radius: 0.25rem;
        font-weight: 500;
        font-size: 0.9rem;
    }
    .status-cancelled {
        background-color: #f8d7da;
        color: #842029;
        padding: 0.3rem 0.6rem;
        border-radius: 0.25rem;
        font-weight: 500;
        font-size: 0.9rem;
    }
    .status-no-show {
        background-color: #fff3cd;
        color: #664d03;
        padding: 0.3rem 0.6rem;
        border-radius: 0.25rem;
        font-weight: 500;
        font-size: 0.9rem;
    }

    /* Styled table */
    .styled-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1rem;
    }
    .styled-table thead th {
        background-color: #1f77b4;
        color: white;
        padding: 0.75rem;
        text-align: left;
        font-weight: 600;
        border-radius: 0.25rem 0.25rem 0 0;
    }
    .styled-table tbody tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    .styled-table tbody tr:nth-child(odd) {
        background-color: #ffffff;
    }
    .styled-table tbody td {
        padding: 0.75rem;
        border-bottom: 1px solid #dee2e6;
    }
    .styled-table tbody tr:hover {
        background-color: #f1f5f9;
    }

    /* Slot card */
    .slot-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
    .slot-card-date {
        font-weight: 600;
        color: #1f77b4;
        font-size: 1rem;
    }
    .slot-card-time {
        color: #495057;
        font-size: 0.95rem;
    }

    /* Footer */
    .clinic-footer {
        text-align: center;
        padding: 2rem 0 1rem;
        border-top: 1px solid #e0e0e0;
        color: #6c757d;
        font-size: 0.9rem;
    }

    /* Tighter spacing for containers and forms */
    div[data-testid="stMetric"] { padding: 0.5rem 0; }

    /* Consistent subheader styling */
    .stTabs [data-baseweb="tab-panel"] { padding-top: 1rem; }

    /* Better button grouping spacing */
    .stButton > button { margin-top: 0.25rem; }
    div[data-testid="stForm"] { padding: 1rem; }

    /* Password strength indicator */
    .pwd-strength-weak { color: #dc3545; font-size: 0.85rem; }
    .pwd-strength-ok { color: #ffc107; font-size: 0.85rem; }
    .pwd-strength-good { color: #28a745; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

def format_appointment_date(date_str):
    """Format date string to readable format."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except:
        return date_str

def format_appointment_time(time_str):
    """Format time string nicely."""
    try:
        return time_str if ":" in time_str else f"{time_str}:00"
    except:
        return time_str

def get_status_badge_html(status):
    """Return HTML badge for appointment status."""
    status_class = {
        "Scheduled": "status-scheduled",
        "Completed": "status-completed",
        "Cancelled": "status-cancelled",
        "No-Show": "status-no-show",
    }.get(status, "status-scheduled")
    return f'<span class="{status_class}">{status}</span>'

# ─── CONSTANTS ─────────────────────────────────────────────────────────────────
CLINIC_ID = "ClearVision-01"
APPOINTMENT_TYPES = [
    "Routine Vision Check",
    "Glaucoma Screening",
    "Fundus Exam",
    "Cataract Evaluation",
    "Retinal Exam",
]
APPT_STATUSES = ["Scheduled", "Completed", "No-Show", "Cancelled"]

PATH_PATIENTS     = Path("patients.json")
PATH_DOCTORS      = Path("doctors.json")
PATH_APPOINTMENTS = Path("appointments.json")

# ─── DATA STORE CLASS ──────────────────────────────────────────────────────────
class DataStore:
    """Centralized persistence layer for JSON files."""

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def load_json(path, default):
        """Load JSON file with validation."""
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if type(data) is type(default):
                        return data
                    else:
                        st.warning(
                            f"⚠️  Data in **{path.name}** has an unexpected format. "
                            f"Using defaults. You may want to check or delete the file to reset."
                        )
                        return default
            except json.JSONDecodeError as e:
                st.error(
                    f"⚠️  **{path.name}** contains malformed JSON (parse error: {e}). "
                    f"Using defaults. Please fix or delete the file to restore normal operation."
                )
                return default
            except OSError as e:
                st.error(
                    f"⚠️  Could not read **{path.name}**: {e}. "
                    f"Check file permissions and try again."
                )
                return default
        else:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(default, f, indent=2)
            except OSError as e:
                st.error(
                    f"⚠️  Could not create **{path.name}**: {e}. "
                    f"Check that the directory is writable."
                )
            return default

    @staticmethod
    def save_json(path, data):
        """Atomic write: write to .tmp then rename to avoid partial-write corruption."""
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp.replace(path)
            return True
        except OSError as e:
            st.error(
                f"⚠️  Could not save **{path.name}**: {e}. "
                f"Your changes were not persisted — please try again. "
                f"If this persists, check disk space and file permissions."
            )
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    @staticmethod
    def reload_json(path, default):
        """Reload a JSON file from disk (no side effects). Used before writes to get fresh data."""
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return default
        return default

    @staticmethod
    def transactional_save(*file_pairs):
        """
        Transactional save for one or more files.
        Accepts pairs of (path, data): transactional_save((path1, data1), (path2, data2), ...)
        Backs up originals, writes all, and rolls back everything on any failure.
        Returns (success: bool, message: str).
        """
        backups = []

        try:
            # Phase 1: read backups
            for path, _ in file_pairs:
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        backups.append((path, json.load(f)))
                else:
                    backups.append((path, None))

            # Phase 2: write all to .tmp files
            tmp_files = []
            for path, data in file_pairs:
                tmp = path.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                tmp_files.append((tmp, path))

            # Phase 3: atomic rename all
            for tmp, target in tmp_files:
                tmp.replace(target)

            return True, "Changes saved successfully."
        except OSError as e:
            # Rollback: restore all backups
            for path, original in backups:
                if original is not None:
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(original, f, indent=2)
                    except OSError:
                        pass
            # Clean up any leftover .tmp files
            for path, _ in file_pairs:
                try:
                    path.with_suffix(".tmp").unlink(missing_ok=True)
                except OSError:
                    pass
            return False, f"Save failed: {e}. All changes rolled back."

# ─── VALIDATORS CLASS ──────────────────────────────────────────────────────────
class Validators:
    """Centralized validation logic."""

    @staticmethod
    def email_valid(email):
        """Validate email with stronger checks."""
        email = email.strip()
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def password_strength(password):
        """Check password strength. Returns 'weak', 'ok', or 'good'."""
        if len(password) < 6:
            return 'weak'
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        if has_upper and has_digit:
            return 'good'
        return 'ok'

    @staticmethod
    def validate_patient_registration(name, email, password, confirm, existing_patients):
        """Validate patient registration form."""
        errors = []
        if not name.strip():
            errors.append("Full Name is required.")
        normalized_email = email.strip().lower()
        if not Validators.email_valid(email):
            errors.append("Please enter a valid email address (e.g., name@example.com).")
        elif any(p.get("email", "").strip().lower() == normalized_email for p in existing_patients):
            errors.append("An account with this email already exists. Please log in instead.")
        if not password.strip():
            errors.append("Password is required.")
        elif len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        return errors

    @staticmethod
    def validate_doctor_registration(name, email, specialty, password, confirm, existing_doctors):
        """Validate doctor registration form."""
        errors = []
        if not name.strip():
            errors.append("Full Name is required.")
        normalized_email = email.strip().lower()
        if not Validators.email_valid(email):
            errors.append("Please enter a valid email address (e.g., name@example.com).")
        elif any(d.get("email", "").strip().lower() == normalized_email for d in existing_doctors):
            errors.append("An account with this email already exists. Please log in instead.")
        if not specialty.strip():
            errors.append("Specialty is required.")
        if not password.strip():
            errors.append("Password is required.")
        elif len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        return errors

    @staticmethod
    def validate_booking(doctor, appt_type, symptoms, slot):
        """Validate appointment booking form."""
        errors = []
        if not doctor:
            errors.append("Please select a doctor.")
        if appt_type == "— Select appointment type —":
            errors.append("Appointment Type is required.")
        if not symptoms.strip():
            errors.append("Symptom summary is required.")
        elif len(symptoms.strip()) < 10:
            errors.append("Symptom summary is too short — please provide more detail.")
        if not slot:
            if doctor:
                errors.append("No available time slots. Please ask your doctor to add time slots.")
            else:
                errors.append("No available time slot to book.")
        return errors

# ─── APPOINTMENT SERVICE CLASS ──────────────────────────────────────────────────
class AppointmentService:
    """Business logic for appointments and slots."""

    @staticmethod
    def build_appointment(patient_name, patient_email, doctor, slot, appt_type, symptoms):
        """Create appointment object."""
        slot_date, slot_time = slot.split("T")
        return {
            "appointment_id":      f"appt-{str(uuid.uuid4())[:8]}",
            "clinic_id":           CLINIC_ID,
            "patient_name":        patient_name,
            "patient_email":       patient_email,
            "doctor_id":           doctor.get("doctor_id", ""),
            "doctor_name":         doctor.get("name", ""),
            "appointment_date":    slot_date,
            "appointment_time":    slot_time,
            "submitted_timestamp": datetime.now().isoformat(),
            "appointment_type":    appt_type,
            "symptom_summary":     symptoms,
            "status":              "Scheduled",
            "doctor_note":         "",
        }

    @staticmethod
    def remove_slot_from_doctor(doctors_list, doctor_id, slot):
        """Remove a time slot from doctor's availability."""
        for doc in doctors_list:
            if doc.get("doctor_id") == doctor_id and slot in doc.get("available_slots", []):
                doc["available_slots"].remove(slot)
                break

    @staticmethod
    def add_slot_to_doctor(doctors_list, doctor_id, slot):
        """Add a time slot to doctor's availability."""
        for doc in doctors_list:
            if doc.get("doctor_id") == doctor_id and slot not in doc.get("available_slots", []):
                doc["available_slots"].append(slot)
                break

    @staticmethod
    def reschedule_appointment(appointments, appt_id, new_date, new_time):
        """Reschedule an appointment to new date/time."""
        for appt in appointments:
            if appt.get("appointment_id") == appt_id:
                appt["appointment_date"] = new_date
                appt["appointment_time"] = new_time
                break

    @staticmethod
    def cancel_appointment(appointments, appt_id):
        """Mark appointment as cancelled."""
        for appt in appointments:
            if appt.get("appointment_id") == appt_id:
                appt["status"] = "Cancelled"
                break

    @staticmethod
    def update_appointment_status(appointments, appt_id, status, note):
        """Update appointment status and doctor note."""
        for appt in appointments:
            if appt.get("appointment_id") == appt_id:
                appt["status"]      = status
                appt["doctor_note"] = note
                break

    @staticmethod
    def get_doctor_by_id(doctors_list, doctor_id):
        """Retrieve doctor by ID."""
        return next((d for d in doctors_list if d.get("doctor_id") == doctor_id), None)

    @staticmethod
    def get_appointment_by_id(appointments, appt_id):
        """Retrieve appointment by ID."""
        return next((a for a in appointments if a.get("appointment_id") == appt_id), None)

    @staticmethod
    def get_patient_appointments(appointments, patient_email):
        """Get all appointments for a patient."""
        email = patient_email.strip().lower()
        return [a for a in appointments if a.get("patient_email", "").strip().lower() == email]

    @staticmethod
    def get_doctor_appointments(appointments, doctor_id):
        """Get all appointments for a doctor."""
        return [a for a in appointments if a.get("doctor_id") == doctor_id]

    @staticmethod
    def get_scheduled_appointments(appointments, patient_email):
        """Get only scheduled appointments for a patient."""
        return [a for a in AppointmentService.get_patient_appointments(appointments, patient_email)
                if a.get("status") == "Scheduled"]

# ─── RECORD CREATION CLASS ─────────────────────────────────────────────────────
class RecordFactory:
    """Create new patient and doctor records."""

    @staticmethod
    def create_patient_record(name, email, password):
        """Create new patient record."""
        return {
            "patient_id": f"pat_{str(uuid.uuid4())[:8]}",
            "name":       name.strip(),
            "email":      email.strip().lower(),
            "password":   DataStore.hash_password(password),
        }

    @staticmethod
    def create_doctor_record(name, email, specialty, password):
        """Create new doctor record."""
        return {
            "doctor_id":       f"doc_{str(uuid.uuid4())[:8]}",
            "name":            name.strip(),
            "email":           email.strip().lower(),
            "specialty":       specialty.strip(),
            "password":        DataStore.hash_password(password),
            "available_slots": [],
        }

# ─── AI ASSISTANT ──────────────────────────────────────────────────────────────
def get_ai_response(user_input, appointments, doctors, patient_email):
    """Generate AI assistant response."""
    q = user_input.lower()
    if "next appointment" in q:
        scheduled = AppointmentService.get_scheduled_appointments(appointments, patient_email)
        if scheduled:
            nxt = sorted(scheduled, key=lambda x: x.get("appointment_date", ""))[0]
            return (f"Your next appointment is on {format_appointment_date(nxt.get('appointment_date', ''))} at "
                    f"{nxt.get('appointment_time', '')} with {nxt.get('doctor_name', '')} "
                    f"for a {nxt.get('appointment_type', '')}.")
        return "You have no upcoming scheduled appointments. Use the form on the left to book one."
    if "available" in q or "slot" in q:
        open_slots = [f"{d.get('name', 'Unknown')}: {s.replace('T', ' at ')}"
                      for d in doctors for s in d.get("available_slots", [])]
        return ("Available slots:\n" + "\n".join(open_slots)) if open_slots \
            else "There are currently no available time slots. Please ask a doctor to add some."
    if "cancel" in q:
        return ("To cancel an appointment:\n"
                "1. Click the 'Book Appointment' tab\n"
                "2. Go to the 'Cancel an Appointment' tab\n"
                "3. Select an appointment and click Cancel")
    if "doctor" in q:
        avail = [f"{d.get('name', 'Unknown')} ({d.get('specialty', 'General')})"
                 for d in doctors if d.get("available_slots")]
        return ("Doctors with open slots:\n" + "\n".join(avail)) if avail \
            else "No doctors currently have available slots. Please check back later."
    if "prepare" in q or "exam" in q:
        return ("Exam preparation tips:\n"
                "- Bring your insurance card and photo ID\n"
                "- Avoid contact lenses 24 hours before a retinal or fundus exam\n"
                "- Arrange a ride if dilation drops will be used\n"
                "- Bring a list of current medications\n"
                "- Note any recent vision changes to share with your doctor")
    return ("I can help with: checking available slots, your next appointment, "
            "cancellation steps, doctor availability, and exam preparation. "
            "What would you like to know?")

# ─── SESSION STATE MANAGEMENT ──────────────────────────────────────────────────
def reset_session():
    """Centralized function to reset session state."""
    st.session_state.update({
        "logged_in": False,
        "role": None,
        "current_user_name": None,
        "current_user_email": None,
        "current_doctor_id": None,
        "page": "login",
        "patient_selected_appt_id": None,
        "doctor_selected_appt_id": None,
        "messages": [
            {"role": "assistant", "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?"}
        ],
        "_flash_message": None,
        "_flash_type": None,
    })

def set_flash(message, msg_type="success"):
    """Set a one-shot flash message that survives exactly one rerun."""
    st.session_state["_flash_message"] = message
    st.session_state["_flash_type"] = msg_type

def show_flash():
    """Display and clear any pending flash message."""
    msg = st.session_state.get("_flash_message")
    if msg:
        msg_type = st.session_state.get("_flash_type", "success")
        if msg_type == "success":
            st.success(msg)
        elif msg_type == "error":
            st.error(msg)
        elif msg_type == "warning":
            st.warning(msg)
        else:
            st.info(msg)
        st.session_state["_flash_message"] = None
        st.session_state["_flash_type"] = None

def require_role(expected_role):
    """Role-based authorization check. Returns True if authorized, False otherwise."""
    if st.session_state.get("role") != expected_role:
        reset_session()
        navigate_to("login")
        return False
    return True

# ─── UI HELPERS CLASS ──────────────────────────────────────────────────────────
class UIHelpers:
    """Shared UI components and styling."""

    @staticmethod
    def show_validation_errors(errors):
        """Display validation errors."""
        for err in errors:
            st.warning(f"⚠️  {err}")

    @staticmethod
    def render_styled_table(appointments):
        """Render appointments as a styled HTML table instead of st.dataframe."""
        if not appointments:
            st.info("No appointments to display.")
            return

        html_rows = []
        for a in appointments:
            status_html = get_status_badge_html(a.get("status", "Scheduled"))
            row = f"""
            <tr>
                <td>{a.get("appointment_id", "")}</td>
                <td>{a.get("patient_name", "")}</td>
                <td>{a.get("doctor_name", "")}</td>
                <td>{format_appointment_date(a.get("appointment_date", ""))}</td>
                <td>{a.get("appointment_time", "")}</td>
                <td>{a.get("appointment_type", "")}</td>
                <td>{status_html}</td>
            </tr>
            """
            html_rows.append(row)

        html = f"""
        <table class="styled-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Patient</th>
                    <th>Doctor</th>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {"".join(html_rows)}
            </tbody>
        </table>
        """
        st.markdown(html, unsafe_allow_html=True)

    @staticmethod
    def appt_selectbox(label, appointments, key, state_key="patient_selected_appt_id"):
        """Selectbox backed by appointment_id — immune to list reordering."""
        label_to_id = {
            f"{format_appointment_date(a.get('appointment_date','?'))} {a.get('appointment_time','')}  —  "
            f"{a.get('appointment_type','?')}  —  {a.get('status','?')}": a.get("appointment_id", "")
            for a in appointments
        }
        current_id    = st.session_state.get(state_key)
        current_label = next((lbl for lbl, aid in label_to_id.items() if aid == current_id), None)
        options       = ["— Select an appointment —"] + list(label_to_id.keys())
        default_idx   = options.index(current_label) if current_label in options else 0

        chosen = st.selectbox(label, options=options, index=default_idx, key=key)
        st.session_state[state_key] = (
            None if chosen == "— Select an appointment —" else label_to_id[chosen]
        )

# ─── NAVIGATION HELPER ─────────────────────────────────────────────────────────
def navigate_to(page):
    """Navigate to a page and optionally reset page-specific state keys."""
    if page == "patient_dashboard":
        st.session_state["doctor_selected_appt_id"] = None
    elif page == "doctor_dashboard":
        st.session_state["patient_selected_appt_id"] = None
    st.session_state["page"] = page
    st.rerun()

# ─── PAGE RENDERERS ────────────────────────────────────────────────────────────
def render_sidebar():
    """Render the sidebar with navigation."""
    with st.sidebar:
        st.markdown("## 👁️ ClearVision Clinic")
        st.divider()
        role_icon = "🩺" if st.session_state["role"] == "Doctor" else "👤"
        st.markdown(f"{role_icon} **{st.session_state.get('current_user_name', 'User')}**")
        st.caption(f"Role: {st.session_state.get('role', 'Unknown')}")
        st.divider()

        if st.session_state.get("role") == "Patient":
            if st.button("My Appointments", key="nav_dashboard_btn", type="primary", use_container_width=True):
                navigate_to("patient_dashboard")
            if st.button("Book Appointment", key="nav_book_btn", type="primary", use_container_width=True):
                navigate_to("patient_book")
        elif st.session_state.get("role") == "Doctor":
            if st.button("Appointment Dashboard", key="nav_dashboard_btn", type="primary", use_container_width=True):
                navigate_to("doctor_dashboard")
            if st.button("Manage Time Slots", key="nav_slots_btn", type="primary", use_container_width=True):
                navigate_to("doctor_slots")

        st.divider()
        if st.button("Log Out", key="logout_btn", use_container_width=True):
            reset_session()
            navigate_to("login")

def render_clinic_footer():
    """Render footer with clinic branding."""
    st.markdown("""
    <div class="clinic-footer">
        <strong>ClearVision Clinic</strong> | Ophthalmology Appointment Portal<br>
        © 2026. All rights reserved.
    </div>
    """, unsafe_allow_html=True)

# ── Login page ─────────────────────────────────────────────────────────────────
def render_login_page(all_patients, doctors):
    """Render login/register page."""
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<h1 style='text-align: center;'>👁️ ClearVision Clinic</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'><em>Ophthalmology Appointment Portal</em></p>", unsafe_allow_html=True)
        st.divider()

        show_flash()

        tab_patient, tab_doctor = st.tabs(["Patient Login", "Doctor Login"])
        with tab_patient:
            mode = st.radio("", ["Login", "Register"], key="patient_mode", horizontal=True)
            st.divider()
            if mode == "Login":
                _render_patient_login(all_patients)
            else:
                _render_patient_register(all_patients)

        with tab_doctor:
            mode = st.radio("", ["Login", "Register"], key="doctor_mode", horizontal=True)
            st.divider()
            if mode == "Login":
                _render_doctor_login(doctors)
            else:
                _render_doctor_register(doctors)


def _render_patient_login(all_patients):
    """Render patient login form."""
    st.subheader("Patient Login")
    email    = st.text_input("Email",    placeholder="yourname@email.com", key="login_patient_email")
    password = st.text_input("Password", type="password",                  key="login_patient_password")

    if st.button("Log In as Patient", key="login_patient_btn", type="primary", use_container_width=True):
        if not Validators.email_valid(email):
            st.warning("⚠️  Please enter a valid email address.")
        elif not password.strip():
            st.warning("⚠️  Please enter your password.")
        else:
            matched = next(
                (p for p in all_patients
                 if p.get("email", "").strip().lower() == email.strip().lower()
                 and p.get("password") == DataStore.hash_password(password)),
                None,
            )
            if matched:
                st.session_state.update({
                    "logged_in": True, "role": "Patient",
                    "current_user_name": matched.get("name", "User"),
                    "current_user_email": matched.get("email", ""),
                })
                navigate_to("patient_dashboard")
            else:
                st.error("Incorrect email or password. Please try again.")


def _render_patient_register(all_patients):
    """Render patient registration form."""
    st.subheader("Patient Register")
    name     = st.text_input("Full Name *",        placeholder="James Lee",          key="reg_patient_name")
    email    = st.text_input("Email *",            placeholder="yourname@email.com", key="reg_patient_email")
    password = st.text_input("Password *",         type="password",                  key="reg_patient_password",
                             help="Must be at least 6 characters (at least 1 uppercase + 1 digit recommended).")
    confirm  = st.text_input("Confirm Password *", type="password",                  key="reg_patient_confirm")

    # Password strength indicator
    if password:
        strength = Validators.password_strength(password)
        if strength == 'weak':
            st.markdown('<span class="pwd-strength-weak">⚠️ Weak password</span>', unsafe_allow_html=True)
        elif strength == 'ok':
            st.markdown('<span class="pwd-strength-ok">✓ Good password</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="pwd-strength-good">✓✓ Strong password</span>', unsafe_allow_html=True)

    if st.button("Create Account", key="reg_patient_btn", type="primary", use_container_width=True):
        errors = Validators.validate_patient_registration(name, email, password, confirm, all_patients)
        if errors:
            UIHelpers.show_validation_errors(errors)
        else:
            with st.spinner("Creating your account..."):
                all_patients.append(RecordFactory.create_patient_record(name, email, password))
                if DataStore.save_json(PATH_PATIENTS, all_patients):
                    set_flash("Account created successfully! Please log in.")
                    st.session_state["patient_mode"] = "Login"
                    navigate_to("login")
                else:
                    all_patients.pop()
                    st.error("⚠️  Could not create account. Please try again.")


def _render_doctor_login(doctors):
    """Render doctor login form."""
    st.subheader("Doctor Login")
    email    = st.text_input("Email",    placeholder="doctor@clearvision.com", key="login_doc_email")
    password = st.text_input("Password", type="password",                      key="login_doc_password")

    if st.button("Log In as Doctor", key="login_doctor_btn", type="primary", use_container_width=True):
        if not Validators.email_valid(email):
            st.warning("⚠️  Please enter a valid email address.")
        elif not password.strip():
            st.warning("⚠️  Please enter your password.")
        else:
            matched = next(
                (d for d in doctors
                 if d.get("email", "").strip().lower() == email.strip().lower()
                 and d.get("password") == DataStore.hash_password(password)),
                None,
            )
            if matched:
                st.session_state.update({
                    "logged_in": True, "role": "Doctor",
                    "current_user_name": matched.get("name", "Dr. User"),
                    "current_doctor_id": matched.get("doctor_id", ""),
                })
                navigate_to("doctor_dashboard")
            else:
                st.error("Incorrect email or password. Please try again.")


def _render_doctor_register(doctors):
    """Render doctor registration form."""
    st.subheader("Doctor Registration")
    name      = st.text_input("Full Name *",        placeholder="Dr. Jane Smith",         key="reg_doc_name")
    email     = st.text_input("Email *",            placeholder="doctor@clearvision.com", key="reg_doc_email")
    specialty = st.text_input("Specialty *",        placeholder="e.g. Retinal Disease",   key="reg_doc_specialty")
    password  = st.text_input("Password *",         type="password",                      key="reg_doc_password",
                              help="Must be at least 6 characters (at least 1 uppercase + 1 digit recommended).")
    confirm   = st.text_input("Confirm Password *", type="password",                      key="reg_doc_confirm")

    # Password strength indicator
    if password:
        strength = Validators.password_strength(password)
        if strength == 'weak':
            st.markdown('<span class="pwd-strength-weak">⚠️ Weak password</span>', unsafe_allow_html=True)
        elif strength == 'ok':
            st.markdown('<span class="pwd-strength-ok">✓ Good password</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="pwd-strength-good">✓✓ Strong password</span>', unsafe_allow_html=True)

    if st.button("Create Doctor Account", key="reg_doc_btn", type="primary", use_container_width=True):
        errors = Validators.validate_doctor_registration(name, email, specialty, password, confirm, doctors)
        if errors:
            UIHelpers.show_validation_errors(errors)
        else:
            with st.spinner("Creating your account..."):
                doctors.append(RecordFactory.create_doctor_record(name, email, specialty, password))
                if DataStore.save_json(PATH_DOCTORS, doctors):
                    set_flash("Doctor account created successfully! Please log in.")
                    st.session_state["doctor_mode"] = "Login"
                    navigate_to("login")
                else:
                    doctors.pop()
                    st.error("⚠️  Could not create account. Please try again.")


# ── Patient dashboard ──────────────────────────────────────────────────────────
def render_patient_dashboard(all_appointments, patient_email, patient_name):
    """Render patient dashboard."""
    if not require_role("Patient"):
        return

    my_appointments = AppointmentService.get_patient_appointments(all_appointments, patient_email)

    st.title("📋 My Appointments")
    st.caption(f"Logged in as {patient_email}")
    st.divider()

    col1, col2 = st.columns([4, 2])
    with col1:
        if my_appointments:
            UIHelpers.render_styled_table(my_appointments)
        else:
            st.info("🗓️ You have no appointments yet. Use **Book Appointment** in the sidebar to get started.")
    with col2:
        st.metric("Total",     len(my_appointments))
        st.metric("Scheduled", sum(1 for a in my_appointments if a.get("status") == "Scheduled"))
        st.metric("Completed", sum(1 for a in my_appointments if a.get("status") == "Completed"))
        st.metric("Cancelled", sum(1 for a in my_appointments if a.get("status") == "Cancelled"))

    if my_appointments:
        st.divider()
        st.markdown('<div class="section-header">📝 Appointment Details</div>', unsafe_allow_html=True)
        UIHelpers.appt_selectbox("Choose an appointment to inspect:", my_appointments,
                       key="patient_appt_selector", state_key="patient_selected_appt_id")
        appt = AppointmentService.get_appointment_by_id(all_appointments, st.session_state.get("patient_selected_appt_id"))
        if appt:
            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Doctor:** {appt.get('doctor_name', 'N/A')}")
                    st.markdown(f"**Date:** {format_appointment_date(appt.get('appointment_date', 'N/A'))}  at  {appt.get('appointment_time', '')}")
                    st.markdown(f"**Type:** {appt.get('appointment_type', 'N/A')}")
                with col_b:
                    st.markdown(f"**Status:** {get_status_badge_html(appt.get('status', 'N/A'))}", unsafe_allow_html=True)
                    st.markdown(f"**Booked At:** {appt.get('submitted_timestamp', 'N/A')}")
                    note = appt.get("doctor_note", "").strip()
                    st.markdown(f"**Doctor Note:** {note if note else '(none)'}")
                st.markdown("**Symptom Summary:**")
                st.info(appt.get("symptom_summary", "No symptom notes provided."))


# ── Patient book page ──────────────────────────────────────────────────────────
def render_patient_book(all_appointments, doctors, patient_name, patient_email):
    """Render patient booking page."""
    if not require_role("Patient"):
        return

    st.title("📅 Book Appointment")
    st.caption(f"Logged in as {patient_email}")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["Book New Appointment", "Reschedule", "Cancel an Appointment"])
    with tab1:
        _render_book_tab(all_appointments, doctors, patient_name, patient_email)
    with tab2:
        _render_reschedule_tab(all_appointments, doctors, patient_email)
    with tab3:
        _render_cancel_tab(all_appointments, doctors, patient_email)


def _render_book_tab(all_appointments, doctors, patient_name, patient_email):
    """Render booking tab."""
    col1, col2 = st.columns([3, 3])

    with col1:
        st.subheader("📋 Appointment Details")

        if doctors:
            doc_id_to_label = {d.get("doctor_id", ""): f"{d.get('name', 'Unknown')} — {d.get('specialty', 'General')}"
                              for d in doctors}
            selected_doc_id = st.selectbox(
                "Select Doctor *",
                options=list(doc_id_to_label.keys()),
                format_func=lambda did: doc_id_to_label.get(did, "Unknown"),
                key="form_doctor_id_selector",
            )
            form_doctor = AppointmentService.get_doctor_by_id(doctors, selected_doc_id)
        else:
            st.warning("No doctors are registered yet.")
            form_doctor = None

        appt_type = st.selectbox(
            "Appointment Type *",
            options=["— Select appointment type —"] + APPOINTMENT_TYPES,
            key="form_appointment_type",
            help="Choose the type of eye care service you need.",
        )
        symptoms = st.text_area(
            "Describe your symptoms *",
            placeholder="e.g. Blurry vision on left side, seeing floaters...",
            height=120, key="form_symptom_summary",
            help="Provide at least 10 characters describing your symptoms or reason for visit.",
        )

        available_slots = list(form_doctor.get("available_slots", [])) if form_doctor else []
        if available_slots:
            slot = st.selectbox(
                "Available Time Slot *", options=available_slots, key="form_slot_selector",
                format_func=lambda x: x.replace("T", "  "),
            )
        else:
            if form_doctor:
                st.info("⏰ No available slots for this doctor. Please ask your doctor to add time slots or check back later.")
            slot = None

        st.divider()
        st.caption("Fields marked * are required. Status defaults to **Scheduled**.")
        clicked = st.button("📅  Book Appointment", key="form_book_btn", type="primary", use_container_width=True)

        if clicked:
            errors = Validators.validate_booking(form_doctor, appt_type, symptoms, slot)
            if errors:
                UIHelpers.show_validation_errors(errors)
            else:
                with st.spinner("Booking your appointment..."):
                    fresh_appts = DataStore.reload_json(PATH_APPOINTMENTS, [])
                    fresh_docs = DataStore.reload_json(PATH_DOCTORS, [])

                    new_appt = AppointmentService.build_appointment(patient_name, patient_email,
                                                 form_doctor, slot, appt_type, symptoms.strip())
                    fresh_appts.append(new_appt)
                    AppointmentService.remove_slot_from_doctor(fresh_docs, form_doctor.get("doctor_id", ""), slot)
                    success, msg = DataStore.transactional_save(
                        (PATH_APPOINTMENTS, fresh_appts), (PATH_DOCTORS, fresh_docs)
                    )
                    if success:
                        st.balloons()
                        navigate_to("patient_dashboard")
                    else:
                        st.error(f"⚠️  Booking failed: {msg}")

    with col2:
        _render_ai_assistant(all_appointments, doctors, patient_email)


def _render_ai_assistant(all_appointments, doctors, patient_email):
    """Render AI assistant chat."""
    st.subheader("🤖 AI Assistant")
    hdr_col, btn_col = st.columns([3, 1])
    with hdr_col:
        st.caption("Try asking: What slots are available?")
    with btn_col:
        if st.button("Clear", key="clear_messages_btn"):
            st.session_state["messages"] = [
                {"role": "assistant", "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?"}
            ]
            st.rerun()

    with st.container(border=True, height=250):
        for msg in st.session_state.get("messages", []):
            with st.chat_message(msg.get("role", "user")):
                st.write(msg.get("content", ""))

    user_input = st.chat_input("Ask a question...")
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        response = get_ai_response(user_input, all_appointments, doctors, patient_email)
        st.session_state["messages"].append({"role": "assistant", "content": response})
        st.rerun()


def _render_reschedule_tab(all_appointments, doctors, patient_email):
    """Render reschedule tab."""
    st.markdown("### 🔄 Reschedule an Appointment")
    scheduled = AppointmentService.get_scheduled_appointments(all_appointments, patient_email)

    if not scheduled:
        st.info("You have no scheduled appointments to reschedule.")
        return

    rs_options = {
        f"{a.get('doctor_name', 'Unknown')} — {format_appointment_date(a.get('appointment_date', ''))} "
        f"{a.get('appointment_time', '')} ({a.get('appointment_type', 'N/A')})": a.get("appointment_id", "")
        for a in scheduled
    }
    rs_label = st.selectbox("Select appointment to reschedule", options=list(rs_options.keys()), key="reschedule_appt_selector")
    rs_appt  = AppointmentService.get_appointment_by_id(all_appointments, rs_options[rs_label])
    rs_doc   = AppointmentService.get_doctor_by_id(doctors, rs_appt.get("doctor_id", "")) if rs_appt else None
    new_slots = list(rs_doc.get("available_slots", [])) if rs_doc else []

    if not new_slots:
        st.warning("No alternative slots available for this doctor. Please ask them to add more slots.")
        return

    new_slot = st.selectbox("Select New Time Slot", options=new_slots, key="reschedule_slot_selector",
                            format_func=lambda x: x.replace("T", "  "))

    if st.button("Confirm Reschedule", key="reschedule_btn", type="primary", use_container_width=True):
        with st.spinner("Rescheduling..."):
            fresh_appts = DataStore.reload_json(PATH_APPOINTMENTS, [])
            fresh_docs = DataStore.reload_json(PATH_DOCTORS, [])

            fresh_rs_appt = AppointmentService.get_appointment_by_id(fresh_appts, rs_appt.get("appointment_id", ""))
            fresh_rs_doc = AppointmentService.get_doctor_by_id(fresh_docs, rs_appt.get("doctor_id", ""))

            old_slot = fresh_rs_appt.get("appointment_date", "") + "T" + fresh_rs_appt.get("appointment_time", "")
            slot_date, slot_time = new_slot.split("T")
            AppointmentService.reschedule_appointment(fresh_appts, fresh_rs_appt.get("appointment_id", ""), slot_date, slot_time)
            if fresh_rs_doc:
                AppointmentService.remove_slot_from_doctor(fresh_docs, fresh_rs_doc.get("doctor_id", ""), new_slot)
                AppointmentService.add_slot_to_doctor(fresh_docs, fresh_rs_doc.get("doctor_id", ""), old_slot)
            success, msg = DataStore.transactional_save(
                (PATH_APPOINTMENTS, fresh_appts), (PATH_DOCTORS, fresh_docs)
            )
            if success:
                st.success(f"Appointment rescheduled to {format_appointment_date(slot_date)} at {slot_time}.")
                st.rerun()
            else:
                st.error(f"⚠️  Reschedule failed: {msg}")


def _render_cancel_tab(all_appointments, doctors, patient_email):
    """Render cancel tab."""
    st.markdown("### ❌ Cancel an Appointment")
    scheduled = AppointmentService.get_scheduled_appointments(all_appointments, patient_email)

    if not scheduled:
        st.info("You have no scheduled appointments to cancel.")
        return

    UIHelpers.render_styled_table(scheduled)
    cl_options = {
        f"{a.get('doctor_name', 'Unknown')} — {format_appointment_date(a.get('appointment_date', ''))} "
        f"{a.get('appointment_time', '')} ({a.get('appointment_type', 'N/A')})": a.get("appointment_id", "")
        for a in scheduled
    }
    cl_label = st.selectbox("Select appointment to cancel", options=list(cl_options.keys()), key="cancel_appt_selector")

    if st.button("Cancel Appointment", key="cancel_btn", type="primary", use_container_width=True):
        with st.spinner("Cancelling appointment..."):
            fresh_appts = DataStore.reload_json(PATH_APPOINTMENTS, [])
            fresh_docs = DataStore.reload_json(PATH_DOCTORS, [])

            appt_id = cl_options[cl_label]
            appt = AppointmentService.get_appointment_by_id(fresh_appts, appt_id)
            if appt:
                old_slot = appt.get("appointment_date", "") + "T" + appt.get("appointment_time", "")
                AppointmentService.add_slot_to_doctor(fresh_docs, appt.get("doctor_id", ""), old_slot)
            AppointmentService.cancel_appointment(fresh_appts, appt_id)
            success, msg = DataStore.transactional_save(
                (PATH_APPOINTMENTS, fresh_appts), (PATH_DOCTORS, fresh_docs)
            )
            if success:
                st.success("Appointment cancelled successfully. The time slot has been freed.")
                st.rerun()
            else:
                st.error(f"⚠️  Could not save cancellation: {msg}")


# ── Doctor dashboard ───────────────────────────────────────────────────────────
def render_doctor_dashboard(all_appointments, doctor_id, doctor_name):
    """Render doctor dashboard."""
    if not require_role("Doctor"):
        return

    my_schedule = AppointmentService.get_doctor_appointments(all_appointments, doctor_id)

    st.title("📊 Appointment Dashboard")
    st.caption(f"Patient roster for {doctor_name}")
    st.divider()

    col1, col2 = st.columns([4, 2])
    with col1:
        if my_schedule:
            UIHelpers.render_styled_table(my_schedule)
        else:
            st.info("No appointments assigned to you yet.")
    with col2:
        st.metric("My Appointments", len(my_schedule))
        st.metric("Scheduled", sum(1 for a in my_schedule if a.get("status") == "Scheduled"))
        st.metric("Completed", sum(1 for a in my_schedule if a.get("status") == "Completed"))
        st.metric("No-Show",   sum(1 for a in my_schedule if a.get("status") == "No-Show"))

    if my_schedule:
        st.divider()
        st.markdown('<div class="section-header">✏️ Update Appointment Status</div>', unsafe_allow_html=True)
        UIHelpers.appt_selectbox("Choose an appointment to update:", my_schedule,
                       key="doctor_appt_selector", state_key="doctor_selected_appt_id")
        appt = AppointmentService.get_appointment_by_id(all_appointments, st.session_state.get("doctor_selected_appt_id"))
        if appt:
            _render_appt_update_form(all_appointments, appt)


def _render_appt_update_form(all_appointments, appt):
    """Render appointment update form."""
    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Patient:** {appt.get('patient_name', 'N/A')}")
            st.markdown(f"**Email:** {appt.get('patient_email', 'N/A')}")
            st.markdown(f"**Date & Time:** {format_appointment_date(appt.get('appointment_date', 'N/A'))}  {appt.get('appointment_time', '')}")
        with col_b:
            st.markdown(f"**Type:** {appt.get('appointment_type', 'N/A')}")
            st.markdown(f"**Status:** {get_status_badge_html(appt.get('status', 'N/A'))}", unsafe_allow_html=True)
            st.markdown(f"**Booked At:** {appt.get('submitted_timestamp', 'N/A')}")
        st.markdown("**Symptom Summary:**")
        st.info(appt.get("symptom_summary", "No symptom notes provided."))
        st.divider()

        current_status = appt.get("status", "Scheduled")
        col_s1, col_s2 = st.columns([2, 3])
        with col_s1:
            new_status = st.selectbox(
                "Update Status", options=APPT_STATUSES,
                index=APPT_STATUSES.index(current_status) if current_status in APPT_STATUSES else 0,
                key=f"doctor_status_{appt.get('appointment_id', '')}",
            )
            new_note = st.text_input("Doctor Note", value=appt.get("doctor_note", ""),
                                     key=f"doctor_note_{appt.get('appointment_id', '')}")
        with col_s2:
            st.write("")
            st.write("")
            if st.button("Save Changes", key=f"doctor_save_btn_{appt.get('appointment_id', '')}", type="primary", use_container_width=True):
                with st.spinner("Saving..."):
                    fresh_appts = DataStore.reload_json(PATH_APPOINTMENTS, [])
                    fresh_appt = AppointmentService.get_appointment_by_id(fresh_appts, appt.get("appointment_id", ""))
                    if fresh_appt:
                        AppointmentService.update_appointment_status(fresh_appts, appt.get("appointment_id", ""), new_status, new_note)
                        if DataStore.save_json(PATH_APPOINTMENTS, fresh_appts):
                            st.success("Appointment updated successfully.")
                            st.rerun()
                        else:
                            st.error("⚠️  Could not save changes. Please try again.")


# ── Doctor slots page ──────────────────────────────────────────────────────────
def render_doctor_slots(doctors, doctor_id, doctor_name):
    """Render doctor time slots management page."""
    if not require_role("Doctor"):
        return

    current_doctor = AppointmentService.get_doctor_by_id(doctors, doctor_id)

    st.title("⏰ Manage Time Slots")
    st.caption(f"Managing slots for {doctor_name}")
    st.divider()

    tab1, tab2 = st.tabs(["Add New Slot", "Remove a Slot"])

    with tab1:
        col1, col2 = st.columns([3, 3])
        with col1:
            st.subheader("➕ Add Time Slot")
            slot_date = st.date_input("Date", key="slot_date_input")
            slot_hour = st.selectbox("Hour", options=[f"{h:02d}:00" for h in range(8, 18)], key="slot_hour_input")
            if st.button("Add Slot", key="add_slot_btn", type="primary", use_container_width=True):
                new_slot = f"{slot_date}T{slot_hour}"
                if current_doctor and new_slot in current_doctor.get("available_slots", []):
                    st.warning("This slot already exists.")
                else:
                    fresh_docs = DataStore.reload_json(PATH_DOCTORS, [])
                    AppointmentService.add_slot_to_doctor(fresh_docs, doctor_id, new_slot)
                    if DataStore.save_json(PATH_DOCTORS, fresh_docs):
                        st.success(f"Slot added: {format_appointment_date(str(slot_date))} at {slot_hour}")
                        st.rerun()
                    else:
                        st.error("⚠️  Could not save the new slot. Please try again.")
        with col2:
            st.subheader("📅 Your Current Slots")
            slots = list(current_doctor.get("available_slots", [])) if current_doctor else []
            if slots:
                for s in slots:
                    parts = s.split("T")
                    slot_date_str = format_appointment_date(parts[0]) if len(parts) > 0 else "N/A"
                    slot_time_str = parts[1] if len(parts) > 1 else "N/A"
                    st.markdown(f"""
                    <div class="slot-card">
                        <div class="slot-card-date">{slot_date_str}</div>
                        <div class="slot-card-time">⏰ {slot_time_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("You have no available slots at the moment.")

    with tab2:
        col1, col2 = st.columns([3, 3])
        with col1:
            st.subheader("➖ Remove Time Slot")
            slots = list(current_doctor.get("available_slots", [])) if current_doctor else []
            if slots:
                slot_to_remove = st.selectbox(
                    "Select Slot to Remove", options=slots, key="remove_slot_selector",
                    format_func=lambda x: x.replace("T", "  "),
                )
                if st.button("Remove Slot", key="remove_slot_btn", type="primary", use_container_width=True):
                    with st.spinner("Removing slot..."):
                        fresh_docs = DataStore.reload_json(PATH_DOCTORS, [])
                        AppointmentService.remove_slot_from_doctor(fresh_docs, doctor_id, slot_to_remove)
                        if DataStore.save_json(PATH_DOCTORS, fresh_docs):
                            parts = slot_to_remove.split("T")
                            slot_date_str = format_appointment_date(parts[0]) if len(parts) > 0 else "N/A"
                            slot_time_str = parts[1] if len(parts) > 1 else "N/A"
                            st.success(f"Slot removed: {slot_date_str} at {slot_time_str}")
                            st.rerun()
                        else:
                            st.error("⚠️  Could not save slot removal. Please try again.")
            else:
                st.info("No slots available to remove.")

# ─── INIT ──────────────────────────────────────────────────────────────────────
_SESSION_DEFAULTS = {
    "logged_in":               False,
    "role":                    None,
    "current_user_name":       None,
    "current_user_email":      None,
    "current_doctor_id":       None,
    "page":                    "login",
    "patient_selected_appt_id": None,
    "doctor_selected_appt_id":  None,
    "messages":                [{"role": "assistant", "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?"}],
    "_flash_message":          None,
    "_flash_type":             None,
}
for _key, _val in _SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

# Inject custom CSS
inject_custom_css()

all_patients     = DataStore.load_json(PATH_PATIENTS, [])
doctors          = DataStore.load_json(PATH_DOCTORS, [])
all_appointments = DataStore.load_json(PATH_APPOINTMENTS, [])

# ─── MAIN ──────────────────────────────────────────────────────────────────────
if st.session_state.get("logged_in"):
    render_sidebar()

page = st.session_state.get("page", "login")
if page == "login":
    render_login_page(all_patients, doctors)
elif page == "patient_dashboard":
    render_patient_dashboard(all_appointments, st.session_state.get("current_user_email", ""),
                           st.session_state.get("current_user_name", ""))
elif page == "patient_book":
    render_patient_book(all_appointments, doctors, st.session_state.get("current_user_name", ""),
                       st.session_state.get("current_user_email", ""))
elif page == "doctor_dashboard":
    render_doctor_dashboard(all_appointments, st.session_state.get("current_doctor_id", ""),
                          st.session_state.get("current_user_name", ""))
elif page == "doctor_slots":
    render_doctor_slots(doctors, st.session_state.get("current_doctor_id", ""),
                       st.session_state.get("current_user_name", ""))

# Render footer
render_clinic_footer()
