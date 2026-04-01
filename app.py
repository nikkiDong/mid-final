import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import uuid
import time

st.set_page_config("ClearVision Clinic", layout="wide", initial_sidebar_state="expanded")

CLINIC_ID = "ClearVision-01"
EXAM_TYPES = [
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
if "role" not in st.session_state:
    st.session_state["role"] = "Patient"

if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"

if "selected_appointment_index" not in st.session_state:
    st.session_state["selected_appointment_index"] = None

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hi! I am the ClearVision Clinic assistant. How can I help you today?",
        }
    ]

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ClearVision Clinic")
    st.markdown(f"**Clinic ID:** `{CLINIC_ID}`")
    st.divider()

    selected_role = st.radio("Select Role", ["Patient", "Doctor"], key="role_selector", horizontal=True)
    if selected_role != st.session_state["role"]:
        st.session_state["role"] = selected_role
        st.session_state["page"] = "dashboard"
        st.session_state["selected_appointment_index"] = None
        st.rerun()

    st.divider()

    if st.session_state["role"] == "Patient":
        if st.button("My Appointments", key="nav_dashboard_btn", type="primary", use_container_width=True):
            st.session_state["page"] = "dashboard"
            st.rerun()
        if st.button("Book Appointment", key="nav_book_btn", type="primary", use_container_width=True):
            st.session_state["page"] = "book"
            st.rerun()
    else:
        if st.button("Appointment Dashboard", key="nav_dashboard_btn", type="primary", use_container_width=True):
            st.session_state["page"] = "dashboard"
            st.rerun()
        if st.button("Manage Time Slots", key="nav_slots_btn", type="primary", use_container_width=True):
            st.session_state["page"] = "slots"
            st.rerun()

# ─── JSON LOADING ──────────────────────────────────────────────────────────────
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

