import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import uuid
import time

st.set_page_config("ClearVision Clinic", layout="wide", initial_sidebar_state="expanded")

CLINIC_ID = "ClearVision-01"
APPOINTMENT_TYPES = [
    "Routine Vision Check",
    "Glaucoma Screening",
    "Fundus Exam",
    "Cataract Evaluation",
    "Retinal Exam",
]

doctors = [
    {"doctor_id": "doc_01", "name": "Dr. Sarah Chen",   "specialty": "Retinal Disease",      "available_slots": ["2026-05-01T09:00", "2026-05-01T10:30"]},
    {"doctor_id": "doc_02", "name": "Dr. James Park",   "specialty": "Glaucoma",              "available_slots": ["2026-05-01T11:00", "2026-05-02T09:00"]},
    {"doctor_id": "doc_03", "name": "Dr. Emily Torres", "specialty": "General Ophthalmology", "available_slots": ["2026-05-01T14:00", "2026-05-02T10:30"]},
]

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "role" not in st.session_state:
    st.session_state["role"] = None

if "current_user_name" not in st.session_state:
    st.session_state["current_user_name"] = None

if "current_user_email" not in st.session_state:
    st.session_state["current_user_email"] = None

if "current_doctor_id" not in st.session_state:
    st.session_state["current_doctor_id"] = None

if "page" not in st.session_state:
    st.session_state["page"] = "login"

if "selected_appointment_index" not in st.session_state:
    st.session_state["selected_appointment_index"] = None

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?",
        }
    ]

# ─── JSON LOADING ──────────────────────────────────────────────────────────────
json_path_patients = Path("patients.json")
if json_path_patients.exists():
    with open(json_path_patients, "r") as f:
        all_patients = json.load(f)
else:
    all_patients = []

json_path_doctors = Path("doctors.json")
if json_path_doctors.exists():
    with open(json_path_doctors, "r") as f:
        doctors = json.load(f)

json_path_appointments = Path("appointments.json")
if json_path_appointments.exists():
    with open(json_path_appointments, "r") as f:
        all_appointments = json.load(f)
else:
    all_appointments = []

