from flask import Blueprint, request, jsonify
import bcrypt
from datetime import datetime, timezone
import database as db_module

from geocoding import resolve_location_coordinates

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.json or {}
        if not data.get('email') or not data.get('password') or not data.get('name'):
            return jsonify({"message": "Name, email, and password are required"}), 400

        # Check existing user
        if db_module.users_collection.find_one({"email": data['email']}):
            return jsonify({"message": "Email already exists"}), 400

        hashed_pw = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        category_val = data.get('category') or data.get('serviceCategory') or data.get('service_category') or 'General Service'
        user_loc = data.get('location', 'Gampaha')
        lat, lon, _ = resolve_location_coordinates(user_loc, data.get('lat'), data.get('lon'))

        new_user = {
            "name": data['name'],
            "email": data['email'],
            "location": user_loc,
            "role": data.get('role', 'seeker'),
            "category": category_val,
            "password": hashed_pw,
            "reliability": 5.0,
            "experience": data.get('experience', 0),
            "lat": lat,
            "lon": lon,
            "joined_at": datetime.now(timezone.utc).isoformat(),
            "bio": f"Hello! I am {data['name']}, registered on WorkPub.",
            "skills": [],
            "phone": data.get('phone', ''),
            "is_verified": False
        }

        db_module.users_collection.insert_one(new_user)

        return jsonify({
            "message": "Account created successfully!",
            "user": {
                "name": new_user["name"],
                "email": new_user["email"],
                "role": new_user["role"],
                "category": new_user["category"],
                "location": new_user["location"]
            }
        }), 201

    except Exception as e:
        print(f"Registration Error: {e}")
        return jsonify({"message": f"An error occurred during registration: {str(e)}"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json or {}
        if not data.get('email') or not data.get('password'):
            return jsonify({"message": "Email and password required"}), 400

        user = db_module.users_collection.find_one({"email": data['email']})
        if user and bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
            user['_id'] = str(user['_id'])
            user.pop('password', None)
            return jsonify({
                "message": "Login successful",
                "user": user
            }), 200

        return jsonify({"message": "Invalid email or password credentials"}), 401
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@auth_bp.route('/api/auth/google', methods=['POST'])
def google_auth():
    try:
        data = request.json or {}
        email = data.get('email')
        name = data.get('name') or (email.split('@')[0] if email else 'Google User')
        google_id = data.get('google_id') or data.get('sub') or f"google_{int(datetime.now().timestamp())}"
        picture = data.get('picture', '')
        requested_role = data.get('role')
        requested_category = data.get('category') or data.get('serviceCategory') or 'General Service'

        if not email:
            return jsonify({"message": "Email is required for Google authentication"}), 400

        user = db_module.users_collection.find_one({"email": email})

        if user:
            user['_id'] = str(user['_id'])
            user.pop('password', None)

            if not user.get('role') and requested_role:
                db_module.users_collection.update_one({"email": email}, {"$set": {"role": requested_role, "category": requested_category}})
                user['role'] = requested_role
                user['category'] = requested_category

            return jsonify({
                "message": "Google authentication successful",
                "user": user,
                "is_new_user": False
            }), 200
        else:
            role = requested_role if requested_role else 'seeker'
            category_val = requested_category if role == 'worker' else 'General Service'

            new_user = {
                "name": name,
                "email": email,
                "role": role,
                "category": category_val,
                "location": data.get('location', 'Gampaha'),
                "joined_at": datetime.now(timezone.utc).isoformat(),
                "bio": f"Hello! I am {name}, registered via Google on WorkPub.",
                "skills": [],
                "phone": "",
                "reliability": 0.0,
                "is_verified": True,
                "is_google_auth": True,
                "google_id": google_id,
                "picture": picture
            }

            result = db_module.users_collection.insert_one(new_user)
            new_user['_id'] = str(result.inserted_id)

            return jsonify({
                "message": "Google Account created successfully!",
                "user": new_user,
                "is_new_user": True
            }), 201

    except Exception as e:
        print(f"Google Auth Error: {e}")
        return jsonify({"message": f"Google Auth Error: {str(e)}"}), 500
