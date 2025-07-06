"""
arabic_english_detection.py
NEW FILE - Create this file in your project directory
This module handles all bilingual (Arabic/English) detection logic
"""

import re
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
from rapidfuzz import fuzz

# ============================================
# TIME OFF DETECTION
# ============================================

def detect_time_off_intent_multilingual(query: str) -> Tuple[bool, float]:
    """
    Detect if the user is trying to request time off in Arabic or English
    
    Args:
        query: User's message
        
    Returns:
        Tuple (is_time_off_request: bool, confidence: float)
    """
    query_lower = query.lower()
    
    # Non-request patterns (questions about balance, history, etc.)
    non_request_patterns = [
        # English
        r'how many days', r'how much (leave|time off|vacation)',
        r'check my (leave|balance|time off)', r'(leave|vacation|time off) balance',
        r'days (remaining|left|available)', r'did i take', r'have i taken',
        r'days i took', r'time off history', r'leave history',
        # Arabic
        r'كم يوم', r'كم (إجازة|اجازة|عطلة)', r'رصيد (إجازة|اجازة|إجازات|اجازات)',
        r'أيام (متبقية|متبقيه|باقية|باقيه)', r'هل أخذت', r'تاريخ (الإجازات|الاجازات)',
    ]
    
    if any(re.search(pattern, query_lower) for pattern in non_request_patterns):
        return False, 0.0
    
    # Expand time-off intent patterns
    TIME_OFF_PATTERNS = [
        # English
        r'request time off', r'take time off', r'need time off', r'book time off',
        r'request leave', r'take leave', r'i want a vacation', r'i need a vacation',
        r'i want a break', r'i need a break', r'going on vacation', r'plan to take',
        r'i want time off', r'can i take', r'may i take', r'i would like to take',
        r'apply for leave', r'leave application', r'leave request', r'leave of absence',
        r'absent from work', r'personal day', r'holiday request', r'vacation request',
        # Arabic
        r'إجازة', r'اجازة', r'عطلة', r'راحة', r'أريد إجازة', r'أحتاج إجازة', r'أريد أن آخذ إجازة',
        r'أريد أن آخذ يوم إجازة', r'أحتاج يوم إجازة', r'أريد يوم عطلة', r'أرغب في إجازة',
        r'أرغب في عطلة', r'أريد أن أطلب إجازة', r'أريد أن أطلب عطلة', r'أريد إجازة سنوية',
        r'أريد إجازة مرضية', r'أريد إجازة بدون راتب', r'أحتاج إجازة سنوية', r'أحتاج إجازة مرضية',
        r'أحتاج إجازة بدون راتب', r'أرغب في إجازة سنوية', r'أرغب في إجازة مرضية', r'أرغب في إجازة بدون راتب',
        r'أريد أن أأخذ إجازة', r'أريد أن أأخذ عطلة', r'أحتاج إلى إجازة', r'أحتاج إلى عطلة',
    ]
    
    if any(re.search(pattern, query_lower) for pattern in TIME_OFF_PATTERNS):
        return True, 0.8
    
    # Fuzzy matching for time-off patterns
    for pattern in TIME_OFF_PATTERNS:
        score = fuzz.partial_ratio(pattern.lower(), query_lower)
        if score >= 80:
            return True, 0.7
    
    # Keyword-based detection
    vacation_words = {
        'english': ['vacation', 'holiday', 'leave', 'off', 'away', 'pto', 'break'],
        'arabic': ['إجازة', 'اجازة', 'عطلة', 'راحة', 'استراحة']
    }
    
    temporal_words = {
        'english': ['tomorrow', 'next', 'this', 'from', 'to', 'between', 'on', 'starting'],
        'arabic': ['غدا', 'غداً', 'بكرة', 'القادم', 'القادمة', 'من', 'إلى', 'الى', 'بين', 'يوم', 'أيام', 'يوماً', 'الأسبوع', 'الشهر']
    }
    
    has_vacation = any(word in query_lower for word in vacation_words['english']) or \
                   any(word in query for word in vacation_words['arabic'])
                   
    has_temporal = any(word in query_lower for word in temporal_words['english']) or \
                   any(word in query for word in temporal_words['arabic'])
    
    if has_vacation and has_temporal:
        return True, 0.6  # Moderate confidence for fallback
    
    return False, 0.0

# ============================================
# OVERTIME DETECTION
# ============================================

