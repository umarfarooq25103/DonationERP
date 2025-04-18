from datetime import datetime
from app import db

class Recipient(db.Model):
    __tablename__ = 'recipients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cnic = db.Column(db.String(13), unique=True, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    monthly_income = db.Column(db.Float, nullable=False)
    family_data = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with vouchers
    vouchers = db.relationship('Voucher', backref='recipient', lazy=True)
    
    def __repr__(self):
        return f"<Recipient {self.name}>"

class Voucher(db.Model):
    __tablename__ = 'vouchers'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('recipients.id'), nullable=False)
    donation_type = db.Column(db.String(50), nullable=False)  # Zakat, Sadqa, Other
    amount = db.Column(db.Float, nullable=False)
    donation_mode = db.Column(db.String(50), nullable=False)  # One-time, Monthly
    donation_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Voucher #{self.id} for {self.recipient_id}>"
