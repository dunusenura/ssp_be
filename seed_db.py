import certifi
from pymongo import MongoClient
import bcrypt
from datetime import datetime, timezone
import config

def seed_database():
    ca = certifi.where()
    try:
        client = MongoClient(
            config.MONGO_URI, 
            tlsCAFile=ca, 
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=4000
        )
        # Test connection
        client.admin.command('ping')
        print("Connected to MongoDB Atlas cluster.")
    except Exception as e:
        print(f"Atlas SSL/Connection alert: {e}")
        print("Attempting connection to local MongoDB instance...")
        try:
            client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=3000)
            client.admin.command('ping')
            print("Connected to local MongoDB instance.")
        except Exception as loc_e:
            print(f"Could not connect to MongoDB instance: {loc_e}")
            print("Database seeding skipped. App will operate with in-memory state or standard Atlas connection upon app runtime.")
            return

    db = client['WorkPubDB']

    # Hash default password
    hashed_pw = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt())

    # 1. Real-world Verified Workers (Gampaha Region)
    sample_workers = [
        {
            "name": "Kusumsiri Perera",
            "email": "kusumsiri@gmail.com",
            "role": "worker",
            "category": "Electrician",
            "location": "Gampaha",
            "district": "Gampaha",
            "password": hashed_pw,
            "reliability": 4.9,
            "review_count": 18,
            "experience": 8,
            "hourly_rate": 1800,
            "bio": "Certified Industrial & Domestic Master Electrician. Expert in 3-phase wiring, DB board setup, solar inverters, and emergency leakages.",
            "skills": ["3-Phase Wiring", "DB Board Assembly", "Solar Inverter Setup", "Short Circuit Repair"],
            "phone": "0771234567",
            "availability": "available",
            "operating_radius": 20,
            "lat": 7.0873,
            "lon": 80.0144,
            "is_verified": True
        },
        {
            "name": "Surendra Silva",
            "email": "surendz@gmail.com",
            "role": "worker",
            "category": "AC Technician",
            "location": "Kadawatha",
            "district": "Gampaha",
            "password": hashed_pw,
            "reliability": 4.8,
            "review_count": 22,
            "experience": 6,
            "hourly_rate": 2200,
            "bio": "Licensed HVAC & Inverter AC Technician. Chemical servicing, gas refilling (R32/R410a), leak testing, and compressor replacements.",
            "skills": ["Inverter AC Repair", "Chemical Pressure Wash", "R32 Gas Refill", "Compressor Overhaul"],
            "phone": "0772345678",
            "availability": "available",
            "operating_radius": 25,
            "lat": 7.0012,
            "lon": 79.9512,
            "is_verified": True
        },
        {
            "name": "Kamal Jayasinghe",
            "email": "kamal@gmail.com",
            "role": "worker",
            "category": "Plumber",
            "location": "Negombo",
            "district": "Gampaha",
            "password": hashed_pw,
            "reliability": 4.7,
            "review_count": 15,
            "experience": 10,
            "hourly_rate": 1500,
            "bio": "Master Plumbing Specialist. Over 10 years experience in bathroom sanitary fitting, pressure pump installation, and underground pipe leaks.",
            "skills": ["Pressure Pump Repair", "PPR Pipe Welding", "Bathroom Sanitary Fitting", "Overhead Tank Setup"],
            "phone": "0773456789",
            "availability": "available",
            "operating_radius": 18,
            "lat": 7.2083,
            "lon": 79.8358,
            "is_verified": True
        },
        {
            "name": "Aruna Fernando",
            "email": "aruna.mason@gmail.com",
            "role": "worker",
            "category": "Mason",
            "location": "Yakkala",
            "district": "Gampaha",
            "password": hashed_pw,
            "reliability": 4.9,
            "review_count": 12,
            "experience": 12,
            "hourly_rate": 2000,
            "bio": "Expert Masonry & Tile Installation Specialist. Tile laying, plastering, boundary wall masonry, and waterproofing.",
            "skills": ["Granite & Tile Fitting", "Waterproofing", "Concrete Slab Masonry", "Boundary Wall Construction"],
            "phone": "0774567890",
            "availability": "available",
            "operating_radius": 15,
            "lat": 7.0921,
            "lon": 80.0345,
            "is_verified": True
        },
        {
            "name": "Nimal Rathnayake",
            "email": "nimal.cctv@gmail.com",
            "role": "worker",
            "category": "CCTV Installer",
            "location": "Ja-Ela",
            "district": "Gampaha",
            "password": hashed_pw,
            "reliability": 5.0,
            "review_count": 9,
            "experience": 5,
            "hourly_rate": 2500,
            "bio": "Security Systems & IP CCTV Surveillance Specialist. Hikvision, Dahua IP camera installation, remote mobile view setup, and DVR troubleshooting.",
            "skills": ["IP Camera Installation", "DVR & NVR Setup", "Mobile Live Stream Sync", "Cat6 Cabling"],
            "phone": "0775678901",
            "availability": "available",
            "operating_radius": 30,
            "lat": 7.0744,
            "lon": 79.8919,
            "is_verified": True
        }
    ]

    # 2. Real-world Seeker User
    sample_seeker = {
        "name": "Nimali Gunasekera",
        "email": "nimali@gmail.com",
        "role": "seeker",
        "category": "General Service",
        "location": "Gampaha",
        "district": "Gampaha",
        "password": hashed_pw,
        "phone": "0718889900",
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "is_verified": True
    }

    # 3. Real-world Open Jobs in Gampaha
    sample_jobs = [
        {
            "category": "Electrician",
            "title": "Emergency Main DB Board Circuit Breaker Tripping Repair",
            "location": "Gampaha City",
            "budget": 3500,
            "task_details": "Main circuit breaker keeps tripping whenever air conditioner is switched on. Need diagnostic testing and DB board rewiring.",
            "district": "Gampaha",
            "posted_by": "nimali@gmail.com",
            "status": "open",
            "coordinates": {"lat": 7.0873, "lon": 80.0144},
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "category": "AC Technician",
            "title": "Split AC Chemical Cleaning & Gas Top Up",
            "location": "Kadawatha",
            "budget": 6500,
            "task_details": "12,000 BTU Inverter AC unit needs deep chemical pressure wash and R32 refrigerant gas pressure check.",
            "district": "Gampaha",
            "posted_by": "nimali@gmail.com",
            "status": "open",
            "coordinates": {"lat": 7.0012, "lon": 79.9512},
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "category": "Plumber",
            "title": "Bathroom Overhead Water Tank Pressure Pump Fitting",
            "location": "Yakkala",
            "budget": 4500,
            "task_details": "Need an experienced plumber to connect a auto-cut pressure pump to the top bathroom supply line.",
            "district": "Gampaha",
            "posted_by": "nimali@gmail.com",
            "status": "open",
            "coordinates": {"lat": 7.0921, "lon": 80.0345},
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "category": "CCTV Installer",
            "title": "4-Channel Hikvision IP Camera System Installation",
            "location": "Ja-Ela",
            "budget": 12000,
            "task_details": "Installation of 4 outdoor bullet cameras, DVR configuration, Cat6 cable routing and mobile app connectivity.",
            "district": "Gampaha",
            "posted_by": "nimali@gmail.com",
            "status": "open",
            "coordinates": {"lat": 7.0744, "lon": 79.8919},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]

    for w in sample_workers:
        db.users.update_one({"email": w["email"]}, {"$set": w}, upsert=True)

    db.users.update_one({"email": sample_seeker["email"]}, {"$set": sample_seeker}, upsert=True)

    if db.jobs.count_documents({"district": "Gampaha"}) == 0:
        db.jobs.insert_many(sample_jobs)

    print("✅ Successfully seeded WorkPub database with realistic workers, seekers, and open jobs in Gampaha!")

if __name__ == "__main__":
    seed_database()