def detect_overtime_intent_multilingual(query: str) -> bool:
    """Detect if the user is trying to request overtime in Arabic or English"""
    query_lower = query.lower()
    
    overtime_keywords = {
        'english': [
            'overtime', 'over time', 'extra hours', 'work extra',
            'work late', 'additional hours', 'extra work',
            'ot request', 'request overtime', 'book overtime'
        ],
        'arabic': [
            'إضافي', 'اضافي', 'عمل إضافي', 'عمل اضافي',
            'وقت إضافي', 'وقت اضافي', 'دوام إضافي', 'دوام اضافي',
            'ساعات إضافية', 'ساعات اضافية', 'شغل إضافي', 'شغل اضافي',
            'أوفر تايم', 'اوفر تايم', 'أوفرتايم', 'اوفرتايم'
        ]
    }
    
    return any(keyword in query_lower for keyword in overtime_keywords['english']) or \
           any(keyword in query for keyword in overtime_keywords['arabic'])

# ============================================
# TEMPLATE DETECTION
# ============================================

def detect_template_intent_multilingual(query: str) -> Optional[str]:
    """Detect if user is asking for a template in Arabic or English"""
    query_lower = query.lower()
    
    # Arabic letter detection
    if any(keyword in query for keyword in ['عربي', 'عربية', 'بالعربي', 'بالعربية', 'العربية']):
        if any(keyword in query for keyword in ['عمل', 'توظيف', 'وظيفة']):
            return 'employment_letter_arabic'
    
    # Embassy/visa letter
    embassy_keywords = {
        'english': ['embassy', 'visa', 'travel', 'consulate'],
        'arabic': ['سفارة', 'سفاره', 'قنصلية', 'قنصليه', 'فيزا', 'تأشيرة', 'تاشيرة']
    }
    if any(keyword in query_lower for keyword in embassy_keywords['english']) or \
       any(keyword in query for keyword in embassy_keywords['arabic']):
        return 'employment_letter_embassy'
    
    # Experience letter
    experience_keywords = {
        'english': ['experience', 'service', 'former', 'past'],
        'arabic': ['خبرة', 'خبره', 'شهادة خبرة', 'شهادة خبره']
    }
    if any(keyword in query_lower for keyword in experience_keywords['english']) or \
       any(keyword in query for keyword in experience_keywords['arabic']):
        return 'experience_letter'
    
    # Employment letter
    employment_keywords = {
        'english': ['employment letter', 'work certificate', 'employment certificate'],
        'arabic': ['خطاب عمل', 'شهادة عمل', 'رسالة عمل', 'خطاب توظيف']
    }
    if any(keyword in query_lower for keyword in employment_keywords['english']) or \
       any(keyword in query for keyword in employment_keywords['arabic']):
        return 'employment_letter'
    
    # General template request
    template_keywords = {
        'english': ['template', 'document', 'certificate', 'letter'],
        'arabic': ['خطاب', 'شهادة', 'شهاده', 'نموذج', 'وثيقة', 'وثيقه', 'رسالة', 'رساله', 'مستند']
    }
    if any(keyword in query_lower for keyword in template_keywords['english']) or \
       any(keyword in query for keyword in template_keywords['arabic']):
        return 'general_template_request'
    
    return None

# ============================================
# APPROVAL DETECTION (FOR MANAGERS)
# ============================================

def detect_approval_intent_multilingual(query: str) -> Optional[str]:
    """Detect if the user (manager) is trying to approve/deny requests"""
    query_lower = query.lower()
    
    # View pending requests
    view_keywords = {
        'english': [
            'pending requests', 'pending time off', 'pending leave',
            'requests pending', 'time off requests', 'leave requests',
            'approve requests', 'review requests', 'show requests',
            'view requests', 'check requests', 'my team requests'
        ],
        'arabic': [
            'طلبات معلقة', 'طلبات معلقه', 'الطلبات المعلقة', 'الطلبات المعلقه',
            'طلبات إجازة', 'طلبات اجازة', 'طلبات الإجازة', 'طلبات الاجازة',
            'طلبات فريقي', 'طلبات موظفيني', 'طلبات الموظفين'
        ]
    }
    
    # Approve keywords
    approve_keywords = {
        'english': [
            'approve request', 'approve time off', 'approve leave',
            'approve id', 'approve #', 'yes approve', 'confirm request',
            'accept request', 'grant time off', 'grant leave'
        ],
        'arabic': [
            'موافقة طلب', 'موافقه طلب', 'أوافق على', 'اوافق على',
            'قبول طلب', 'اقبل طلب', 'أقبل طلب', 'موافق على الطلب'
        ]
    }
    
    # Deny keywords
    deny_keywords = {
        'english': [
            'deny request', 'deny time off', 'deny leave',
            'reject request', 'reject time off', 'reject leave',
            'decline request', 'refuse request'
        ],
        'arabic': [
            'رفض طلب', 'أرفض طلب', 'ارفض طلب',
            'لا أوافق', 'لا اوافق', 'رفض الطلب'
        ]
    }
    
    # Check intents
    if any(keyword in query_lower for keyword in approve_keywords['english']) or \
       any(keyword in query for keyword in approve_keywords['arabic']):
        return 'approve'
        
    if any(keyword in query_lower for keyword in deny_keywords['english']) or \
       any(keyword in query for keyword in deny_keywords['arabic']):
        return 'deny'
        
    if any(keyword in query_lower for keyword in view_keywords['english']) or \
       any(keyword in query for keyword in view_keywords['arabic']):
        return 'view_pending'
    
    # Pattern matching for "approve 123" or "موافقة 123"
    if re.search(r'\b(approve|accept|grant)\s+\d+\b', query_lower) or \
       re.search(r'(موافقة|موافقه|أوافق|اوافق)\s*\d+', query):
        return 'approve'
        
    if re.search(r'\b(deny|reject|decline|refuse)\s+\d+\b', query_lower) or \
       re.search(r'(رفض|أرفض|ارفض)\s*\d+', query):
        return 'deny'
    
    return None

