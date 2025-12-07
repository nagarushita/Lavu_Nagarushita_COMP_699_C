from datetime import datetime
from app import db

class AlertRule(db.Model):
    __tablename__ = 'alert_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    rule_type = db.Column(db.String(50), nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    threshold_value = db.Column(db.Float, nullable=False)
    threshold_unit = db.Column(db.String(20), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    notify_email = db.Column(db.Boolean, default=False)
    escalation_minutes = db.Column(db.Integer, default=10)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    alerts = db.relationship('Alert', backref='rule', lazy='dynamic')
    
    def __repr__(self):
        return f'<AlertRule {self.name}>'


class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('alert_rules.id'), nullable=False, index=True)
    triggered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')
    triggered_value = db.Column(db.Float, nullable=False)
    details = db.Column(db.Text, nullable=True)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def __repr__(self):
        return f'<Alert {self.id} - Rule {self.rule_id}>'
