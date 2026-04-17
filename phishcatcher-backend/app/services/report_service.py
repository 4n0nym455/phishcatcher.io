"""
Professional PDF Report Generation Service for PhishCatcher

Generates professional, analytical PDF reports with:
- Clean, modern design
- Data visualizations
- Color-coded severity indicators
- Professional typography and layout
"""

import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line, Polygon
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib import colors


def _escape_xml(text: str) -> str:
    """Escape XML special characters for ReportLab Paragraph."""
    if not text:
        return text
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&apos;'))


BRAND_PURPLE = HexColor('#6366f1')
BRAND_LIGHT = HexColor('#818cf8')
BRAND_DIM = HexColor('#e0e7ff')
DANGER_RED = HexColor('#ef4444')
DANGER_LIGHT = HexColor('#fee2e2')
DANGER_DARK = HexColor('#dc2626')
WARNING_AMBER = HexColor('#f59e0b')
WARNING_LIGHT = HexColor('#fef3c7')
WARNING_DARK = HexColor('#d97706')
SUCCESS_GREEN = HexColor('#10b981')
SUCCESS_LIGHT = HexColor('#dcfce7')
SUCCESS_DARK = HexColor('#059669')
TEXT_DARK = HexColor('#1e293b')
TEXT_MUTED = HexColor('#64748b')
TEXT_LIGHT = HexColor('#94a3b8')
BORDER_LIGHT = HexColor('#e2e8f0')
BG_PAGE = HexColor('#f8fafc')
BG_CARD = HexColor('#ffffff')
INFO_BLUE = HexColor('#3b82f6')
INFO_LIGHT = HexColor('#dbeafe')


def redact_email(email: str) -> str:
    """Redact email address for privacy."""
    if not email or '@' not in email:
        return email or 'Unknown'
    try:
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            local = local[0] + '*'
        elif len(local) <= 4:
            local = local[:2] + '**'
        else:
            local = local[:3] + '***'
        if '.' in domain:
            parts = domain.rsplit('.', 2)
            if len(parts) >= 2:
                domain = parts[0][:3] + '***.' + parts[-2] + '.' + parts[-1]
            else:
                domain = domain[:3] + '***.' + parts[-1]
        else:
            domain = domain[:3] + '***'
        return f"{local}@{domain}"
    except:
        return email


def redact_subject(subject: str, risk_score: float = 0) -> str:
    """Redact subject if high risk."""
    if risk_score >= 70 and subject:
        if len(subject) <= 4:
            return '*' * len(subject)
        return subject[:2] + '***' + subject[-2:]
    return subject