# ============================================
# EXIT INTENT DETECTION
# ============================================

def detect_exit_intent_multilingual(query: str) -> bool:
    """Detect if the user wants to exit the current flow"""
    query_lower = query.lower().strip()
    
    exit_keywords = {
        'english': [
            'cancel', 'exit', 'stop', 'quit', 'nevermind', 'never mind',
            'back', 'go back', 'return', 'normal chat', 'regular chat',
            'forget it', 'skip', 'abort', 'done', 'finish'
        ],
        'arabic': [
            'إلغاء', 'الغاء', 'ألغي', 'الغي', 'ألغ', 'الغ',
            'توقف', 'أوقف', 'اوقف', 'قف',
            'رجوع', 'ارجع', 'أرجع', 'عودة', 'عوده',
            'خروج', 'اخرج', 'أخرج',
            'انهي', 'أنهي', 'انتهى', 'انتهيت',
            'كفاية', 'كفايه', 'خلاص', 'بس'
        ]
    }
    
    return query_lower in exit_keywords['english'] or \
           query.strip() in exit_keywords['arabic'] or \
           any(keyword in query_lower for keyword in exit_keywords['english']) or \
           any(keyword in query for keyword in exit_keywords['arabic'])

# ============================================
# DATE PARSING
# ============================================

def parse_arabic_date(date_str: str) -> Optional[str]:
    """Parse Arabic date expressions and return ISO format"""
    
    # Arabic month names
    arabic_months = {
        'يناير': 1, 'كانون الثاني': 1,
        'فبراير': 2, 'شباط': 2,
        'مارس': 3, 'آذار': 3,
        'أبريل': 4, 'ابريل': 4, 'نيسان': 4,
        'مايو': 5, 'أيار': 5,
        'يونيو': 6, 'حزيران': 6,
        'يوليو': 7, 'تموز': 7,
        'أغسطس': 8, 'اغسطس': 8, 'آب': 8,
        'سبتمبر': 9, 'أيلول': 9,
        'أكتوبر': 10, 'اكتوبر': 10, 'تشرين الأول': 10,
        'نوفمبر': 11, 'تشرين الثاني': 11,
        'ديسمبر': 12, 'كانون الأول': 12
    }
    
    today = datetime.now()
    
    # Handle relative dates
    if 'اليوم' in date_str:
        return today.strftime('%Y-%m-%d')
    elif any(word in date_str for word in ['غدا', 'غداً', 'بكرة', 'بكره']):
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'بعد غد' in date_str:
        return (today + timedelta(days=2)).strftime('%Y-%m-%d')
    
    # Try to parse month and day
    for month_name, month_num in arabic_months.items():
        if month_name in date_str:
            day_match = re.search(r'(\d+)', date_str)
            if day_match:
                day = int(day_match.group(1))
                year = today.year
                try:
                    parsed_date = datetime(year, month_num, day)
                    if parsed_date < today:
                        parsed_date = datetime(year + 1, month_num, day)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
    
    return None

def convert_arabic_numerals(text: str) -> str:
    """Convert Arabic numerals to English numerals"""
    arabic_to_english = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    for ar, en in arabic_to_english.items():
        text = text.replace(ar, en)
    return text