# ─── SIDEBAR (shown only after login) ─────────────────────────────────────────
if st.session_state["logged_in"]:
    with st.sidebar:
        st.markdown("## ClearVision Clinic")
        st.divider()

        role_icon = "🩺" if st.session_state["role"] == "Doctor" else "👤"
        st.markdown(f"{role_icon} **{st.session_state['current_user_name']}**")
        st.caption(f"Role: {st.session_state['role']}")
        st.divider()

        if st.session_state["role"] == "Patient":
            if st.button("My Appointments", key="nav_dashboard_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "patient_dashboard"
                st.session_state["selected_appointment_index"] = None
                st.rerun()
            if st.button("Book Appointment", key="nav_book_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "patient_book"
                st.rerun()

        elif st.session_state["role"] == "Doctor":
            if st.button("Appointment Dashboard", key="nav_dashboard_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "doctor_dashboard"
                st.session_state["selected_appointment_index"] = None
                st.rerun()
            if st.button("Manage Time Slots", key="nav_slots_btn", type="primary", use_container_width=True):
                st.session_state["page"] = "doctor_slots"
                st.rerun()

        st.divider()
        if st.button("Log Out", key="logout_btn", use_container_width=True):
            for key in ["logged_in", "role", "current_user_name", "current_user_email",
                        "current_doctor_id", "selected_appointment_index"]:
                st.session_state[key] = None if key not in ["logged_in"] else False
            st.session_state["page"] = "login"
            st.session_state["messages"] = [{"role": "assistant", "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?"}]
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["page"] == "login":
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.markdown("# 👁️ ClearVision Clinic")
        st.markdown("*Ophthalmology Appointment Portal*")
        st.divider()

        tab_patient, tab_doctor = st.tabs(["Patient Login", "Doctor Login"])

        with tab_patient:
            patient_mode = st.radio("", ["Login", "Register"], key="patient_mode", horizontal=True)
            st.divider()

            if patient_mode == "Login":
                st.subheader("Patient Login")
                login_email = st.text_input("Email", placeholder="yourname@email.com", key="login_patient_email")
                login_password = st.text_input("Password", type="password", key="login_patient_password")

                if st.button("Log In as Patient", key="login_patient_btn", type="primary", use_container_width=True):
                    if not login_email.strip() or "@" not in login_email:
                        st.warning("⚠️  Please enter a valid email address.")
                    elif not login_password.strip():
                        st.warning("⚠️  Please enter your password.")
                    else:
                        matched = next((p for p in all_patients if p["email"].lower() == login_email.strip().lower() and p["password"] == login_password), None)
                        if matched:
                            st.session_state["logged_in"] = True
                            st.session_state["role"] = "Patient"
                            st.session_state["current_user_name"] = matched["name"]
                            st.session_state["current_user_email"] = matched["email"]
                            st.session_state["page"] = "patient_dashboard"
                            st.rerun()
                        else:
                            st.error("Incorrect email or password. Please try again.")

                st.caption("Demo account: `james@email.com` / `patient123`")

            else:
                st.subheader("Patient Register")
                reg_name = st.text_input("Full Name *", placeholder="James Lee", key="reg_patient_name")
                reg_email = st.text_input("Email *", placeholder="yourname@email.com", key="reg_patient_email")
                reg_password = st.text_input("Password *", type="password", key="reg_patient_password")
                reg_confirm = st.text_input("Confirm Password *", type="password", key="reg_patient_confirm")

                if st.button("Create Account", key="reg_patient_btn", type="primary", use_container_width=True):
                    reg_errors = []
                    if not reg_name.strip():
                        reg_errors.append("Full Name is required.")
                    if not reg_email.strip() or "@" not in reg_email or "." not in reg_email.split("@")[-1]:
                        reg_errors.append("Please enter a valid email address.")
                    elif any(p["email"].lower() == reg_email.strip().lower() for p in all_patients):
                        reg_errors.append("An account with this email already exists.")
                    if not reg_password.strip():
                        reg_errors.append("Password is required.")
                    elif len(reg_password) < 6:
                        reg_errors.append("Password must be at least 6 characters.")
                    if reg_password != reg_confirm:
                        reg_errors.append("Passwords do not match.")

                    if reg_errors:
                        for err in reg_errors:
                            st.warning(f"⚠️  {err}")
                    else:
                        with st.spinner("Creating your account..."):
                            new_patient = {
                                "patient_id": f"pat_{str(__import__('uuid').uuid4())[:8]}",
                                "name":       reg_name.strip(),
                                "email":      reg_email.strip(),
                                "password":   reg_password,
                            }
                            all_patients.append(new_patient)
                            with open(json_path_patients, "w") as f:
                                json.dump(all_patients, f, indent=2)

                            st.session_state["logged_in"] = True
                            st.session_state["role"] = "Patient"
                            st.session_state["current_user_name"] = reg_name.strip()
                            st.session_state["current_user_email"] = reg_email.strip()
                            st.session_state["page"] = "patient_dashboard"
                            time.sleep(1)
                            st.rerun()

        with tab_doctor:
            st.subheader("Doctor Login")
            selected_doctor = st.selectbox(
                "Select your profile",
                options=doctors,
                key="login_doctor_selector",
                format_func=lambda x: f"{x['name']} — {x['specialty']}",
            )
            login_doctor_password = st.text_input("Password", type="password", placeholder="Enter password", key="login_doctor_password")

            if st.button("Log In as Doctor", key="login_doctor_btn", type="primary", use_container_width=True):
                if not login_doctor_password.strip():
                    st.warning("⚠️  Please enter your password.")
                elif login_doctor_password != "doctor123":
                    st.error("Incorrect password. Please try again.")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = "Doctor"
                    st.session_state["current_user_name"] = selected_doctor["name"]
                    st.session_state["current_doctor_id"] = selected_doctor["doctor_id"]
                    st.session_state["page"] = "doctor_dashboard"
                    st.rerun()

            st.caption("Demo password: `doctor123`")

# ══════════════════════════════════════════════════════════════════════════════
# PATIENT — MY APPOINTMENTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "patient_dashboard":
    patient_email = st.session_state["current_user_email"]
    my_appointments = [a for a in all_appointments if a.get("patient_email", "").lower() == patient_email.lower()]

    st.title(f"My Appointments")
    st.markdown(f"*Welcome, **{st.session_state['current_user_name']}** — {patient_email}*")
    st.divider()

    col1, col2 = st.columns([4, 2])

    with col1:
        st.markdown("## My Appointments")
        if len(my_appointments) > 0:
            st.dataframe(my_appointments, use_container_width=True)
        else:
            st.warning("You have no appointments booked yet. Click 'Book Appointment' to get started.")

    with col2:
        scheduled_count = sum(1 for a in my_appointments if a.get("status") == "Scheduled")
        completed_count = sum(1 for a in my_appointments if a.get("status") == "Completed")
        cancelled_count = sum(1 for a in my_appointments if a.get("status") == "Cancelled")

        st.metric("Total Appointments", f"{len(my_appointments)}")
        st.metric("Scheduled",          f"{scheduled_count}")
        st.metric("Completed",          f"{completed_count}")
        st.metric("Cancelled",          f"{cancelled_count}")

    st.divider()

    if len(my_appointments) > 0:
        st.subheader("Appointment Details")

        selector_options = [
            f"#{i + 1}  —  {a.get('appointment_date', '?')} {a.get('appointment_time', '')}  —  {a.get('appointment_type', '?')}  —  {a.get('status', '?')}"
            for i, a in enumerate(my_appointments)
        ]

        if (
            st.session_state["selected_appointment_index"] is not None
            and st.session_state["selected_appointment_index"] < len(my_appointments)
        ):
            default_idx = st.session_state["selected_appointment_index"] + 1
        else:
            default_idx = 0

        selected_label = st.selectbox(
            "Choose an appointment to inspect:",
            options=["— Select an appointment —"] + selector_options,
            index=default_idx,
            key="patient_appt_selector",
        )

        if selected_label == "— Select an appointment —":
            st.session_state["selected_appointment_index"] = None
        else:
            st.session_state["selected_appointment_index"] = selector_options.index(selected_label)

        if st.session_state["selected_appointment_index"] is not None:
            appt = my_appointments[st.session_state["selected_appointment_index"]]
            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Doctor:** {appt.get('doctor_name', 'N/A')}")
                    st.markdown(f"**Date:** {appt.get('appointment_date', 'N/A')}  {appt.get('appointment_time', '')}")
                    st.markdown(f"**Appointment Type:** {appt.get('appointment_type', 'N/A')}")
                with col_b:
                    st.markdown(f"**Status:** {appt.get('status', 'N/A')}")
                    st.markdown(f"**Booked At:** {appt.get('submitted_timestamp', 'N/A')}")
                    doctor_note = appt.get("doctor_note", "").strip()
                    st.markdown(f"**Doctor Note:** {doctor_note if doctor_note else '(none)'}")
                st.markdown("**Symptom Summary:**")
                st.info(appt.get("symptom_summary", "No symptom notes provided."))

# ══════════════════════════════════════════════════════════════════════════════
# PATIENT — BOOK APPOINTMENT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "patient_book":
    st.title("Book Appointment")
    st.markdown(f"*Welcome, **{st.session_state['current_user_name']}***")
    st.divider()

    tab1, tab2 = st.tabs(["Book New Appointment", "Cancel an Appointment"])

    with tab1:
        col1, col2 = st.columns([3, 3])

        with col1:
            st.subheader("Appointment Details")

            form_selected_doctor = st.selectbox(
                "Select Doctor *",
                options=doctors,
                key="form_doctor_selector",
                format_func=lambda x: f"{x['name']} — {x['specialty']}",
            )
            form_appointment_type = st.selectbox(
                "Appointment Type *",
                options=["— Select appointment type —"] + APPOINTMENT_TYPES,
                key="form_appointment_type",
            )
            form_symptom_summary = st.text_area(
                "Describe your symptoms *",
                placeholder="e.g. Blurry vision on left side, seeing floaters...",
                height=120,
                key="form_symptom_summary",
            )

            available_slots = form_selected_doctor.get("available_slots", [])
            if available_slots:
                form_selected_slot = st.selectbox(
                    "Available Time Slot *",
                    options=available_slots,
                    key="form_slot_selector",
                    format_func=lambda x: x.replace("T", "  "),
                )
            else:
                st.warning("No available slots for this doctor.")
                form_selected_slot = None

            submit_col, note_col = st.columns([1, 2])
            with submit_col:
                form_submit_clicked = st.button("Book Appointment", key="form_book_btn", type="primary", use_container_width=True)
            with note_col:
                st.caption("Fields marked * are required. Status defaults to **Scheduled**.")

            if form_submit_clicked:
                validation_errors = []
                if form_appointment_type == "— Select appointment type —":
                    validation_errors.append("Appointment Type is required.")
                if not form_symptom_summary.strip():
                    validation_errors.append("Symptom summary is required.")
                elif len(form_symptom_summary.strip()) < 10:
                    validation_errors.append("Symptom summary is too short — please provide more detail.")
                if not form_selected_slot:
                    validation_errors.append("No available time slot to book.")

                if validation_errors:
                    for err in validation_errors:
                        st.warning(f"⚠️  {err}")
                else:
                    with st.spinner("Booking your appointment..."):
                        slot_date, slot_time = form_selected_slot.split("T")
                        new_appointment = {
                            "appointment_id":      f"appt-{str(uuid.uuid4())[:8]}",
                            "clinic_id":           CLINIC_ID,
                            "patient_name":        st.session_state["current_user_name"],
                            "patient_email":       st.session_state["current_user_email"],
                            "doctor_id":           form_selected_doctor["doctor_id"],
                            "doctor_name":         form_selected_doctor["name"],
                            "appointment_date":    slot_date,
                            "appointment_time":    slot_time,
                            "submitted_timestamp": datetime.now().isoformat(),
                            "appointment_type":    form_appointment_type,
                            "symptom_summary":     form_symptom_summary.strip(),
                            "status":              "Scheduled",
                            "doctor_note":         "",
                        }
                        all_appointments.append(new_appointment)

                        for doc in doctors:
                            if doc["doctor_id"] == form_selected_doctor["doctor_id"]:
                                if form_selected_slot in doc["available_slots"]:
                                    doc["available_slots"].remove(form_selected_slot)
                                break

                        with open(json_path_appointments, "w") as f:
                            json.dump(all_appointments, f, indent=2)
                        with open(json_path_doctors, "w") as f:
                            json.dump(doctors, f, indent=2)

                        st.session_state["selected_appointment_index"] = None
                        st.balloons()
                        time.sleep(8)
                        st.session_state["page"] = "patient_dashboard"
                        st.rerun()

        with col2:
            st.subheader("AI Assistant")
            col11, col22 = st.columns([3, 1])
            with col11:
                st.caption("Try asking: What slots are available today?")
            with col22:
                if st.button("Clear Messages", key="clear_messages_btn"):
                    st.session_state["messages"] = [{"role": "assistant", "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?"}]
                    st.rerun()

            with st.container(border=True, height=250):
                for message in st.session_state["messages"]:
                    with st.chat_message(message["role"]):
                        st.write(message["content"])

            user_input = st.chat_input("Ask a question....")
            if user_input:
                with st.spinner("Thinking..."):
                    st.session_state["messages"].append({"role": "user", "content": user_input})

                    user_lower = user_input.lower()
                    if "next appointment" in user_lower:
                        my_appts = [a for a in all_appointments if a.get("patient_email", "").lower() == st.session_state["current_user_email"].lower() and a.get("status") == "Scheduled"]
                        if my_appts:
                            next_appt = sorted(my_appts, key=lambda x: x.get("appointment_date", ""))[0]
                            ai_response = f"Your next appointment is on {next_appt['appointment_date']} at {next_appt['appointment_time']} with {next_appt['doctor_name']} for a {next_appt['appointment_type']}."
                        else:
                            ai_response = "You have no upcoming scheduled appointments. Use the form on the left to book one."
                    elif "available" in user_lower or "slot" in user_lower:
                        open_slots = []
                        for doc in doctors:
                            for slot in doc.get("available_slots", []):
                                open_slots.append(f"{doc['name']}: {slot.replace('T', ' at ')}")
                        ai_response = ("Available slots:\n" + "\n".join(open_slots)) if open_slots else "There are currently no available time slots."
                    elif "cancel" in user_lower:
                        ai_response = "To cancel an appointment:\n1. Click the 'Cancel an Appointment' tab above\n2. Your scheduled appointments will be listed\n3. Select the one you want to cancel and click Cancel"
                    elif "doctor" in user_lower:
                        available_doctors = [d["name"] + " (" + d["specialty"] + ")" for d in doctors if d.get("available_slots")]
                        ai_response = ("Doctors with open slots:\n" + "\n".join(available_doctors)) if available_doctors else "No doctors currently have available slots."
                    elif "prepare" in user_lower or "exam" in user_lower:
                        ai_response = "Exam preparation tips:\n- Bring your insurance card and photo ID\n- Avoid contact lenses 24 hours before a retinal or fundus exam\n- Arrange a ride if dilation drops will be used\n- Bring a list of current medications\n- Note any recent vision changes to share with your doctor"
                    else:
                        ai_response = "I can help with: checking available slots, your next appointment, cancellation steps, doctor availability, and exam preparation. What would you like to know?"

                    st.session_state["messages"].append({"role": "assistant", "content": ai_response})
                    time.sleep(2)
                    st.rerun()

    with tab2:
        st.markdown("### Cancel an Appointment")
        patient_email = st.session_state["current_user_email"]
        scheduled = [a for a in all_appointments if a.get("patient_email", "").lower() == patient_email.lower() and a.get("status") == "Scheduled"]

        if scheduled:
            st.dataframe(scheduled, use_container_width=True)
            appt_options = [f"{a['doctor_name']} — {a['appointment_date']} {a['appointment_time']} ({a['appointment_type']})" for a in scheduled]
            selected_appt_label = st.selectbox("Select appointment to cancel", options=appt_options, key="cancel_appt_selector")

            if st.button("Cancel Appointment", key="cancel_btn", type="primary", use_container_width=True):
                with st.spinner("Cancelling appointment..."):
                    idx = appt_options.index(selected_appt_label)
                    appt_to_cancel = scheduled[idx]
                    for appt in all_appointments:
                        if appt["appointment_id"] == appt_to_cancel["appointment_id"]:
                            appt["status"] = "Cancelled"
                            break
                    with open(json_path_appointments, "w") as f:
                        json.dump(all_appointments, f, indent=2)
                    st.success("Appointment cancelled successfully.")
                    time.sleep(3)
                    st.rerun()
        else:
            st.info("You have no scheduled appointments to cancel.")

# ══════════════════════════════════════════════════════════════════════════════
# DOCTOR — APPOINTMENT DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "doctor_dashboard":
    doctor_id = st.session_state["current_doctor_id"]
    my_schedule = [a for a in all_appointments if a.get("doctor_id") == doctor_id]

    st.title("Appointment Dashboard")
    st.markdown(f"*Welcome, **{st.session_state['current_user_name']}** — your patient roster today.*")
    st.divider()

    col1, col2 = st.columns([4, 2])

    with col1:
        st.markdown("## Patient Roster")
        if len(my_schedule) > 0:
            st.dataframe(my_schedule, use_container_width=True)
        else:
            st.warning("No appointments assigned to you yet.")

    with col2:
        scheduled_count = sum(1 for a in my_schedule if a.get("status") == "Scheduled")
        completed_count = sum(1 for a in my_schedule if a.get("status") == "Completed")
        no_show_count   = sum(1 for a in my_schedule if a.get("status") == "No-Show")

        st.metric("My Appointments", f"{len(my_schedule)}")
        st.metric("Scheduled",       f"{scheduled_count}")
        st.metric("Completed",       f"{completed_count}")
        st.metric("No-Show",         f"{no_show_count}")

    st.divider()

    if len(my_schedule) > 0:
        st.subheader("Update Appointment Status")

        selector_options = [
            f"#{i + 1}  —  {a.get('patient_name', '?')}  —  {a.get('appointment_date', '?')} {a.get('appointment_time', '')}  —  {a.get('status', '?')}"
            for i, a in enumerate(my_schedule)
        ]

        if (
            st.session_state["selected_appointment_index"] is not None
            and st.session_state["selected_appointment_index"] < len(my_schedule)
        ):
            default_idx = st.session_state["selected_appointment_index"] + 1
        else:
            default_idx = 0

        selected_label = st.selectbox(
            "Choose an appointment to update:",
            options=["— Select an appointment —"] + selector_options,
            index=default_idx,
            key="doctor_appt_selector",
        )

        if selected_label == "— Select an appointment —":
            st.session_state["selected_appointment_index"] = None
        else:
            st.session_state["selected_appointment_index"] = selector_options.index(selected_label)

        if st.session_state["selected_appointment_index"] is not None:
            idx  = st.session_state["selected_appointment_index"]
            appt = my_schedule[idx]

            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Patient Name:** {appt.get('patient_name', 'N/A')}")
                    st.markdown(f"**Patient Email:** {appt.get('patient_email', 'N/A')}")
                    st.markdown(f"**Date & Time:** {appt.get('appointment_date', 'N/A')}  {appt.get('appointment_time', '')}")
                with col_b:
                    st.markdown(f"**Appointment Type:** {appt.get('appointment_type', 'N/A')}")
                    st.markdown(f"**Current Status:** {appt.get('status', 'N/A')}")
                    st.markdown(f"**Booked At:** {appt.get('submitted_timestamp', 'N/A')}")

                st.markdown("**Symptom Summary:**")
                st.info(appt.get("symptom_summary", "No symptom notes provided."))
                st.divider()

                col_s1, col_s2 = st.columns([2, 3])
                with col_s1:
                    status_options = ["Scheduled", "Completed", "No-Show", "Cancelled"]
                    current_status = appt.get("status", "Scheduled")
                    new_status = st.selectbox(
                        "Update Status",
                        options=status_options,
                        index=status_options.index(current_status) if current_status in status_options else 0,
                        key="doctor_status_selector",
                    )
                    new_note = st.text_input("Doctor Note", value=appt.get("doctor_note", ""), key="doctor_note_input")
                with col_s2:
                    st.write("")
                    st.write("")
                    if st.button("Save Changes", key="doctor_save_btn", type="primary", use_container_width=True):
                        with st.spinner("Saving..."):
                            appt_id = appt["appointment_id"]
                            for a in all_appointments:
                                if a["appointment_id"] == appt_id:
                                    a["status"]      = new_status
                                    a["doctor_note"] = new_note
                                    break
                            with open(json_path_appointments, "w") as f:
                                json.dump(all_appointments, f, indent=2)
                            st.success("Appointment updated successfully.")
                            time.sleep(2)
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# DOCTOR — MANAGE TIME SLOTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "doctor_slots":
    doctor_id = st.session_state["current_doctor_id"]
    current_doctor = next((d for d in doctors if d["doctor_id"] == doctor_id), None)

    st.title("Manage Time Slots")
    st.markdown(f"*Manage available appointment slots for **{st.session_state['current_user_name']}**.*")
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
                for doc in doctors:
                    if doc["doctor_id"] == doctor_id:
                        if new_slot not in doc["available_slots"]:
                            doc["available_slots"].append(new_slot)
                            with open(json_path_doctors, "w") as f:
                                json.dump(doctors, f, indent=2)
                            st.success(f"Slot added: {slot_date} at {slot_hour}")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.warning("This slot already exists.")
                        break

        with col2:
            st.subheader("Your Current Slots")
            if current_doctor and current_doctor.get("available_slots"):
                for s in current_doctor["available_slots"]:
                    st.markdown(f"- {s.replace('T', '  ')}")
            else:
                st.info("You have no available slots at the moment.")

    with tab2:
        col1, col2 = st.columns([3, 3])

        with col1:
            st.subheader("Remove Time Slot")
            if current_doctor and current_doctor.get("available_slots"):
                slot_to_remove = st.selectbox(
                    "Select Slot to Remove",
                    options=current_doctor["available_slots"],
                    key="remove_slot_selector",
                    format_func=lambda x: x.replace("T", "  "),
                )
                if st.button("Remove Slot", key="remove_slot_btn", type="primary", use_container_width=True):
                    with st.spinner("Removing slot..."):
                        for doc in doctors:
                            if doc["doctor_id"] == doctor_id:
                                doc["available_slots"].remove(slot_to_remove)
                                break
                        with open(json_path_doctors, "w") as f:
                            json.dump(doctors, f, indent=2)
                        st.success(f"Slot removed: {slot_to_remove.replace('T', ' at ')}")
                        time.sleep(2)
                        st.rerun()
            else:
                st.info("No slots available to remove.")
        with col2:
            st.write("")
