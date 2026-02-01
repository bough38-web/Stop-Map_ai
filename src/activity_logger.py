import json
import os
from datetime import datetime
from pathlib import Path

# Storage directory
# Use absolute path resolution to avoid issues with Streamlit execution context
BASE_DIR = Path(os.path.abspath(__file__)).parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)

ACCESS_LOG_FILE = STORAGE_DIR / "access_logs.json"
ACTIVITY_STATUS_FILE = STORAGE_DIR / "activity_status.json"
ACTIVITY_STATUS_FILE = STORAGE_DIR / "activity_status.json"
CHANGE_HISTORY_FILE = STORAGE_DIR / "change_history.json"

# [CONSTANTS] Activity Status Constants
# Centralized source of truth for all activity statuses
ACTIVITY_STATUS_MAP = {
    "방문": "✅ 방문",
    "상담중": "🟡 상담중",
    "상담완료": "🔵 상담완료",
    "상담불가": "🔴 상담불가",
    "계약완료": "🟢 계약완료"
}

# Helper to get normalized status
def normalize_status(status_str):
    if not status_str or status_str == "None" or status_str == "nan": return ""
    
    # Check if already has emoji (Value check)
    if status_str in ACTIVITY_STATUS_MAP.values():
        return status_str
        
    activity_key = str(status_str).replace("✅ ", "").replace("🟡 ", "").replace("🔵 ", "").replace("🔴 ", "").replace("🟢 ", "").strip()
    return ACTIVITY_STATUS_MAP.get(activity_key, status_str) # Default to original if no match


def load_json_file(filepath):
    """Load JSON file, return empty dict/list if not exists"""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return [] if 'logs' in filepath.name or 'history' in filepath.name else {}
    return [] if 'logs' in filepath.name or 'history' in filepath.name else {}


def save_json_file(filepath, data):
    """Save data to JSON file"""
    try:
        # Ensure parent dir exists
        if hasattr(filepath, 'parent'):
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"DEBUG: Successfully saved to {filepath}")
        return True
    except Exception as e:
        print(f"DEBUG: Error saving {filepath}: {e}")
        return False


# ===== ACCESS LOGGING =====

def log_access(user_role, user_name, action="login"):
    """Log user access"""
    logs = load_json_file(ACCESS_LOG_FILE)
    
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_role": user_role,
        "user_name": user_name,
        "action": action
    }
    
    logs.append(log_entry)
    
    # Keep only last 1000 entries
    if len(logs) > 1000:
        logs = logs[-1000:]
    
    save_json_file(ACCESS_LOG_FILE, logs)


def get_access_logs(limit=100):
    """Get recent access logs"""
    logs = load_json_file(ACCESS_LOG_FILE)
    return logs[-limit:] if logs else []


# ===== ACTIVITY STATUS =====

from . import utils

def get_record_key(row):
    """Generate unique key for a record (Normalized)"""
    # Use centralized logic to prevent mismatch
    return utils.generate_record_key(row.get('사업장명'), row.get('소재지전체주소'))


def get_activity_status(record_key):
    """Get activity status for a record"""
    statuses = load_json_file(ACTIVITY_STATUS_FILE)
    return statuses.get(record_key, {
        "활동진행상태": "",
        "특이사항": "",
        "변경일시": "",
        "변경자": ""
    })


def save_activity_status(record_key, status, notes, user_name):
    """Save activity status for a record"""
    statuses = load_json_file(ACTIVITY_STATUS_FILE)
    
    old_data = statuses.get(record_key, {})
    
    new_data = {
        "활동진행상태": status,
        "특이사항": notes,
        "변경일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "변경자": user_name
    }
    
    statuses[record_key] = new_data
    save_json_file(ACTIVITY_STATUS_FILE, statuses)
    
    # Log change history
    if old_data.get("활동진행상태") != status or old_data.get("특이사항") != notes:
        log_change_history(record_key, old_data, new_data, user_name)

    return True


def log_change_history(record_key, old_data, new_data, user_name):
    """Log change to history"""
    history = load_json_file(CHANGE_HISTORY_FILE)
    
    change_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "record_key": record_key,
        "user": user_name,
        "old_status": old_data.get("활동진행상태", ""),
        "new_status": new_data.get("활동진행상태", ""),
        "old_notes": old_data.get("특이사항", ""),
        "new_notes": new_data.get("특이사항", "")
    }
    
    history.append(change_entry)
    
    # Keep only last 5000 entries
    if len(history) > 5000:
        history = history[-5000:]
    
    save_json_file(CHANGE_HISTORY_FILE, history)


