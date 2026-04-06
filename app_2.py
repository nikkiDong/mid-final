import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

st.set_page_config("ClearVision Clinic", layout="wide", initial_sidebar_state="expanded")

# ── Constants ─────────────────────────────────────────────────────────────────
CLINIC_ID = "ClearVision-01"
APPOINTMENT_TYPES = ["Routine Vision Check", "Glaucoma Screening", "Fundus Exam",
                     "Cataract Evaluation", "Retinal Exam"]
APPT_STATUSES = ["Scheduled", "Completed", "No-Show", "Cancelled"]
PATH_PATIENTS     = Path("patients.json")
PATH_DOCTORS      = Path("doctors.json")
PATH_APPOINTMENTS = Path("appointments.json")

_SESSION_DEFAULTS = {
    "logged_in": False, "role": None,
    "current_user_name": None, "current_user_email": None, "current_doctor_id": None,
    "page": "login", "selected_appointment_id": None, "_reg_success": None,
    "messages": [{"role": "assistant",
                  "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?"}],
}
for _k, _v in _SESSION_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.section-header { font-size:1.4rem; font-weight:600; color:#1f77b4; border-bottom:3px solid #1f77b4; padding-bottom:.5rem; margin-bottom:1.5rem; }
.status-scheduled { background:#d4edda; color:#155724; padding:.25rem .55rem; border-radius:.25rem; font-weight:600; font-size:.82rem; }
.status-completed  { background:#cfe2ff; color:#084298; padding:.25rem .55rem; border-radius:.25rem; font-weight:600; font-size:.82rem; }
.status-cancelled  { background:#f8d7da; color:#842029; padding:.25rem .55rem; border-radius:.25rem; font-weight:600; font-size:.82rem; }
.status-no-show    { background:#fff3cd; color:#664d03; padding:.25rem .55rem; border-radius:.25rem; font-weight:600; font-size:.82rem; }
.slot-card { background:#f8f9fa; border:1px solid #dee2e6; border-radius:.5rem; padding:1rem; margin-bottom:.75rem; box-shadow:0 1px 2px rgba(0,0,0,.05); }
.slot-card-date { font-weight:600; color:#1f77b4; } .slot-card-time { color:#495057; font-size:.95rem; }
.appt-card { background:#fff; border:1px solid #dee2e6; border-radius:.5rem; padding:1rem 1.25rem; margin-bottom:.6rem; box-shadow:0 1px 3px rgba(0,0,0,.06); }
.appt-card-type { font-size:1rem; font-weight:600; color:#212529; }
.appt-card-meta { color:#6c757d; font-size:.85rem; margin-top:.3rem; }
.banner-success { background:#d1e7dd; color:#0a3622; border:1px solid #a3cfbb; border-radius:.4rem; padding:.75rem 1rem; margin-bottom:1rem; font-weight:500; }
.clinic-footer { text-align:center; padding:2rem 0 1rem; border-top:1px solid #e0e0e0; color:#6c757d; font-size:.9rem; }
.stContainer > div { padding-top:.25rem; } div[data-testid="stMetric"] { padding:.5rem 0; }
.stTabs [data-baseweb="tab-panel"] { padding-top:1rem; }
</style>""", unsafe_allow_html=True)

# ── Persistence ───────────────────────────────────────────────────────────────
def load_json(path, default):
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, (list, dict)):
                return data
            st.warning(f"Invalid format in {path.name}, using default.")
        except (OSError, json.JSONDecodeError) as e:
            st.warning(f"Could not load {path.name}: {e}")
    else:
        try:
            path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        except OSError as e:
            st.error(f"Failed to initialise {path.name}: {e}")
    return default

def save_json(path, data) -> bool:
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(path)
        return True
    except OSError as e:
        st.error(f"Failed to save {path.name}: {e}")
        tmp.unlink(missing_ok=True)
        return False

def transactional_save(*pairs) -> tuple[bool, str]:
    """Atomically write multiple (path, data) pairs; roll back all on failure."""
    backups = []
    try:
        for path, _ in pairs:
            backups.append((path, json.loads(path.read_text()) if path.exists() else None))
        tmps = []
        for path, data in pairs:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmps.append((tmp, path))
        for tmp, target in tmps:
            tmp.replace(target)
        return True, "Saved."
    except OSError as e:
        for path, original in backups:
            if original is not None:
                try:
                    path.write_text(json.dumps(original, indent=2), encoding="utf-8")
                except OSError:
                    pass
        for path, _ in pairs:
            path.with_suffix(".tmp").unlink(missing_ok=True)
        return False, f"Save failed: {e}. All changes rolled back."

# ── Utils ─────────────────────────────────────────────────────────────────────
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def norm_email(email: str) -> str:
    return email.strip().lower()

def fmt_date(s: str) -> str:
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%b %d, %Y")
    except Exception:
        return s

_STATUS_CSS = {"Scheduled": "status-scheduled", "Completed": "status-completed",
               "Cancelled": "status-cancelled",  "No-Show":   "status-no-show"}

def status_badge(status: str) -> str:
    return f'<span class="{_STATUS_CSS.get(status, "status-scheduled")}">{status}</span>'

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(norm_email(email)))

# ── Data access ───────────────────────────────────────────────────────────────
def doctor_by_id(doctors, did):
    return next((d for d in doctors if d.get("doctor_id") == did), None)

def appt_by_id(appointments, aid):
    return next((a for a in appointments if a.get("appointment_id") == aid), None)

def patient_appts(appointments, email):
    e = norm_email(email)
    return [a for a in appointments if norm_email(a.get("patient_email", "")) == e]

def doctor_appts(appointments, did):
    return [a for a in appointments if a.get("doctor_id") == did]

def scheduled_appts(appointments, email):
    return [a for a in patient_appts(appointments, email) if a.get("status") == "Scheduled"]

# ── Business logic ────────────────────────────────────────────────────────────
def new_appointment(patient_name, patient_email, doctor, slot, appt_type, symptoms) -> dict:
    date, time = slot.split("T")
    return {"appointment_id": f"appt-{str(uuid.uuid4())[:8]}", "clinic_id": CLINIC_ID,
            "patient_name": patient_name, "patient_email": norm_email(patient_email),
            "doctor_id": doctor.get("doctor_id", ""), "doctor_name": doctor.get("name", ""),
            "appointment_date": date, "appointment_time": time,
            "submitted_timestamp": datetime.now().isoformat(),
            "appointment_type": appt_type, "symptom_summary": symptoms,
            "status": "Scheduled", "doctor_note": ""}

def remove_slot(doctors, did, slot):
    doc = doctor_by_id(doctors, did)
    if doc and slot in doc.get("available_slots", []):
        doc["available_slots"].remove(slot)

def add_slot(doctors, did, slot):
    doc = doctor_by_id(doctors, did)
    if doc and slot not in doc.get("available_slots", []):
        doc["available_slots"].append(slot)

def reschedule(appointments, aid, date, time):
    if a := appt_by_id(appointments, aid):
        a["appointment_date"], a["appointment_time"] = date, time

def cancel(appointments, aid):
    if a := appt_by_id(appointments, aid):
        a["status"] = "Cancelled"

def update_status(appointments, aid, status, note):
    if a := appt_by_id(appointments, aid):
        a["status"], a["doctor_note"] = status, note

def new_patient(name, email, pw) -> dict:
    return {"patient_id": f"pat_{str(uuid.uuid4())[:8]}", "name": name.strip(),
            "email": norm_email(email), "password": hash_pw(pw)}

def new_doctor(name, email, specialty, pw) -> dict:
    return {"doctor_id": f"doc_{str(uuid.uuid4())[:8]}", "name": name.strip(),
            "email": norm_email(email), "specialty": specialty.strip(),
            "password": hash_pw(pw), "available_slots": []}

# ── Validation ────────────────────────────────────────────────────────────────
def validate_auth(name, email, password, confirm, existing, key="email") -> list[str]:
    errors = []
    email = norm_email(email)
    if not name.strip():
        errors.append("Full Name is required.")
    if not valid_email(email):
        errors.append("Please enter a valid email address.")
    elif any(norm_email(r.get(key, "")) == email for r in existing):
        errors.append("An account with this email already exists.")
    if not password.strip():
        errors.append("Password is required.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    if password != confirm:
        errors.append("Passwords do not match.")
    return errors

def validate_booking(doctor, appt_type, symptoms, slot) -> list[str]:
    errors = []
    if not doctor:
        errors.append("Please select a doctor.")
    if appt_type == "— Select appointment type —":
        errors.append("Appointment Type is required.")
    if not symptoms.strip():
        errors.append("Please describe your symptoms.")
    elif len(symptoms.strip()) < 10:
        errors.append("Symptom description is too short (min 10 characters).")
    if not slot:
        errors.append("No available time slots — please ask your doctor to add some.")
    return errors

# ── Shared UI helpers ─────────────────────────────────────────────────────────
def show_errors(errors: list[str]):
    if errors:
        st.error("Please fix the following:\n" + "\n".join(f"• {e}" for e in errors))

def show_success(msg: str):
    """Uniform success banner across all pages."""
    st.markdown(f'<div class="banner-success">✅ {msg}</div>', unsafe_allow_html=True)

def appt_cards(appointments):
    """Polished card-based appointment list — replaces raw dataframe."""
    if not appointments:
        return
    for a in appointments:
        booked = a.get("submitted_timestamp", "")[:10] if a.get("submitted_timestamp") else "—"
        st.markdown(f"""
        <div class="appt-card">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="appt-card-type">{a.get('appointment_type','N/A')}</span>
            {status_badge(a.get('status','Scheduled'))}
          </div>
          <div class="appt-card-meta">
            📅 {fmt_date(a.get('appointment_date',''))} &nbsp;·&nbsp;
            ⏰ {a.get('appointment_time','')} &nbsp;·&nbsp;
            🩺 Dr. {a.get('doctor_name','N/A')} &nbsp;·&nbsp;
            👤 {a.get('patient_name','N/A')}
          </div>
          <div style="color:#adb5bd;font-size:.78rem;margin-top:.2rem;">
            ID: {a.get('appointment_id','')} &nbsp;·&nbsp; Booked: {booked}
          </div>
        </div>""", unsafe_allow_html=True)

def appt_selectbox(label, appointments, key):
    """Stable selectbox keyed by appointment_id, immune to list reordering."""
    lbl_to_id = {
        f"{fmt_date(a.get('appointment_date','?'))}  {a.get('appointment_time','')}  |  "
        f"{a.get('appointment_type','?')}  |  {a.get('status','?')}": a.get("appointment_id", "")
        for a in appointments
    }
    cur_id  = st.session_state.get("selected_appointment_id")
    cur_lbl = next((l for l, i in lbl_to_id.items() if i == cur_id), None)
    options = ["— Select an appointment —"] + list(lbl_to_id)
    chosen  = st.selectbox(label, options, index=options.index(cur_lbl) if cur_lbl in options else 0, key=key)
    st.session_state["selected_appointment_id"] = None if chosen == options[0] else lbl_to_id[chosen]

# ── AI assistant ──────────────────────────────────────────────────────────────
def ai_response(q: str, appointments, doctors, email: str) -> str:
    q = q.lower()
    if "next appointment" in q:
        sc = scheduled_appts(appointments, email)
        if sc:
            n = min(sc, key=lambda x: x.get("appointment_date", ""))
            return (f"Your next appointment is {fmt_date(n['appointment_date'])} at "
                    f"{n['appointment_time']} with Dr. {n['doctor_name']} ({n['appointment_type']}).")
        return "You have no upcoming appointments. Use the form to book one."
    if "available" in q or "slot" in q:
        slots = [f"Dr. {d['name']}: {s.replace('T',' at ')}" for d in doctors for s in d.get("available_slots", [])]
        return ("Available slots:\n" + "\n".join(slots)) if slots else "No available time slots right now."
    if "cancel" in q:
        return "To cancel: go to Book Appointment → Cancel tab → select your appointment and click Cancel."
    if "doctor" in q:
        avail = [f"Dr. {d['name']} ({d.get('specialty','General')})" for d in doctors if d.get("available_slots")]
        return ("Doctors with open slots:\n" + "\n".join(avail)) if avail else "No doctors have open slots right now."
    if "prepare" in q or "exam" in q:
        return ("Exam tips:\n- Bring insurance card & photo ID\n"
                "- Avoid contacts 24 h before retinal/fundus exam\n"
                "- Arrange a ride if dilation drops are used\n"
                "- Bring your medication list")
    return "I can help with: slots, next appointment, cancellations, doctor availability, exam prep."

# ── Session helpers ───────────────────────────────────────────────────────────
def reset_session():
    """Full reset — only called on explicit logout."""
    st.session_state.update(_SESSION_DEFAULTS)

def nav(page: str):
    """Navigate to a page and clear transient selection state."""
    st.session_state["page"] = page
    st.session_state["selected_appointment_id"] = None
    st.rerun()

def require_role(role: str) -> bool:
    """Return True if current user has the required role; otherwise redirect to login."""
    if st.session_state.get("logged_in") and st.session_state.get("role") == role:
        return True
    nav("login")
    return False

# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    role = st.session_state.get("role", "")
    with st.sidebar:
        st.markdown("## 👁️ ClearVision Clinic")
        st.divider()
        st.markdown(f"{'🩺' if role == 'Doctor' else '👤'} **{st.session_state.get('current_user_name','User')}**")
        st.caption(f"Role: {role or 'Unknown'}")
        st.divider()
        # Page-prefixed keys prevent any cross-role key collisions
        if role == "Patient":
            if st.button("My Appointments",  key="pat_nav_dashboard", type="primary", use_container_width=True): nav("patient_dashboard")
            if st.button("Book Appointment", key="pat_nav_book",      type="primary", use_container_width=True): nav("patient_book")
        elif role == "Doctor":
            if st.button("Appointment Dashboard", key="doc_nav_dashboard", type="primary", use_container_width=True): nav("doctor_dashboard")
            if st.button("Manage Time Slots",     key="doc_nav_slots",     type="primary", use_container_width=True): nav("doctor_slots")
        st.divider()
        if st.button("Log Out", key="sidebar_logout", use_container_width=True):
            reset_session()
            nav("login")

# ── Login page ────────────────────────────────────────────────────────────────
def render_login(all_patients, doctors):
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<h1 style='text-align:center;'>👁️ ClearVision Clinic</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#666;'><em>Ophthalmology Appointment Portal</em></p>",
                    unsafe_allow_html=True)
        st.divider()
        if msg := st.session_state.pop("_reg_success", None):
            show_success(msg)

        tab_p, tab_d = st.tabs(["Patient", "Doctor"])

        # ── Patient tab ──
        with tab_p:
            mode = st.radio("", ["Login", "Register"], key="patient_mode", horizontal=True)
            st.divider()
            if mode == "Login":
                st.subheader("Patient Login")
                with st.form("pat_login_form"):
                    email = st.text_input("Email", placeholder="yourname@email.com")
                    pw    = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Log In as Patient", type="primary", use_container_width=True)
                if submitted:
                    if not valid_email(email):
                        st.error("⚠️ Please enter a valid email address.")
                    elif not pw.strip():
                        st.error("⚠️ Password is required.")
                    else:
                        matched = next((p for p in all_patients
                                        if norm_email(p.get("email", "")) == norm_email(email)
                                        and p.get("password") == hash_pw(pw)), None)
                        if matched:
                            st.session_state.update({"logged_in": True, "role": "Patient",
                                                      "current_user_name":  matched["name"],
                                                      "current_user_email": matched["email"]})
                            nav("patient_dashboard")
                        else:
                            st.error("⚠️ Incorrect email or password.")
            else:
                st.subheader("Create Patient Account")
                with st.form("pat_register_form"):
                    name    = st.text_input("Full Name *",        placeholder="James Lee")
                    email   = st.text_input("Email *",            placeholder="yourname@email.com")
                    pw      = st.text_input("Password *",         type="password", help="At least 6 characters.")
                    confirm = st.text_input("Confirm Password *", type="password")
                    submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
                if submitted:
                    errors = validate_auth(name, email, pw, confirm, all_patients)
                    if errors:
                        show_errors(errors)
                    else:
                        all_patients.append(new_patient(name, email, pw))
                        if save_json(PATH_PATIENTS, all_patients):
                            st.session_state["_reg_success"] = "Account created! Please log in."
                            st.session_state["patient_mode"] = "Login"
                            nav("login")
                        else:
                            all_patients.pop()
                            st.error("⚠️ Could not save account. Please try again.")

        # ── Doctor tab ──
        with tab_d:
            mode = st.radio("", ["Login", "Register"], key="doctor_mode", horizontal=True)
            st.divider()
            if mode == "Login":
                st.subheader("Doctor Login")
                with st.form("doc_login_form"):
                    email = st.text_input("Email", placeholder="doctor@clearvision.com")
                    pw    = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Log In as Doctor", type="primary", use_container_width=True)
                if submitted:
                    if not valid_email(email):
                        st.error("⚠️ Please enter a valid email address.")
                    elif not pw.strip():
                        st.error("⚠️ Password is required.")
                    else:
                        matched = next((d for d in doctors
                                        if norm_email(d.get("email", "")) == norm_email(email)
                                        and d.get("password") == hash_pw(pw)), None)
                        if matched:
                            st.session_state.update({"logged_in": True, "role": "Doctor",
                                                      "current_user_name": matched["name"],
                                                      "current_doctor_id": matched["doctor_id"]})
                            nav("doctor_dashboard")
                        else:
                            st.error("⚠️ Incorrect email or password.")
            else:
                st.subheader("Create Doctor Account")
                with st.form("doc_register_form"):
                    name      = st.text_input("Full Name *",        placeholder="Dr. Jane Smith")
                    email     = st.text_input("Email *",            placeholder="doctor@clearvision.com")
                    specialty = st.text_input("Specialty *",        placeholder="e.g. Retinal Disease")
                    pw        = st.text_input("Password *",         type="password", help="At least 6 characters.")
                    confirm   = st.text_input("Confirm Password *", type="password")
                    submitted = st.form_submit_button("Create Doctor Account", type="primary", use_container_width=True)
                if submitted:
                    errors = validate_auth(name, email, pw, confirm, doctors)
                    if not specialty.strip():
                        errors.insert(2, "Specialty is required.")
                    if errors:
                        show_errors(errors)
                    else:
                        doctors.append(new_doctor(name, email, specialty, pw))
                        if save_json(PATH_DOCTORS, doctors):
                            st.session_state["_reg_success"] = "Doctor account created! Please log in."
                            st.session_state["doctor_mode"] = "Login"
                            nav("login")
                        else:
                            doctors.pop()
                            st.error("⚠️ Could not save account. Please try again.")

# ── Patient dashboard ─────────────────────────────────────────────────────────
def render_patient_dashboard(all_appointments, patient_email, patient_name):
    if not require_role("Patient"):
        return

    # Consume one-shot flash messages set before navigation
    if flash := st.session_state.pop("_flash_success", None):
        show_success(flash)

    appts = patient_appts(all_appointments, patient_email)
    st.title("📋 My Appointments")
    st.caption(f"Logged in as {patient_email}")
    st.divider()

    col1, col2 = st.columns([4, 2])
    with col1:
        appt_cards(appts) if appts else st.info("🗓️ No appointments yet. Use **Book Appointment** to get started.")
    with col2:
        st.metric("Total",     len(appts))
        st.metric("Scheduled", sum(1 for a in appts if a.get("status") == "Scheduled"))
        st.metric("Completed", sum(1 for a in appts if a.get("status") == "Completed"))
        st.metric("Cancelled", sum(1 for a in appts if a.get("status") == "Cancelled"))

    if appts:
        st.divider()
        st.markdown('<div class="section-header">📝 Appointment Details</div>', unsafe_allow_html=True)
        appt_selectbox("Select an appointment:", appts, key="pd_appt_selector")
        if appt := appt_by_id(all_appointments, st.session_state.get("selected_appointment_id")):
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Doctor:** Dr. {appt.get('doctor_name','N/A')}")
                    st.markdown(f"**Date:** {fmt_date(appt.get('appointment_date','N/A'))}  at  {appt.get('appointment_time','')}")
                    st.markdown(f"**Type:** {appt.get('appointment_type','N/A')}")
                with c2:
                    st.markdown(f"**Status:** {status_badge(appt.get('status','N/A'))}", unsafe_allow_html=True)
                    st.markdown(f"**Booked At:** {appt.get('submitted_timestamp','N/A')}")
                    st.markdown(f"**Doctor Note:** {appt.get('doctor_note','').strip() or '(none)'}")
                st.markdown("**Symptom Summary:**")
                st.info(appt.get("symptom_summary", "No symptom notes provided."))

# ── Patient book page ─────────────────────────────────────────────────────────
def render_patient_book(all_appointments, doctors, patient_name, patient_email):
    if not require_role("Patient"):
        return

    st.title("📅 Book Appointment")
    st.caption(f"Logged in as {patient_email}")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["Book New", "Reschedule", "Cancel"])

    # ── Book new ──
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📋 Appointment Details")
            if doctors:
                id_to_lbl   = {d["doctor_id"]: f"Dr. {d['name']} — {d.get('specialty','General')}" for d in doctors}
                selected_id = st.selectbox("Select Doctor *", list(id_to_lbl),
                                           format_func=id_to_lbl.get, key="pb_doctor_selector")
                form_doc    = doctor_by_id(doctors, selected_id)
            else:
                st.warning("No doctors registered yet."); form_doc = None

            appt_type = st.selectbox("Appointment Type *",
                                     ["— Select appointment type —"] + APPOINTMENT_TYPES,
                                     key="pb_appt_type")
            symptoms  = st.text_area("Describe your symptoms *", height=120, key="pb_symptoms",
                                     placeholder="e.g. Blurry vision, seeing floaters...")

            slots = list(form_doc.get("available_slots", [])) if form_doc else []
            slot  = (st.selectbox("Available Time Slot *", sorted(slots), key="pb_slot_selector",
                                  format_func=lambda x: x.replace("T", "  "))
                     if slots else None)
            if form_doc and not slots:
                st.info("⏰ No available slots for this doctor.")

            b_col, c_col = st.columns([1, 2])
            with b_col:
                clicked = st.button("Book Appointment", key="pb_book_btn",
                                    type="primary", use_container_width=True)
            with c_col:
                st.caption("Fields marked * are required.")

            if clicked:
                errors = validate_booking(form_doc, appt_type, symptoms, slot)
                if errors:
                    show_errors(errors)
                else:
                    # Race-condition guard: re-verify slot is still available
                    live_doc = doctor_by_id(doctors, form_doc["doctor_id"])
                    if not live_doc or slot not in live_doc.get("available_slots", []):
                        st.error("⚠️ This time slot was just taken. Please select another.")
                    else:
                        with st.spinner("Booking..."):
                            appt = new_appointment(patient_name, patient_email,
                                                   form_doc, slot, appt_type, symptoms.strip())
                            all_appointments.append(appt)
                            remove_slot(doctors, form_doc["doctor_id"], slot)
                            ok, msg = transactional_save(
                                (PATH_APPOINTMENTS, all_appointments), (PATH_DOCTORS, doctors))
                            if ok:
                                st.session_state["_flash_success"] = (
                                    f"Appointment booked for {fmt_date(appt['appointment_date'])} "
                                    f"at {appt['appointment_time']} with Dr. {appt['doctor_name']}.")
                                st.balloons()
                                nav("patient_dashboard")
                            else:
                                all_appointments.pop()
                                add_slot(doctors, form_doc["doctor_id"], slot)
                                st.error(f"⚠️ Booking failed: {msg}")

        with col2:
            st.subheader("🤖 AI Assistant")
            hdr, btn = st.columns([3, 1])
            with hdr: st.caption("Try: What slots are available?")
            with btn:
                if st.button("Clear", key="pb_clear_chat"):
                    st.session_state["messages"] = [_SESSION_DEFAULTS["messages"][0]]
                    st.rerun()
            with st.container(border=True, height=250):
                for msg in st.session_state.get("messages", []):
                    with st.chat_message(msg["role"]): st.write(msg["content"])
            if user_input := st.chat_input("Ask a question...", key="pb_chat_input"):
                st.session_state["messages"].append({"role": "user", "content": user_input})
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": ai_response(user_input, all_appointments, doctors, patient_email)})
                st.rerun()

    # ── Reschedule ──
    with tab2:
        st.markdown("### 🔄 Reschedule an Appointment")
        scheduled = scheduled_appts(all_appointments, patient_email)
        if not scheduled:
            st.info("No scheduled appointments to reschedule.")
        else:
            opts    = {f"Dr. {a['doctor_name']}  |  {fmt_date(a['appointment_date'])} {a['appointment_time']}  |  {a['appointment_type']}": a["appointment_id"]
                       for a in scheduled}
            lbl     = st.selectbox("Select appointment", list(opts), key="pb_reschedule_selector")
            rs_appt = appt_by_id(all_appointments, opts[lbl])
            rs_doc  = doctor_by_id(doctors, rs_appt.get("doctor_id", "")) if rs_appt else None
            new_slots = sorted(rs_doc.get("available_slots", [])) if rs_doc else []

            if not new_slots:
                st.warning("No alternative slots available for this doctor.")
            else:
                new_slot = st.selectbox("New Time Slot", new_slots, key="pb_reschedule_slot",
                                        format_func=lambda x: x.replace("T", "  "))
                if st.button("Confirm Reschedule", key="pb_reschedule_btn",
                             type="primary", use_container_width=True):
                    live_appt = appt_by_id(all_appointments, rs_appt["appointment_id"])
                    live_doc  = doctor_by_id(doctors, rs_doc["doctor_id"]) if rs_doc else None
                    if not live_appt or live_appt.get("status") != "Scheduled":
                        st.error("⚠️ This appointment is no longer active.")
                    elif not live_doc or new_slot not in live_doc.get("available_slots", []):
                        st.error("⚠️ That slot was just taken. Please select another.")
                    else:
                        with st.spinner("Rescheduling..."):
                            old_slot   = rs_appt["appointment_date"] + "T" + rs_appt["appointment_time"]
                            date, time = new_slot.split("T")
                            reschedule(all_appointments, rs_appt["appointment_id"], date, time)
                            remove_slot(doctors, rs_doc["doctor_id"], new_slot)
                            add_slot(doctors, rs_doc["doctor_id"], old_slot)
                            ok, msg = transactional_save(
                                (PATH_APPOINTMENTS, all_appointments), (PATH_DOCTORS, doctors))
                            if ok:
                                show_success(f"Rescheduled to {fmt_date(date)} at {time}.")
                                st.rerun()
                            else:
                                reschedule(all_appointments, rs_appt["appointment_id"],
                                           rs_appt["appointment_date"], rs_appt["appointment_time"])
                                add_slot(doctors, rs_doc["doctor_id"], new_slot)
                                remove_slot(doctors, rs_doc["doctor_id"], old_slot)
                                st.error(f"⚠️ Reschedule failed: {msg}")

    # ── Cancel ──
    with tab3:
        st.markdown("### ❌ Cancel an Appointment")
        scheduled = scheduled_appts(all_appointments, patient_email)
        if not scheduled:
            st.info("No scheduled appointments to cancel.")
        else:
            appt_cards(scheduled)
            st.divider()
            opts = {f"Dr. {a['doctor_name']}  |  {fmt_date(a['appointment_date'])} {a['appointment_time']}  |  {a['appointment_type']}": a["appointment_id"]
                    for a in scheduled}
            lbl  = st.selectbox("Select appointment to cancel", list(opts), key="pb_cancel_selector")
            if st.button("Cancel Appointment", key="pb_cancel_btn", type="primary", use_container_width=True):
                aid       = opts[lbl]
                live_appt = appt_by_id(all_appointments, aid)
                if not live_appt or live_appt.get("status") != "Scheduled":
                    st.error("⚠️ This appointment is no longer active.")
                else:
                    with st.spinner("Cancelling..."):
                        old_slot = live_appt["appointment_date"] + "T" + live_appt["appointment_time"]
                        add_slot(doctors, live_appt["doctor_id"], old_slot)
                        cancel(all_appointments, aid)
                        ok, msg = transactional_save(
                            (PATH_APPOINTMENTS, all_appointments), (PATH_DOCTORS, doctors))
                        if ok:
                            show_success("Appointment cancelled. Time slot has been freed.")
                            st.rerun()
                        else:
                            live_appt["status"] = "Scheduled"
                            remove_slot(doctors, live_appt["doctor_id"], old_slot)
                            st.error(f"⚠️ Could not save cancellation: {msg}")

# ── Doctor dashboard ──────────────────────────────────────────────────────────
def render_doctor_dashboard(all_appointments, doctor_id, doctor_name):
    if not require_role("Doctor"):
        return

    schedule = doctor_appts(all_appointments, doctor_id)
    st.title("📊 Appointment Dashboard")
    st.caption(f"Patient roster for {doctor_name}")
    st.divider()

    col1, col2 = st.columns([4, 2])
    with col1:
        appt_cards(schedule) if schedule else st.info("No appointments assigned to you yet.")
    with col2:
        st.metric("My Appointments", len(schedule))
        st.metric("Scheduled", sum(1 for a in schedule if a.get("status") == "Scheduled"))
        st.metric("Completed", sum(1 for a in schedule if a.get("status") == "Completed"))
        st.metric("No-Show",   sum(1 for a in schedule if a.get("status") == "No-Show"))

    if schedule:
        st.divider()
        st.markdown('<div class="section-header">✏️ Update Appointment Status</div>', unsafe_allow_html=True)
        appt_selectbox("Select an appointment:", schedule, key="dd_appt_selector")
        if appt := appt_by_id(all_appointments, st.session_state.get("selected_appointment_id")):
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Patient:** {appt.get('patient_name','N/A')}")
                    st.markdown(f"**Email:** {appt.get('patient_email','N/A')}")
                    st.markdown(f"**Date & Time:** {fmt_date(appt.get('appointment_date','N/A'))}  {appt.get('appointment_time','')}")
                with c2:
                    st.markdown(f"**Type:** {appt.get('appointment_type','N/A')}")
                    st.markdown(f"**Status:** {status_badge(appt.get('status','N/A'))}", unsafe_allow_html=True)
                    st.markdown(f"**Booked At:** {appt.get('submitted_timestamp','N/A')}")
                st.markdown("**Symptom Summary:**")
                st.info(appt.get("symptom_summary", "No symptom notes."))
                st.divider()

                aid     = appt["appointment_id"]
                current = appt.get("status", "Scheduled")
                s_col, b_col = st.columns([2, 3])
                with s_col:
                    new_status = st.selectbox("Update Status", APPT_STATUSES,
                                              index=APPT_STATUSES.index(current) if current in APPT_STATUSES else 0,
                                              key=f"dd_status_{aid}")
                    new_note   = st.text_input("Doctor Note", value=appt.get("doctor_note", ""),
                                               key=f"dd_note_{aid}")
                with b_col:
                    st.write(""); st.write("")
                    if st.button("Save Changes", key=f"dd_save_{aid}",
                                 type="primary", use_container_width=True):
                        update_status(all_appointments, aid, new_status, new_note)
                        if save_json(PATH_APPOINTMENTS, all_appointments):
                            show_success("Appointment updated successfully.")
                            st.rerun()
                        else:
                            st.error("⚠️ Could not save changes. Please try again.")

# ── Doctor slots page ─────────────────────────────────────────────────────────
def render_doctor_slots(doctors, doctor_id, doctor_name):
    if not require_role("Doctor"):
        return

    doc = doctor_by_id(doctors, doctor_id)
    st.title("⏰ Manage Time Slots")
    st.caption(f"Managing slots for {doctor_name}")
    st.divider()

    tab1, tab2 = st.tabs(["Add Slot", "Remove Slot"])
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("➕ Add Time Slot")
            slot_date = st.date_input("Date", key="ds_slot_date")
            slot_hour = st.selectbox("Hour", [f"{h:02d}:00" for h in range(8, 18)], key="ds_slot_hour")
            if st.button("Add Slot", key="ds_add_btn", type="primary", use_container_width=True):
                new_slot = f"{slot_date}T{slot_hour}"
                if doc and new_slot in doc.get("available_slots", []):
                    st.warning("This slot already exists.")
                else:
                    add_slot(doctors, doctor_id, new_slot)
                    if save_json(PATH_DOCTORS, doctors):
                        show_success(f"Slot added: {fmt_date(str(slot_date))} at {slot_hour}")
                        st.rerun()
                    else:
                        st.error("⚠️ Could not save slot.")
        with col2:
            st.subheader("📅 Your Current Slots")
            slots = sorted(doc.get("available_slots", [])) if doc else []
            if slots:
                for s in slots:
                    parts = s.split("T")
                    st.markdown(
                        f'<div class="slot-card"><div class="slot-card-date">{fmt_date(parts[0])}</div>'
                        f'<div class="slot-card-time">⏰ {parts[1] if len(parts) > 1 else "N/A"}</div></div>',
                        unsafe_allow_html=True)
            else:
                st.info("No available slots at the moment.")

    with tab2:
        st.subheader("➖ Remove Time Slot")
        slots = sorted(doc.get("available_slots", [])) if doc else []
        if slots:
            to_remove = st.selectbox("Select slot", slots, key="ds_remove_selector",
                                     format_func=lambda x: x.replace("T", "  "))
            if st.button("Remove Slot", key="ds_remove_btn", type="primary", use_container_width=True):
                remove_slot(doctors, doctor_id, to_remove)
                if save_json(PATH_DOCTORS, doctors):
                    parts = to_remove.split("T")
                    show_success(f"Slot removed: {fmt_date(parts[0])} at {parts[1] if len(parts) > 1 else ''}")
                    st.rerun()
                else:
                    st.error("⚠️ Could not save removal.")
        else:
            st.info("No slots to remove.")

# ── Main ──────────────────────────────────────────────────────────────────────
all_patients     = load_json(PATH_PATIENTS, [])
doctors          = load_json(PATH_DOCTORS, [])
all_appointments = load_json(PATH_APPOINTMENTS, [])

if st.session_state.get("logged_in"):
    render_sidebar()

ss   = st.session_state
page = ss.get("page", "login")

if   page == "login":             render_login(all_patients, doctors)
elif page == "patient_dashboard": render_patient_dashboard(all_appointments, ss.get("current_user_email",""), ss.get("current_user_name",""))
elif page == "patient_book":      render_patient_book(all_appointments, doctors, ss.get("current_user_name",""), ss.get("current_user_email",""))
elif page == "doctor_dashboard":  render_doctor_dashboard(all_appointments, ss.get("current_doctor_id",""), ss.get("current_user_name",""))
elif page == "doctor_slots":      render_doctor_slots(doctors, ss.get("current_doctor_id",""), ss.get("current_user_name",""))

st.markdown('<div class="clinic-footer"><strong>ClearVision Clinic</strong> | Ophthalmology Appointment Portal<br>© 2026. All rights reserved.</div>', unsafe_allow_html=True)
