import certifi
from pymongo import MongoClient
from flask_pymongo import PyMongo
from datetime import datetime, timezone
import config

client = None
db = None
users_collection = None
jobs_collection = None
messages_collection = None
reviews_collection = None
bookings_collection = None
notifications_collection = None
payments_collection = None
saved_cards_collection = None

mongo = PyMongo()

def init_db(app):
    global client, db, users_collection, jobs_collection, messages_collection
    global reviews_collection, bookings_collection, notifications_collection
    global payments_collection, saved_cards_collection

    ca = certifi.where()
    app.config["MONGO_URI"] = config.MONGO_URI
    mongo.init_app(app)

    try:
        client = MongoClient(
            config.MONGO_URI, 
            tlsCAFile=ca, 
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000
        )
        db = client['WorkPubDB']
    except Exception as e:
        print(f"MongoDB connection notice: {e}")
        db = mongo.db

    users_collection = db['users']
    jobs_collection = db['jobs']
    messages_collection = db['messages']
    reviews_collection = db['reviews']
    bookings_collection = db['bookings']
    notifications_collection = db['notifications']
    payments_collection = db['payments']
    saved_cards_collection = db['saved_cards']

def add_notification(user_identifier, title, message, notif_type="info", link=""):
    if not user_identifier or notifications_collection is None:
        return
    try:
        notif = {
            "user_id": str(user_identifier),
            "title": title,
            "message": message,
            "type": notif_type,
            "is_read": False,
            "status": "unread",
            "link": link or "",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        notifications_collection.insert_one(notif)
    except Exception as e:
        print(f"Error creating notification: {e}")
