from flask import Blueprint, render_template, session
from app.models import LiveAlert, BED_TYPE_LABELS, BED_TYPE_ICONS
from app.utils.decorators import login_required

user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/dashboard')
@login_required
def dashboard():
    alerts = LiveAlert.query.filter_by(user_id=session['user_id'])\
        .order_by(LiveAlert.created_at.desc()).all()
    return render_template('user/dashboard.html',
                           alerts=alerts,
                           bed_type_labels=BED_TYPE_LABELS,
                           bed_type_icons=BED_TYPE_ICONS)
