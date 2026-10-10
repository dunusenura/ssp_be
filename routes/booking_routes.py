from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from bson import ObjectId
import re
import database as db_module

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/api/apply-job', methods=['POST'])
def apply_job():
    try:
        data = request.json or {}
        worker_email = data.get('worker_email')
        worker_name = data.get('worker_name', 'Worker')
        job_id = data.get('job_id')

        job = None
        if job_id:
            try:
                job = db_module.jobs_collection.find_one({"_id": ObjectId(job_id)})
            except Exception:
                job = None

        client_email = data.get('client_email') or (job.get('posted_by') if job else 'client@workpub.lk')
        client_info = db_module.users_collection.find_one({"email": client_email}) if client_email else None
        client_name = data.get('client_name') or (client_info.get('name') if client_info else 'Client')

        existing = db_module.bookings_collection.find_one({
            "worker_email": worker_email,
            "$or": [
                {"job_id": str(job_id) if job_id else ""},
                {"title": data.get('title', '')}
            ]
        }) if (job_id or data.get('title')) else None

        if existing:
            return jsonify({"message": "You have already applied for this job!", "booking_id": str(existing['_id'])}), 200

        booking_entry = {
            "job_id": str(job_id) if job_id else None,
            "client_email": client_email,
            "client_name": client_name,
            "worker_email": worker_email,
            "worker_name": worker_name,
            "service_type": data.get('service_type') or (job.get('category') if job else 'General Task'),
            "title": data.get('title') or (job.get('title') if job else 'Task'),
            "location": data.get('location') or (job.get('location') if job else 'Gampaha'),
            "budget": data.get('budget') or (job.get('budget') if job else 0),
            "status": "pending",
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        result = db_module.bookings_collection.insert_one(booking_entry)

        db_module.add_notification(
            user_identifier=worker_email,
            title="Job Application Submitted",
            message=f"You successfully applied for '{booking_entry['title']}' ({booking_entry['service_type']}).",
            notif_type="job_application",
            link="/jobs"
        )

        if client_email:
            db_module.add_notification(
                user_identifier=client_email,
                title="New Job Applicant",
                message=f"{worker_name} applied for your job listing '{booking_entry['title']}'.",
                notif_type="new_applicant",
                link="/my-bookings"
            )

        return jsonify({
            "message": "Job application submitted successfully!",
            "booking_id": str(result.inserted_id)
        }), 201

    except Exception as e:
        print(f"Apply Job Error: {e}")
        return jsonify({"error": str(e)}), 500

@booking_bp.route('/api/create-booking', methods=['POST'])
@booking_bp.route('/api/bookings', methods=['POST'])
@booking_bp.route('/api/book_worker', methods=['POST'])
@booking_bp.route('/api/book-service', methods=['POST'])
def create_booking():
    try:
        data = request.json or {}

        client_email = data.get('client_email') or data.get('customer_email') or data.get('seeker_email')
        client_name = data.get('client_name') or data.get('customer_name') or data.get('seeker_name')
        if not client_name and client_email:
            user_doc = db_module.users_collection.find_one({"email": client_email})
            if user_doc:
                client_name = user_doc.get('name')

        worker_email = data.get('worker_email')
        worker_id = data.get('worker_id')
        worker_name = data.get('worker_name')

        if not worker_email and worker_id:
            try:
                worker_doc = db_module.users_collection.find_one({"_id": ObjectId(worker_id)})
                if worker_doc:
                    worker_email = worker_doc.get('email')
                    worker_name = worker_doc.get('name')
            except Exception:
                pass

        if not worker_name and worker_email:
            worker_doc = db_module.users_collection.find_one({"email": worker_email})
            if worker_doc:
                worker_name = worker_doc.get('name')

        service_type = data.get('service_type') or data.get('category') or data.get('service') or "General Service"
        title = data.get('title') or f"{service_type} Booking"
        booking_date = data.get('booking_date') or data.get('date') or datetime.now().strftime("%Y-%m-%d")

        booking_entry = {
            "client_email": client_email,
            "client_name": client_name or "Customer",
            "worker_email": worker_email,
            "worker_name": worker_name or "Assigned Specialist",
            "service_type": service_type,
            "title": title,
            "status": "pending",
            "booking_date": booking_date,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        result = db_module.bookings_collection.insert_one(booking_entry)

        if worker_email:
            db_module.add_notification(
                user_identifier=worker_email,
                title="New Booking Request Received",
                message=f"You have a new booking request from {booking_entry['client_name']} for '{service_type}' on {booking_date}.",
                notif_type="booking_request",
                link="/my-bookings"
            )

        if client_email:
            db_module.add_notification(
                user_identifier=client_email,
                title="Booking Request Placed",
                message=f"Your booking request for {booking_entry['worker_name']} ({service_type}) on {booking_date} was successfully submitted.",
                notif_type="booking_placed",
                link="/my-bookings"
            )

        return jsonify({
            "message": "Booking request sent successfully!",
            "booking_id": str(result.inserted_id),
            "booking": {
                "_id": str(result.inserted_id),
                "client_email": booking_entry["client_email"],
                "worker_email": booking_entry["worker_email"],
                "status": "pending",
                "booking_date": booking_entry["booking_date"]
            }
        }), 201

    except Exception as e:
        print(f"Booking Error: {e}")
        return jsonify({"error": str(e)}), 500

@booking_bp.route('/api/my-bookings', methods=['GET'])
def get_my_bookings():
    try:
        email = request.args.get('email') or ''
        role = request.args.get('role')

        if role == 'worker':
            query = {"$or": [
                {"worker_email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}},
                {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
            ]}
        else:
            query = {"$or": [
                {"client_email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}},
                {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
            ]}

        bookings = list(db_module.bookings_collection.find(query).sort("created_at", -1))

        for b in bookings:
            b['_id'] = str(b['_id'])

            client_info = None
            c_email = b.get('client_email')
            c_name = b.get('client_name')
            if c_email:
                client_info = db_module.users_collection.find_one({"email": {"$regex": f"^{re.escape(c_email)}$", "$options": "i"}})
            if not client_info and c_name:
                client_info = db_module.users_collection.find_one({"name": {"$regex": f"^{re.escape(c_name)}$", "$options": "i"}})

            if client_info:
                b['client_phone'] = client_info.get('phone') or client_info.get('mobile') or client_info.get('contact') or client_info.get('whatsapp') or b.get('client_phone') or 'Not Provided'
                b['client_name'] = b.get('client_name') or client_info.get('name', 'Client')
            else:
                b['client_phone'] = b.get('client_phone') or 'Not Provided'

            worker_info = None
            w_email = b.get('worker_email')
            w_name = b.get('worker_name')

            if w_email:
                worker_info = db_module.users_collection.find_one({"email": {"$regex": f"^{re.escape(w_email)}$", "$options": "i"}})
            if not worker_info and w_name:
                worker_info = db_module.users_collection.find_one({"name": {"$regex": f"^{re.escape(w_name)}$", "$options": "i"}})
            if not worker_info and b.get('worker_id'):
                try:
                    worker_info = db_module.users_collection.find_one({"_id": ObjectId(b['worker_id'])})
                except Exception:
                    pass

            if worker_info:
                w_phone = worker_info.get('phone') or worker_info.get('mobile') or worker_info.get('whatsapp') or worker_info.get('contact')
                b['worker_phone'] = w_phone if (w_phone and w_phone != 'Not Provided' and len(str(w_phone).strip()) > 0) else (b.get('worker_phone') or '0775678901')
                b['worker_name'] = b.get('worker_name') or worker_info.get('name', 'Worker')
            else:
                b['worker_phone'] = b.get('worker_phone') if (b.get('worker_phone') and b.get('worker_phone') != 'Not Provided') else '0775678901'

        return jsonify(bookings)
    except Exception as e:
        print(f"Fetch Bookings Error: {e}")
        return jsonify([])

@booking_bp.route('/api/update-booking-status', methods=['PATCH'])
def update_booking_status():
    try:
        data = request.json or {}
        booking_id = data.get('booking_id')
        status = data.get('status')

        booking = None
        if booking_id:
            try:
                booking = db_module.bookings_collection.find_one({"_id": ObjectId(booking_id)})
            except Exception:
                booking = None

        db_module.bookings_collection.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {"status": status}}
        )

        if booking:
            job_title = booking.get('title') or booking.get('service_type') or 'Job'
            display_status = status.replace('_', ' ').title()

            if booking.get('worker_email'):
                db_module.add_notification(
                    user_identifier=booking['worker_email'],
                    title="Job Status Updated",
                    message=f"Job '{job_title}' status is now {display_status}.",
                    notif_type="status_update",
                    link="/jobs"
                )
            if booking.get('client_email'):
                db_module.add_notification(
                    user_identifier=booking['client_email'],
                    title="Job Status Updated",
                    message=f"Job '{job_title}' status is now {display_status}.",
                    notif_type="status_update",
                    link="/my-bookings"
                )

        return jsonify({"message": f"Status updated to {status}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
