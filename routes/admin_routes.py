from flask import Blueprint, request, jsonify
from bson import ObjectId
import re
from datetime import datetime, timezone
import database as db_module

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/metrics', methods=['GET'])
@admin_bp.route('/api/admin/dashboard-stats', methods=['GET'])
def get_admin_metrics():
    """
    Computes real-time dynamic dashboard metrics from MongoDB:
    1. Total Registered Workers (users with role 'worker')
    2. Active Jobs Posted (jobs with active/open status)
    3. Verification Approvals Pending (workers awaiting credential approval)
    """
    try:
        # 1. Total Registered Workers
        worker_query = {"role": {"$regex": "^worker$", "$options": "i"}}
        total_workers = db_module.users_collection.count_documents(worker_query)

        # 2. Active Jobs Posted
        # Count all jobs that are not completed, cancelled, or closed
        job_query = {
            "$or": [
                {"status": {"$in": ["open", "active", "pending", "in_progress"]}},
                {"status": None},
                {"status": {"$exists": False}}
            ]
        }
        active_jobs = db_module.jobs_collection.count_documents(job_query)

        # 3. Verification Approvals Pending
        pending_query = {
            "role": {"$regex": "^worker$", "$options": "i"},
            "$or": [
                {"is_verified": False},
                {"is_verified": None},
                {"is_verified": {"$exists": False}}
            ]
        }
        pending_approvals = db_module.users_collection.count_documents(pending_query)

        # Total seekers / clients for supplemental analytics
        total_seekers = db_module.users_collection.count_documents({"role": {"$regex": "^seeker$", "$options": "i"}})

        return jsonify({
            "total_registered_workers": total_workers,
            "active_jobs_posted": active_jobs,
            "verification_approvals_pending": pending_approvals,
            "total_seekers": total_seekers,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    except Exception as e:
        print(f"Error fetching admin metrics: {e}")
        return jsonify({
            "error": "Failed to fetch metrics",
            "message": str(e),
            "total_registered_workers": 0,
            "active_jobs_posted": 0,
            "verification_approvals_pending": 0
        }), 500


@admin_bp.route('/api/admin/pending-workers', methods=['GET'])
@admin_bp.route('/api/admin/verification-queue', methods=['GET'])
def get_pending_workers():
    """
    Retrieves the queue of workers currently awaiting credential verification.
    """
    try:
        limit = int(request.args.get('limit', 50))
        query = {
            "role": {"$regex": "^worker$", "$options": "i"},
            "$or": [
                {"is_verified": False},
                {"is_verified": None},
                {"is_verified": {"$exists": False}}
            ]
        }

        pending_workers = list(db_module.users_collection.find(query).sort("_id", -1).limit(limit))

        queue = []
        for w in pending_workers:
            queue.append({
                "id": str(w["_id"]),
                "name": w.get("name") or "Unnamed Applicant",
                "email": w.get("email", ""),
                "location": w.get("location") or "Gampaha",
                "category": w.get("category") or "General Service",
                "experience": w.get("experience", 0),
                "phone": w.get("phone", ""),
                "hourly_rate": w.get("hourly_rate", ""),
                "bio": w.get("bio", ""),
                "skills": w.get("skills", []),
                "joined_at": w.get("joined_at", ""),
                "is_verified": False
            })

        return jsonify(queue), 200

    except Exception as e:
        print(f"Error fetching pending verification queue: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/api/admin/approve-worker', methods=['POST'])
def approve_worker_credentials():
    """
    Approves and verifies a worker's credentials in MongoDB.
    Accepts: { worker_id: "<id>", email: "<optional email>" }
    """
    try:
        data = request.json or {}
        worker_id = data.get('worker_id') or data.get('id')
        email = data.get('email')

        if not worker_id and not email:
            return jsonify({"error": "Worker ID or email is required"}), 400

        filter_conditions = []
        if worker_id and ObjectId.is_valid(worker_id):
            filter_conditions.append({"_id": ObjectId(worker_id)})
        if email:
            filter_conditions.append({"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}})

        if not filter_conditions:
            return jsonify({"error": "Invalid worker identifier"}), 400

        result = db_module.users_collection.update_one(
            {"$or": filter_conditions},
            {"$set": {"is_verified": True}}
        )

        if result.matched_count > 0:
            # Fetch updated worker details for response
            updated_worker = db_module.users_collection.find_one({"$or": filter_conditions})
            worker_name = updated_worker.get("name", "Worker") if updated_worker else "Worker"
            target_email = updated_worker.get("email", "") if updated_worker else email

            # Dispatch congratulatory system notification to worker
            if target_email:
                try:
                    db_module.add_notification(
                        user_identifier=target_email,
                        title="Credentials Approved! 🛡️",
                        message="Congratulations! Your professional credentials have been officially verified by WorkPub Administration. You now display the Verified badge.",
                        notif_type="success",
                        link="/profile"
                    )
                except Exception as notif_err:
                    print(f"Notification alert: {notif_err}")

            return jsonify({
                "message": f"Credentials for {worker_name} approved successfully!",
                "worker_id": str(worker_id) if worker_id else str(updated_worker.get("_id", "")),
                "is_verified": True
            }), 200
        else:
            return jsonify({"error": "Worker record not found"}), 404

    except Exception as e:
        print(f"Error approving worker credentials: {e}")
        return jsonify({"error": str(e)}), 500
