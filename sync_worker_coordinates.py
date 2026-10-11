"""
Migration script to synchronize worker location coordinates in MongoDB.
Fixes all workers whose lat/lon are missing, defaulted, or mismatched.
"""
import certifi
from pymongo import MongoClient
import config
from geocoding import resolve_location_coordinates

def sync_coordinates():
    try:
        client = MongoClient(
            config.MONGO_URI, 
            tlsCAFile=certifi.where(), 
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000
        )
        db = client['WorkPubDB']
        workers = list(db.users.find({'role': 'worker'}))
        print(f"Found {len(workers)} worker records to verify...")

        updated_count = 0
        for w in workers:
            name = w.get('name', 'Unknown')
            loc = w.get('location', '')
            curr_lat = w.get('lat')
            curr_lon = w.get('lon')

            resolved_lat, resolved_lon, resolved_name = resolve_location_coordinates(loc, curr_lat, curr_lon)

            # Check if coordinates need updating
            if curr_lat != resolved_lat or curr_lon != resolved_lon:
                db.users.update_one(
                    {'_id': w['_id']},
                    {'$set': {'lat': resolved_lat, 'lon': resolved_lon}}
                )
                print(f"Updated {name} ({loc}): [{curr_lat}, {curr_lon}] -> [{resolved_lat}, {resolved_lon}] ({resolved_name})")
                updated_count += 1
            else:
                print(f"Already accurate: {name} ({loc}) at [{curr_lat}, {curr_lon}]")

        print(f"\nDone! Updated {updated_count} workers with exact geocoded coordinates.")
    except Exception as e:
        print(f"Sync error: {e}")

if __name__ == "__main__":
    sync_coordinates()