def get_change_history(record_key=None, limit=100):
    """Get change history, optionally filtered by record_key"""
    history = load_json_file(CHANGE_HISTORY_FILE)
    
    if record_key:
        history = [h for h in history if h.get("record_key") == record_key]
    
    return history[-limit:] if history else []
    
    
def get_user_activity_keys(user_name):
    """Get list of record keys that have been modified by this user"""
    statuses = load_json_file(ACTIVITY_STATUS_FILE)
    if not statuses: return []
    
    keys = []
    for k, v in statuses.items():
        if v.get('변경자') == user_name:
            keys.append(k)
            
    return keys



# ===== VIEW LOGGING =====

VIEW_LOG_FILE = STORAGE_DIR / "view_logs.json"

def log_view(user_role, user_name, target, details):
    """Log view/search activity"""
    logs = load_json_file(VIEW_LOG_FILE)
    
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_role": user_role,
        "user_name": user_name,
        "target": target,
        "details": details
    }
    
    logs.append(log_entry)
    
    # Keep only last 2000 entries (views happen more often)
    if len(logs) > 2000:
        logs = logs[-2000:]
        
    save_json_file(VIEW_LOG_FILE, logs)

def get_view_logs(limit=100):
    """Get recent view logs"""
    logs = load_json_file(VIEW_LOG_FILE)
    return logs[-limit:] if logs else []


# ===== VISIT REPORTS (Text, Voice, Photo) =====

VISIT_REPORT_FILE = STORAGE_DIR / "visit_reports.json"
VISIT_MEDIA_DIR = STORAGE_DIR / "visits"
VISIT_MEDIA_DIR.mkdir(exist_ok=True)

def save_visit_report(record_key, content, audio_file, photo_file, user_info):
    """
    Save a comprehensive visit report.
    - record_key: Unique ID of the place
    - content: Text notes
    - audio_file: Streamlit UploadedFile object (Audio)
    - photo_file: Streamlit UploadedFile object (Image)
    - user_info: Dict with user details
    """
    reports = load_json_file(VISIT_REPORT_FILE)
    
    timestamp = datetime.now()
    ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    file_prefix = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{user_info.get('name', 'unknown')}"
    
    # Save Media Files
    audio_path = None
    photo_path = None
    
    if audio_file:
        # Determine extension (usually wav or webm depending on browser/streamlit version)
        ext = audio_file.name.split('.')[-1] if '.' in audio_file.name else "wav"
        fname = f"{file_prefix}_audio.{ext}"
        save_path = VISIT_MEDIA_DIR / fname
        with open(save_path, "wb") as f:
            f.write(audio_file.getvalue())
        audio_path = str(fname) # Store relative filename
        
    if photo_file:
        ext = photo_file.name.split('.')[-1] if '.' in photo_file.name else "jpg"
        fname = f"{file_prefix}_photo.{ext}"
        save_path = VISIT_MEDIA_DIR / fname
        with open(save_path, "wb") as f:
            f.write(photo_file.getvalue())
        photo_path = str(fname)

    report_entry = {
        "id": f"rep_{timestamp.timestamp()}",
        "timestamp": ts_str,
        "record_key": record_key,
        "content": content,
        "audio_path": audio_path,
        "photo_path": photo_path,
        "user_name": user_info.get("name"),
        "user_role": user_info.get("role"),
        "user_branch": user_info.get("branch")
    }
    
    reports.append(report_entry)
    save_json_file(VISIT_REPORT_FILE, reports)
    return True

def get_visit_reports(record_key=None, user_name=None, user_branch=None, limit=100):
    """
    Get visit reports filtered by key, user, or branch.
    """
    reports = load_json_file(VISIT_REPORT_FILE)
    if not isinstance(reports, list):
        reports = []
    
    if record_key:
        reports = [r for r in reports if r.get("record_key") == record_key]
        
    if user_name:
        reports = [r for r in reports if r.get("user_name") == user_name]
        
    if user_branch:
        reports = [r for r in reports if r.get("user_branch") == user_branch]
        
    # Sort by timestamp desc
    reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return reports[:limit]

def get_media_path(filename):
    """Return absolute path to media file"""
    if not filename: return None
    return str(VISIT_MEDIA_DIR / filename)
