"""
EMERGIX — Seed Data Script
Loads hospital data and creates initial admin users and bed inventory.
Run: python seed_data.py
"""

import json
import os
import sys
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Emergix import create_app
from Emergix.models import db, User, Hospital, BedInventory


def slugify(name):
    """Convert hospital name to a slug for admin username."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '_', slug)
    slug = slug[:30]
    return slug


def seed(force=False):
    """Seed the database with hospital data."""
    app = create_app()

    with app.app_context():
        if force:
            print("Force re-seeding: dropping existing tables...")
            db.drop_all()
            
        # Create all tables
        db.create_all()

        # Check if already seeded
        if Hospital.query.count() > 0:
            print("Database already has hospital data. Skipping seed.")
            print(f"  Hospitals: {Hospital.query.count()}")
            print(f"  Users: {User.query.count()}")
            print(f"  Bed Inventory: {BedInventory.query.count()}")
            return

        # Load hospital data
        seed_file = os.path.join(os.path.dirname(__file__), 'seed_hospitals.json')
        with open(seed_file, 'r', encoding='utf-8') as f:
            hospitals_data = json.load(f)

        print(f"Seeding {len(hospitals_data)} hospitals...")

        for i, h_data in enumerate(hospitals_data, 1):
            # Create hospital
            hospital = Hospital(
                name=h_data['name'],
                address=h_data['address'],
                city=h_data['city'],
                state=h_data.get('state', 'Odisha'),
                pincode=h_data.get('pincode', ''),
                phone=h_data.get('phone', ''),
                email=h_data.get('email', ''),
                website=h_data.get('website', ''),
                latitude=h_data['latitude'],
                longitude=h_data['longitude'],
                hospital_type=h_data.get('hospital_type', 'government'),
                established=h_data.get('established'),
                emergency_24h=h_data.get('emergency_24h', True),
                ambulance=h_data.get('ambulance', False),
                is_active=True
            )
            db.session.add(hospital)
            db.session.flush()  # Get the hospital ID

            # Create admin user for this hospital
            admin_username = f"admin_{slugify(h_data['name'])}"
            admin_user = User(
                username=admin_username,
                email=f"admin{i}@emergix.in",
                phone=f"900000{i:04d}",
                role='hospital_admin',
                is_management=True,
                hospital_id=hospital.id
            )
            admin_user.set_password('Admin@123')
            db.session.add(admin_user)

            # Create bed inventory
            beds = h_data.get('beds', {})
            for bed_type, counts in beds.items():
                total, available = counts
                inventory = BedInventory(
                    hospital_id=hospital.id,
                    bed_type=bed_type,
                    total_beds=total,
                    available_beds=available
                )
                db.session.add(inventory)

            print(f"  [{i}/{len(hospitals_data)}] {h_data['name']} — admin: {admin_username}")

        # Create the legacy management user (backward compatibility)
        # Assign to hospital_id=1 (AIIMS Bhubaneswar)
        management_user = User.query.filter_by(username='management').first()
        if not management_user:
            management_user = User(
                username='management',
                email='management@emergix.in',
                role='hospital_admin',
                is_management=True,
                hospital_id=1
            )
            management_user.set_password('management123')
            db.session.add(management_user)
            print("\n  Created legacy management user (username: management, password: management123)")

        # Create a demo patient user
        demo_patient = User(
            username='priya',
            email='priya@example.com',
            phone='9876543210',
            role='patient',
            is_management=False
        )
        demo_patient.set_password('patient123')
        db.session.add(demo_patient)
        print("  Created demo patient user (username: priya, password: patient123)")

        db.session.commit()
        print(f"\n Seed complete!")
        print(f"   {Hospital.query.count()} hospitals")
        print(f"   {User.query.count()} users")
        print(f"   {BedInventory.query.count()} bed inventory records")
        print(f"\n Default credentials:")
        print(f"   Management: management / management123")
        print(f"   Hospital Admins: admin_<hospital_slug> / Admin@123")
        print(f"   Demo Patient: priya / patient123")


if __name__ == '__main__':
    force_reseed = '--force' in sys.argv
    seed(force=force_reseed)
