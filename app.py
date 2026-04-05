import streamlit as st
import json
import hashlib
from pathlib import Path
from datetime import datetime
import uuid

st.set_page_config("ClearVision Clinic", layout="wide", initial_sidebar_state="expanded")

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

# ─── PERSISTENCE ───────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            st.warning(f"Could not load {path.name}: {e}")
            return default
    else:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
        except OSError as e:
            st.error(f"Failed to initialize {path.name}: {e}")
        return default

def save_json(path, data):
    """Atomic write: write to .tmp then rename to avoid partial-write corruption."""
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(path)
        return True
    except OSError as e:
        st.error(f"Failed to save {path.name}: {e}")
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False

# ─── DATA ACCESS ───────────────────────────────────────────────────────────────
def get_doctor_by_id(doctors_list, doctor_id):
    return next((d for d in doctors_list if d["doctor_id"] == doctor_id), None)

def get_appointment_by_id(appointments, appt_id):
    return next((a for a in appointments if a.get("appointment_id") == appt_id), None)

def get_patient_appointments(appointments, patient_email):
    email = patient_email.strip().lower()
    return [a for a in appointments if a.get("patient_email", "").lower() == email]

def get_doctor_appointments(appointments, doctor_id):
    return [a for a in appointments if a.get("doctor_id") == doctor_id]

def get_scheduled_appointments(appointments, patient_email):
    return [a for a in get_patient_appointments(appointments, patient_email)
            if a.get("status") == "Scheduled"]

# ─── BUSINESS LOGIC ────────────────────────────────────────────────────────────
def build_appointment(patient_name, patient_email, doctor, slot, appt_type, symptoms):
    slot_date, slot_time = slot.split("T")
    return {
        "appointment_id":      f"appt-{str(uuid.uuid4())[:8]}",
        "clinic_id":           CLINIC_ID,
        "patient_name":        patient_name,
        "patient_email":       patient_email,
        "doctor_id":           doctor["doctor_id"],
        "doctor_name":         doctor["name"],
        "appointment_date":    slot_date,
        "appointment_time":    slot_time,
        "submitted_timestamp": datetime.now().isoformat(),
        "appointment_type":    appt_type,
        "symptom_summary":     symptoms,
        "status":              "Scheduled",
        "doctor_note":         "",
    }

def remove_slot_from_doctor(doctors_list, doctor_id, slot):
    for doc in doctors_list:
        if doc["doctor_id"] == doctor_id and slot in doc["available_slots"]:
            doc["available_slots"].remove(slot)
            break

def add_slot_to_doctor(doctors_list, doctor_id, slot):
    for doc in doctors_list:
        if doc["doctor_id"] == doctor_id and slot not in doc["available_slots"]:
            doc["available_slots"].append(slot)
            break

def reschedule_appointment(appointments, appt_id, new_date, new_time):
    for appt in appointments:
        if appt["appointment_id"] == appt_id:
            appt["appointment_date"] = new_date
            appt["appointment_time"] = new_time
            break

def cancel_appointment(appointments, appt_id):
    for appt in appointments:
        if appt["appointment_id"] == appt_id:
            appt["status"] = "Cancelled"
            break

def update_appointment_status(appointments, appt_id, status, note):
    for appt in appointments:
        if appt["appointment_id"] == appt_id:
            appt["status"]      = status
            appt["doctor_note"] = note
            break

# ─── VALIDATION ────────────────────────────────────────────────────────────────
def _email_valid(email):
    return email.strip() and "@" in email and "." in email.split("@")[-1]

