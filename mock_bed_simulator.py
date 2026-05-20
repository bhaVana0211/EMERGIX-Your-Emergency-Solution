"""
EMERGIX — Mock Bed Simulator
Randomly updates bed availability to simulate real-world bed turnover.
Runs as a background thread in development or as a standalone script.
"""

import os
import sys
import time
import random
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('emergix.simulator')


def run_simulator(app=None, socketio=None):
    """Run the bed simulator. Updates random beds every 30-120 seconds."""
    if app is None:
        from Emergix import create_app, socketio as sio
        app = create_app()
        socketio = sio

    logger.info("Mock bed simulator started")

    with app.app_context():
        from Emergix.models import db, BedInventory, Hospital
        from datetime import datetime, timezone

        while True:
            try:
                # Random delay between 30-120 seconds
                delay = random.randint(30, 120)
                time.sleep(delay)

                # Pick a random hospital
                hospitals = Hospital.query.filter_by(is_active=True).all()
                if not hospitals:
                    continue

                hospital = random.choice(hospitals)
                inventory_items = BedInventory.query.filter_by(hospital_id=hospital.id).all()

                if not inventory_items:
                    continue

                # Pick a random bed type
                item = random.choice(inventory_items)

                # Randomly increment or decrement available beds
                change = random.choice([-1, -1, 1, 1, 1])  # Slight bias toward freeing beds
                new_available = item.available_beds + change

                # Clamp to valid range
                new_available = max(0, min(new_available, item.total_beds))

                if new_available != item.available_beds:
                    item.available_beds = new_available
                    item.last_updated = datetime.now(timezone.utc)
                    db.session.commit()

                    logger.info(
                        f"  📊 {hospital.name} | {item.bed_type}: "
                        f"{item.available_beds}/{item.total_beds} available"
                    )

                    # Emit WebSocket event
                    if socketio:
                        socketio.emit('bed_updated', {
                            'hospital_id': hospital.id,
                            'bed_type': item.bed_type,
                            'available_beds': item.available_beds,
                            'total_beds': item.total_beds,
                            'occupancy_pct': item.occupancy_pct,
                            'updated_at': item.last_updated.isoformat()
                        })

            except Exception as e:
                logger.error(f"Simulator error: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass
                time.sleep(10)


if __name__ == '__main__':
    run_simulator()
