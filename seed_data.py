"""
seed_data.py — Populates database with 59 hospitals across 21 Indian cities.
Usage: python seed_data.py
"""
import json, os, sys

# ── Force local app/ package (prevents Windows path conflicts) ────────────
project_root = os.path.dirname(os.path.abspath(__file__))
for key in list(sys.modules.keys()):
    if key == 'app' or key.startswith('app.'):
        del sys.modules[key]
if project_root in sys.path:
    sys.path.remove(project_root)
sys.path.insert(0, project_root)

app_init = os.path.join(project_root, 'app', '__init__.py')
if not os.path.exists(app_init):
    print(f"ERROR: Cannot find app/__init__.py at {app_init}")
    print("Run this script from the EMERGIX_build/ directory.")
    sys.exit(1)

from app import create_app
from app.extensions import db
from app.models import User, Hospital, BedInventory, BED_TYPES

app = create_app('development')


def seed():
    with app.app_context():
        db.create_all()

        print("Clearing existing data...")
        BedInventory.query.delete()
        Hospital.query.delete()
        User.query.delete()
        db.session.commit()

        json_path = os.path.join(project_root, 'seed_hospitals.json')
        with open(json_path) as f:
            hospitals_data = json.load(f)

        print(f"Seeding {len(hospitals_data)} hospitals...")
        cities = set(h['city'] for h in hospitals_data)
        print(f"  Cities: {', '.join(sorted(cities))}\n")

        created = []
        for h_data in hospitals_data:
            hospital = Hospital(
                name=h_data['name'], address=h_data['address'],
                city=h_data.get('city', 'India'), state='India',
                pincode=h_data.get('pincode'), phone=h_data.get('phone'),
                email=h_data.get('email'), website=h_data.get('website'),
                latitude=h_data['latitude'], longitude=h_data['longitude'],
                hospital_type=h_data.get('hospital_type', 'government'),
                established=h_data.get('established'),
                emergency_24h=h_data.get('emergency_24h', True),
                ambulance=h_data.get('ambulance', False),
                description=h_data.get('description', ''),
                is_active=True,
            )
            db.session.add(hospital)
            db.session.flush()

            for bed_type in BED_TYPES:
                counts = h_data.get('beds', {}).get(bed_type, [10, 7])
                db.session.add(BedInventory(
                    hospital_id=hospital.id, bed_type=bed_type,
                    total_beds=counts[0], available_beds=counts[1],
                ))
            created.append(hospital)

        db.session.commit()
        print(f"✓ {len(created)} hospitals created\n")

        # ── Admin users ───────────────────────────────────────────────────────
        print("Creating admin accounts...")
        print(f"\n{'─'*62}")
        print(f"  {'#':<4} {'Username':<14} {'Hospital (City)':<38} {'Password'}")
        print(f"{'─'*62}")

        for i, hospital in enumerate(created, 1):
            admin = User(
                full_name=f"Admin – {hospital.name}",
                username=f"admin_{i}",
                email=f"admin{i}@emergix.health",
                phone=f"9861{i:06d}",
                role='hospital_admin', is_management=True,
                hospital_id=hospital.id,
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            label = f"{hospital.name[:28]} ({hospital.city})"
            print(f"  {i:<4} {'admin_'+str(i):<14} {label:<38} Admin@123")

        # Legacy management user
        mgmt = User(
            full_name='Management Admin', username='management',
            email='management@emergix.health', phone='9999999999',
            role='hospital_admin', is_management=True,
            hospital_id=created[0].id,
        )
        mgmt.set_password('management123')
        db.session.add(mgmt)

        # Demo patient
        patient = User(
            full_name='Demo Patient', username='demo_patient',
            email='demo@emergix.health', phone='9800000001',
            role='patient',
        )
        patient.set_password('Demo@1234')
        db.session.add(patient)

        db.session.commit()
        print(f"{'─'*62}")
        print(f"\n  Legacy admin  → username: management    / password: management123")
        print(f"  Demo patient  → email: demo@emergix.health / password: Demo@1234")
        print(f"\n✅  Seed complete!  Run: python run.py\n")


if __name__ == '__main__':
    seed()
