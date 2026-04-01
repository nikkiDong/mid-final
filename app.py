import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import uuid
import time

st.set_page_config("ClearVision Clinic", layout="wide", initial_sidebar_state="expanded")

doctors = [
    {"doctor_id": "doc_01", "name": "Dr. Sarah Chen", "specialty": "Retinal Disease", "available_slots": ["2025-08-01T09:00", "2025-08-01T10:30"]},
    {"doctor_id": "doc_02", "name": "Dr. James Park", "specialty": "Glaucoma", "available_slots": ["2025-08-01T11:00", "2025-08-02T09:00"]},
    {"doctor_id": "doc_03", "name": "Dr. Emily Torres", "specialty": "General Ophthalmology", "available_slots": ["2025-08-01T14:00", "2025-08-02T10:30"]},
]

patients = [
    {"patient_id": "pat_01", "name": "James Lee", "email": "james@email.com", "symptom_notes": "Blurry vision"},
    {"patient_id": "pat_02", "name": "Maria Gomez", "email": "maria@email.com", "symptom_notes": "Eye pain and floaters"},
]

if "page" not in st.session_state:
    st.session_state["page"] = "home"

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hi! I'm the ClearVision Clinic assistant. How can I help you today?"
        }
    ]

with st.sidebar:
    st.markdown("## ClearVision Clinic")
    if st.button("Home", key="home_btn", type="primary", use_container_width=True):
        st.session_state["page"] = "home"
        st.rerun()

    if st.button("Appointments", key="appointments_btn", type="primary", use_container_width=True):
        st.session_state["page"] = "appointments"
        st.rerun()

json_path_doctors = Path("doctors.json")
if json_path_doctors.exists():
    with open(json_path_doctors, "r") as f:
        doctors = json.load(f)

json_path_patients = Path("patients.json")
if json_path_patients.exists():
    with open(json_path_patients, "r") as f:
        patients = json.load(f)

json_path_appointments = Path("appointments.json")
if json_path_appointments.exists():
    with open(json_path_appointments, "r") as f:
        appointments = json.load(f)
else:
    appointments = []

if st.session_state["page"] == "home":
    col1, col2 = st.columns([4, 2])
    with col1:
        selected_category = st.radio("Select a Category", ["Appointments", "Doctors", "Patients"], horizontal=True)

        if selected_category == "Doctors":
            st.markdown("## Doctors")
            if len(doctors) > 0:
                st.dataframe(doctors)
            else:
                st.warning("No doctors found")
        elif selected_category == "Patients":
            st.markdown("## Patients")
            if len(patients) > 0:
                st.dataframe(patients)
            else:
                st.warning("No patients found")
        else:
            st.markdown("## Appointments")
            if len(appointments) > 0:
                st.dataframe(appointments)
            else:
                st.warning("No appointments recorded yet")
    with col2:
        if selected_category == "Doctors":
            st.metric("Total Doctors", f"{len(doctors)}")
        elif selected_category == "Patients":
            st.metric("Total Patients", f"{len(patients)}")
        else:
            st.metric("Total Appointments", f"{len(appointments)}")

