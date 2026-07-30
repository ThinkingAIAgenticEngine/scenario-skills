"""
Intent Parser Module - Recognize user query intent and extract parameters
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class IntentParser:
    """Query Intent Parser"""
    
    # Intent keyword mapping
    INTENT_KEYWORDS = {
        'behavior_trace': ['what did', 'behavior', 'events', 'trace', 'log', 'history', 'actions', 'activity'],
        'economy_query': ['spent', 'money', 'payment', 'consumption', 'purchase', 'economy', 'recharge', 'paid', 'how much'],
        'progress_query': ['level', 'progress', 'stage', 'achievement', 'rank', 'chapter'],
        'churn_analysis': ['churn', 'why', 'stop playing', 'quit', 'inactive', 'left', 'uninstalled'],
        'session_query': ['login', 'online', 'session', 'active time', 'last seen', 'duration'],
        'profile_query': ['profile', 'info', 'information', 'details', 'check', 'view', 'look at']
    }
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse user input, return intent and parameters
        
        Returns:
            {
                'intent': str,
                'user_id': str,
                'time_range': dict,
                'original_text': str
            }
        """
        text_lower = text.lower()
        
        return {
            'intent': self._parse_intent(text_lower),
            'user_id': self._extract_user_id(text),
            'time_range': self._parse_time_range(text_lower),
            'original_text': text
        }
    
    def _parse_intent(self, text: str) -> str:
        """Parse query intent"""
        scores = {}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[intent] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return 'profile_query'  # Default intent
    
    def _extract_user_id(self, text: str) -> Optional[str]:
        """Extract user ID from text"""
        patterns = [
            (r'user\s*[:]?\s*(\d+)', 'user ID'),
            (r'player\s*[:]?\s*(\d+)', 'player ID'),
            (r'(?:uid|UID|user.?id)\s*[:]?\s*(\d+)', 'UID'),
            (r'#(\d{5,})', 'hash ID'),
            (r'\b(\d{6,})\b', 'numeric ID'),
        ]
        
        for pattern, _ in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _parse_time_range(self, text: str) -> Dict[str, Any]:
        """Parse time range"""
        now = datetime.now()
        
        # Yesterday
        if 'yesterday' in text:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return {'start': start, 'end': end, 'label': 'yesterday'}
        
        # Today
        if 'today' in text:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
            return {'start': start, 'end': end, 'label': 'today'}
        
        # Last N days
        match = re.search(r'last\s*(\d+)\s*days?', text)
        if match:
            days = int(match.group(1))
            return {
                'start': now - timedelta(days=days),
                'end': now,
                'label': f'last {days} days'
            }
        
        # Last week
        if 'last week' in text:
            start = now - timedelta(days=now.weekday() + 7)
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            return {'start': start, 'end': end, 'label': 'last week'}
        
        # Last month
        if 'last month' in text:
            first_day = now.replace(day=1)
            end = first_day - timedelta(days=1)
            start = end.replace(day=1)
            return {'start': start, 'end': end, 'label': 'last month'}
        
        # Default last 7 days
        return {
            'start': now - timedelta(days=7),
            'end': now,
            'label': 'last 7 days'
        }


# Convenience function
def parse_query(text: str) -> Dict[str, Any]:
    """Convenience function: Parse query"""
    parser = IntentParser()
    return parser.parse(text)


if __name__ == '__main__':
    # Test
    test_cases = [
        "Check user 12345",
        "What did player 67890 do yesterday",
        "How much did user 11111 spend",
        "Why did 22222 churn",
        "Progress of user 33333",
    ]
    
    parser = IntentParser()
    for text in test_cases:
        result = parser.parse(text)
        print(f"\nInput: {text}")
        print(f"Intent: {result['intent']}")
        print(f"User ID: {result['user_id']}")
        print(f"Time Range: {result['time_range']['label']}")
