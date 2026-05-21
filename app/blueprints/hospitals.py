from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.models import Hospital, BED_TYPES, BED_TYPE_LABELS, BED_TYPE_ICONS
from app.utils.decorators import login_required
from app.utils.geo import build_maps_url

hospitals_bp = Blueprint('hospitals', __name__, url_prefix='/hospitals')


@hospitals_bp.route('/')
@login_required
def discovery():
    return render_template('hospitals/discovery.html',
                           bed_types=BED_TYPES,
                           bed_type_labels=BED_TYPE_LABELS,
                           bed_type_icons=BED_TYPE_ICONS)


@hospitals_bp.route('/<int:hospital_id>')
@login_required
def detail(hospital_id):
    hospital = Hospital.query.get_or_404(hospital_id)
    inventory = {b.bed_type: b for b in hospital.bed_inventory}

    user_lat = request.args.get('ulat', '')
    user_lng = request.args.get('ulng', '')
    maps_url = None
    if user_lat and user_lng:
        try:
            maps_url = build_maps_url(float(user_lat), float(user_lng),
                                      hospital.latitude, hospital.longitude)
        except ValueError:
            pass

    return render_template('hospitals/detail.html',
                           hospital=hospital,
                           inventory=inventory,
                           bed_types=BED_TYPES,
                           bed_type_labels=BED_TYPE_LABELS,
                           bed_type_icons=BED_TYPE_ICONS,
                           maps_url=maps_url,
                           user_lat=user_lat,
                           user_lng=user_lng)
