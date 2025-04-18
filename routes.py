import json
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import extract, desc, func
from app import app, db
from models import Recipient, Voucher

# Make current datetime available to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

# Load FRC data from JSON file
def load_frc_data():
    try:
        with open('frc_data.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        app.logger.error(f"Error loading FRC data: {e}")
        return {}

# Home route
@app.route('/')
def index():
    # Get some statistics for the dashboard
    recipient_count = Recipient.query.count()
    voucher_count = Voucher.query.count()
    total_donations = db.session.query(func.sum(Voucher.amount)).scalar() or 0
    
    # Get recent vouchers
    recent_vouchers = Voucher.query.order_by(desc(Voucher.created_at)).limit(5).all()
    
    return render_template('index.html', 
                          recipient_count=recipient_count,
                          voucher_count=voucher_count,
                          total_donations=total_donations,
                          recent_vouchers=recent_vouchers)

# Recipient Management
@app.route('/recipients', methods=['GET'])
def list_recipients():
    recipients = Recipient.query.all()
    return render_template('add_recipient.html', recipients=recipients)

@app.route('/recipients/add', methods=['GET', 'POST'])
def add_recipient():
    if request.method == 'POST':
        try:
            name = request.form['name']
            cnic = request.form['cnic']
            address = request.form['address']
            phone = request.form['phone']
            monthly_income = float(request.form['monthly_income'])
            family_data = request.form.get('family_data', '')
            
            # Check if recipient with this CNIC already exists
            existing_recipient = Recipient.query.filter_by(cnic=cnic).first()
            if existing_recipient:
                flash('A recipient with this CNIC already exists.', 'danger')
                return redirect(url_for('add_recipient'))
            
            # Create new recipient
            new_recipient = Recipient(
                name=name,
                cnic=cnic,
                address=address,
                phone=phone,
                monthly_income=monthly_income,
                family_data=family_data
            )
            
            db.session.add(new_recipient)
            db.session.commit()
            
            flash('Recipient added successfully!', 'success')
            return redirect(url_for('add_recipient'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding recipient: {str(e)}', 'danger')
            return redirect(url_for('add_recipient'))
    
    # GET request
    recipients = Recipient.query.all()
    return render_template('add_recipient.html', recipients=recipients)

@app.route('/api/frc/<cnic>', methods=['GET'])
def get_frc_data(cnic):
    frc_data = load_frc_data()
    if cnic in frc_data:
        return jsonify(frc_data[cnic])
    return jsonify({"error": "CNIC not found in FRC database"}), 404

# Voucher Creation
@app.route('/vouchers/create', methods=['GET', 'POST'])
def create_voucher():
    if request.method == 'POST':
        try:
            recipient_id = request.form['recipient_id']
            donation_type = request.form['donation_type']
            amount = float(request.form['amount'])
            donation_mode = request.form['donation_mode']
            donation_date = datetime.strptime(request.form['donation_date'], '%Y-%m-%d').date()
            notes = request.form.get('notes', '')
            
            # Create new voucher
            new_voucher = Voucher(
                recipient_id=recipient_id,
                donation_type=donation_type,
                amount=amount,
                donation_mode=donation_mode,
                donation_date=donation_date,
                notes=notes
            )
            
            db.session.add(new_voucher)
            db.session.commit()
            
            flash('Voucher created successfully!', 'success')
            return redirect(url_for('create_voucher'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating voucher: {str(e)}', 'danger')
            return redirect(url_for('create_voucher'))
    
    # GET request
    recipients = Recipient.query.all()
    return render_template('create_voucher.html', recipients=recipients)

# Reporting
@app.route('/reports', methods=['GET'])
def reports():
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    donation_type = request.args.get('donation_type')
    recipient_name = request.args.get('recipient_name')
    
    # Start with base query
    query = db.session.query(
        Voucher, 
        Recipient.name.label('recipient_name')
    ).join(Recipient)
    
    # Apply filters
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        query = query.filter(Voucher.donation_date >= start_date)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        query = query.filter(Voucher.donation_date <= end_date)
    
    if donation_type and donation_type != 'All':
        query = query.filter(Voucher.donation_type == donation_type)
    
    if recipient_name:
        query = query.filter(Recipient.name.ilike(f'%{recipient_name}%'))
    
    # Execute query
    vouchers = query.order_by(desc(Voucher.donation_date)).all()
    
    # Calculate totals by donation type
    totals_by_type = db.session.query(
        Voucher.donation_type,
        func.sum(Voucher.amount).label('total')
    ).group_by(Voucher.donation_type).all()
    
    # Convert to dictionary for easy access in template
    totals = {t.donation_type: t.total for t in totals_by_type}
    
    # Get grand total
    grand_total = sum(t.total for t in totals_by_type)
    
    return render_template(
        'reports.html',
        vouchers=vouchers,
        totals=totals,
        grand_total=grand_total,
        current_filters={
            'start_date': start_date,
            'end_date': end_date,
            'donation_type': donation_type,
            'recipient_name': recipient_name
        }
    )

# Export to CSV
@app.route('/reports/export', methods=['GET'])
def export_reports():
    import csv
    from io import StringIO
    from flask import Response
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    donation_type = request.args.get('donation_type')
    recipient_name = request.args.get('recipient_name')
    
    # Start with base query
    query = db.session.query(
        Voucher, 
        Recipient.name.label('recipient_name'),
        Recipient.cnic.label('recipient_cnic')
    ).join(Recipient)
    
    # Apply filters
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        query = query.filter(Voucher.donation_date >= start_date)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        query = query.filter(Voucher.donation_date <= end_date)
    
    if donation_type and donation_type != 'All':
        query = query.filter(Voucher.donation_type == donation_type)
    
    if recipient_name:
        query = query.filter(Recipient.name.ilike(f'%{recipient_name}%'))
    
    # Execute query
    vouchers = query.order_by(desc(Voucher.donation_date)).all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Voucher ID', 'Recipient Name', 'CNIC', 'Donation Type', 
                    'Amount', 'Donation Mode', 'Date', 'Notes'])
    
    # Write data
    for voucher, recipient_name, recipient_cnic in vouchers:
        writer.writerow([
            voucher.id,
            recipient_name,
            recipient_cnic,
            voucher.donation_type,
            voucher.amount,
            voucher.donation_mode,
            voucher.donation_date.strftime('%Y-%m-%d'),
            voucher.notes
        ])
    
    # Create response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=donation_report.csv"}
    )
