"""
seed_data.py — Populates the database with 59 hospitals across 21 Indian cities.
Usage: python seed_data.py
"""
import json, os, sys, pathlib

# ── Step 1: locate project root and guarantee instance/ folder ────────────────
project_root  = pathlib.Path(__file__).parent.resolve()
instance_dir  = project_root / 'instance'
instance_dir.mkdir(parents=True, exist_ok=True)   # MUST exist before SQLAlchemy

print(f"Project root : {project_root}")
print(f"Instance dir : {instance_dir}")

# ── Step 2: put project root first on sys.path (fixes Windows 'app' conflict) ─
for key in list(sys.modules.keys()):
    if key == 'app' or key.startswith('app.'):
        del sys.modules[key]

root_str = str(project_root)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

# ── Step 3: verify local app package exists ───────────────────────────────────
app_init = project_root / 'app' / '__init__.py'
if not app_init.exists():
    print(f"\nERROR: Cannot find {app_init}")
    print("Run this script from the EMERGIX project folder (where run.py lives).")
    sys.exit(1)

from app import create_app
from app.extensions import db
from app.models import User, Hospital, BedInventory, BED_TYPES

app = create_app('development')
print(f"Database     : {app.config['SQLALCHEMY_DATABASE_URI']}\n")


def seed():
    with app.app_context():
        print("Dropping old schema and recreating with latest models...")
        db.drop_all()
        db.create_all()

        # ── Load hospital JSON ────────────────────────────────────────────────
        json_path = project_root / 'seed_hospitals.json'
        with open(json_path) as f:
            hospitals_data = json.load(f)

        cities = sorted(set(h['city'] for h in hospitals_data))
        print(f"Seeding {len(hospitals_data)} hospitals across {len(cities)} cities...")
        print(f"Cities: {', '.join(cities)}\n")

        created = []
        for h_data in hospitals_data:
            hospital = Hospital(
                name=h_data['name'],         address=h_data['address'],
                city=h_data.get('city','India'), state='India',
                pincode=h_data.get('pincode'),   phone=h_data.get('phone'),
                email=h_data.get('email'),       website=h_data.get('website'),
                latitude=h_data['latitude'],     longitude=h_data['longitude'],
                hospital_type=h_data.get('hospital_type','government'),
                established=h_data.get('established'),
                emergency_24h=h_data.get('emergency_24h', True),
                ambulance=h_data.get('ambulance', False),
                description=h_data.get('description',''),
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
        print(f"{'─'*68}")
        print(f"  {'#':<5} {'Username':<14} {'Password':<12} Hospital (City)")
        print(f"{'─'*68}")

        for i, hospital in enumerate(created, 1):
            admin = User(
                full_name=f"Admin – {hospital.name}",
                username=f"admin_{i}",
                email=f"admin{i}@emergix.health",
                phone=f"9861{i:06d}",
                role='hospital_admin', is_management=True,
                hospital_id=hospital.id, auth_provider='local',
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            label = f"{hospital.name[:30]} ({hospital.city})"
            print(f"  {i:<5} {'admin_'+str(i):<14} {'Admin@123':<12} {label}")

        # Legacy management user (backward compat)
        mgmt = User(
            full_name='Management Admin', username='management',
            email='management@emergix.health', phone='9999999999',
            role='hospital_admin', is_management=True,
            hospital_id=created[0].id, auth_provider='local',
        )
        mgmt.set_password('management123')
        db.session.add(mgmt)

        # Demo patient
        patient = User(
            full_name='Demo Patient', username='demo_patient',
            email='demo@emergix.health', phone='9800000001',
            role='patient', auth_provider='local',
        )
        patient.set_password('Demo@1234')
        db.session.add(patient)

        db.session.commit()

        print(f"{'─'*68}")
        print(f"\n  Legacy admin  → username: management       password: management123")
        print(f"  Demo patient  → email: demo@emergix.health  password: Demo@1234")
        print(f"\n✅  Seed complete!  Now run:  python run.py\n")


if __name__ == '__main__':
    seed()