elif st.session_state["page"] == "appointments":
    tab1, tab2 = st.tabs(["Book New Appointment", "Cancel an Appointment"])

    with tab1:
        col1, col2 = st.columns([3, 3])

        with col1:
            selected_doctor = st.selectbox("Doctor", options=doctors, key="doctor_selector",
                                           format_func=lambda x: f"{x['name']} — {x['specialty']}")

            patient_name = st.text_input("Patient Name")
            patient_email = st.text_input("Patient Email")

            exam_types = ["Routine Vision Check", "Glaucoma Screening", "Fundus Exam", "Cataract Evaluation", "Retinal Exam"]
            exam_type = st.selectbox("Exam Type", options=exam_types, key="exam_type_selector")

            symptom_notes = st.text_area("Describe your symptoms")

            available_slots = selected_doctor.get("available_slots", [])
            if available_slots:
                selected_slot = st.selectbox("Available Time Slot", options=available_slots, key="slot_selector")
            else:
                st.warning("No available slots for this doctor")
                selected_slot = None

            if st.button("Book Appointment", key="book_btn", type="primary", use_container_width=True):
                if not patient_name or not patient_email or not selected_slot:
                    st.error("Please fill in all required fields and select a time slot.")
                else:
                    with st.spinner("Booking your appointment..."):
                        existing_patient = next((p for p in patients if p["email"] == patient_email), None)
                        if not existing_patient:
                            patients.append({
                                "patient_id": f"pat_{str(uuid.uuid4())[:8]}",
                                "name": patient_name,
                                "email": patient_email,
                                "symptom_notes": symptom_notes
                            })
                            with open(json_path_patients, "w") as f:
                                json.dump(patients, f)

                        appointments.append({
                            "id": str(uuid.uuid4()),
                            "patient_name": patient_name,
                            "patient_email": patient_email,
                            "doctor_id": selected_doctor["doctor_id"],
                            "doctor_name": selected_doctor["name"],
                            "datetime": selected_slot,
                            "exam_type": exam_type,
                            "status": "Scheduled",
                            "symptom_notes": symptom_notes
                        })

                        for doc in doctors:
                            if doc["doctor_id"] == selected_doctor["doctor_id"]:
                                if selected_slot in doc["available_slots"]:
                                    doc["available_slots"].remove(selected_slot)
                                break

                        with open(json_path_appointments, "w") as f:
                            json.dump(appointments, f)

                        with open(json_path_doctors, "w") as f:
                            json.dump(doctors, f)

                        st.balloons()
                        time.sleep(8)
                        st.session_state["page"] = "home"
                        st.rerun()

        with col2:
            st.subheader("AI Assistant")
            col11, col22 = st.columns([3, 1])
            with col11:
                st.caption("Try asking: What slots are available today?")
            with col22:
                if st.button("Clear Messages"):
                    st.session_state["messages"] = [{"role": "assistant", "content": "Hi! I'm the ClearVision Clinic assistant. How can I help you today?"}]
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
                            "content": user_input
                        }
                    )

                    user_lower = user_input.lower()
                    if "next appointment" in user_lower:
                        ai_response = "To check your next appointment, go to the Home page and select the Appointments category to view all scheduled appointments."
                    elif "available" in user_lower or "slot" in user_lower:
                        open_slots = []
                        for doc in doctors:
                            for slot in doc.get("available_slots", []):
                                open_slots.append(f"{doc['name']}: {slot}")
                        if open_slots:
                            ai_response = "Available slots:\n" + "\n".join(open_slots)
                        else:
                            ai_response = "There are currently no available time slots."
                    elif "cancel" in user_lower:
                        ai_response = "To cancel an appointment:\n1. Go to the Appointments page\n2. Select the Cancel an Appointment tab\n3. Enter your email to find your appointments\n4. Select the appointment and click Cancel"
                    elif "doctor" in user_lower:
                        available_doctors = [d["name"] + " (" + d["specialty"] + ")" for d in doctors if d.get("available_slots")]
                        if available_doctors:
                            ai_response = "Doctors with open slots:\n" + "\n".join(available_doctors)
                        else:
                            ai_response = "No doctors currently have available slots."
                    elif "prepare" in user_lower or "exam" in user_lower:
                        ai_response = "Exam preparation tips:\n- Bring your insurance card and photo ID\n- Avoid contact lenses 24 hours before a retinal exam\n- Arrange a ride if dilation drops will be used\n- Bring a list of current medications\n- Note any recent vision changes to share with your doctor"
                    else:
                        ai_response = "I can help you with: checking available slots, booking appointments, cancellation steps, doctor availability, and exam preparation. What would you like to know?"

                    st.session_state["messages"].append(
                        {
                            "role": "assistant",
                            "content": ai_response
                        }
                    )
                    time.sleep(2)
                    st.rerun()

    with tab2:
        st.markdown("### Cancel an Appointment")
        search_email = st.text_input("Enter your email to find your appointments")

        if search_email:
            patient_appointments = [a for a in appointments if a.get("patient_email", "").lower() == search_email.lower()]
            if patient_appointments:
                st.dataframe(patient_appointments)
                scheduled = [a for a in patient_appointments if a["status"] == "Scheduled"]
                appt_options = [f"{a['doctor_name']} — {a['datetime']} ({a['exam_type']})" for a in scheduled]
                if appt_options:
                    selected_appt_label = st.selectbox("Select appointment to cancel", options=appt_options)
                    if st.button("Cancel Appointment", key="cancel_btn", type="primary", use_container_width=True):
                        with st.spinner("Cancelling appointment..."):
                            idx = appt_options.index(selected_appt_label)
                            appt_to_cancel = scheduled[idx]

                            for appt in appointments:
                                if appt["id"] == appt_to_cancel["id"]:
                                    appt["status"] = "Cancelled"
                                    break

                            with open(json_path_appointments, "w") as f:
                                json.dump(appointments, f)

                            st.success("Appointment cancelled successfully.")
                            time.sleep(3)
                            st.rerun()
                else:
                    st.info("No scheduled appointments found for this email.")
            else:
                st.warning("No appointments found for this email.")
