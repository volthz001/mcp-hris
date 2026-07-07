from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from db import mongo

home_bp = Blueprint('home', __name__)

@home_bp.route('/home/summary', methods=['GET'])
@jwt_required()
def home_summary():
    user_id = get_jwt_identity()
    now = datetime.utcnow()
    month, year = now.month, now.year

    records = list(mongo.db.attendances.find({
        'user_id': user_id,
        'month': month,
        'year': year,
    }))

    hadir = sum(1 for r in records if r.get('status') == 'hadir')
    izin  = sum(1 for r in records if r.get('status') == 'izin')
    alpha = sum(1 for r in records if r.get('status') == 'alpha')

    payslip = mongo.db.payrolls.find_one(
        {'user_id': user_id},
        sort=[('year', -1), ('month', -1)]
    )

    return jsonify({
        'hadir': hadir,
        'izin': izin,
        'alpha': alpha,
        'total_hari_kerja': hadir + izin + alpha,
        'payslip_bulan': f"{payslip['month_label']}" if payslip else None,
        'gaji_terakhir': payslip.get('take_home_pay') if payslip else None,
    })