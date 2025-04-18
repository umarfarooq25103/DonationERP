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

@app.route('/api/recipient/<int:recipient_id>/vouchers', methods=['GET'])
def get_recipient_vouchers(recipient_id):
    try:
        # Check if recipient exists
        recipient = Recipient.query.get(recipient_id)
        if not recipient:
            return jsonify({"error": "Recipient not found"}), 404
        
        # Get recent vouchers for this recipient (limit to 5)
        vouchers = Voucher.query.filter_by(recipient_id=recipient_id).order_by(desc(Voucher.donation_date)).limit(5).all()
        
        # Format the response
        voucher_list = []
        for voucher in vouchers:
            voucher_list.append({
                'id': voucher.id,
                'donation_type': voucher.donation_type,
                'amount': float(voucher.amount),
                'donation_mode': voucher.donation_mode,
                'donation_date': voucher.donation_date.strftime('%d-%m-%Y'),
                'notes': voucher.notes
            })
        
        return jsonify({
            'recipient': {
                'id': recipient.id,
                'name': recipient.name,
                'cnic': recipient.cnic
            },
            'vouchers': voucher_list
        })
    except Exception as e:
        app.logger.error(f"Error fetching recipient vouchers: {str(e)}")
        return jsonify({"error": "An error occurred while fetching recipient vouchers"}), 500

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
            payment_method = request.form.get('payment_method', 'cash')
            
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
            return redirect(url_for('view_voucher', voucher_id=new_voucher.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating voucher: {str(e)}', 'danger')
            return redirect(url_for('create_voucher'))
    
    # GET request
    recipients = Recipient.query.all()
    vouchers_count = Voucher.query.count()
    
    # Check if we have a recipient_id in the query parameters
    recipient_id = request.args.get('recipient_id')
    selected_recipient = None
    if recipient_id:
        try:
            selected_recipient = Recipient.query.get(int(recipient_id))
        except:
            pass
    
    return render_template(
        'create_voucher.html',
        recipients=recipients,
        vouchers_count=vouchers_count,
        selected_recipient=selected_recipient
    )

@app.route('/vouchers/<int:voucher_id>', methods=['GET'])
def view_voucher(voucher_id):
    voucher = Voucher.query.get_or_404(voucher_id)
    recipient = Recipient.query.get(voucher.recipient_id)
    
    return render_template('view_voucher.html', 
                           voucher=voucher, 
                           recipient=recipient)

# Reporting
@app.route('/reports', methods=['GET'])
def reports():
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    donation_type = request.args.get('donation_type')
    donation_mode = request.args.get('donation_mode')
    recipient_name = request.args.get('recipient_name')
    report_type = request.args.get('report_type', 'daily')  # Default to daily report
    
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
    
    if donation_mode and donation_mode != 'All':
        query = query.filter(Voucher.donation_mode == donation_mode)
    
    if recipient_name:
        query = query.filter(Recipient.name.ilike(f'%{recipient_name}%'))
    
    # Execute query
    vouchers = query.order_by(desc(Voucher.donation_date)).all()
    
    # Calculate totals by donation type
    totals_by_type = db.session.query(
        Voucher.donation_type,
        func.sum(Voucher.amount).label('total')
    )
    
    # Apply the same filters to the totals query
    if start_date:
        totals_by_type = totals_by_type.filter(Voucher.donation_date >= start_date)
    
    if end_date:
        totals_by_type = totals_by_type.filter(Voucher.donation_date <= end_date)
    
    if recipient_name:
        totals_by_type = totals_by_type.join(Recipient).filter(Recipient.name.ilike(f'%{recipient_name}%'))
    
    if donation_mode and donation_mode != 'All':
        totals_by_type = totals_by_type.filter(Voucher.donation_mode == donation_mode)
    
    # Group and execute
    totals_by_type = totals_by_type.group_by(Voucher.donation_type).all()
    
    # Convert to dictionary for easy access in template
    totals = {t.donation_type: t.total for t in totals_by_type}
    
    # Get grand total
    grand_total = sum(t.total for t in totals_by_type) if totals_by_type else 0
    
    # Get monthly/yearly summaries if needed
    monthly_summary = None
    yearly_summary = None
    
    if report_type == 'monthly' or report_type == 'yearly':
        # Monthly summary
        monthly_query = db.session.query(
            extract('year', Voucher.donation_date).label('year'),
            extract('month', Voucher.donation_date).label('month'),
            func.sum(Voucher.amount).label('total')
        )
        
        # Apply the same filters
        if start_date:
            monthly_query = monthly_query.filter(Voucher.donation_date >= start_date)
        
        if end_date:
            monthly_query = monthly_query.filter(Voucher.donation_date <= end_date)
        
        if donation_type and donation_type != 'All':
            monthly_query = monthly_query.filter(Voucher.donation_type == donation_type)
        
        if donation_mode and donation_mode != 'All':
            monthly_query = monthly_query.filter(Voucher.donation_mode == donation_mode)
        
        if recipient_name:
            monthly_query = monthly_query.join(Recipient).filter(Recipient.name.ilike(f'%{recipient_name}%'))
        
        # Group and execute
        monthly_summary = monthly_query.group_by('year', 'month').order_by('year', 'month').all()
    
    if report_type == 'yearly':
        # Yearly summary
        yearly_query = db.session.query(
            extract('year', Voucher.donation_date).label('year'),
            func.sum(Voucher.amount).label('total')
        )
        
        # Apply the same filters
        if start_date:
            yearly_query = yearly_query.filter(Voucher.donation_date >= start_date)
        
        if end_date:
            yearly_query = yearly_query.filter(Voucher.donation_date <= end_date)
        
        if donation_type and donation_type != 'All':
            yearly_query = yearly_query.filter(Voucher.donation_type == donation_type)
        
        if donation_mode and donation_mode != 'All':
            yearly_query = yearly_query.filter(Voucher.donation_mode == donation_mode)
        
        if recipient_name:
            yearly_query = yearly_query.join(Recipient).filter(Recipient.name.ilike(f'%{recipient_name}%'))
        
        # Group and execute
        yearly_summary = yearly_query.group_by('year').order_by('year').all()
    
    # Get list of all donation types and modes for filtering
    all_donation_types = db.session.query(Voucher.donation_type).distinct().all()
    all_donation_types = [dt[0] for dt in all_donation_types]
    
    all_donation_modes = db.session.query(Voucher.donation_mode).distinct().all()
    all_donation_modes = [dm[0] for dm in all_donation_modes]
    
    return render_template(
        'reports.html',
        vouchers=vouchers,
        totals=totals,
        grand_total=grand_total,
        monthly_summary=monthly_summary,
        yearly_summary=yearly_summary,
        all_donation_types=all_donation_types,
        all_donation_modes=all_donation_modes,
        report_type=report_type,
        current_filters={
            'start_date': start_date,
            'end_date': end_date,
            'donation_type': donation_type,
            'donation_mode': donation_mode,
            'recipient_name': recipient_name,
            'report_type': report_type
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
    donation_mode = request.args.get('donation_mode')
    recipient_name = request.args.get('recipient_name')
    report_type = request.args.get('report_type', 'daily')
    
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
    
    if donation_mode and donation_mode != 'All':
        query = query.filter(Voucher.donation_mode == donation_mode)
    
    if recipient_name:
        query = query.filter(Recipient.name.ilike(f'%{recipient_name}%'))
    
    # Execute query
    vouchers = query.order_by(desc(Voucher.donation_date)).all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    if report_type == 'daily':
        # Detailed report with all vouchers
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
    
    elif report_type == 'monthly':
        # Monthly summary report
        monthly_query = db.session.query(
            extract('year', Voucher.donation_date).label('year'),
            extract('month', Voucher.donation_date).label('month'),
            Voucher.donation_type,
            func.sum(Voucher.amount).label('total')
        )
        
        # Apply the same filters
        if start_date:
            monthly_query = monthly_query.filter(Voucher.donation_date >= start_date)
        
        if end_date:
            monthly_query = monthly_query.filter(Voucher.donation_date <= end_date)
        
        if donation_type and donation_type != 'All':
            monthly_query = monthly_query.filter(Voucher.donation_type == donation_type)
        
        if donation_mode and donation_mode != 'All':
            monthly_query = monthly_query.filter(Voucher.donation_mode == donation_mode)
        
        if recipient_name:
            monthly_query = monthly_query.join(Recipient).filter(Recipient.name.ilike(f'%{recipient_name}%'))
        
        # Group and execute
        monthly_data = monthly_query.group_by('year', 'month', Voucher.donation_type).order_by('year', 'month').all()
        
        # Write header
        writer.writerow(['Year', 'Month', 'Donation Type', 'Total Amount'])
        
        # Write data
        for year, month, donation_type, total in monthly_data:
            month_name = datetime(2000, int(month), 1).strftime('%B')
            writer.writerow([int(year), f"{int(month)} - {month_name}", donation_type, total])
    
    elif report_type == 'yearly':
        # Yearly summary report
        yearly_query = db.session.query(
            extract('year', Voucher.donation_date).label('year'),
            Voucher.donation_type,
            func.sum(Voucher.amount).label('total')
        )
        
        # Apply the same filters
        if start_date:
            yearly_query = yearly_query.filter(Voucher.donation_date >= start_date)
        
        if end_date:
            yearly_query = yearly_query.filter(Voucher.donation_date <= end_date)
        
        if donation_type and donation_type != 'All':
            yearly_query = yearly_query.filter(Voucher.donation_type == donation_type)
        
        if donation_mode and donation_mode != 'All':
            yearly_query = yearly_query.filter(Voucher.donation_mode == donation_mode)
        
        if recipient_name:
            yearly_query = yearly_query.join(Recipient).filter(Recipient.name.ilike(f'%{recipient_name}%'))
        
        # Group and execute
        yearly_data = yearly_query.group_by('year', Voucher.donation_type).order_by('year').all()
        
        # Write header
        writer.writerow(['Year', 'Donation Type', 'Total Amount'])
        
        # Write data
        for year, donation_type, total in yearly_data:
            writer.writerow([int(year), donation_type, total])
    
    # Create file name based on report type
    filename = f"donation_report_{report_type}"
    if start_date:
        filename += f"_from_{start_date.strftime('%Y-%m-%d')}"
    if end_date:
        filename += f"_to_{end_date.strftime('%Y-%m-%d')}"
    filename += ".csv"
    
    # Create response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
