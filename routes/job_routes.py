from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from bson import ObjectId
import re
from rapidfuzz import process, fuzz
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import database as db_module

job_bp = Blueprint('job', __name__)

CATEGORIES = [
    "Electrician", "Plumber", "AC Technician", "Carpenter",
    "Mason", "Painter", "Appliance Repair", "CCTV Installer",
    "Aluminum Fabricator", "Land Surveyor", "Cleaning Services", "General Service"
]

@job_bp.route('/api/post-job', methods=['POST'])
@job_bp.route('/api/jobs', methods=['POST'])
@job_bp.route('/api/tasks', methods=['POST'])
def post_job():
    try:
        data = request.json or {}

        title = data.get('title') or data.get('name') or 'General Task'
        category = data.get('category') or data.get('serviceCategory') or 'General Service'
        location = data.get('location') or 'Gampaha'
        task_details = data.get('task_details') or data.get('details') or data.get('description') or ''
        posted_by = data.get('email') or data.get('posted_by') or data.get('user_email') or ''

        raw_budget = str(data.get('budget', 0)).replace(',', '').replace('LKR', '').replace('Rs.', '').strip()
        try:
            budget = int(float(raw_budget)) if raw_budget else 0
        except (ValueError, TypeError):
            budget = 0

        new_job = {
            "category": category,
            "title": title,
            "location": location,
            "budget": budget,
            "task_details": task_details,
            "district": data.get('district', 'Gampaha'),
            "posted_by": posted_by,
            "status": "open",
            "coordinates": data.get('coordinates', {"lat": 7.0912, "lon": 79.9991}),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        result = db_module.jobs_collection.insert_one(new_job)

        if posted_by:
            try:
                db_module.add_notification(
                    user_identifier=posted_by,
                    title="Job Posted Successfully",
                    message=f"Your job listing '{new_job['title']}' is now live for workers.",
                    notif_type="job_post",
                    link="/services"
                )
            except Exception as ne:
                print(f"Notification Error: {ne}")

        return jsonify({"message": "Job posted successfully!", "id": str(result.inserted_id)}), 201
    except Exception as e:
        print(f"Post Job Error: {e}")
        return jsonify({"message": f"Failed to post job: {str(e)}"}), 500

@job_bp.route('/api/jobs/customer/<path:customer_email>', methods=['GET'])
@job_bp.route('/api/customer-jobs', methods=['GET'])
def get_customer_jobs(customer_email=None):
    try:
        email = customer_email or request.args.get('email') or ''
        if not email:
            return jsonify({"error": "customer email is required"}), 400

        jobs = list(db_module.jobs_collection.find(
            {"posted_by": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
        ).sort("created_at", -1))

        for job in jobs:
            job['_id'] = str(job['_id'])

        return jsonify(jobs), 200
    except Exception as e:
        print(f"Get Customer Jobs Error: {e}")
        return jsonify({"error": str(e)}), 500

@job_bp.route('/api/jobs/<job_id>', methods=['PUT', 'PATCH'])
@job_bp.route('/api/update-job/<job_id>', methods=['PUT', 'PATCH'])
def update_job(job_id):
    try:
        data = request.json or {}

        update_fields = {}
        if 'title' in data:
            update_fields['title'] = data['title']
        if 'category' in data:
            update_fields['category'] = data['category']
        if 'location' in data:
            update_fields['location'] = data['location']
        if 'task_details' in data or 'details' in data:
            update_fields['task_details'] = data.get('task_details') or data.get('details', '')
        if 'budget' in data:
            raw_budget = str(data.get('budget', 0)).replace(',', '').replace('LKR', '').replace('Rs.', '').strip()
            try:
                update_fields['budget'] = int(float(raw_budget)) if raw_budget else 0
            except (ValueError, TypeError):
                update_fields['budget'] = 0
        if 'status' in data:
            update_fields['status'] = data['status']

        update_fields['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = db_module.jobs_collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Job not found"}), 404

        updated_job = db_module.jobs_collection.find_one({"_id": ObjectId(job_id)})
        updated_job['_id'] = str(updated_job['_id'])

        return jsonify({"message": "Job updated successfully!", "job": updated_job}), 200
    except Exception as e:
        print(f"Update Job Error: {e}")
        return jsonify({"error": str(e)}), 500

@job_bp.route('/api/jobs/<job_id>', methods=['DELETE'])
@job_bp.route('/api/delete-job/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    try:
        result = db_module.jobs_collection.delete_one({"_id": ObjectId(job_id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Job not found or already deleted"}), 404

        return jsonify({"message": "Job deleted successfully!"}), 200
    except Exception as e:
        print(f"Delete Job Error: {e}")
        return jsonify({"error": str(e)}), 500

@job_bp.route('/api/job-details/<job_id>', methods=['GET'])
def get_job_details(job_id):
    try:
        job = db_module.jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            return jsonify({"error": "Job not found"}), 404

        poster = db_module.users_collection.find_one({"email": job.get('posted_by')})

        response = {
            "job": {
                "_id": str(job['_id']),
                "title": job.get('title'),
                "category": job.get('category'),
                "budget": job.get('budget'),
                "task_details": job.get('task_details'),
                "location": job.get('location'),
                "district": job.get('district', 'Gampaha')
            },
            "poster": {
                "name": poster.get('name') if poster else "Unknown Client",
                "email": job.get('posted_by', "Not Provided"),
                "lat": poster.get('lat', 7.0912) if poster else 7.0912,
                "lon": poster.get('lon', 79.9991) if poster else 79.9991
            }
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@job_bp.route('/api/jobs/gampaha', methods=['GET'])
def get_gampaha_jobs():
    try:
        jobs = list(db_module.jobs_collection.find({"district": "Gampaha"}).sort("created_at", -1))
        for job in jobs:
            job['_id'] = str(job['_id'])
        return jsonify(jobs)
    except Exception as e:
        return jsonify([])

@job_bp.route('/search', methods=['GET'])
def search_workers():
    try:
        category = request.args.get('category')
        if not category or category == "all" or category.lower() == "all categories":
            query = {"role": "worker"}
        else:
            query = {"role": "worker", "category": {"$regex": re.escape(category), "$options": "i"}}

        workers = list(db_module.users_collection.find(query))
        sanitized_workers = []

        for w in workers:
            w['_id'] = str(w['_id'])
            w.pop('password', None)
            w.pop('phone', None)
            w.pop('mobile', None)

            w_reviews = list(db_module.reviews_collection.find({"worker_email": {"$regex": f"^{re.escape(w.get('email', ''))}$", "$options": "i"}}))
            if w_reviews and len(w_reviews) > 0:
                avg_rating = sum([float(r.get('rating', 5)) for r in w_reviews]) / len(w_reviews)
                w['reliability'] = round(avg_rating, 1)
                w['review_count'] = len(w_reviews)
            else:
                w['reliability'] = 0.0
                w['review_count'] = 0

            sanitized_workers.append(w)

        sanitized_workers.sort(key=lambda x: x.get('reliability', 0), reverse=True)
        return jsonify(sanitized_workers)
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@job_bp.route('/recommend', methods=['GET'])
def recommend_workers():
    try:
        email = request.args.get('email')
        all_workers = list(db_module.users_collection.find({"role": "worker"}))
        if not all_workers or len(all_workers) < 2: return jsonify([])

        df = pd.DataFrame(all_workers)
        df['_id'] = df['_id'].astype(str)
        if email not in df['email'].values: return jsonify([])

        df['features'] = df['category'].fillna('') + " " + df['location'].fillna('')
        tfidf = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf.fit_transform(df['features'])
        cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

        idx = df[df['email'] == email].index[0]
        sim_scores = sorted(list(enumerate(cosine_sim[idx])), key=lambda x: x[1], reverse=True)
        recommended_indices = [i[0] for i in sim_scores if df.iloc[i[0]]['email'] != email][:3]

        recommendations = df.iloc[recommended_indices].to_dict(orient='records')
        for rec in recommendations:
            rec.pop('password', None)
            rec.pop('phone', None)
            rec.pop('mobile', None)
        return jsonify(recommendations)
    except Exception as e:
        return jsonify([])

@job_bp.route('/api/hints', methods=['GET'])
def get_hints():
    query = request.args.get('q', '')
    if not query or len(query) < 2: return jsonify([])
    matches = process.extract(query, CATEGORIES, scorer=fuzz.WRatio, limit=5)
    suggestions = [match[0] for match in matches if match[1] > 60]
    return jsonify(suggestions)
