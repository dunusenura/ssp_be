from flask import Blueprint, request, jsonify
from datetime import datetime
import re
import database as db_module

review_bp = Blueprint('review', __name__)

@review_bp.route('/api/add-review', methods=['POST'])
def add_review():
    try:
        data = request.json or {}
        worker_email = data.get('worker_email')
        rating = int(data.get('rating', 5))
        new_review = {
            "reviewer_email": data.get('reviewer_email'),
            "worker_email": worker_email,
            "rating": rating,
            "comment": data.get('comment'),
            "timestamp": datetime.utcnow().isoformat()
        }
        db_module.reviews_collection.insert_one(new_review)

        all_worker_reviews = list(db_module.reviews_collection.find({"worker_email": worker_email}))
        if all_worker_reviews:
            avg_rating = sum(r['rating'] for r in all_worker_reviews) / len(all_worker_reviews)
            db_module.users_collection.update_one(
                {"email": worker_email},
                {"$set": {"reliability": round(avg_rating, 1)}}
            )
        return jsonify({"message": "Review added and reliability updated!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@review_bp.route('/api/get-reviews', methods=['GET'])
def get_reviews():
    try:
        worker_email = request.args.get('email')
        if not worker_email:
            return jsonify({"error": "Worker email is required"}), 400

        reviews = list(db_module.reviews_collection.find({"worker_email": worker_email}).sort("timestamp", -1))

        for review in reviews:
            review['_id'] = str(review['_id'])

            if 'reviewer_email' in review and not review.get('reviewer_name'):
                reviewer = db_module.users_collection.find_one({"email": review['reviewer_email']})
                review['reviewer_name'] = reviewer.get('name') if reviewer else "Verified User"

        return jsonify(reviews), 200
    except Exception as e:
        print(f"Get Reviews Error: {e}")
        return jsonify([]), 500
