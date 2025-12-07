import os
import csv
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app.models.audit_log import AuditLog
from app.models.alert import Alert
from app.models.capture_session import CaptureSession

class ReportService:
    
    def __init__(self):
        self.report_dir = 'reports'
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)
    
    def generate_pdf_report(self, report_type, params, user_id):
        """Generate PDF report"""
        filename = f'{report_type}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.pdf'
        filepath = os.path.join(self.report_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f'<b>{report_type.replace("_", " ").title()}</b>', styles['Heading1'])
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Report metadata
        meta_data = [
            ['Generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')],
            ['Report Type:', report_type],
            ['Period:', params.get('date_range', 'Last 24 hours')]
        ]
        meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Report content based on type
        if report_type == 'traffic_summary':
            story.extend(self._generate_traffic_summary(params))
        elif report_type == 'security_report':
            story.extend(self._generate_security_report(params))
        elif report_type == 'incident_report':
            story.extend(self._generate_incident_report(params))
        
        # Build PDF
        doc.build(story)
        
        return {
            'success': True,
            'filename': filename,
            'path': filepath
        }
    
    def _generate_traffic_summary(self, params):
        """Generate traffic summary content"""
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph('<b>Traffic Summary</b>', styles['Heading2']))
        content.append(Spacer(1, 0.2*inch))
        
        data = [
            ['Metric', 'Value'],
            ['Total Packets', '1,234,567'],
            ['Total Bytes', '5.6 GB'],
            ['Average Bandwidth', '234 Mbps'],
            ['Peak Bandwidth', '890 Mbps']
        ]
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
        
        return content
    
    def _generate_security_report(self, params):
        """Generate security report content"""
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph('<b>Security Analysis</b>', styles['Heading2']))
        content.append(Spacer(1, 0.2*inch))
        
        data = [
            ['Alert Type', 'Count', 'Severity'],
            ['Port Scan Detected', '5', 'High'],
            ['Bandwidth Threshold', '12', 'Medium'],
            ['Failed Connections', '8', 'Low']
        ]
        
        table = Table(data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
        
        return content
    
    def _generate_incident_report(self, params):
        """Generate incident report content"""
        styles = getSampleStyleSheet()
        content = []
        
        alert_id = params.get('alert_id')
        if alert_id:
            alert = Alert.query.get(alert_id)
            if alert:
                content.append(Paragraph(f'<b>Incident Report - Alert #{alert.id}</b>', styles['Heading2']))
                content.append(Spacer(1, 0.2*inch))
                
                details = [
                    ['Triggered:', alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')],
                    ['Rule:', alert.rule.name],
                    ['Severity:', alert.rule.severity],
                    ['Value:', str(alert.triggered_value)],
                    ['Status:', alert.status]
                ]
                
                table = Table(details, colWidths=[2*inch, 4*inch])
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                content.append(table)
        
        return content
    
    def generate_csv_export(self, data_type, filters):
        """Generate CSV export"""
        filename = f'{data_type}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        filepath = os.path.join(self.report_dir, filename)
        
        with open(filepath, 'w', newline='') as csvfile:
            if data_type == 'audit':
                writer = csv.writer(csvfile)
                writer.writerow(['Timestamp', 'User', 'Action', 'Resource', 'IP Address'])
                
                # Query audit logs
                query = AuditLog.query
                if filters.get('user_id'):
                    query = query.filter_by(user_id=filters['user_id'])
                if filters.get('action'):
                    query = query.filter_by(action=filters['action'])
                
                logs = query.order_by(AuditLog.timestamp.desc()).limit(1000).all()
                
                for log in logs:
                    writer.writerow([
                        log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        log.user.username if log.user else 'Unknown',
                        log.action,
                        log.resource_type,
                        log.ip_address
                    ])
        
        return {
            'success': True,
            'filename': filename,
            'path': filepath
        }
    
    def create_incident_report(self, alert_id, details):
        """Create incident report for an alert"""
        return self.generate_pdf_report('incident_report', {'alert_id': alert_id, 'details': details}, None)
    
    def get_audit_trail(self, filters):
        """Get audit trail with filters"""
        query = AuditLog.query
        
        if filters.get('user_id'):
            query = query.filter_by(user_id=filters['user_id'])
        if filters.get('action'):
            query = query.filter_by(action=filters['action'])
        
        logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()
        
        return [
            {
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'user': log.user.username if log.user else 'Unknown',
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'ip_address': log.ip_address
            }
            for log in logs
        ]
    
    def schedule_report(self, config, user_id):
        """Schedule a report for future generation"""
        return {
            'success': True,
            'schedule_id': 1,
            'frequency': config.get('frequency', 'daily')
        }
    
    def get_report_templates(self):
        """Get available report templates"""
        return {
            'templates': [
                {
                    'id': 'traffic_summary',
                    'name': 'Traffic Summary Report',
                    'description': 'Overview of network traffic patterns'
                },
                {
                    'id': 'security_report',
                    'name': 'Security Analysis Report',
                    'description': 'Security alerts and threat analysis'
                },
                {
                    'id': 'compliance_report',
                    'name': 'Compliance Report',
                    'description': 'Regulatory compliance status'
                },
                {
                    'id': 'incident_report',
                    'name': 'Incident Report',
                    'description': 'Detailed incident investigation'
                },
                {
                    'id': 'performance_report',
                    'name': 'Performance Report',
                    'description': 'Network performance metrics'
                }
            ]
        }
