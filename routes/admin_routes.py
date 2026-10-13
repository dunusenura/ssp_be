from flask import Blueprint, request, jsonify
from bson import ObjectId
import re
from datetime import datetime, timezone
import database as db_module
from socket_service import emit_event
from geocoding import resolve_location_coordinates

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
            "verification_status": {"$nin": ["rejected", "revoked", "approved"]},
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
            "verification_status": {"$nin": ["rejected", "revoked", "approved"]},
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
            {"$set": {
                "is_verified": True,
                "verification_status": "approved"
            }}
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
                        message="Congratulations! Your professional credentials have been officially verified by WorkPub Administration. You now display the Verified Pro badge.",
                        notif_type="success",
                        link="/profile"
                    )
                except Exception as notif_err:
                    print(f"Notification alert: {notif_err}")

            # Emit real-time Socket event
            resolved_id = str(worker_id) if worker_id else str(updated_worker.get("_id", ""))
            emit_event('verification-updated', {
                "worker_id": resolved_id,
                "email": target_email,
                "name": worker_name,
                "is_verified": True,
                "verification_status": "approved",
                "action": "approved"
            })
            emit_event('worker-updated', {
                "worker_id": resolved_id,
                "email": target_email,
                "name": worker_name,
                "is_verified": True,
                "verification_status": "approved"
            })

            return jsonify({
                "message": f"Credentials for {worker_name} approved successfully!",
                "worker_id": str(worker_id) if worker_id else str(updated_worker.get("_id", "")),
                "is_verified": True,
                "verification_status": "approved"
            }), 200
        else:
            return jsonify({"error": "Worker record not found"}), 404

    except Exception as e:
        print(f"Error approving worker credentials: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/api/admin/reject-worker', methods=['POST'])
@admin_bp.route('/api/admin/revoke-worker', methods=['POST'])
def reject_worker_credentials():
    """
    Rejects or revokes a worker's credentials in MongoDB.
    Accepts: { worker_id: "<id>", email: "<optional email>", reason: "<optional reason>" }
    """
    try:
        data = request.json or {}
        worker_id = data.get('worker_id') or data.get('id')
        email = data.get('email')
        reason = data.get('reason') or "Credentials could not be verified by administration"

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
            {"$set": {
                "is_verified": False,
                "verification_status": "rejected",
                "rejection_reason": reason
            }}
        )

        if result.matched_count > 0:
            updated_worker = db_module.users_collection.find_one({"$or": filter_conditions})
            worker_name = updated_worker.get("name", "Worker") if updated_worker else "Worker"
            target_email = updated_worker.get("email", "") if updated_worker else email

            # Dispatch system notification to worker
            if target_email:
                try:
                    db_module.add_notification(
                        user_identifier=target_email,
                        title="Credential Verification Update",
                        message=f"Your credential verification request was reviewed and could not be approved at this time ({reason}). Please update your profile information or contact support.",
                        notif_type="warning",
                        link="/profile"
                    )
                except Exception as notif_err:
                    print(f"Notification alert: {notif_err}")

            resolved_id = str(worker_id) if worker_id else str(updated_worker.get("_id", ""))
            emit_event('verification-updated', {
                "worker_id": resolved_id,
                "email": target_email,
                "name": worker_name,
                "is_verified": False,
                "verification_status": "rejected",
                "action": "rejected"
            })
            emit_event('worker-updated', {
                "worker_id": resolved_id,
                "email": target_email,
                "name": worker_name,
                "is_verified": False,
                "verification_status": "rejected"
            })

            return jsonify({
                "message": f"Credentials for {worker_name} rejected/revoked successfully.",
                "worker_id": resolved_id,
                "is_verified": False,
                "verification_status": "rejected"
            }), 200
        else:
            return jsonify({"error": "Worker record not found"}), 404

    except Exception as e:
        print(f"Error rejecting worker credentials: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/api/admin/worker-category-stats', methods=['GET'])
@admin_bp.route('/api/admin/category-distribution', methods=['GET'])
def get_worker_category_stats():
    """
    Aggregates registered worker profiles by their category
    and returns exact live counts and distribution percentages.
    """
    try:
        pipeline = [
            {
                "$match": {
                    "role": {"$regex": "^worker$", "$options": "i"}
                }
            },
            {
                "$project": {
                    "category": {
                        "$cond": {
                            "if": {
                                "$and": [
                                    {"$ne": ["$category", None]},
                                    {"$ne": ["$category", ""]},
                                    {"$ne": ["$category", False]}
                                ]
                            },
                            "then": "$category",
                            "else": "General Service"
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": "$category",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1, "_id": 1}
            }
        ]

        results = list(db_module.users_collection.aggregate(pipeline))

        stats = []
        total_workers = sum(item.get("count", 0) for item in results)

        for item in results:
            cat_name = item.get("_id") or "General Service"
            cnt = item.get("count", 0)
            stats.append({
                "category": cat_name,
                "count": cnt,
                "percentage": round((cnt / total_workers * 100), 1) if total_workers > 0 else 0
            })

        return jsonify({
            "total_workers": total_workers,
            "categories": stats
        }), 200

    except Exception as e:
        print(f"Error aggregating worker category stats: {e}")
        return jsonify({
            "error": "Failed to aggregate category stats",
            "message": str(e),
            "total_workers": 0,
            "categories": []
        }), 500


@admin_bp.route('/api/admin/workers-by-category', methods=['GET'])
@admin_bp.route('/api/admin/workers-map-data', methods=['GET'])
def get_workers_by_category():
    """
    Accepts category and search query parameters.
    Returns all registered workers matching the query with exact resolved geographic
    coordinates (lat, lon), locality, contact details, verification status, and profile info.
    """
    category = request.args.get('category', '').strip()
    search_query = request.args.get('q', '').strip()

    try:
        query = {"role": {"$regex": "^worker$", "$options": "i"}}
        and_conditions = []

        if category and category.lower() not in ['all', 'all categories', '']:
            and_conditions.append({
                "category": {"$regex": re.escape(category), "$options": "i"}
            })

        if search_query:
            and_conditions.append({
                "$or": [
                    {"name": {"$regex": re.escape(search_query), "$options": "i"}},
                    {"category": {"$regex": re.escape(search_query), "$options": "i"}},
                    {"location": {"$regex": re.escape(search_query), "$options": "i"}},
                    {"email": {"$regex": re.escape(search_query), "$options": "i"}},
                    {"phone": {"$regex": re.escape(search_query), "$options": "i"}}
                ]
            })

        if and_conditions:
            query["$and"] = and_conditions

        workers = list(db_module.users_collection.find(query).sort("name", 1))

        formatted_workers = []
        for w in workers:
            w_id = str(w.get("_id", ""))
            loc = w.get("location") or "Gampaha"
            stored_lat = w.get("lat")
            stored_lon = w.get("lon")

            lat, lon, resolved_name = resolve_location_coordinates(loc, stored_lat, stored_lon)

            reliability = float(w.get("reliability", 5.0) or 5.0)
            is_verified = bool(w.get("is_verified", False))
            v_status = w.get("verification_status") or ("approved" if is_verified else "pending")

            formatted_workers.append({
                "id": w_id,
                "_id": w_id,
                "name": w.get("name") or "Service Worker",
                "email": w.get("email", ""),
                "phone": w.get("phone") or "",
                "category": w.get("category") or "General Service",
                "location": loc,
                "district": "Gampaha",
                "resolved_locality": resolved_name or loc,
                "lat": lat,
                "lon": lon,
                "hourly_rate": w.get("hourly_rate") or "1,500",
                "availability": w.get("availability") or "available",
                "is_verified": is_verified,
                "verification_status": v_status,
                "experience": w.get("experience", 0),
                "reliability": round(reliability, 1),
                "bio": w.get("bio") or "",
                "skills": w.get("skills") if isinstance(w.get("skills"), list) else []
            })

        return jsonify({
            "category": category or "all",
            "total": len(formatted_workers),
            "workers": formatted_workers
        }), 200

    except Exception as e:
        print(f"Error fetching workers by category: {e}")
        return jsonify({
            "error": "Failed to fetch workers by category",
            "message": str(e),
            "category": category or "all",
            "total": 0,
            "workers": []
        }), 500