def validate_patient_registration(name, email, password, confirm, existing_patients):
    errors = []
    if not name.strip():
        errors.append("Full Name is required.")
    if not _email_valid(email):
        errors.append("Please enter a valid email address.")
    elif any(p["email"] == email.strip().lower() for p in existing_patients):
        errors.append("An account with this email already exists.")
    if not password.strip():
        errors.append("Password is required.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    if password != confirm:
        errors.append("Passwords do not match.")
    return errors

def validate_doctor_registration(name, email, specialty, password, confirm, existing_doctors):
    errors = []
    if not name.strip():
        errors.append("Full Name is required.")
    if not _email_valid(email):
        errors.append("Please enter a valid email address.")
    elif any(d.get("email", "") == email.strip().lower() for d in existing_doctors):
        errors.append("An account with this email already exists.")
    if not specialty.strip():
        errors.append("Specialty is required.")
    if not password.strip():
        errors.append("Password is required.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    if password != confirm:
        errors.append("Passwords do not match.")
    return errors

def validate_booking(doctor, appt_type, symptoms, slot):
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
        errors.append("No available time slot to book.")
    return errors

# ─── RECORD CREATION ───────────────────────────────────────────────────────────
def create_patient_record(name, email, password):
    return {
        "patient_id": f"pat_{str(uuid.uuid4())[:8]}",
        "name":       name.strip(),
        "email":      email.strip().lower(),
        "password":   hash_password(password),
    }

def create_doctor_record(name, email, specialty, password):
    return {
        "doctor_id":       f"doc_{str(uuid.uuid4())[:8]}",
        "name":            name.strip(),
        "email":           email.strip().lower(),
        "specialty":       specialty.strip(),
        "password":        hash_password(password),
        "available_slots": [],
    }

# ─── AI ASSISTANT ──────────────────────────────────────────────────────────────
def get_ai_response(user_input, appointments, doctors, patient_email):
    q = user_input.lower()
    if "next appointment" in q:
        scheduled = get_scheduled_appointments(appointments, patient_email)
        if scheduled:
            nxt = sorted(scheduled, key=lambda x: x.get("appointment_date", ""))[0]
            return (f"Your next appointment is on {nxt['appointment_date']} at "
                    f"{nxt['appointment_time']} with {nxt['doctor_name']} "
                    f"for a {nxt['appointment_type']}.")
        return "You have no upcoming scheduled appointments. Use the form on the left to book one."
    if "available" in q or "slot" in q:
        open_slots = [f"{d['name']}: {s.replace('T', ' at ')}"
                      for d in doctors for s in d.get("available_slots", [])]
        return ("Available slots:\n" + "\n".join(open_slots)) if open_slots \
            else "There are currently no available time slots."
    if "cancel" in q:
        return ("To cancel an appointment:\n"
                "1. Click the 'Cancel an Appointment' tab above\n"
                "2. Your scheduled appointments will be listed\n"
                "3. Select one and click Cancel")
    if "doctor" in q:
        avail = [f"{d['name']} ({d['specialty']})" for d in doctors if d.get("available_slots")]
        return ("Doctors with open slots:\n" + "\n".join(avail)) if avail \
            else "No doctors currently have available slots."
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

# ─── UI COMPONENTS ─────────────────────────────────────────────────────────────
def navigate_to(page):
    st.session_state["page"] = page
    st.session_state["selected_appointment_id"] = None
    st.rerun()

def show_validation_errors(errors):
    for err in errors:
        st.warning(f"⚠️  {err}")

def render_appt_table(appointments):
    keys = ["appointment_id", "patient_name", "appointment_date", "appointment_time",
            "appointment_type", "status", "doctor_name"]
    rows = [{k: a.get(k, "") for k in keys} for a in appointments]
    st.dataframe(
        rows,
        column_config={
            "appointment_id":   st.column_config.TextColumn("ID",     width="small"),
            "patient_name":     st.column_config.TextColumn("Patient"),
            "doctor_name":      st.column_config.TextColumn("Doctor"),
            "appointment_date": st.column_config.TextColumn("Date",   width="medium"),
            "appointment_time": st.column_config.TextColumn("Time",   width="small"),
            "appointment_type": st.column_config.TextColumn("Type"),
            "status":           st.column_config.TextColumn("Status", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )

def appt_selectbox(label, appointments, key):
    """Selectbox backed by appointment_id — immune to list reordering."""
    label_to_id = {
        f"{a.get('appointment_date','?')} {a.get('appointment_time','')}  —  "
        f"{a.get('appointment_type','?')}  —  {a.get('status','?')}": a["appointment_id"]
        for a in appointments
    }
    current_id    = st.session_state.get("selected_appointment_id")
    current_label = next((lbl for lbl, aid in label_to_id.items() if aid == current_id), None)
    options       = ["— Select an appointment —"] + list(label_to_id.keys())
    default_idx   = options.index(current_label) if current_label in options else 0

    chosen = st.selectbox(label, options=options, index=default_idx, key=key)
    st.session_state["selected_appointment_id"] = (
        None if chosen == "— Select an appointment —" else label_to_id[chosen]
    )

# ─── PAGE RENDERERS ────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## ClearVision Clinic")
        st.divider()
        role_icon = "🩺" if st.session_state["role"] == "Doctor" else "👤"
        st.markdown(f"{role_icon} **{st.session_state['current_user_name']}**")
        st.caption(f"Role: {st.session_state['role']}")
        st.divider()

        if st.session_state["role"] == "Patient":
            if st.button("My Appointments", key="nav_dashboard_btn", type="primary", use_container_width=True):
                navigate_to("patient_dashboard")
            if st.button("Book Appointment", key="nav_book_btn", type="primary", use_container_width=True):
                navigate_to("patient_book")
        elif st.session_state["role"] == "Doctor":
            if st.button("Appointment Dashboard", key="nav_dashboard_btn", type="primary", use_container_width=True):
                navigate_to("doctor_dashboard")
            if st.button("Manage Time Slots", key="nav_slots_btn", type="primary", use_container_width=True):
                navigate_to("doctor_slots")

        st.divider()
        if st.button("Log Out", key="logout_btn", use_container_width=True):
            for key in ["logged_in", "role", "current_user_name", "current_user_email",
                        "current_doctor_id", "selected_appointment_id"]:
                st.session_state[key] = False if key == "logged_in" else None
            st.session_state["page"] = "login"
            st.session_state["messages"] = [
                {"role": "assistant", "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?"}
            ]
            st.rerun()


# ── Login page ─────────────────────────────────────────────────────────────────
def render_login_page(all_patients, doctors):
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("# 👁️ ClearVision Clinic")
        st.markdown("*Ophthalmology Appointment Portal*")
        st.divider()

        if st.session_state["_reg_success"]:
            st.success(st.session_state["_reg_success"])
            st.session_state["_reg_success"] = None

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
    st.subheader("Patient Login")
    email    = st.text_input("Email",    placeholder="yourname@email.com", key="login_patient_email")
    password = st.text_input("Password", type="password",                  key="login_patient_password")

    if st.button("Log In as Patient", key="login_patient_btn", type="primary", use_container_width=True):
        if not _email_valid(email):
            st.warning("⚠️  Please enter a valid email address.")
        elif not password.strip():
            st.warning("⚠️  Please enter your password.")
        else:
            matched = next(
                (p for p in all_patients
                 if p["email"] == email.strip().lower()
                 and p["password"] == hash_password(password)),
                None,
            )
            if matched:
                st.session_state.update({
                    "logged_in": True, "role": "Patient",
                    "current_user_name": matched["name"],
                    "current_user_email": matched["email"],
                })
                navigate_to("patient_dashboard")
            else:
                st.error("Incorrect email or password. Please try again.")


def _render_patient_register(all_patients):
    st.subheader("Patient Register")
    name     = st.text_input("Full Name *",        placeholder="James Lee",          key="reg_patient_name")
    email    = st.text_input("Email *",            placeholder="yourname@email.com", key="reg_patient_email")
    password = st.text_input("Password *",         type="password",                  key="reg_patient_password")
    confirm  = st.text_input("Confirm Password *", type="password",                  key="reg_patient_confirm")

    if st.button("Create Account", key="reg_patient_btn", type="primary", use_container_width=True):
        errors = validate_patient_registration(name, email, password, confirm, all_patients)
        if errors:
            show_validation_errors(errors)
        else:
            with st.spinner("Creating your account..."):
                all_patients.append(create_patient_record(name, email, password))
                if save_json(PATH_PATIENTS, all_patients):
                    st.session_state["_reg_success"] = "Account created successfully! Please log in."
                    st.session_state["patient_mode"] = "Login"
                    navigate_to("login")


def _render_doctor_login(doctors):
    st.subheader("Doctor Login")
    email    = st.text_input("Email",    placeholder="doctor@clearvision.com", key="login_doc_email")
    password = st.text_input("Password", type="password",                      key="login_doc_password")

    if st.button("Log In as Doctor", key="login_doctor_btn", type="primary", use_container_width=True):
        if not _email_valid(email):
            st.warning("⚠️  Please enter a valid email address.")
        elif not password.strip():
            st.warning("⚠️  Please enter your password.")
        else:
            matched = next(
                (d for d in doctors
                 if d.get("email", "") == email.strip().lower()
                 and d.get("password") == hash_password(password)),
                None,
            )
            if matched:
                st.session_state.update({
                    "logged_in": True, "role": "Doctor",
                    "current_user_name": matched["name"],
                    "current_doctor_id": matched["doctor_id"],
                })
                navigate_to("doctor_dashboard")
            else:
                st.error("Incorrect email or password. Please try again.")


def _render_doctor_register(doctors):
    st.subheader("Doctor Registration")
    name      = st.text_input("Full Name *",        placeholder="Dr. Jane Smith",         key="reg_doc_name")
    email     = st.text_input("Email *",            placeholder="doctor@clearvision.com", key="reg_doc_email")
    specialty = st.text_input("Specialty *",        placeholder="e.g. Retinal Disease",   key="reg_doc_specialty")
    password  = st.text_input("Password *",         type="password",                      key="reg_doc_password")
    confirm   = st.text_input("Confirm Password *", type="password",                      key="reg_doc_confirm")

    if st.button("Create Doctor Account", key="reg_doc_btn", type="primary", use_container_width=True):
        errors = validate_doctor_registration(name, email, specialty, password, confirm, doctors)
        if errors:
            show_validation_errors(errors)
        else:
            with st.spinner("Creating your account..."):
                doctors.append(create_doctor_record(name, email, specialty, password))
                if save_json(PATH_DOCTORS, doctors):
                    st.session_state["_reg_success"] = "Doctor account created successfully! Please log in."
                    st.session_state["doctor_mode"] = "Login"
                    navigate_to("login")


# ── Patient dashboard ──────────────────────────────────────────────────────────
def render_patient_dashboard(all_appointments, patient_email, patient_name):
    my_appointments = get_patient_appointments(all_appointments, patient_email)

    st.title("My Appointments")
    st.caption(f"Logged in as {patient_email}")
    st.divider()

    col1, col2 = st.columns([4, 2])
    with col1:
        if my_appointments:
            render_appt_table(my_appointments)
        else:
            st.info("You have no appointments yet. Use **Book Appointment** in the sidebar to get started.")
    with col2:
        st.metric("Total",     len(my_appointments))
        st.metric("Scheduled", sum(1 for a in my_appointments if a.get("status") == "Scheduled"))
        st.metric("Completed", sum(1 for a in my_appointments if a.get("status") == "Completed"))
        st.metric("Cancelled", sum(1 for a in my_appointments if a.get("status") == "Cancelled"))

    if my_appointments:
        st.divider()
        st.subheader("Appointment Details")
        appt_selectbox("Choose an appointment to inspect:", my_appointments, key="patient_appt_selector")
        appt = get_appointment_by_id(all_appointments, st.session_state["selected_appointment_id"])
        if appt:
            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Doctor:** {appt.get('doctor_name', 'N/A')}")
                    st.markdown(f"**Date:** {appt.get('appointment_date', 'N/A')}  {appt.get('appointment_time', '')}")
                    st.markdown(f"**Type:** {appt.get('appointment_type', 'N/A')}")
                with col_b:
                    st.markdown(f"**Status:** {appt.get('status', 'N/A')}")
                    st.markdown(f"**Booked At:** {appt.get('submitted_timestamp', 'N/A')}")
                    note = appt.get("doctor_note", "").strip()
                    st.markdown(f"**Doctor Note:** {note if note else '(none)'}")
                st.markdown("**Symptom Summary:**")
                st.info(appt.get("symptom_summary", "No symptom notes provided."))


# ── Patient book page ──────────────────────────────────────────────────────────
def render_patient_book(all_appointments, doctors, patient_name, patient_email):
    st.title("Book Appointment")
    st.caption(f"Logged in as {patient_email}")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["Book New Appointment", "Reschedule", "Cancel an Appointment"])
    with tab1:
        _render_book_tab(all_appointments, doctors, patient_name, patient_email)
    with tab2:
        _render_reschedule_tab(all_appointments, doctors, patient_email)
    with tab3:
        _render_cancel_tab(all_appointments, patient_email)


def _render_book_tab(all_appointments, doctors, patient_name, patient_email):
    col1, col2 = st.columns([3, 3])

    with col1:
        st.subheader("Appointment Details")

        if doctors:
            doc_id_to_label = {d["doctor_id"]: f"{d['name']} — {d['specialty']}" for d in doctors}
            selected_doc_id = st.selectbox(
                "Select Doctor *",
                options=list(doc_id_to_label.keys()),
                format_func=lambda did: doc_id_to_label[did],
                key="form_doctor_id_selector",
            )
            form_doctor = get_doctor_by_id(doctors, selected_doc_id)
        else:
            st.warning("No doctors are registered yet.")
            form_doctor = None

        appt_type = st.selectbox(
            "Appointment Type *",
            options=["— Select appointment type —"] + APPOINTMENT_TYPES,
            key="form_appointment_type",
        )
        symptoms = st.text_area(
            "Describe your symptoms *",
            placeholder="e.g. Blurry vision on left side, seeing floaters...",
            height=120, key="form_symptom_summary",
        )

        available_slots = form_doctor.get("available_slots", []) if form_doctor else []
        if available_slots:
            slot = st.selectbox(
                "Available Time Slot *", options=available_slots, key="form_slot_selector",
                format_func=lambda x: x.replace("T", "  "),
            )
        else:
            if form_doctor:
                st.warning("No available slots for this doctor.")
            slot = None

        btn_col, cap_col = st.columns([1, 2])
        with btn_col:
            clicked = st.button("Book Appointment", key="form_book_btn", type="primary", use_container_width=True)
        with cap_col:
            st.caption("Fields marked * are required. Status defaults to **Scheduled**.")

        if clicked:
            errors = validate_booking(form_doctor, appt_type, symptoms, slot)
            if errors:
                show_validation_errors(errors)
            else:
                with st.spinner("Booking your appointment..."):
                    new_appt = build_appointment(patient_name, patient_email,
                                                 form_doctor, slot, appt_type, symptoms.strip())
                    all_appointments.append(new_appt)
                    remove_slot_from_doctor(doctors, form_doctor["doctor_id"], slot)
                    saved_appts = save_json(PATH_APPOINTMENTS, all_appointments)
                    saved_docs  = save_json(PATH_DOCTORS, doctors)
                    if saved_appts and saved_docs:
                        st.balloons()
                        navigate_to("patient_dashboard")
                    elif not saved_appts:
                        st.error("⚠️  Appointment could not be saved. Please try again.")
                    else:
                        st.warning("⚠️  Appointment saved but slot update failed — please notify the clinic.")

    with col2:
        _render_ai_assistant(all_appointments, doctors, patient_email)


def _render_ai_assistant(all_appointments, doctors, patient_email):
    st.subheader("AI Assistant")
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
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    user_input = st.chat_input("Ask a question...")
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        response = get_ai_response(user_input, all_appointments, doctors, patient_email)
        st.session_state["messages"].append({"role": "assistant", "content": response})
        st.rerun()


def _render_reschedule_tab(all_appointments, doctors, patient_email):
    st.markdown("### Reschedule an Appointment")
    scheduled = get_scheduled_appointments(all_appointments, patient_email)

    if not scheduled:
        st.info("You have no scheduled appointments to reschedule.")
        return

    rs_options = {
        f"{a['doctor_name']} — {a['appointment_date']} {a['appointment_time']} ({a['appointment_type']})": a["appointment_id"]
        for a in scheduled
    }
    rs_label = st.selectbox("Select appointment to reschedule", options=list(rs_options.keys()), key="reschedule_appt_selector")
    rs_appt  = get_appointment_by_id(all_appointments, rs_options[rs_label])
    rs_doc   = get_doctor_by_id(doctors, rs_appt["doctor_id"]) if rs_appt else None
    new_slots = rs_doc.get("available_slots", []) if rs_doc else []

    if not new_slots:
        st.warning("No alternative slots available for this doctor.")
        return

    new_slot = st.selectbox("Select New Time Slot", options=new_slots, key="reschedule_slot_selector",
                            format_func=lambda x: x.replace("T", "  "))

    if st.button("Confirm Reschedule", key="reschedule_btn", type="primary", use_container_width=True):
        with st.spinner("Rescheduling..."):
            old_slot = rs_appt["appointment_date"] + "T" + rs_appt["appointment_time"]
            slot_date, slot_time = new_slot.split("T")
            reschedule_appointment(all_appointments, rs_appt["appointment_id"], slot_date, slot_time)
            if rs_doc:
                remove_slot_from_doctor(doctors, rs_doc["doctor_id"], new_slot)
                add_slot_to_doctor(doctors, rs_doc["doctor_id"], old_slot)
            saved_appts = save_json(PATH_APPOINTMENTS, all_appointments)
            saved_docs  = save_json(PATH_DOCTORS, doctors)
            if saved_appts and saved_docs:
                st.success(f"Appointment rescheduled to {slot_date} at {slot_time}.")
                st.rerun()
            elif not saved_appts:
                st.error("⚠️  Could not save the reschedule. Please try again.")
            else:
                st.warning("⚠️  Reschedule saved but slot update failed — please notify the clinic.")


def _render_cancel_tab(all_appointments, patient_email):
    st.markdown("### Cancel an Appointment")
    scheduled = get_scheduled_appointments(all_appointments, patient_email)

    if not scheduled:
        st.info("You have no scheduled appointments to cancel.")
        return

    render_appt_table(scheduled)
    cl_options = {
        f"{a['doctor_name']} — {a['appointment_date']} {a['appointment_time']} ({a['appointment_type']})": a["appointment_id"]
        for a in scheduled
    }
    cl_label = st.selectbox("Select appointment to cancel", options=list(cl_options.keys()), key="cancel_appt_selector")

    if st.button("Cancel Appointment", key="cancel_btn", type="primary", use_container_width=True):
        with st.spinner("Cancelling appointment..."):
            cancel_appointment(all_appointments, cl_options[cl_label])
            if save_json(PATH_APPOINTMENTS, all_appointments):
                st.success("Appointment cancelled successfully.")
                st.rerun()


# ── Doctor dashboard ───────────────────────────────────────────────────────────
def render_doctor_dashboard(all_appointments, doctor_id, doctor_name):
    my_schedule = get_doctor_appointments(all_appointments, doctor_id)

    st.title("Appointment Dashboard")
    st.caption(f"Patient roster for {doctor_name}")
    st.divider()

    col1, col2 = st.columns([4, 2])
    with col1:
        if my_schedule:
            render_appt_table(my_schedule)
        else:
            st.info("No appointments assigned to you yet.")
    with col2:
        st.metric("My Appointments", len(my_schedule))
        st.metric("Scheduled", sum(1 for a in my_schedule if a.get("status") == "Scheduled"))
        st.metric("Completed", sum(1 for a in my_schedule if a.get("status") == "Completed"))
        st.metric("No-Show",   sum(1 for a in my_schedule if a.get("status") == "No-Show"))

    if my_schedule:
        st.divider()
        st.subheader("Update Appointment Status")
        appt_selectbox("Choose an appointment to update:", my_schedule, key="doctor_appt_selector")
        appt = get_appointment_by_id(all_appointments, st.session_state["selected_appointment_id"])
        if appt:
            _render_appt_update_form(all_appointments, appt)


def _render_appt_update_form(all_appointments, appt):
    with st.container(border=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Patient:** {appt.get('patient_name', 'N/A')}")
            st.markdown(f"**Email:** {appt.get('patient_email', 'N/A')}")
            st.markdown(f"**Date & Time:** {appt.get('appointment_date', 'N/A')}  {appt.get('appointment_time', '')}")
        with col_b:
            st.markdown(f"**Type:** {appt.get('appointment_type', 'N/A')}")
            st.markdown(f"**Status:** {appt.get('status', 'N/A')}")
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
                key=f"doctor_status_{appt['appointment_id']}",
            )
            new_note = st.text_input("Doctor Note", value=appt.get("doctor_note", ""),
                                     key=f"doctor_note_{appt['appointment_id']}")
        with col_s2:
            st.write("")
            st.write("")
            if st.button("Save Changes", key="doctor_save_btn", type="primary", use_container_width=True):
                with st.spinner("Saving..."):
                    update_appointment_status(all_appointments, appt["appointment_id"], new_status, new_note)
                    if save_json(PATH_APPOINTMENTS, all_appointments):
                        st.success("Appointment updated successfully.")
                        st.rerun()


# ── Doctor slots page ──────────────────────────────────────────────────────────
def render_doctor_slots(doctors, doctor_id, doctor_name):
    current_doctor = get_doctor_by_id(doctors, doctor_id)

    st.title("Manage Time Slots")
    st.caption(f"Managing slots for {doctor_name}")
    st.divider()

    tab1, tab2 = st.tabs(["Add New Slot", "Remove a Slot"])

    with tab1:
        col1, col2 = st.columns([3, 3])
        with col1:
            st.subheader("Add Time Slot")
            slot_date = st.date_input("Date", key="slot_date_input")
            slot_hour = st.selectbox("Hour", options=[f"{h:02d}:00" for h in range(8, 18)], key="slot_hour_input")
            if st.button("Add Slot", key="add_slot_btn", type="primary", use_container_width=True):
                new_slot = f"{slot_date}T{slot_hour}"
                if current_doctor and new_slot in current_doctor.get("available_slots", []):
                    st.warning("This slot already exists.")
                else:
                    add_slot_to_doctor(doctors, doctor_id, new_slot)
                    if save_json(PATH_DOCTORS, doctors):
                        st.success(f"Slot added: {slot_date} at {slot_hour}")
                        st.rerun()
        with col2:
            st.subheader("Your Current Slots")
            slots = current_doctor.get("available_slots", []) if current_doctor else []
            if slots:
                for s in slots:
                    st.markdown(f"- {s.replace('T', '  ')}")
            else:
                st.info("You have no available slots at the moment.")

    with tab2:
        col1, col2 = st.columns([3, 3])
        with col1:
            st.subheader("Remove Time Slot")
            slots = current_doctor.get("available_slots", []) if current_doctor else []
            if slots:
                slot_to_remove = st.selectbox(
                    "Select Slot to Remove", options=slots, key="remove_slot_selector",
                    format_func=lambda x: x.replace("T", "  "),
                )
                if st.button("Remove Slot", key="remove_slot_btn", type="primary", use_container_width=True):
                    with st.spinner("Removing slot..."):
                        remove_slot_from_doctor(doctors, doctor_id, slot_to_remove)
                        if save_json(PATH_DOCTORS, doctors):
                            st.success(f"Slot removed: {slot_to_remove.replace('T', ' at ')}")
                            st.rerun()
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
    "selected_appointment_id": None,
    "messages":                [{"role": "assistant", "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?"}],
    "_reg_success":            None,
}
for _key, _val in _SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

all_patients     = load_json(PATH_PATIENTS, [])
doctors          = load_json(PATH_DOCTORS, [])
all_appointments = load_json(PATH_APPOINTMENTS, [])

# ─── MAIN ──────────────────────────────────────────────────────────────────────
if st.session_state["logged_in"]:
    render_sidebar()

page = st.session_state["page"]
if page == "login":
    render_login_page(all_patients, doctors)
elif page == "patient_dashboard":
    render_patient_dashboard(all_appointments, st.session_state["current_user_email"], st.session_state["current_user_name"])
elif page == "patient_book":
    render_patient_book(all_appointments, doctors, st.session_state["current_user_name"], st.session_state["current_user_email"])
elif page == "doctor_dashboard":
    render_doctor_dashboard(all_appointments, st.session_state["current_doctor_id"], st.session_state["current_user_name"])
elif page == "doctor_slots":
    render_doctor_slots(doctors, st.session_state["current_doctor_id"], st.session_state["current_user_name"])
