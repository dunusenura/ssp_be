from flask import Blueprint, request, jsonify
from bson import ObjectId
import re
from whatsapp_gateway import WhatsAppGateway
import database as db_module

user_bp = Blueprint('user', __name__)

@user_bp.route('/api/user-profile', methods=['GET'])
def get_profile():
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({"error": "Email required"}), 400
        user_data = db_module.users_collection.find_one({"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}})
        if not user_data:
            return jsonify({"error": "User not found"}), 404
        user_data['_id'] = str(user_data['_id'])
        user_data.pop('password', None)

        if (user_data.get('role') or '').lower() == 'worker':
            w_reviews = list(db_module.reviews_collection.find({"worker_email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}))
            if w_reviews and len(w_reviews) > 0:
                avg_rating = sum([float(r.get('rating', 5)) for r in w_reviews]) / len(w_reviews)
                user_data['reliability'] = round(avg_rating, 1)
                user_data['review_count'] = len(w_reviews)
            else:
                user_data['reliability'] = 0.0
                user_data['review_count'] = 0

        return jsonify(user_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_bp.route('/api/update-profile', methods=['POST', 'PUT', 'PATCH'])
@user_bp.route('/api/users/profile', methods=['POST', 'PUT', 'PATCH'])
def update_profile():
    try:
        data = request.json or {}
        email = data.get('email')

        if not email and data.get('id'):
            try:
                user_doc = db_module.users_collection.find_one({"_id": ObjectId(data.get('id'))})
                if user_doc:
                    email = user_doc.get('email')
            except Exception:
                pass

        if not email:
            return jsonify({"message": "Email is required"}), 400

        category_val = data.get('category') or data.get('serviceCategory') or data.get('service_category')

        updates = {
            "bio": data.get('bio'),
            "location": data.get('location'),
            "skills": data.get('skills'),
            "phone": data.get('phone'),
            "category": category_val,
            "hourly_rate": data.get('hourly_rate'),
            "availability": data.get('availability'),
            "operating_radius": data.get('operating_radius'),
            "experience": data.get('experience')
        }

        updates = {k: v for k, v in updates.items() if v is not None}

        result = db_module.users_collection.update_one(
            {"email": email},
            {"$set": updates}
        )

        if result.matched_count > 0:
            updated_user = db_module.users_collection.find_one({"email": email})
            if updated_user:
                updated_user['_id'] = str(updated_user['_id'])
                updated_user.pop('password', None)
            return jsonify({
                "message": "Profile updated successfully!",
                "user": updated_user
            }), 200
        else:
            return jsonify({"message": "User not found"}), 404

    except Exception as e:
        return jsonify({"message": str(e)}), 500

@user_bp.route('/api/workers/<worker_id>', methods=['GET', 'PUT', 'PATCH'])
def handle_worker_by_id(worker_id):
    try:
        if request.method in ['PUT', 'PATCH']:
            data = request.json or {}
            category_val = data.get('category') or data.get('serviceCategory') or data.get('service_category')
            updates = {
                "bio": data.get('bio'),
                "location": data.get('location'),
                "skills": data.get('skills'),
                "phone": data.get('phone'),
                "category": category_val,
                "hourly_rate": data.get('hourly_rate'),
                "availability": data.get('availability'),
                "operating_radius": data.get('operating_radius'),
                "experience": data.get('experience')
            }
            updates = {k: v for k, v in updates.items() if v is not None}

            query_conds = [{"email": worker_id}]
            if ObjectId.is_valid(worker_id):
                query_conds.append({"_id": ObjectId(worker_id)})

            db_module.users_collection.update_one({"$or": query_conds}, {"$set": updates})

            updated_worker = db_module.users_collection.find_one({"$or": query_conds})
            if updated_worker:
                updated_worker['_id'] = str(updated_worker['_id'])
                updated_worker.pop('password', None)
                return jsonify({"message": "Worker updated successfully", "worker": updated_worker, "user": updated_worker}), 200
            return jsonify({"error": "Worker not found"}), 404
        else:
            query_conds = [{"email": worker_id}]
            if ObjectId.is_valid(worker_id):
                query_conds.append({"_id": ObjectId(worker_id)})
            worker = db_module.users_collection.find_one({"$or": query_conds})
            if not worker:
                return jsonify({"error": "Worker not found"}), 404
            worker['_id'] = str(worker['_id'])
            worker.pop('password', None)
            return jsonify(worker), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_bp.route('/api/worker-details', methods=['GET'])
def get_worker_details():
    try:
        email = request.args.get('email')
        worker = db_module.users_collection.find_one({"email": email, "role": "worker"})

        if not worker:
            return jsonify({"error": "Worker not found"}), 404

        worker['_id'] = str(worker['_id'])
        worker.pop('password', None)

        raw_phone = worker.get('phone') or worker.get('mobile')
        worker['masked_phone'] = WhatsAppGateway.mask_phone_number(raw_phone)
        worker['masked_email'] = WhatsAppGateway.mask_email(worker.get('email'))

        worker['phone'] = worker['masked_phone']
        worker['mobile'] = worker['masked_phone']

        return jsonify(worker), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_bp.route('/api/popular-skills', methods=['GET'])
def get_popular_skills():
    try:
        pipeline = [
            {"$match": {"role": "worker"}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 15}
        ]
        results = list(db_module.users_collection.aggregate(pipeline))
        categories = [item['_id'] for item in results if item['_id']]
        return jsonify(categories)
    except Exception as e:
        return jsonify([])

@user_bp.route('/api/unread-chats', methods=['GET'])
def get_unread_chats():
    user_email = request.args.get('email')
    if not user_email:
        return jsonify({"unread": []})
    try:
        unreads = list(db_module.messages_collection.find({
            "receiver": user_email,
            "status": {"$ne": "read"}
        }).sort("timestamp", -1))
        for u in unreads:
            u['_id'] = str(u['_id'])
        return jsonify({"unread": unreads})
    except Exception as e:
        return jsonify({"unread": []})

@user_bp.route('/api/notifications/<user_id>', methods=['GET'])
def get_notifications(user_id):
    try:
        email = request.args.get('email', '')
        query_conditions = [{"user_id": user_id}, {"receiver_id": user_id}]
        if email:
            query_conditions.extend([{"user_id": email}, {"receiver_id": email}])

        query = {"$or": query_conditions}

        notifs = list(db_module.notifications_collection.find(query).sort("created_at", -1).limit(30))

        unread_count = 0
        formatted_notifs = []
        for n in notifs:
            n_id = str(n['_id'])
            is_unread = not n.get('is_read', False) and n.get('status') != 'read'
            if is_unread:
                unread_count += 1
            formatted_notifs.append({
                "id": n_id,
                "title": n.get('title', 'Notification'),
                "message": n.get('message', ''),
                "type": n.get('type', 'info'),
                "is_read": not is_unread,
                "link": n.get('link', ''),
                "created_at": n.get('created_at', '')
            })

        return jsonify({
            "has_new": unread_count > 0,
            "count": unread_count,
            "notifications": formatted_notifs
        }), 200
    except Exception as e:
        print(f"Notifications API Error: {e}")
        return jsonify({"has_new": False, "count": 0, "notifications": []}), 200

@user_bp.route('/api/notifications/mark-read', methods=['POST'])
def mark_notification_read():
    try:
        data = request.json or {}
        notif_id = data.get('id')
        user_id = data.get('user_id')
        email = data.get('email')

        if notif_id:
            try:
                db_module.notifications_collection.update_one(
                    {"_id": ObjectId(notif_id)},
                    {"$set": {"is_read": True, "status": "read"}}
                )
            except Exception:
                pass
        else:
            query_conditions = []
            if user_id: query_conditions.extend([{"user_id": user_id}, {"receiver_id": user_id}])
            if email: query_conditions.extend([{"user_id": email}, {"receiver_id": email}])
            if query_conditions:
                db_module.notifications_collection.update_many(
                    {"$or": query_conditions},
                    {"$set": {"is_read": True, "status": "read"}}
                )

        return jsonify({"message": "Marked as read successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
