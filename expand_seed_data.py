import json
import random
from Emergix.app import app
from Emergix.models import db, Hospital, BedInventory

CITIES = [
    {"name": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lng": 72.5714},
    {"name": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567},
    {"name": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lng": 78.4867},
    {"name": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lng": 75.7873},
    {"name": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lng": 80.9462},
    {"name": "Kanpur", "state": "Uttar Pradesh", "lat": 26.4499, "lng": 80.3319},
    {"name": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lng": 79.0882},
    {"name": "Indore", "state": "Madhya Pradesh", "lat": 22.7196, "lng": 75.8577},
    {"name": "Thane", "state": "Maharashtra", "lat": 19.2183, "lng": 72.9781},
    {"name": "Bhopal", "state": "Madhya Pradesh", "lat": 23.2599, "lng": 77.4126},
]

def generate_hospitals():
    print("Expanding seed data with pan-India hospitals...")
    with app.app_context():
        count = 0
        for city in CITIES:
            # Generate 5 hospitals per city
            for i in range(1, 6):
                hosp = Hospital(
                    name=f"{city['name']} City Hospital {i}",
                    address=f"Sector {i}, Main Road, {city['name']}",
                    city=city["name"],
                    state=city["state"],
                    pincode="123456",
                    phone=f"0{random.randint(100, 999)}-{random.randint(1000000, 9999999)}",
                    latitude=city["lat"] + random.uniform(-0.05, 0.05),
                    longitude=city["lng"] + random.uniform(-0.05, 0.05),
                    hospital_type=random.choice(['government', 'private', 'trust']),
                    emergency_24h=True,
                    ambulance=random.choice([True, False]),
                    is_active=True
                )
                db.session.add(hosp)
                db.session.flush()

                beds_data = {
                    "general": [random.randint(50, 200), random.randint(10, 50)],
                    "icu": [random.randint(20, 50), random.randint(0, 10)],
                    "oxygen": [random.randint(30, 100), random.randint(5, 20)],
                    "ventilator": [random.randint(10, 30), random.randint(0, 5)],
                    "emergency": [random.randint(20, 50), random.randint(5, 15)]
                }

                for btype, counts in beds_data.items():
                    total, avail = counts
                    inv = BedInventory(
                        hospital_id=hosp.id,
                        bed_type=btype,
                        total_beds=total,
                        available_beds=avail
                    )
                    db.session.add(inv)
                
                count += 1
        
        db.session.commit()
        print(f"Successfully added {count} dummy hospitals across India.")

if __name__ == "__main__":
    generate_hospitals()
