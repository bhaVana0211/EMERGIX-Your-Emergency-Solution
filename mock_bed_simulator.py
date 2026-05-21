"""
mock_bed_simulator.py — Simulates live bed count changes for demo purposes.
Run as a separate process: python mock_bed_simulator.py
"""
import os
import sys
import time
import random
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [SIMULATOR] %(message)s')
logger = logging.getLogger(__name__)


def run_simulator(interval_min=20, interval_max=60):
    from app import create_app
    from app.extensions import db, socketio
    from app.models import BedInventory

    app = create_app('development')

    logger.info(f"Bed simulator started (interval: {interval_min}–{interval_max}s)")

    with app.app_context():
        while True:
            sleep_time = random.randint(interval_min, interval_max)
            time.sleep(sleep_time)

            try:
                # Pick 2–4 random bed inventory rows and adjust them
                all_beds = BedInventory.query.all()
                if not all_beds:
                    continue
                selected = random.sample(all_beds, min(random.randint(2, 4), len(all_beds)))

                for bed in selected:
                    if bed.total_beds == 0:
                        continue
                    # Randomly increment or decrement by 1–3
                    delta = random.choice([-3, -2, -1, -1, 1, 1, 2, 3])
                    new_available = bed.available_beds + delta
                    new_available = max(0, min(bed.total_beds, new_available))
                    bed.available_beds = new_available

                db.session.commit()

                # Emit bed_updated events via socketio if running
                try:
                    for bed in selected:
                        socketio.emit('bed_updated', {
                            'hospital_id': bed.hospital_id,
                            'bed_type': bed.bed_type,
                            'available_beds': bed.available_beds,
                            'total_beds': bed.total_beds,
                            'occupancy_pct': bed.occupancy_pct(),
                        }, namespace='/')
                except Exception:
                    pass  # Socketio not running standalone

                for bed in selected:
                    logger.info(f"  Hospital {bed.hospital_id} | {bed.bed_type}: "
                                f"{bed.available_beds}/{bed.total_beds} available")

            except Exception as e:
                logger.error(f"Simulator error: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass


if __name__ == '__main__':
    run_simulator(interval_min=15, interval_max=45)