# ══════════════════════════════════════════════════════════════════════════════
# PATIENT — MY APPOINTMENTS (dashboard)
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["role"] == "Patient" and st.session_state["page"] == "dashboard":
    st.title("My Appointments")
    st.markdown("*Enter your email below to view your scheduled appointments.*")
    st.divider()

    col1, col2 = st.columns([4, 2])

    with col1:
        patient_email_input = st.text_input("Your Email", placeholder="yourname@email.com", key="my_appt_email")
        if patient_email_input:
            my_appointments = [
                a for a in all_appointments
                if a.get("patient_email", "").lower() == patient_email_input.lower()
            ]
            if len(my_appointments) > 0:
                st.markdown("## Your Appointments")
                st.dataframe(my_appointments, use_container_width=True)
            else:
                st.warning("No appointments found for this email.")
        else:
            st.info("Enter your email to see your appointments.")

    with col2:
        if patient_email_input:
            my_appointments = [
                a for a in all_appointments
                if a.get("patient_email", "").lower() == patient_email_input.lower()
            ]
            scheduled_count = sum(1 for a in my_appointments if a.get("status") == "Scheduled")
            completed_count = sum(1 for a in my_appointments if a.get("status") == "Completed")
            st.metric("My Appointments", f"{len(my_appointments)}")
            st.metric("Scheduled",       f"{scheduled_count}")
            st.metric("Completed",       f"{completed_count}")

    st.divider()

    if patient_email_input:
        my_appointments = [
            a for a in all_appointments
            if a.get("patient_email", "").lower() == patient_email_input.lower()
        ]
        if len(my_appointments) > 0:
            st.subheader("Appointment Details")

            selector_options = [
                f"#{i + 1}  —  {a.get('appointment_date', '?')}  —  {a.get('appointment_type', '?')}  —  {a.get('status', '?')}"
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
                        st.markdown(f"**Appointment Date:** {appt.get('appointment_date', 'N/A')}")
                        st.markdown(f"**Appointment Time:** {appt.get('appointment_time', 'N/A')}")
                        st.markdown(f"**Appointment Type:** {appt.get('appointment_type', 'N/A')}")
                    with col_b:
                        st.markdown(f"**Status:** {appt.get('status', 'N/A')}")
                        st.markdown(f"**Booked At:** {appt.get('submitted_timestamp', 'N/A')}")
                        doctor_note = appt.get("doctor_note", "").strip()
                        st.markdown(f"**Doctor Note:** {doctor_note if doctor_note else '(none)'}")
                    st.markdown("**Symptom Summary:**")
                    st.info(appt.get("symptom_summary", "No symptom summary provided."))

# ══════════════════════════════════════════════════════════════════════════════
# PATIENT — BOOK APPOINTMENT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["role"] == "Patient" and st.session_state["page"] == "book":
    st.title("Book Appointment")
    st.markdown("*ClearVision Clinic — Schedule a new appointment below.*")
    st.divider()

    tab1, tab2 = st.tabs(["Book New Appointment", "Cancel an Appointment"])

    with tab1:
        col1, col2 = st.columns([3, 3])

        with col1:
            st.subheader("Patient Information")

            form_patient_name = st.text_input("Patient Name *", placeholder="Full name", key="form_patient_name")
            form_patient_email = st.text_input("Patient Email *", placeholder="yourname@email.com", key="form_patient_email")
            form_selected_doctor = st.selectbox(
                "Select Doctor *",
                options=doctors,
                key="form_doctor_selector",
                format_func=lambda x: f"{x['name']} — {x['specialty']}",
            )
            form_exam_type = st.selectbox(
                "Exam Type *",
                options=["— Select exam type —"] + EXAM_TYPES,
                key="form_exam_type",
            )
            form_symptom_notes = st.text_area(
                "Describe your symptoms *",
                placeholder="e.g. Blurry vision on left side, seeing floaters...",
                height=120,
                key="form_symptom_notes",
            )

            available_slots = form_selected_doctor.get("available_slots", [])
            if available_slots:
                form_selected_slot = st.selectbox("Available Time Slot *", options=available_slots, key="form_slot_selector")
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
                if not form_patient_name.strip():
                    validation_errors.append("Patient Name is required.")
                if not form_patient_email.strip():
                    validation_errors.append("Patient Email is required.")
                elif "@" not in form_patient_email or "." not in form_patient_email.split("@")[-1]:
                    validation_errors.append("Please enter a valid email address.")
                if form_exam_type == "— Select exam type —":
                    validation_errors.append("Exam Type is required.")
                if not form_symptom_notes.strip():
                    validation_errors.append("Symptom notes are required.")
                elif len(form_symptom_notes.strip()) < 10:
                    validation_errors.append("Symptom notes are too short — please provide more detail.")
                if not form_selected_slot:
                    validation_errors.append("No available time slot to book.")

                if validation_errors:
                    for err in validation_errors:
                        st.warning(f"⚠️  {err}")
                else:
                    with st.spinner("Booking your appointment..."):
                        slot_date_part = form_selected_slot.split("T")[0] if "T" in form_selected_slot else form_selected_slot
                        slot_time_part = form_selected_slot.split("T")[1] if "T" in form_selected_slot else ""
                        new_appointment = {
                            "appointment_id":      str(uuid.uuid4()),
                            "clinic_id":           CLINIC_ID,
                            "patient_name":        form_patient_name.strip(),
                            "patient_email":       form_patient_email.strip(),
                            "doctor_id":           form_selected_doctor["doctor_id"],
                            "doctor_name":         form_selected_doctor["name"],
                            "appointment_date":    slot_date_part,
                            "appointment_time":    slot_time_part,
                            "submitted_timestamp": datetime.now().isoformat(),
                            "appointment_type":    form_exam_type,
                            "symptom_summary":     form_symptom_notes.strip(),
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

                        st.session_state["selected_appointment_index"] = len(all_appointments) - 1
                        st.balloons()
                        time.sleep(8)
                        st.session_state["page"] = "dashboard"
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
                        ai_response = "To check your next appointment, go to My Appointments in the sidebar and enter your email to view all your scheduled visits."
                    elif "available" in user_lower or "slot" in user_lower:
                        open_slots = []
                        for doc in doctors:
                            for slot in doc.get("available_slots", []):
                                open_slots.append(f"{doc['name']}: {slot}")
                        ai_response = ("Available slots:\n" + "\n".join(open_slots)) if open_slots else "There are currently no available time slots."
                    elif "cancel" in user_lower:
                        ai_response = "To cancel an appointment:\n1. Click the 'Cancel an Appointment' tab on this page\n2. Enter your email to find your appointments\n3. Select the appointment and click Cancel"
                    elif "doctor" in user_lower:
                        available_doctors = [d["name"] + " (" + d["specialty"] + ")" for d in doctors if d.get("available_slots")]
                        ai_response = ("Doctors with open slots:\n" + "\n".join(available_doctors)) if available_doctors else "No doctors currently have available slots."
                    elif "prepare" in user_lower or "exam" in user_lower:
                        ai_response = "Exam preparation tips:\n- Bring your insurance card and photo ID\n- Avoid contact lenses 24 hours before a retinal or fundus exam\n- Arrange a ride if dilation drops will be used\n- Bring a list of current medications\n- Note any recent vision changes to share with your doctor"
                    else:
                        ai_response = "I can help with: checking available slots, booking appointments, cancellation steps, doctor availability, and exam preparation. What would you like to know?"

                    st.session_state["messages"].append({"role": "assistant", "content": ai_response})
                    time.sleep(2)
                    st.rerun()

    with tab2:
        st.markdown("### Cancel an Appointment")
        search_email = st.text_input("Enter your email to find your appointments", key="cancel_search_email")

        if search_email:
            patient_appointments = [a for a in all_appointments if a.get("patient_email", "").lower() == search_email.lower()]
            if patient_appointments:
                st.dataframe(patient_appointments, use_container_width=True)
                scheduled = [a for a in patient_appointments if a["status"] == "Scheduled"]
                appt_options = [f"{a['doctor_name']} — {a.get('appointment_date', '?')} {a.get('appointment_time', '')} ({a.get('appointment_type', '?')})" for a in scheduled]
                if appt_options:
                    selected_appt_label = st.selectbox("Select appointment to cancel", options=appt_options, key="cancel_appt_selector")
                    if st.button("Cancel Appointment", key="cancel_btn", type="primary", use_container_width=True):
                        with st.spinner("Cancelling appointment..."):
                            idx = appt_options.index(selected_appt_label)
                            appt_to_cancel = scheduled[idx]
                            for appt in all_appointments:
                                if appt.get("appointment_id") == appt_to_cancel.get("appointment_id"):
                                    appt["status"] = "Cancelled"
                                    break
                            with open(json_path_appointments, "w") as f:
                                json.dump(all_appointments, f, indent=2)
                            st.success("Appointment cancelled successfully.")
                            time.sleep(3)
                            st.rerun()
                else:
                    st.info("No scheduled appointments found for this email.")
            else:
                st.warning("No appointments found for this email.")

# ══════════════════════════════════════════════════════════════════════════════
# DOCTOR — APPOINTMENT DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["role"] == "Doctor" and st.session_state["page"] == "dashboard":
    st.title("Appointment Dashboard")
    st.markdown("*ClearVision Clinic — View and manage all patient appointments.*")
    st.divider()

    col1, col2 = st.columns([4, 2])

    with col1:
        st.markdown("## All Appointments")
        if len(all_appointments) > 0:
            st.dataframe(all_appointments, use_container_width=True)
        else:
            st.warning("No appointments have been booked yet.")

    with col2:
        scheduled_count = sum(1 for a in all_appointments if a.get("status") == "Scheduled")
        completed_count = sum(1 for a in all_appointments if a.get("status") == "Completed")
        no_show_count   = sum(1 for a in all_appointments if a.get("status") == "No-Show")
        cancelled_count = sum(1 for a in all_appointments if a.get("status") == "Cancelled")

        st.metric("Total Appointments", f"{len(all_appointments)}")
        st.metric("Scheduled",          f"{scheduled_count}")
        st.metric("Completed",          f"{completed_count}")
        st.metric("No-Show / Cancelled",f"{no_show_count + cancelled_count}")

    st.divider()

    if len(all_appointments) > 0:
        st.subheader("Update Appointment Status")

        selector_options = [
            f"#{i + 1}  —  {a.get('patient_email', '?')}  —  {a.get('appointment_date', '?')}  —  {a.get('appointment_type', '?')}"
            for i, a in enumerate(all_appointments)
        ]

        if (
            st.session_state["selected_appointment_index"] is not None
            and st.session_state["selected_appointment_index"] < len(all_appointments)
        ):
            default_idx = st.session_state["selected_appointment_index"] + 1
        else:
            default_idx = 0

        selected_label = st.selectbox(
            "Choose an appointment to inspect:",
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
            appt = all_appointments[idx]

            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Patient Name:** {appt.get('patient_name', 'N/A')}")
                    st.markdown(f"**Patient Email:** {appt.get('patient_email', 'N/A')}")
                    st.markdown(f"**Appointment Date:** {appt.get('appointment_date', 'N/A')}")
                    st.markdown(f"**Appointment Time:** {appt.get('appointment_time', 'N/A')}")
                    st.markdown(f"**Appointment Type:** {appt.get('appointment_type', 'N/A')}")
                with col_b:
                    st.markdown(f"**Doctor:** {appt.get('doctor_name', 'N/A')}")
                    st.markdown(f"**Current Status:** {appt.get('status', 'N/A')}")
                    st.markdown(f"**Booked At:** {appt.get('submitted_timestamp', 'N/A')}")

                st.markdown("**Symptom Summary:**")
                st.info(appt.get("symptom_summary", "No symptom summary provided."))

                st.divider()
                col_s1, col_s2 = st.columns([2, 3])
                with col_s1:
                    new_status = st.selectbox(
                        "Update Status",
                        options=["Scheduled", "Completed", "No-Show", "Cancelled"],
                        index=["Scheduled", "Completed", "No-Show", "Cancelled"].index(appt.get("status", "Scheduled")),
                        key="doctor_status_selector",
                    )
                    new_note = st.text_input("Doctor Note", value=appt.get("doctor_note", ""), key="doctor_note_input")
                with col_s2:
                    st.write("")
                    st.write("")
                    if st.button("Save Changes", key="doctor_save_btn", type="primary", use_container_width=True):
                        with st.spinner("Saving..."):
                            all_appointments[idx]["status"]      = new_status
                            all_appointments[idx]["doctor_note"] = new_note
                            with open(json_path_appointments, "w") as f:
                                json.dump(all_appointments, f, indent=2)
                            st.success("Appointment updated successfully.")
                            time.sleep(2)
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# DOCTOR — MANAGE TIME SLOTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["role"] == "Doctor" and st.session_state["page"] == "slots":
    st.title("Manage Time Slots")
    st.markdown("*ClearVision Clinic — Add or remove available appointment slots.*")
    st.divider()

    tab1, tab2 = st.tabs(["Add New Slot", "Remove a Slot"])

    with tab1:
        col1, col2 = st.columns([3, 3])

        with col1:
            st.subheader("Add Time Slot")
            slot_doctor = st.selectbox(
                "Select Doctor",
                options=doctors,
                key="slot_doctor_selector",
                format_func=lambda x: f"{x['name']} — {x['specialty']}",
            )
            slot_date = st.date_input("Date", key="slot_date_input")
            slot_hour = st.selectbox("Hour", options=[f"{h:02d}:00" for h in range(8, 18)], key="slot_hour_input")

            if st.button("Add Slot", key="add_slot_btn", type="primary", use_container_width=True):
                new_slot = f"{slot_date}T{slot_hour}"
                for doc in doctors:
                    if doc["doctor_id"] == slot_doctor["doctor_id"]:
                        if new_slot not in doc["available_slots"]:
                            doc["available_slots"].append(new_slot)
                            with open(json_path_doctors, "w") as f:
                                json.dump(doctors, f, indent=2)
                            st.success(f"Slot {new_slot} added for {slot_doctor['name']}.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.warning("This slot already exists.")
                        break

        with col2:
            st.subheader("Current Slots")
            for doc in doctors:
                if doc.get("available_slots"):
                    st.markdown(f"**{doc['name']}**")
                    for s in doc["available_slots"]:
                        st.markdown(f"- {s}")
                else:
                    st.markdown(f"**{doc['name']}** — no slots")

    with tab2:
        col1, col2 = st.columns([3, 3])

        with col1:
            st.subheader("Remove Time Slot")
            remove_doctor = st.selectbox(
                "Select Doctor",
                options=doctors,
                key="remove_doctor_selector",
                format_func=lambda x: f"{x['name']} — {x['specialty']}",
            )
            remove_slots = remove_doctor.get("available_slots", [])
            if remove_slots:
                slot_to_remove = st.selectbox("Select Slot to Remove", options=remove_slots, key="remove_slot_selector")
                if st.button("Remove Slot", key="remove_slot_btn", type="primary", use_container_width=True):
                    with st.spinner("Removing slot..."):
                        for doc in doctors:
                            if doc["doctor_id"] == remove_doctor["doctor_id"]:
                                doc["available_slots"].remove(slot_to_remove)
                                break
                        with open(json_path_doctors, "w") as f:
                            json.dump(doctors, f, indent=2)
                        st.success(f"Slot {slot_to_remove} removed.")
                        time.sleep(2)
                        st.rerun()
            else:
                st.info("No slots available to remove for this doctor.")
        with col2:
            st.write("")
