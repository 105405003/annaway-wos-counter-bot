"""
時間操作工具
"""
from datetime import datetime

def now() -> datetime:
    """獲取當前時間"""
    return datetime.now()

def format_mmss(seconds: int) -> str:
    """
    格式化秒數為 MM:SS
    
    Args:
        seconds: 總秒數
        
    Returns:
        格式化的字串，例如 "05:30"
    """
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"

def format_countdown(seconds: int) -> str:
    """
    格式化倒數顯示
    
    Args:
        seconds: 剩餘秒數
        
    Returns:
        格式化的字串
    """
    if seconds > 60:
        return format_mmss(seconds)
    elif seconds > 0:
        return f"{seconds}"
    else:
        return "**REFILL**"