def normalize_analysis_data(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize analysis data from different sources (MongoDB, PostgreSQL, API)."""
    normalized = dict(analysis)
    
    email_metadata = analysis.get('email_metadata', {})
    risk_assessment = analysis.get('risk_assessment', {})
    threat_intel = analysis.get('threat_intelligence', {})
    ml_prediction = analysis.get('ml_prediction', {})
    
    normalized['id'] = analysis.get('_id') or analysis.get('id') or analysis.get('job_id')
    normalized['subject'] = (
        email_metadata.get('subject') or
        analysis.get('subject') or
        analysis.get('subject_line') or
        'Unknown Subject'
    )
    normalized['sender'] = (
        email_metadata.get('sender') or
        email_metadata.get('from') or
        analysis.get('sender') or
        analysis.get('from') or
        'Unknown Sender'
    )
    normalized['date'] = (
        email_metadata.get('date') or
        email_metadata.get('timestamp') or
        analysis.get('date') or
        analysis.get('timestamp') or
        'Unknown Date'
    )
    
    normalized['risk_score'] = (
        risk_assessment.get('overall_score') or
        risk_assessment.get('risk_score') or
        risk_assessment.get('score') or
        threat_intel.get('threat_score') or
        threat_intel.get('score') or
        threat_intel.get('overall_risk_score') or
        ml_prediction.get('score') or
        analysis.get('risk_score') or
        analysis.get('overall_risk_score') or
        analysis.get('threat_score') or
        0
    )
    normalized['threat_category'] = (
        risk_assessment.get('category') or
        risk_assessment.get('threat_category') or
        threat_intel.get('category') or
        threat_intel.get('threat_category') or
        analysis.get('threat_category') or
        analysis.get('category') or
        'Unknown'
    )
    normalized['confidence'] = (
        risk_assessment.get('confidence') or
        ml_prediction.get('confidence') or
        analysis.get('confidence') or
        0
    )
    
    findings = analysis.get('findings', [])
    if isinstance(findings, list):
        normalized['indicators'] = [
            {
                'type': f.get('type', f.get('title', 'Finding')),
                'description': f.get('description', ''),
                'severity': f.get('severity', f.get('risk_level', 'info')),
                'source': f.get('source', 'Analysis'),
            }
            for f in findings[:15]
        ]
    else:
        normalized['indicators'] = analysis.get('indicators', [])
    
    links = analysis.get('links_analyzed', [])
    if isinstance(links, list):
        normalized['urls_analyzed'] = [
            {
                'url': link.get('url', link.get('original', link.get('href', 'Unknown'))),
                'risk_score': link.get('risk_score', link.get('score', link.get('reputation', 0))),
                'status': link.get('status', link.get('result', 'unknown')),
            }
            for link in links[:10]
        ]
    else:
        normalized['urls_analyzed'] = analysis.get('urls_analyzed', analysis.get('urls', []))
    
    normalized['recommendations'] = (
        risk_assessment.get('recommendations') or
        analysis.get('recommendations') or
        []
    )
    
    normalized['findings_count'] = analysis.get('findings_count', len(normalized.get('indicators', [])))
    normalized['source_type'] = analysis.get('source_type', 'upload')
    normalized['file_name'] = analysis.get('file_name', normalized.get('subject', 'Unknown'))
    
    normalized['links_analyzed'] = normalized.get('urls_analyzed', [])
    normalized['attachments_analyzed'] = analysis.get('attachments_analyzed', [])
    
    return normalized


def redact_subject(subject: str, risk_score: float = 0) -> str:
    """Redact subject if high risk."""
    if risk_score >= 70 and subject:
        if len(subject) <= 4:
            return '*' * len(subject)
        return subject[:2] + '***' + subject[-2:]
    return subject


def segment_url(url: str) -> str:
    """Segment URL to prevent accidental clicks (e.g., h[ttp]s://www.example[.]com)."""
    if not url:
        return 'Unknown'
    # Segment common protocols
    url = url.replace('https://', 'h[ttps]://')
    url = url.replace('http://', 'h[ttp]://')
    # Segment @ symbol in email
    url = url.replace('@', '[@]')
    # Segment dots in domain (but keep path intact)
    parts = url.split('/')
    if len(parts) >= 2:
        domain = parts[2] if len(parts) > 2 else parts[1]
        if domain and not domain.startswith('['):
            segmented_domain = domain.replace('.', '[.]')
            url = '/'.join(parts[:2]) + '/' + segmented_domain + '/' + '/'.join(parts[3:]) if len(parts) > 3 else url
    return url


def extract_domain(email: str) -> str:
    """Extract domain from email."""
    if not email or '@' not in email:
        return 'unknown'
    try:
        return email.split('@')[1]
    except:
        return 'unknown'


class ProfessionalReportService:
    """Generate professional PDF reports."""
    
    def __init__(self):
        self.page_width = A4[0]
        self.page_height = A4[1]
        self.margin = 0.6 * inch
        self.content_width = self.page_width - (2 * self.margin)
        self._setup_styles()
    
    def _setup_styles(self):
        """Setup professional paragraph styles."""
        self.styles = getSampleStyleSheet()
        
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            fontSize=28,
            textColor=BRAND_PURPLE,
            alignment=TA_CENTER,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            fontSize=12,
            textColor=TEXT_MUTED,
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            fontSize=14,
            textColor=BRAND_PURPLE,
            spaceBefore=16,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubsectionTitle',
            fontSize=11,
            textColor=TEXT_DARK,
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            fontSize=9,
            textColor=TEXT_DARK,
            spaceAfter=6,
            leading=14,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='BodySmall',
            fontSize=8,
            textColor=TEXT_MUTED,
            spaceAfter=4,
            leading=11,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='FooterText',
            fontSize=7,
            textColor=TEXT_MUTED,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(name='MetricLarge', fontSize=28, textColor=BRAND_PURPLE, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='MetricRed', fontSize=28, textColor=DANGER_RED, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='MetricAmber', fontSize=28, textColor=WARNING_AMBER, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='MetricGreen', fontSize=28, textColor=SUCCESS_GREEN, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='MetricBlue', fontSize=28, textColor=INFO_BLUE, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='MetricLabel', fontSize=9, textColor=TEXT_MUTED, alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(name='MetricSublabel', fontSize=8, textColor=TEXT_LIGHT, alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(name='TableHeader', fontSize=9, textColor=white, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='TableCell', fontSize=8, textColor=TEXT_DARK, fontName='Helvetica'))
        self.styles.add(ParagraphStyle(name='ScoreRed', fontSize=9, textColor=DANGER_RED, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='ScoreAmber', fontSize=9, textColor=WARNING_AMBER, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='ScoreGreen', fontSize=9, textColor=SUCCESS_GREEN, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='ScoreBlue', fontSize=9, textColor=INFO_BLUE, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='SeverityCritical', fontSize=8, textColor=DANGER_RED, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='SeverityHigh', fontSize=8, textColor=WARNING_AMBER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='SeverityMedium', fontSize=8, textColor=INFO_BLUE, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='SeverityLow', fontSize=8, textColor=SUCCESS_GREEN, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='RiskLarge', fontSize=36, textColor=DANGER_RED, alignment=TA_CENTER, fontName='Helvetica-Bold', leading=42))
        self.styles.add(ParagraphStyle(name='RiskMedium', fontSize=36, textColor=WARNING_AMBER, alignment=TA_CENTER, fontName='Helvetica-Bold', leading=42))
        self.styles.add(ParagraphStyle(name='RiskLow', fontSize=36, textColor=SUCCESS_GREEN, alignment=TA_CENTER, fontName='Helvetica-Bold', leading=42))
        self.styles.add(ParagraphStyle(name='RiskLabel', fontSize=12, textColor=DANGER_RED, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='RiskLabelMed', fontSize=12, textColor=WARNING_AMBER, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='RiskLabelLow', fontSize=12, textColor=SUCCESS_GREEN, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='CoverTitle', fontSize=32, textColor=BRAND_PURPLE, alignment=TA_CENTER, spaceAfter=10, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='CoverSubtitle', fontSize=14, textColor=TEXT_DARK, alignment=TA_CENTER, spaceAfter=6, fontName='Helvetica'))
        self.styles.add(ParagraphStyle(name='CoverMeta', fontSize=10, textColor=TEXT_MUTED, alignment=TA_CENTER, fontName='Helvetica'))
        self.styles.add(ParagraphStyle(name='BulletItem', fontSize=9, textColor=TEXT_DARK, spaceAfter=4, leading=13, fontName='Helvetica', leftIndent=12, bulletIndent=0))
        self.styles.add(ParagraphStyle(name='ExecSummary', fontSize=11, textColor=TEXT_DARK, spaceAfter=8, leading=16, fontName='Helvetica'))
        self.styles.add(ParagraphStyle(name='BadgeDanger', fontSize=10, textColor=DANGER_RED, fontName='Helvetica-Bold', alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(name='BadgeWarning', fontSize=10, textColor=WARNING_AMBER, fontName='Helvetica-Bold', alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(name='BadgeSuccess', fontSize=10, textColor=SUCCESS_GREEN, fontName='Helvetica-Bold', alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(name='BadgeInfo', fontSize=10, textColor=INFO_BLUE, fontName='Helvetica-Bold', alignment=TA_CENTER))
    
    def _draw_footer(self, canvas, doc):
        """Draw page footer with page number."""
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(TEXT_MUTED)
        page_num = canvas.getPageNumber()
        text = f"PhishCatcher Security Report • Page {page_num} • Generated {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
        canvas.drawCentredString(self.page_width / 2, 0.35 * inch, text)
        canvas.restoreState()
    
    def _draw_cover_footer(self, canvas, doc):
        """Draw footer on cover page."""
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(TEXT_LIGHT)
        canvas.drawCentredString(self.page_width / 2, 0.5 * inch, "PhishCatcher • Advanced Email Threat Intelligence")
        canvas.restoreState()
    
    def _create_header_banner(self, title: str) -> Table:
        """Create a header banner with title."""
        banner_data = [[Paragraph(f"<b>{title}</b>", ParagraphStyle(
            name='_BannerTitle',
            fontSize=18,
            textColor=white,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        ))]]
        banner_table = Table(banner_data, colWidths=[self.content_width])
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BRAND_PURPLE),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ('LEFTPADDING', (0, 0), (-1, -1), 16),
            ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ]))
        return banner_table
    
    def _create_risk_gauge(self, score: float, width: float = 3*inch) -> Drawing:
        """Create a visual risk gauge."""
        d = Drawing(width, 1.2*inch)
        
        center_x = width / 2
        center_y = 0.7 * inch
        radius = 0.5 * inch
        
        if score >= 70:
            color = DANGER_RED
        elif score >= 40:
            color = WARNING_AMBER
        else:
            color = SUCCESS_GREEN
        
        d.add(Circle(center_x, center_y, radius, fillColor=BG_CARD, strokeColor=BORDER_LIGHT, strokeWidth=2))
        
        start_angle = 180
        end_angle = 0
        score_angle = start_angle - (score / 100 * 180)
        
        from reportlab.graphics.charts.piecharts import Pie
        p = Pie()
        p.x = center_x - radius
        p.y = center_y - radius
        p.width = radius * 2
        p.height = radius * 2
        p.data = [score, 100 - score]
        p.slices[0].fillColor = color
        p.slices[1].fillColor = BG_PAGE
        p.slices[0].strokeColor = None
        p.slices[1].strokeColor = None
        p.startAngle = start_angle
        p.endAngle = score_angle
        
        d.add(p)
        
        d.add(String(center_x, center_y - 8, f"{int(score)}", 
                    fontSize=24, fillColor=color, fontName='Helvetica-Bold', 
                    textAnchor='middle'))
        
        return d
    
    def _create_pie_chart_data(self, data: Dict[str, int], colors_list: List[Color]) -> Drawing:
        """Create pie chart drawing."""
        d = Drawing(4*inch, 2.5*inch)
        
        labels = list(data.keys())
        values = list(data.values())
        
        if sum(values) == 0:
            d.add(String(2*inch, 1.25*inch, "No data available", 
                        fontSize=12, fillColor=TEXT_MUTED, textAnchor='middle'))
            return d
        
        p = Pie()
        p.x = 0.5*inch
        p.y = 0.25*inch
        p.width = 2*inch
        p.height = 2*inch
        p.data = values
        p.labels = labels
        p.slices[0].fillColor = colors_list[0] if len(colors_list) > 0 else BRAND_PURPLE
        p.slices[1].fillColor = colors_list[1] if len(colors_list) > 1 else DANGER_RED
        p.slices[2].fillColor = colors_list[2] if len(colors_list) > 2 else WARNING_AMBER
        p.slices[3].fillColor = colors_list[3] if len(colors_list) > 3 else SUCCESS_GREEN
        for i in range(len(values), 4):
            p.slices[i].fillColor = BG_PAGE
        p.slices[0].strokeColor = None
        p.slices[1].strokeColor = None
        p.slices[2].strokeColor = None
        p.slices[3].strokeColor = None
        
        d.add(p)
        
        legend_x = 2.8*inch
        legend_y = 2*inch
        for i, (label, val) in enumerate(zip(labels, values)):
            pct = (val / sum(values) * 100) if sum(values) > 0 else 0
            rect_color = colors_list[i] if i < len(colors_list) else TEXT_MUTED
            d.add(Rect(legend_x, legend_y - i*20, 12, 12, fillColor=rect_color, strokeColor=None))
            d.add(String(legend_x + 18, legend_y - i*20 + 2, f"{label}: {val} ({pct:.1f}%)", 
                        fontSize=9, fillColor=TEXT_DARK, fontName='Helvetica'))
        
        return d
    
    def _create_radar_chart(self, data: Dict[str, int], colors_list: List[Color]) -> Drawing:
        """Create radar chart drawing using basic shapes."""
        import math
        from reportlab.graphics.shapes import Path
        
        d = Drawing(6*inch, 4*inch)
        
        labels = list(data.keys())
        values = list(data.values())
        
        if sum(values) == 0:
            d.add(String(3*inch, 2*inch, "No data available", 
                        fontSize=14, fillColor=TEXT_MUTED, textAnchor='middle'))
            return d
        
        bg_rect = Rect(0.2*inch, 0.2*inch, 5.6*inch, 3.6*inch, fillColor=BG_CARD, strokeColor=BORDER_LIGHT, strokeWidth=1, rx=10, ry=10)
        d.add(bg_rect)
        
        center_x = 2.2*inch
        center_y = 2*inch
        radius = 1.5*inch
        
        sides = len(labels)
        angle_step = 2 * math.pi / sides
        
        for level in [0.2, 0.4, 0.6, 0.8, 1.0]:
            r = radius * level
            points = []
            for i in range(sides):
                angle = angle_step * i - math.pi / 2
                x = center_x + r * math.cos(angle)
                y = center_y + r * math.sin(angle)
                points.extend([x, y])
            d.add(Polygon(points, strokeColor=BORDER_LIGHT, strokeWidth=0.75, fillColor=None))
        
        for i in range(sides):
            angle = angle_step * i - math.pi / 2
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            d.add(Line(center_x, center_y, x, y, strokeColor=BORDER_LIGHT, strokeWidth=1))
        
        max_val = max(values) if values else 1
        if max_val == 0:
            max_val = 1
        
        fill_color = colors_list[0] if colors_list else BRAND_PURPLE
        data_points = []
        for i, val in enumerate(values):
            angle = angle_step * i - math.pi / 2
            r = (val / max_val) * radius if val > 0 else 0
            x = center_x + r * math.cos(angle)
            y = center_y + r * math.sin(angle)
            data_points.extend([x, y])
        
        d.add(Polygon(data_points, strokeColor=fill_color, strokeWidth=3, fillColor=fill_color, fillOpacity=0.25))
        
        for i, val in enumerate(values):
            angle = angle_step * i - math.pi / 2
            r = (val / max_val) * radius if val > 0 else 0
            x = center_x + r * math.cos(angle)
            y = center_y + r * math.sin(angle)
            d.add(Circle(x, y, 4, fillColor=fill_color, strokeColor=white, strokeWidth=1.5))
        
        for i, (label, val) in enumerate(zip(labels, values)):
            angle = angle_step * i - math.pi / 2
            label_radius = radius + 0.35*inch
            x = center_x + label_radius * math.cos(angle)
            y = center_y + label_radius * math.sin(angle)
            
            anchor = 'middle'
            offset_x = 0
            if abs(angle + math.pi/2) < 0.01:
                offset_x = 0
            elif angle > -math.pi/4 and angle < math.pi/4:
                anchor = 'start'
                offset_x = 5
            elif angle > math.pi/4 and angle < 3*math.pi/4:
                anchor = 'middle'
            elif angle > 3*math.pi/4 or angle < -3*math.pi/4:
                anchor = 'end'
                offset_x = -5
            else:
                anchor = 'middle'
            
            pct = (val / max_val * 100) if max_val > 0 else 0
            d.add(String(x + offset_x, y - 4, f"{label}", fontSize=10, fillColor=TEXT_DARK, fontName='Helvetica-Bold', textAnchor=anchor))
        
        legend_x = 4.5*inch
        legend_y = 3.4*inch
        for i, (label, val) in enumerate(zip(labels, values)):
            rect_color = colors_list[i] if i < len(colors_list) else BRAND_PURPLE
            pct = (val / sum(values) * 100) if sum(values) > 0 else 0
            d.add(Rect(legend_x, legend_y - i*35, 18, 18, fillColor=rect_color, strokeColor=None, rx=4, ry=4))
            d.add(String(legend_x + 24, legend_y - i*35 + 5, f"{label}", fontSize=10, fillColor=TEXT_DARK, fontName='Helvetica-Bold'))
            d.add(String(legend_x + 24, legend_y - i*35 - 12, f"{val} ({pct:.1f}%)", fontSize=9, fillColor=TEXT_MUTED))
        
        return d
    
    def _create_donut_chart(self, data: Dict[str, int], colors_list: List[Color]) -> Drawing:
        """Create donut chart drawing."""
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics import renderPDF
        
        d = Drawing(5*inch, 3*inch)
        
        labels = list(data.keys())
        values = list(data.values())
        
        if sum(values) == 0:
            d.add(String(2.5*inch, 1.5*inch, "No data available", 
                        fontSize=12, fillColor=TEXT_MUTED, textAnchor='middle'))
            return d
        
        p = Pie()
        p.x = 0.3*inch
        p.y = 0.5*inch
        p.width = 2.2*inch
        p.height = 2.2*inch
        p.data = values
        p.labels = labels
        p.slices[0].fillColor = colors_list[0] if len(colors_list) > 0 else BRAND_PURPLE
        p.slices[1].fillColor = colors_list[1] if len(colors_list) > 1 else DANGER_RED
        p.slices[2].fillColor = colors_list[2] if len(colors_list) > 2 else WARNING_AMBER
        p.slices[3].fillColor = colors_list[3] if len(colors_list) > 3 else SUCCESS_GREEN
        for i in range(len(values), 4):
            p.slices[i].fillColor = BG_PAGE
        for i in range(len(values)):
            p.slices[i].strokeColor = None
        
        d.add(p)
        
        center_x = 1.4*inch
        center_y = 1.6*inch
        inner_circle = Circle(center_x, center_y, 0.55*inch, fillColor=white, strokeColor=None)
        d.add(inner_circle)
        
        total = sum(values)
        d.add(String(center_x, center_y + 8, str(total), 
                    fontSize=18, fillColor=TEXT_DARK, fontName='Helvetica-Bold', 
                    textAnchor='middle'))
        d.add(String(center_x, center_y - 8, "Total", 
                    fontSize=9, fillColor=TEXT_MUTED, fontName='Helvetica', 
                    textAnchor='middle'))
        
        legend_x = 3.2*inch
        legend_y = 2.5*inch
        for i, (label, val) in enumerate(zip(labels, values)):
            pct = (val / sum(values) * 100) if sum(values) > 0 else 0
            rect_color = colors_list[i] if i < len(colors_list) else TEXT_MUTED
            d.add(Rect(legend_x, legend_y - i*28, 16, 16, fillColor=rect_color, strokeColor=None))
            d.add(String(legend_x + 22, legend_y - i*28 + 4, f"{label}", 
                        fontSize=10, fillColor=TEXT_DARK, fontName='Helvetica-Bold'))
            d.add(String(legend_x + 22, legend_y - i*28 - 10, f"{val} ({pct:.1f}%)", 
                        fontSize=9, fillColor=TEXT_MUTED, fontName='Helvetica'))
        
        return d
    
    def _create_bar_chart_data(self, data: Dict[str, int], title: str = "") -> Drawing:
        """Create horizontal bar chart drawing."""
        d = Drawing(5*inch, 2*inch)
        
        labels = list(data.keys())
        values = list(data.values())
        
        if not values or max(values) == 0:
            d.add(String(2.5*inch, inch, "No data available", 
                        fontSize=12, fillColor=TEXT_MUTED, textAnchor='middle'))
            return d
        
        bc = VerticalBarChart()
        bc.x = 0.5*inch
        bc.y = 0.3*inch
        bc.height = 1.5*inch
        bc.width = 4.5*inch
        bc.data = [values]
        bc.strokeColor = None
        
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        bc.bars[0].fillColor = BRAND_PURPLE
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.labels.fontName = 'Helvetica'
        bc.categoryAxis.labels.fontSize = 8
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = max(values) * 1.1
        bc.valueAxis.labels.fontName = 'Helvetica'
        bc.valueAxis.labels.fontSize = 8
        
        d.add(bc)
        return d
    
    def generate_summary_pdf_v2(self, report_data: Dict[str, Any], start_date: str, end_date: str) -> bytes:
        """Generate enhanced summary PDF report with comprehensive charts and analysis."""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=0.6*inch,
            bottomMargin=0.6*inch,
            onFirstPage=self._draw_footer,
            onLaterPages=self._draw_footer
        )
        
        elements = []
        
        total = report_data.get('total_analyses', report_data.get('total_emails', 0))
        threats = (report_data.get('phishing_detected', 0) + report_data.get('malware_detected', 0))
        suspicious = report_data.get('suspicious_detected', 0)
        safe = report_data.get('safe_emails', 0)
        phishing = report_data.get('phishing_detected', 0)
        malware = report_data.get('malware_detected', 0)
        
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(self._create_header_banner("PhishCatcher Security Summary Report"))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph(f"{start_date} to {end_date}", self.styles['CoverMeta']))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
            self.styles['CoverMeta']
        ))
        elements.append(Spacer(1, 0.3*inch))
        
        elements.append(Paragraph("Executive Summary", self.styles['SectionTitle']))
        threat_rate = (threats / total * 100) if total > 0 else 0
        if threat_rate >= 20:
            verdict = "HIGH ALERT"
            verdict_style = self.styles['BadgeDanger']
            verdict_bg = DANGER_LIGHT
        elif threat_rate >= 10:
            verdict = "MODERATE"
            verdict_style = self.styles['BadgeWarning']
            verdict_bg = WARNING_LIGHT
        elif threats > 0:
            verdict = "LOW RISK"
            verdict_style = self.styles['BadgeSuccess']
            verdict_bg = SUCCESS_LIGHT
        else:
            verdict = "NO THREATS"
            verdict_style = self.styles['BadgeSuccess']
            verdict_bg = SUCCESS_LIGHT
        
        verdict_data = [[Paragraph(f"Overall Assessment: {verdict}", verdict_style)]]
        verdict_table = Table(verdict_data, colWidths=[self.content_width])
        verdict_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), verdict_bg),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 16),
            ('RIGHTPADDING', (0, 0), (-1, -1), 16),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ]))
        elements.append(verdict_table)
        elements.append(Spacer(1, 0.2*inch))
        
        exec_summary = []
        if total > 0:
            exec_summary.append(f"Analyzed <b>{total}</b> emails during this period.")
        if threats > 0:
            exec_summary.append(f"Detected <b>{threats}</b> threats ({threat_rate:.1f}% of total).")
        if suspicious > 0:
            exec_summary.append(f"Flagged <b>{suspicious}</b> emails as suspicious.")
        if safe > 0:
            exec_summary.append(f"Verified <b>{safe}</b> emails as safe.")
        
        for summary in exec_summary:
            elements.append(Paragraph(summary, self.styles['ExecSummary']))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("Key Statistics", self.styles['SectionTitle']))
        
        metrics_data = [
            [
                Paragraph(f"<b>{total}</b>", self.styles['MetricLarge']),
                Paragraph(f"<b>{threats}</b>", self.styles['MetricRed']),
                Paragraph(f"<b>{suspicious}</b>", self.styles['MetricAmber']),
                Paragraph(f"<b>{safe}</b>", self.styles['MetricGreen']),
            ],
            [
                Paragraph("Total Analyzed", self.styles['MetricLabel']),
                Paragraph("Threats", self.styles['MetricLabel']),
                Paragraph("Suspicious", self.styles['MetricLabel']),
                Paragraph("Safe", self.styles['MetricLabel']),
            ]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[self.content_width/4]*4)
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
            ('LINEAFTER', (0, 0), (2, -1), 1, BORDER_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.25*inch))
        
        risk_distribution = report_data.get('risk_distribution', {})
        if not risk_distribution and total > 0:
            risk_distribution = {
                'High Risk (70-100)': threats,
                'Suspicious (40-69)': suspicious,
                'Safe (0-39)': safe,
            }
        
        if any(risk_distribution.values()):
            elements.append(Paragraph("Risk Distribution", self.styles['SubsectionTitle']))
            
            risk_colors = [DANGER_RED, WARNING_AMBER, SUCCESS_GREEN]
            donut_chart = self._create_donut_chart(risk_distribution, risk_colors)
            elements.append(donut_chart)
            elements.append(Spacer(1, 0.25*inch))
        
        elements.append(Paragraph("Threat Category Breakdown", self.styles['SubsectionTitle']))
        
        category_data = {
            'Phishing': phishing,
            'Malware': malware,
            'Suspicious': suspicious,
            'Safe': safe,
        }
        category_colors = [DANGER_RED, HexColor('#8b5cf6'), WARNING_AMBER, SUCCESS_GREEN]
        radar_chart = self._create_radar_chart(category_data, category_colors)
        elements.append(radar_chart)
        elements.append(Spacer(1, 0.25*inch))
        
        if phishing > 0 or malware > 0 or suspicious > 0:
            elements.append(Paragraph("Threat Details", self.styles['SubsectionTitle']))
            threat_detail_data = [
                [
                    Paragraph("Category", self.styles['TableHeader']),
                    Paragraph("Count", self.styles['TableHeader']),
                    Paragraph("Percentage", self.styles['TableHeader']),
                    Paragraph("Risk Level", self.styles['TableHeader']),
                ]
            ]
            
            threat_detail_items = [
                ('Phishing', phishing, DANGER_RED),
                ('Malware', malware, DANGER_RED),
                ('Suspicious', suspicious, WARNING_AMBER),
            ]
            
            for cat, count, color in threat_detail_items:
                if count > 0:
                    pct = (count / total * 100) if total > 0 else 0
                    threat_detail_data.append([
                        Paragraph(cat, self.styles['TableCell']),
                        Paragraph(str(count), self.styles['TableCell']),
                        Paragraph(f"{pct:.1f}%", self.styles['TableCell']),
                        Paragraph("HIGH" if color == DANGER_RED else "MEDIUM", 
                                 self.styles['SeverityCritical'] if color == DANGER_RED else self.styles['SeverityHigh']),
                    ])
            
            if threat_detail_data:
                threat_detail_table = Table(threat_detail_data, colWidths=[1.5*inch, 1*inch, 1.2*inch, 1.5*inch])
                threat_detail_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
                ]))
                elements.append(threat_detail_table)
        
        elements.append(PageBreak())
        
        elements.append(self._create_header_banner("Detailed Analysis"))
        elements.append(Spacer(1, 0.2*inch))
        
        daily_breakdown = report_data.get('daily_breakdown', [])
        if daily_breakdown:
            elements.append(Paragraph("Daily Analysis Trend", self.styles['SectionTitle']))
            
            d = Drawing(5*inch, 2.5*inch)
            
            days = [d.get('day', 'Unknown')[-5:] for d in daily_breakdown[:14]]
            threats_data = [d.get('threats', 0) for d in daily_breakdown[:14]]
            suspicious_data = [d.get('suspicious', 0) for d in daily_breakdown[:14]]
            safe_data = [d.get('analyzed', 0) - d.get('threats', 0) - d.get('suspicious', 0) for d in daily_breakdown[:14]]
            
            if not days or max(threats_data + suspicious_data + safe_data) == 0:
                d.add(String(2.5*inch, 1.25*inch, "No data available", 
                            fontSize=12, fillColor=TEXT_MUTED, textAnchor='middle'))
            else:
                from reportlab.graphics.charts.barcharts import VerticalBarChart
                bc = VerticalBarChart()
                bc.x = 0.5*inch
                bc.y = 0.3*inch
                bc.height = 1.8*inch
                bc.width = 4*inch
                bc.data = [threats_data, suspicious_data, safe_data]
                bc.categoryAxis.categoryNames = days
                bc.categoryAxis.labels.fontName = 'Helvetica'
                bc.categoryAxis.labels.fontSize = 7
                bc.categoryAxis.labels.textAnchor = 'middle'
                bc.valueAxis.valueMin = 0
                bc.valueAxis.valueMax = max(max(threats_data + suspicious_data + safe_data) + 1, 5)
                bc.valueAxis.labels.fontName = 'Helvetica'
                bc.valueAxis.labels.fontSize = 8
                
                bc.bars[0].fillColor = DANGER_RED
                bc.bars[1].fillColor = WARNING_AMBER
                bc.bars[2].fillColor = SUCCESS_GREEN
                
                d.add(bc)
                
                legend_y = 2.3*inch
                legend_x = 0.5*inch
                legend_items = [('Threats', DANGER_RED), ('Suspicious', WARNING_AMBER), ('Safe', SUCCESS_GREEN)]
                for i, (label, color) in enumerate(legend_items):
                    d.add(Rect(legend_x + i*1.5*inch, legend_y, 12, 12, fillColor=color, strokeColor=None))
                    d.add(String(legend_x + i*1.5*inch + 16, legend_y + 2, label, 
                                fontSize=8, fillColor=TEXT_DARK, fontName='Helvetica'))
            
            elements.append(d)
        
        elements.append(Spacer(1, 0.2*inch))
        
        top_threats = report_data.get('top_threats', [])
        if top_threats:
            elements.append(Paragraph(f"Top {min(10, len(top_threats))} Threats", self.styles['SectionTitle']))
            
            threat_table_data = [
                [Paragraph("#", self.styles['TableHeader']),
                 Paragraph("Subject", self.styles['TableHeader']),
                 Paragraph("Sender", self.styles['TableHeader']),
                 Paragraph("Score", self.styles['TableHeader']),
                 Paragraph("Category", self.styles['TableHeader'])],
            ]
            
            for i, threat in enumerate(top_threats[:10], 1):
                score = threat.get('risk_score', 0)
                category = threat.get('category', threat.get('threat_category', 'Unknown'))
                
                if score >= 70:
                    score_style = self.styles['ScoreRed']
                elif score >= 40:
                    score_style = self.styles['ScoreAmber']
                else:
                    score_style = self.styles['ScoreGreen']
                
                threat_table_data.append([
                    Paragraph(str(i), self.styles['TableCell']),
                    Paragraph(redact_subject(threat.get("subject", "Unknown"), score), self.styles['TableCell']),
                    Paragraph(redact_email(threat.get("sender", "Unknown")), self.styles['TableCell']),
                    Paragraph(f"<b>{int(score)}</b>", score_style),
                    Paragraph(category[:15], self.styles['TableCell']),
                ])
            
            threat_table = Table(threat_table_data, colWidths=[0.3*inch, 2.5*inch, 1.5*inch, 0.6*inch, 0.9*inch])
            threat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
            ]))
            elements.append(threat_table)
        
        elements.append(Spacer(1, 0.2*inch))
        
        top_senders = report_data.get('top_senders', [])
        if top_senders:
            elements.append(Paragraph("Top Suspicious Senders", self.styles['SectionTitle']))
            
            sender_table_data = [
                [Paragraph("#", self.styles['TableHeader']),
                 Paragraph("Sender", self.styles['TableHeader']),
                 Paragraph("Occurrences", self.styles['TableHeader']),
                 Paragraph("Risk Level", self.styles['TableHeader'])],
            ]
            
            for i, sender in enumerate(top_senders[:10], 1):
                sender_email = sender.get('sender', 'Unknown')
                count = sender.get('count', 1)
                
                sender_table_data.append([
                    Paragraph(str(i), self.styles['TableCell']),
                    Paragraph(redact_email(sender_email), self.styles['TableCell']),
                    Paragraph(str(count), self.styles['TableCell']),
                    Paragraph("HIGH" if count >= 3 else "MEDIUM", 
                             self.styles['SeverityCritical'] if count >= 3 else self.styles['SeverityHigh']),
                ])
            
            sender_table = Table(sender_table_data, colWidths=[0.3*inch, 3*inch, 1.2*inch, 1*inch])
            sender_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
            ]))
            elements.append(sender_table)
        
        elements.append(PageBreak())
        
        elements.append(self._create_header_banner("Recommendations"))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("Security Recommendations", self.styles['SectionTitle']))
        
        recommendations = report_data.get('recommendations', [])
        if not recommendations:
            recommendations = [
                "Review all flagged emails before clicking any links or downloading attachments",
                "Implement email authentication protocols (SPF, DKIM, DMARC) if not already in place",
                "Conduct security awareness training for all users",
                "Enable multi-factor authentication on all email accounts",
                "Regularly update email security filters and threat intelligence feeds",
                "Monitor for patterns in suspicious email senders",
                "Establish a clear process for reporting and handling phishing attempts",
            ]
        
        for i, rec in enumerate(recommendations[:10], 1):
            bullet_data = [[
                Paragraph("•", self.styles['BulletItem']),
                Paragraph(rec, self.styles['BulletItem'])
            ]]
            bullet_table = Table(bullet_data, colWidths=[0.2*inch, self.content_width - 0.2*inch])
            bullet_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(bullet_table)
        
        elements.append(Spacer(1, 0.3*inch))
        
        if threats > 0 or suspicious > 0:
            elements.append(Paragraph("Priority Actions", self.styles['SubsectionTitle']))
            
            priority_data = [
                [Paragraph("Priority", self.styles['TableHeader']),
                 Paragraph("Action Item", self.styles['TableHeader']),
                 Paragraph("Status", self.styles['TableHeader'])],
            ]
            
            priority_items = [
                ("HIGH", "Investigate all high-risk emails immediately", "Action Required"),
                ("HIGH", "Block confirmed malicious senders", "In Progress"),
                ("MEDIUM", "Update email filtering rules", "Pending"),
                ("LOW", "Schedule security awareness training", "Planned"),
            ]
            
            for priority, action, status in priority_items:
                priority_style = self.styles['SeverityCritical'] if priority == "HIGH" else \
                                 self.styles['SeverityHigh'] if priority == "MEDIUM" else \
                                 self.styles['SeverityLow']
                priority_data.append([
                    Paragraph(priority, priority_style),
                    Paragraph(action, self.styles['TableCell']),
                    Paragraph(status, self.styles['TableCell']),
                ])
            
            priority_table = Table(priority_data, colWidths=[0.8*inch, 3.5*inch, 1.2*inch])
            priority_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
            ]))
            elements.append(priority_table)
        
        elements.append(Spacer(1, 0.5*inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_LIGHT, spaceAfter=8))
        elements.append(Paragraph(
            f"Report generated by PhishCatcher on {datetime.now().strftime('%Y-%m-%d %H:%M UTC')} | Confidential",
            self.styles['FooterText']
        ))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_combined_pdf(self, analyses: List[Dict[str, Any]], start_date: Optional[str] = None, end_date: Optional[str] = None) -> bytes:
        """Generate combined PDF report for multiple analyses."""
        analyses = [normalize_analysis_data(a) for a in analyses]
        
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=0.6*inch,
            bottomMargin=0.6*inch,
            onFirstPage=self._draw_footer,
            onLaterPages=self._draw_footer
        )
        
        elements = []
        
        total = len(analyses)
        threats = sum(1 for a in analyses if (a.get('risk_score', 0) or a.get('threat_score', 0)) >= 70)
        suspicious = sum(1 for a in analyses if 40 <= (a.get('risk_score', 0) or a.get('threat_score', 0)) < 70)
        safe = total - threats - suspicious
        
        elements.append(Spacer(1, 0.2*inch))
        
        date_range = f"{start_date} to {end_date}" if start_date and end_date else datetime.now().strftime('%Y-%m-%d')
        
        elements.append(self._create_header_banner("PhishCatcher Combined Analysis Report"))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph(f"Analysis Period: {date_range}", self.styles['CoverMeta']))
        elements.append(Paragraph(f"Total Analyses: {total}", self.styles['CoverMeta']))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
            self.styles['CoverMeta']
        ))
        elements.append(Spacer(1, 0.3*inch))
        
        elements.append(Paragraph("Summary Overview", self.styles['SectionTitle']))
        
        summary_data = [
            [
                Paragraph(f"<b>{total}</b>", self.styles['MetricBlue']),
                Paragraph(f"<b>{threats}</b>", self.styles['MetricRed']),
                Paragraph(f"<b>{suspicious}</b>", self.styles['MetricAmber']),
                Paragraph(f"<b>{safe}</b>", self.styles['MetricGreen']),
            ],
            [
                Paragraph("Total", self.styles['MetricLabel']),
                Paragraph("High Risk", self.styles['MetricLabel']),
                Paragraph("Suspicious", self.styles['MetricLabel']),
                Paragraph("Safe", self.styles['MetricLabel']),
            ]
        ]
        
        summary_table = Table(summary_data, colWidths=[self.content_width/4]*4)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
            ('LINEAFTER', (0, 0), (2, -1), 1, BORDER_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.2*inch))
        
        def get_risk_category(analysis):
            score = analysis.get('risk_score', 0) or 0
            cat = (analysis.get('threat_category') or '').lower()
            if score >= 70:
                return 'Malware' if cat == 'malware' else 'Phishing'
            if score >= 40:
                return 'Suspicious'
            return 'Safe'
        
        counts = {'Phishing': 0, 'Malware': 0, 'Suspicious': 0, 'Safe': 0}
        for a in analyses:
            counts[get_risk_category(a)] += 1
        
        category_breakdown = counts
        category_colors = [DANGER_RED, HexColor('#FF6B35'), WARNING_AMBER, SUCCESS_GREEN]
        pie_chart = self._create_pie_chart_data(category_breakdown, category_colors)
        elements.append(pie_chart)
        
        elements.append(PageBreak())
        
        for idx, analysis in enumerate(analyses):
            score = analysis.get('risk_score', analysis.get('threat_score', 0))
            category = analysis.get('threat_category', analysis.get('category', 'Unknown'))
            
            if score >= 70:
                risk_label = "HIGH RISK"
                risk_style = self.styles['RiskLarge']
                label_style = self.styles['RiskLabel']
                risk_bg = DANGER_LIGHT
            elif score >= 40:
                risk_label = "MEDIUM RISK"
                risk_style = self.styles['RiskMedium']
                label_style = self.styles['RiskLabelMed']
                risk_bg = WARNING_LIGHT
            else:
                risk_label = "LOW RISK"
                risk_style = self.styles['RiskLow']
                label_style = self.styles['RiskLabelLow']
                risk_bg = SUCCESS_LIGHT
            
            metadata = analysis.get('email_metadata', {})
            subject = metadata.get('subject', analysis.get('subject', analysis.get('subject_line', 'Unknown Subject')))
            sender = metadata.get('sender', analysis.get('sender', analysis.get('from', 'Unknown Sender')))
            date = metadata.get('date', analysis.get('date', analysis.get('analyzed_at', 'Unknown Date')))
            analysis_id = analysis.get('id', analysis.get('analysis_id', f'Analysis #{idx + 1}'))
            
            card_content = []
            
            card_content.append(Paragraph(f"Analysis {idx + 1} of {total} | ID: {analysis_id}", self.styles['CoverMeta']))
            card_content.append(Spacer(1, 0.1*inch))
            
            risk_box_data = [[
                Paragraph(f"<b>{int(score)}</b>%", risk_style),
                Paragraph(risk_label, label_style),
            ]]
            risk_box = Table(risk_box_data, colWidths=[1.3*inch, self.content_width - 1.3*inch])
            risk_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), risk_bg),
                ('BACKGROUND', (1, 0), (1, -1), BG_CARD),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (0, -1), 10),
                ('LEFTPADDING', (1, 0), (1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
                ('LINEBELOW', (0, 0), (0, 0), 1, BORDER_LIGHT),
            ]))
            card_content.append(risk_box)
            card_content.append(Spacer(1, 0.15*inch))
            
            card_content.append(Paragraph("Email Information", self.styles['SubsectionTitle']))
            
            links_count = len(analysis.get('urls_analyzed', analysis.get('links_analyzed', [])))
            attachments_count = len(analysis.get('attachments_analyzed', []))
            indicators = analysis.get('indicators', [])
            findings_count = len(indicators)
            source_type = analysis.get('source_type', 'upload')
            confidence = analysis.get('confidence', analysis.get('threat_confidence', 0))
            
            email_rows = [
                [Paragraph("<b>Subject:</b>", self.styles['ReportBody']), 
                 Paragraph(redact_subject(subject, score), self.styles['ReportBody'])],
                [Paragraph("<b>From:</b>", self.styles['ReportBody']), 
                 Paragraph(redact_email(sender), self.styles['ReportBody'])],
                [Paragraph("<b>Date:</b>", self.styles['ReportBody']), 
                 Paragraph(str(date), self.styles['ReportBody'])],
                [Paragraph("<b>Source:</b>", self.styles['ReportBody']), 
                 Paragraph(source_type.title(), self.styles['ReportBody'])],
            ]
            
            email_table = Table(email_rows, colWidths=[0.9*inch, self.content_width - 0.9*inch])
            email_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_DARK),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
                ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ]))
            card_content.append(email_table)
            
            card_content.append(Spacer(1, 0.1*inch))
            
            if indicators:
                finding_summaries = []
                for ind in indicators[:3]:
                    ind_type = ind.get('type', ind.get('indicator_type', 'Unknown'))
                    ind_desc = ind.get('description', '')
                    if ind_desc and len(ind_desc) > 40:
                        ind_desc = ind_desc[:37] + "..."
                    finding_summaries.append(f"{ind_type}" + (f": {ind_desc}" if ind_desc else ""))
                findings_text = " | ".join(finding_summaries) if finding_summaries else "None"
            else:
                findings_text = "None"
            
            if len(findings_text) > 80:
                findings_text = findings_text[:77] + "..."
            
            stats_rows = [
                [Paragraph("<b>Links:</b>", self.styles['ReportBody']), 
                 Paragraph(str(links_count), self.styles['ReportBody']),
                 Paragraph("<b>Attachments:</b>", self.styles['ReportBody']), 
                 Paragraph(str(attachments_count), self.styles['ReportBody']),
                 Paragraph("<b>Findings:</b>", self.styles['ReportBody']), 
                 Paragraph(_escape_xml(findings_text), self.styles['ReportBody'])],
            ]
            
            stats_table = Table(stats_rows, colWidths=[0.8*inch, 0.7*inch, 1.0*inch, 0.8*inch, 0.9*inch, self.content_width - 4.2*inch])
            stats_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_DARK),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f8fafc')),
                ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('LINEAFTER', (1, 0), (1, 0), 0.5, BORDER_LIGHT),
                ('LINEAFTER', (3, 0), (3, 0), 0.5, BORDER_LIGHT),
                ('LINEAFTER', (5, 0), (5, 0), 0.5, BORDER_LIGHT),
            ]))
            card_content.append(stats_table)
            
            if indicators:
                card_content.append(Spacer(1, 0.1*inch))
                card_content.append(Paragraph("Threat Indicators", self.styles['SubsectionTitle']))
                
                ind_data = [
                    [Paragraph("#", self.styles['TableHeader']),
                     Paragraph("Indicator", self.styles['TableHeader']),
                     Paragraph("Source", self.styles['TableHeader']),
                     Paragraph("Severity", self.styles['TableHeader'])],
                ]
                
                for i, ind in enumerate(indicators[:8], 1):
                    ind_type = ind.get('type', ind.get('indicator_type', 'Unknown'))
                    source = ind.get('api_name', ind.get('source', 'Unknown'))
                    severity = ind.get('severity', ind.get('risk_level', 'info'))
                    
                    if severity.upper() in ['CRITICAL', 'HIGH']:
                        sev_style = self.styles['SeverityCritical']
                    elif severity.upper() == 'MEDIUM':
                        sev_style = self.styles['SeverityHigh']
                    else:
                        sev_style = self.styles['SeverityLow']
                    
                    ind_data.append([
                        Paragraph(str(i), self.styles['TableCell']),
                        Paragraph(_escape_xml(ind_type[:40]), self.styles['TableCell']),
                        Paragraph(_escape_xml(source), self.styles['TableCell']),
                        Paragraph(severity.upper(), sev_style),
                    ])
                
                ind_table = Table(ind_data, colWidths=[0.25*inch, 2.5*inch, 1.3*inch, 0.8*inch])
                ind_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
                ]))
                card_content.append(ind_table)
            
            urls = analysis.get('urls_analyzed', analysis.get('urls', []))
            if urls:
                card_content.append(Spacer(1, 0.1*inch))
                card_content.append(Paragraph("URLs Analyzed", self.styles['SubsectionTitle']))
                
                url_data = [
                    [Paragraph("#", self.styles['TableHeader']),
                     Paragraph("URL", self.styles['TableHeader']),
                     Paragraph("Risk", self.styles['TableHeader'])],
                ]
                
                for i, url_info in enumerate(urls[:5], 1):
                    url = url_info.get('url', url_info.get('original', 'Unknown'))
                    url_score = url_info.get('risk_score', url_info.get('score', 0))
                    segmented = segment_url(url)
                    
                    if url_score >= 70:
                        score_style = self.styles['ScoreRed']
                    elif url_score >= 40:
                        score_style = self.styles['ScoreAmber']
                    else:
                        score_style = self.styles['ScoreGreen']
                    
                    url_data.append([
                        Paragraph(str(i), self.styles['TableCell']),
                        Paragraph(_escape_xml(segmented), self.styles['TableCell']),
                        Paragraph(f"{url_score}%", score_style),
                    ])
                
                url_table = Table(url_data, colWidths=[0.25*inch, 4*inch, 0.6*inch])
                url_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
                ]))
                card_content.append(url_table)
            
            elements.append(KeepTogether(card_content))
            
            if idx < total - 1:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_LIGHT, spaceAfter=0.2*inch))
        
        elements.append(PageBreak())
        
        elements.append(self._create_header_banner("Consolidated Recommendations"))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("Security Recommendations", self.styles['SectionTitle']))
        
        common_recs = [
            "Review all flagged emails immediately and do not click any links or download attachments",
            "Verify sender identity through an alternative communication channel before responding",
            "Report suspicious emails to your security team for further analysis",
            "Block malicious domains identified in the threat indicators",
            "Update email security filters with new threat intelligence",
            "Consider implementing additional email authentication protocols",
            "Conduct security awareness training focusing on the identified threat patterns",
        ]
        
        for rec in common_recs:
            bullet_data = [[
                Paragraph("•", self.styles['BulletItem']),
                Paragraph(rec, self.styles['BulletItem'])
            ]]
            bullet_table = Table(bullet_data, colWidths=[0.2*inch, self.content_width - 0.2*inch])
            bullet_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(bullet_table)
        
        elements.append(Spacer(1, 0.5*inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_LIGHT, spaceAfter=8))
        elements.append(Paragraph(
            f"Combined report generated by PhishCatcher on {datetime.now().strftime('%Y-%m-%d %H:%M UTC')} | Contains {total} analyses | Confidential",
            self.styles['FooterText']
        ))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_analysis_pdf(self, analysis: Dict[str, Any], show_sensitive: bool = False) -> bytes:
        """Generate professional analysis PDF report (Analysis Results)."""
        analysis = normalize_analysis_data(analysis)
        
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=0.6*inch,
            bottomMargin=0.6*inch,
            onFirstPage=self._draw_footer,
            onLaterPages=self._draw_footer
        )
        
        elements = []
        
        # Header Banner
        elements.append(self._create_header_banner("PhishCatcher Analysis Results"))
        elements.append(Spacer(1, 0.15*inch))
        
        # Analysis ID Header (after title)
        analysis_id = analysis.get('id', 'N/A')
        created_at = analysis.get('created_at', datetime.now())
        if hasattr(created_at, 'strftime'):
            date_str = created_at.strftime('%Y-%m-%d %H:%M')
        else:
            date_str = str(created_at)
        
        id_header_data = [
            [Paragraph("<b>Analysis ID:</b>", self.styles['ReportBody']),
             Paragraph(_escape_xml(str(analysis_id)), self.styles['ReportBody']),
             Paragraph("<b>Date:</b>", self.styles['ReportBody']),
             Paragraph(date_str, self.styles['ReportBody'])]
        ]
        id_header_table = Table(id_header_data, colWidths=[1.0*inch, 2.8*inch, 0.5*inch, 1.8*inch])
        id_header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_DARK),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(id_header_table)
        elements.append(Spacer(1, 0.2*inch))
        
        score = analysis.get('risk_score', analysis.get('overall_risk_score', 0))
        category = analysis.get('threat_category', 'Unknown')
        confidence = analysis.get('confidence', 0.85)
        
        if score >= 70:
            score_label = "HIGH RISK"
            risk_style = self.styles['RiskLarge']
            label_style = self.styles['RiskLabel']
            risk_bg = DANGER_LIGHT
        elif score >= 40:
            score_label = "MEDIUM RISK"
            risk_style = self.styles['RiskMedium']
            label_style = self.styles['RiskLabelMed']
            risk_bg = WARNING_LIGHT
        else:
            score_label = "LOW RISK"
            risk_style = self.styles['RiskLow']
            label_style = self.styles['RiskLabelLow']
            risk_bg = SUCCESS_LIGHT
        
        # Risk score and confidence side by side
        risk_and_conf_data = [
            [
                Paragraph(f"<b>{int(score)}%</b>", risk_style),
                Paragraph(f"<b>{int(confidence * 100)}%</b>", self.styles['RiskMedium'])
            ],
            [
                Paragraph(score_label, label_style),
                Paragraph("CONFIDENCE", self.styles['RiskLabelMed'])
            ]
        ]
        risk_and_conf_table = Table(risk_and_conf_data, colWidths=[self.content_width/3, self.content_width/3])
        risk_and_conf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), risk_bg),
            ('BACKGROUND', (1, 0), (1, -1), INFO_LIGHT),
            ('BOX', (0, 0), (-1, -1), 2, BORDER_LIGHT),
            ('INNERGRID', (0, 0), (-1, -1), 1, BORDER_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(risk_and_conf_table)
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(f"Threat Category: {category.upper()}", self.styles['ReportSubtitle']))
        
        # Risk Factors Breakdown
        risk_factors = analysis.get('risk_factors', {})
        if risk_factors:
            elements.append(Spacer(1, 0.15*inch))
            elements.append(Paragraph("Risk Factor Breakdown", self.styles['SectionTitle']))
            
            rf_data = [
                [Paragraph("Factor", self.styles['TableHeader']),
                 Paragraph("Score", self.styles['TableHeader']),
                 Paragraph("Level", self.styles['TableHeader'])]
            ]
            
            rf_mapping = [
                ('sender_reputation', 'Sender Reputation'),
                ('content_risk', 'Content Risk'),
                ('link_risk', 'Link Risk'),
                ('attachment_risk', 'Attachment Risk'),
                ('authentication_risk', 'Authentication'),
            ]
            
            for key, label in rf_mapping:
                value = risk_factors.get(key, 0)
                if value >= 70:
                    level_style = self.styles['SeverityCritical']
                    level = "HIGH"
                    bar_bg = DANGER_RED
                elif value >= 40:
                    level_style = self.styles['SeverityHigh']
                    level = "MEDIUM"
                    bar_bg = WARNING_AMBER
                else:
                    level_style = self.styles['SeverityLow']
                    level = "LOW"
                    bar_bg = SUCCESS_GREEN
                
                rf_data.append([
                    Paragraph(label, self.styles['TableCell']),
                    Paragraph(str(value), self.styles['TableCell']),
                    Paragraph(f"<b>{level}</b>", level_style)
                ])
            
            rf_table = Table(rf_data, colWidths=[2.0*inch, 0.8*inch, 0.8*inch])
            rf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
            ]))
            elements.append(rf_table)
        
        # Detailed Findings
        findings = analysis.get('findings', [])
        if findings:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("Detailed Findings", self.styles['SectionTitle']))
            
            for finding in findings[:10]:
                f_severity = finding.get('severity', 'info')
                f_title = _escape_xml(finding.get('title', 'Unknown Finding'))
                f_description = _escape_xml(finding.get('description', ''))
                f_recommendation = _escape_xml(finding.get('recommendation', ''))
                
                if f_severity.upper() in ['CRITICAL', 'HIGH']:
                    sev_bg = DANGER_LIGHT
                    sev_color = DANGER_RED
                elif f_severity.upper() == 'MEDIUM':
                    sev_bg = WARNING_LIGHT
                    sev_color = WARNING_AMBER
                else:
                    sev_bg = SUCCESS_LIGHT
                    sev_color = SUCCESS_GREEN
                
                finding_data = [
                    [Paragraph(f"<b>{f_severity.upper()}</b>", self.styles['ReportBody']),
                     Paragraph(f"<b>{f_title}</b>", self.styles['ReportBody'])]
                ]
                finding_table = Table(finding_data, colWidths=[0.8*inch, self.content_width - 0.8*inch])
                finding_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), sev_bg),
                    ('TEXTCOLOR', (0, 0), (0, -1), sev_color),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
                ]))
                elements.append(finding_table)
                
                if f_description:
                    desc_data = [[Paragraph(f_description, self.styles['TableCell'])]]
                    desc_table = Table(desc_data, colWidths=[self.content_width])
                    desc_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), BG_PAGE),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('LEFTPADDING', (0, 0), (-1, -1), 12),
                        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
                    ]))
                    elements.append(desc_table)
                
                if f_recommendation:
                    rec_data = [[Paragraph(f"Recommendation: {f_recommendation}", self.styles['TableCell'])]]
                    rec_table = Table(rec_data, colWidths=[self.content_width])
                    rec_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), SUCCESS_LIGHT),
                        ('TEXTCOLOR', (0, 0), (-1, -1), SUCCESS_DARK),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('LEFTPADDING', (0, 0), (-1, -1), 12),
                        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
                    ]))
                    elements.append(rec_table)
                
                elements.append(Spacer(1, 0.1*inch))
        
        # Email Information
        elements.append(Spacer(1, 0.15*inch))
        elements.append(Paragraph("Email Information", self.styles['SectionTitle']))
        
        metadata = analysis.get('email_metadata', {})
        sender = metadata.get('sender', analysis.get('sender', analysis.get('from', 'Unknown')))
        subject = metadata.get('subject', analysis.get('subject', analysis.get('subject_line', 'Unknown')))
        date = metadata.get('date', analysis.get('date', 'Unknown'))
        
        if not show_sensitive:
            sender = redact_email(sender)
            subject = redact_subject(subject, score)
        
        email_data = [
            [Paragraph("<b>Sender:</b>", self.styles['ReportBody']), Paragraph(_escape_xml(sender), self.styles['ReportBody'])],
            [Paragraph("<b>Subject:</b>", self.styles['ReportBody']), Paragraph(_escape_xml(subject), self.styles['ReportBody'])],
            [Paragraph("<b>Date:</b>", self.styles['ReportBody']), Paragraph(str(date), self.styles['ReportBody'])],
            [Paragraph("<b>Category:</b>", self.styles['ReportBody']), Paragraph(category, self.styles['ReportBody'])],
        ]
        
        email_table = Table(email_data, colWidths=[0.9*inch, self.content_width - 0.9*inch])
        email_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_DARK),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(email_table)
        
        # Threat Intelligence API Results
        threat_intel = analysis.get('threat_intelligence', {})
        ti_indicators_raw = threat_intel.get('indicators', analysis.get('indicators', []))
        
        # Filter to only show properly structured indicators (objects, not strings)
        ti_indicators = [ind for ind in ti_indicators_raw if isinstance(ind, dict)]
        
        # Filter warnings to only show actual API failures
        ti_warnings_raw = threat_intel.get('warnings', [])
        actual_warnings = []
        for w in ti_warnings_raw:
            if isinstance(w, str) and ('failed' in w.lower() or 'error' in w.lower()):
                actual_warnings.append(w)
        
        if ti_indicators or actual_warnings:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("Threat Intelligence Analysis", self.styles['SectionTitle']))
            
            ti_score = threat_intel.get('overall_risk_score', 0)
            
            # Count successful API calls
            successful_apis = len([ind for ind in ti_indicators if ind.get('success', True)])
            
            # TI Summary
            ti_summary_data = [
                [Paragraph("<b>TI Score:</b>", self.styles['ReportBody']),
                 Paragraph(f"<b>{int(ti_score * 100)}%</b>", self.styles['ReportBody']),
                 Paragraph("<b>APIs Checked:</b>", self.styles['ReportBody']),
                 Paragraph(str(len(ti_indicators)), self.styles['ReportBody']),
                 Paragraph("<b>Failed:</b>", self.styles['ReportBody']),
                 Paragraph(str(len(actual_warnings)), self.styles['ReportBody'])]
            ]
            ti_summary_table = Table(ti_summary_data, colWidths=[0.9*inch, 0.8*inch, 1.0*inch, 0.9*inch, 0.7*inch, 0.8*inch])
            ti_summary_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_DARK),
                ('BACKGROUND', (0, 0), (-1, -1), INFO_LIGHT),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('BOX', (0, 0), (-1, -1), 1, INFO_BLUE),
            ]))
            elements.append(ti_summary_table)
            elements.append(Spacer(1, 0.1*inch))
            
            # API Results Grid
            if ti_indicators:
                ind_table_data = [
                    [Paragraph("API", self.styles['TableHeader']),
                     Paragraph("Type", self.styles['TableHeader']),
                     Paragraph("Score", self.styles['TableHeader']),
                     Paragraph("Risk Level", self.styles['TableHeader']),
                     Paragraph("Details", self.styles['TableHeader'])]
                ]
                
                for ind in ti_indicators[:12]:
                    api_name = ind.get('api_name', 'Unknown')
                    ind_type = ind.get('indicator_type', '')
                    score = ind.get('score', 0)
                    risk_level = ind.get('risk_level', 'none')
                    details = ind.get('details', {})
                    
                    # Format details based on API type
                    detail_str = ""
                    if api_name == 'abuseipdb':
                        detail_str = f"Confidence: {details.get('abuse_confidence_score', 0)}%"
                    elif api_name == 'rdap':
                        age = details.get('age_in_days')
                        detail_str = f"Age: {age} days" if age else "Check unavailable"
                    elif api_name == 'abuseipdb_domain':
                        detail_str = f"IPs: {len(details.get('resolved_ips', []))}"
                    elif api_name == 'phishtank':
                        in_db = details.get('in_database', False)
                        detail_str = "In phishing DB" if in_db else "Not found"
                    elif api_name == 'virustotal_url' or api_name == 'virustotal_hash':
                        mal = details.get('malicious', 0)
                        detail_str = f"Malicious: {mal}"
                    elif api_name == 'urlscan':
                        cats = details.get('categories', [])
                        detail_str = ", ".join(cats[:2]) if cats else "Clean"
                    else:
                        detail_str = "Completed"
                    
                    if risk_level.upper() in ['CRITICAL', 'HIGH']:
                        sev_style = self.styles['SeverityCritical']
                    elif risk_level.upper() == 'MEDIUM':
                        sev_style = self.styles['SeverityHigh']
                    else:
                        sev_style = self.styles['SeverityLow']
                    
                    ind_table_data.append([
                    Paragraph(api_name.upper(), self.styles['TableCell']),
                    Paragraph(ind_type, self.styles['TableCell']),
                    Paragraph(f"{int(score * 100)}%", self.styles['TableCell']),
                    Paragraph(f"<b>{risk_level.upper()}</b>", sev_style),
                    Paragraph(_escape_xml(detail_str[:50]), self.styles['TableCell'])
                ])
            
            ind_table = Table(ind_table_data, colWidths=[1.0*inch, 1.0*inch, 0.6*inch, 0.8*inch, 2.7*inch])
            ind_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (2, 0), (3, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
            ]))
            elements.append(ind_table)
            
            # Show API failure warnings
            if actual_warnings:
                elements.append(Spacer(1, 0.1*inch))
                warn_data = [[
                    Paragraph("<b>⚠ API Failures:</b>", self.styles['ReportBody']),
                    Paragraph(_escape_xml(", ".join(actual_warnings[:5])), self.styles['ReportBody'])
                ]]
                warn_table = Table(warn_data, colWidths=[1.2*inch, self.content_width - 1.2*inch])
                warn_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), WARNING_LIGHT),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('BOX', (0, 0), (-1, -1), 1, WARNING_AMBER),
                ]))
                elements.append(warn_table)
        
        urls = analysis.get('urls_analyzed', analysis.get('urls', []))
        if urls:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("URLs Analyzed", self.styles['SectionTitle']))
            
            url_data = [
                [Paragraph("#", self.styles['TableHeader']),
                 Paragraph("URL", self.styles['TableHeader']),
                 Paragraph("Risk Score", self.styles['TableHeader'])]
            ]
            
            for i, url_info in enumerate(urls[:10], 1):
                url = url_info.get('url', url_info.get('original', 'Unknown'))
                url_score = url_info.get('risk_score', url_info.get('score', 0))
                segmented = segment_url(url)
                
                if url_score >= 70:
                    score_style = self.styles['ScoreRed']
                elif url_score >= 40:
                    score_style = self.styles['ScoreAmber']
                else:
                    score_style = self.styles['ScoreGreen']
                
                url_data.append([
                    Paragraph(str(i), self.styles['TableCell']),
                    Paragraph(_escape_xml(segmented), self.styles['TableCell']),
                    Paragraph(f"{url_score}%", score_style)
                ])
            
            url_table = Table(url_data, colWidths=[0.3*inch, 4*inch, 0.9*inch])
            url_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
            ]))
            elements.append(url_table)
        
        # Attachments
        attachments = analysis.get('attachments_analyzed', [])
        if attachments:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("Attachments Analyzed", self.styles['SectionTitle']))
            
            att_data = [
                [Paragraph("#", self.styles['TableHeader']),
                 Paragraph("Filename", self.styles['TableHeader']),
                 Paragraph("Type", self.styles['TableHeader']),
                 Paragraph("Score", self.styles['TableHeader']),
                 Paragraph("Status", self.styles['TableHeader'])]
            ]
            
            for i, att in enumerate(attachments[:8], 1):
                filename = _escape_xml(att.get('filename', 'Unknown'))
                content_type = att.get('content_type', 'Unknown') or 'Unknown'
                status = att.get('status', 'unknown')
                risk_score = att.get('risk_score', 0)
                
                # Get TI details if available
                ti_details = att.get('ti_details', {})
                if ti_details:
                    mal_count = ti_details.get('malicious', 0)
                    if mal_count > 0:
                        status = 'suspicious'
                
                if status in ['malicious', 'suspicious']:
                    status_style = self.styles['SeverityCritical']
                elif status == 'caution':
                    status_style = self.styles['SeverityHigh']
                else:
                    status_style = self.styles['SeverityLow']
                
                if risk_score >= 70:
                    score_style = self.styles['ScoreRed']
                elif risk_score >= 40:
                    score_style = self.styles['ScoreAmber']
                else:
                    score_style = self.styles['ScoreGreen']
                
                att_data.append([
                    Paragraph(str(i), self.styles['TableCell']),
                    Paragraph(filename[:25], self.styles['TableCell']),
                    Paragraph(content_type[:20], self.styles['TableCell']),
                    Paragraph(f"{risk_score}%", score_style),
                    Paragraph(f"<b>{status.upper()}</b>", status_style)
                ])
            
            att_table = Table(att_data, colWidths=[0.3*inch, 2.2*inch, 1.2*inch, 0.6*inch, 0.8*inch])
            att_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (4, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_CARD, BG_PAGE]),
            ]))
            elements.append(att_table)
        
        recommendations = analysis.get('recommendations', [])
        
        if not recommendations:
            if score >= 70:
                recommendations = [
                    "Do not click any links from this email",
                    "Do not download or open any attachments",
                    "Report this email to your security team immediately",
                    "Verify the sender through an alternative channel before responding",
                    "Consider blocking the sender"
                ]
            elif score >= 40:
                recommendations = [
                    "Exercise caution with links and attachments",
                    "Verify unexpected requests through official channels",
                    "Do not provide any personal or sensitive information",
                    "Report suspicious elements to your security team",
                    "Monitor your accounts for unusual activity"
                ]
            else:
                recommendations = [
                    "No specific threats detected",
                    "Continue practicing good email security habits",
                    "Be cautious of unexpected emails",
                    "Verify sender identity before opening attachments",
                    "Keep your security software updated"
                ]
        
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph("Recommendations", self.styles['SectionTitle']))
        
        for rec in recommendations[:5]:
            bullet_data = [[
                Paragraph("•", self.styles['BulletItem']),
                Paragraph(_escape_xml(rec), self.styles['BulletItem'])
            ]]
            bullet_table = Table(bullet_data, colWidths=[0.2*inch, self.content_width - 0.2*inch])
            bullet_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(bullet_table)
        
        elements.append(Spacer(1, 0.4*inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_LIGHT, spaceAfter=8))
        elements.append(Paragraph(
            f"Analysis Results generated by PhishCatcher on {datetime.now().strftime('%Y-%m-%d %H:%M UTC')} | Analysis ID: {analysis.get('id', 'N/A')}",
            self.styles['FooterText']
        ))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_summary_pdf(self, report_data: Dict[str, Any], start_date: str, end_date: str) -> bytes:
        """Generate basic summary PDF report (legacy, uses v2)."""
        return self.generate_summary_pdf_v2(report_data, start_date, end_date)


report_service = ProfessionalReportService()
