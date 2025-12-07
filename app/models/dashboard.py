from datetime import datetime
from app import db

class Dashboard(db.Model):
    __tablename__ = 'dashboards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    is_default = db.Column(db.Boolean, default=False)
    layout_config = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    widgets = db.relationship('Widget', backref='dashboard', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Dashboard {self.name}>'


class Widget(db.Model):
    __tablename__ = 'widgets'
    
    id = db.Column(db.Integer, primary_key=True)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('dashboards.id'), nullable=False, index=True)
    widget_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    data_source = db.Column(db.String(100), nullable=False)
    position_x = db.Column(db.Integer, nullable=False)
    position_y = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    config = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Widget {self.title}>'
