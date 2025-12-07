from datetime import datetime, timedelta
from app import db, socketio
from app.models.alert import AlertRule, Alert

class AlertEngine:
    
    def evaluate_rules(self, metrics):
        """Evaluate all active rules against current metrics"""
        rules = AlertRule.query.filter_by(is_active=True).all()
        triggered_alerts = []
        
        for rule in rules:
            if self._check_rule_condition(rule, metrics):
                alert = self.create_alert(
                    rule,
                    metrics.get(rule.rule_type, 0),
                    f'{rule.rule_type} threshold exceeded'
                )
                triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def _check_rule_condition(self, rule, metrics):
        """Check if rule condition is met"""
        metric_value = metrics.get(rule.rule_type, 0)
        threshold = rule.threshold_value
        condition = rule.condition
        
        if condition == 'greater_than':
            return metric_value > threshold
        elif condition == 'less_than':
            return metric_value < threshold
        elif condition == 'equals':
            return metric_value == threshold
        
        return False
    
    def create_alert(self, rule, value, details):
        """Create new alert"""
        # Check if similar alert exists in last 5 minutes
        recent_alert = Alert.query.filter(
            Alert.rule_id == rule.id,
            Alert.status == 'active',
            Alert.triggered_at >= datetime.utcnow() - timedelta(minutes=5)
        ).first()
        
        if recent_alert:
            return recent_alert
        
        alert = Alert(
            rule_id=rule.id,
            triggered_value=value,
            details=details,
            status='active'
        )
        db.session.add(alert)
        db.session.commit()
        
        # Emit websocket notification
        socketio.emit('new_alert', {
            'alert_id': alert.id,
            'rule_name': rule.name,
            'severity': rule.severity,
            'value': value,
            'timestamp': alert.triggered_at.isoformat()
        })
        
        return alert
    
    def acknowledge_alert(self, alert_id, user_id):
        """Acknowledge an alert"""
        alert = Alert.query.get(alert_id)
        if not alert:
            return {'success': False, 'message': 'Alert not found'}
        
        alert.status = 'acknowledged'
        alert.acknowledged_by = user_id
        db.session.commit()
        
        return {'success': True}
    
    def resolve_alert(self, alert_id, user_id, notes=''):
        """Resolve an alert"""
        alert = Alert.query.get(alert_id)
        if not alert:
            return {'success': False, 'message': 'Alert not found'}
        
        alert.status = 'resolved'
        alert.resolved_at = datetime.utcnow()
        alert.acknowledged_by = user_id
        alert.details = f'{alert.details}\n\nResolution notes: {notes}'
        db.session.commit()
        
        return {'success': True}
    
    def escalate_alert(self, alert_id):
        """Escalate an alert"""
        alert = Alert.query.get(alert_id)
        if not alert:
            return {'success': False, 'message': 'Alert not found'}
        
        # Emit escalation notification
        socketio.emit('alert_escalated', {
            'alert_id': alert.id,
            'rule_name': alert.rule.name,
            'severity': alert.rule.severity
        })
        
        return {'success': True}
    
    def check_escalations(self):
        """Check for alerts that need escalation"""
        escalation_candidates = Alert.query.join(AlertRule).filter(
            Alert.status == 'active',
            Alert.acknowledged_by.is_(None),
            Alert.triggered_at < datetime.utcnow() - db.text('alert_rules.escalation_minutes * INTERVAL \'1 minute\'')
        ).all()
        
        for alert in escalation_candidates:
            self.escalate_alert(alert.id)
        
        return len(escalation_candidates)
    
    def get_alert_statistics(self):
        """Get alert statistics"""
        # Count by severity
        critical_count = Alert.query.join(AlertRule).filter(
            Alert.status == 'active',
            AlertRule.severity == 'critical'
        ).count()
        
        high_count = Alert.query.join(AlertRule).filter(
            Alert.status == 'active',
            AlertRule.severity == 'high'
        ).count()
        
        medium_count = Alert.query.join(AlertRule).filter(
            Alert.status == 'active',
            AlertRule.severity == 'medium'
        ).count()
        
        total_count = Alert.query.filter_by(status='active').count()
        
        # Calculate MTTA (Mean Time To Acknowledge)
        acknowledged_alerts = Alert.query.filter(
            Alert.acknowledged_by.isnot(None),
            Alert.triggered_at >= datetime.utcnow() - timedelta(days=7)
        ).all()
        
        if acknowledged_alerts:
            ack_times = [
                (a.resolved_at or datetime.utcnow()) - a.triggered_at
                for a in acknowledged_alerts
            ]
            mtta_seconds = sum(t.total_seconds() for t in ack_times) / len(ack_times)
            mtta_minutes = mtta_seconds / 60
        else:
            mtta_minutes = 0
        
        # Calculate MTTR (Mean Time To Resolve)
        resolved_alerts = Alert.query.filter(
            Alert.status == 'resolved',
            Alert.resolved_at >= datetime.utcnow() - timedelta(days=7)
        ).all()
        
        if resolved_alerts:
            resolve_times = [
                a.resolved_at - a.triggered_at
                for a in resolved_alerts if a.resolved_at
            ]
            mttr_seconds = sum(t.total_seconds() for t in resolve_times) / len(resolve_times)
            mttr_minutes = mttr_seconds / 60
        else:
            mttr_minutes = 0
        
        return {
            'critical': critical_count,
            'high': high_count,
            'medium': medium_count,
            'total': total_count,
            'mtta_minutes': round(mtta_minutes, 2),
            'mttr_minutes': round(mttr_minutes, 2)
        }
    
    def get_hourly_alert_counts(self, hours=24):
        """Get alert counts per hour for the specified time range"""
        from sqlalchemy import func
        
        now = datetime.utcnow()
        start_time = now - timedelta(hours=hours)
        
        # Query alerts grouped by hour
        hourly_data = db.session.query(
            func.strftime('%Y-%m-%d %H:00:00', Alert.triggered_at).label('hour'),
            func.count(Alert.id).label('count')
        ).filter(
            Alert.triggered_at >= start_time
        ).group_by('hour').all()
        
        # Create a complete hourly array
        hourly_counts = [0] * hours
        data_dict = {row.hour: row.count for row in hourly_data}
        
        for i in range(hours):
            hour_time = (start_time + timedelta(hours=i)).strftime('%Y-%m-%d %H:00:00')
            if hour_time in data_dict:
                hourly_counts[i] = data_dict[hour_time]
        
        return hourly_counts
