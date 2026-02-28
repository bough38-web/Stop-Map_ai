import json
import os
from datetime import datetime
from pathlib import Path

# Storage directory
# Use absolute path resolution to avoid issues with Streamlit execution context
# Storage directory - [FIX] Move outside project to prevent Streamlit reload loops
# BASE_DIR = Path(os.path.abspath(__file__)).parent.parent
# Storage directory - [FIX] Move outside project to prevent Streamlit reload loops
# [CLOUD_COMPAT] Handle read-only home directory by falling back to /tmp
STORAGE_DIR = Path(os.path.expanduser("~")) / ".sales_assistant_data"
try:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    import tempfile
    STORAGE_DIR = Path(tempfile.gettempdir()) / ".sales_assistant_data"
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

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
    """Load JSON file, return empty dict/list if not exists or corrupted"""
    filepath = Path(filepath) # Ensure Path object
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"CRITICAL: JSON Decode Error in {filepath}: {e}")
            # [SAFETY] Backup corrupted file
            try:
                backup_path = filepath.with_suffix(f".bak_{datetime.now().strftime('%Y%m%d%H%M%S')}")
                os.rename(filepath, backup_path)
                print(f"Backing up corrupted file to {backup_path}")
            except: pass
            return [] if 'logs' in str(filepath.name) or 'history' in str(filepath.name) else {}
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return [] if 'logs' in str(filepath.name) or 'history' in str(filepath.name) else {}
    return [] if 'logs' in str(filepath.name) or 'history' in str(filepath.name) else {}


def save_json_file(filepath, data):
    """Save data to JSON file atomically (Write to temp -> Rename)"""
    filepath = Path(filepath) # Ensure Path object
    try:
        # Ensure parent dir exists
        if hasattr(filepath, 'parent'):
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
        # Atomic Write Pattern
        temp_path = filepath.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno()) # Force write to disk
            
        # Rename temp to actual (Atomic on POSIX)
        os.replace(temp_path, filepath)
        
        # print(f"DEBUG: Successfully saved to {filepath}")
        return True
    except Exception as e:
        print(f"DEBUG: Error saving {filepath}: {e}")
        # Try to clean up temp
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except: pass
        return False


# ===== ACCESS LOGGING =====

def log_access(user_role, user_name, action="login"):
    """Log user access"""
    logs = load_json_file(ACCESS_LOG_FILE)
    
    log_entry = {
        "timestamp": utils.get_now_kst_str(),
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
    # Fallback to alternative address columns if primary is missing
    addr = row.get('소재지전체주소') or row.get('도로명전체주소') or row.get('주소') or ""
    return utils.generate_record_key(row.get('사업장명'), addr)


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
    from src import utils
    statuses = load_json_file(ACTIVITY_STATUS_FILE)
    
    old_data = statuses.get(record_key, {})
    
    new_data = {
        "활동진행상태": status,
        "특이사항": notes,
        "변경일시": utils.get_now_kst_str(),
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
        "timestamp": utils.get_now_kst_str(),
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
        "timestamp": utils.get_now_kst_str(),
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

# ===== ATOMIC TRANSACTIONS (REDESIGN) =====

def register_visit(record_key, content, audio_file, photo_file, user_info, forced_status=None):
    """
    ATOMIC OPERATION: Register a visit.
    1. Save Visit Report
    2. Update Activity Status (to 'Visit' or forced status)
    3. Log History
    
    Returns: (bool, msg)
    """
    try:
        from src import utils
        # 1. Save Media
        audio_path = None
        photo_path = None
        
        # [FIX] Force KST Timezone to prevent UTC Server Display Bug
        ts_str = utils.get_now_kst_str() # e.g. "2026-03-01 03:00:00"
        
        # For file prefix, create a clean string from the KST timestamp
        # Converting KST string back to datetime to use strftime
        from dateutil import parser
        try:
            timestamp_kst = parser.parse(ts_str)
            file_prefix = f"{timestamp_kst.strftime('%Y%m%d_%H%M%S')}_{user_info.get('name', 'unknown')}"
        except Exception:
            file_prefix = f"visit_{user_info.get('name', 'unknown')}"
        
        if audio_file:
            ext = audio_file.name.split('.')[-1] if '.' in audio_file.name else "wav"
            fname = f"{file_prefix}_audio.{ext}"
            save_path = VISIT_MEDIA_DIR / fname
            with open(save_path, "wb") as f:
                f.write(audio_file.getvalue())
            audio_path = str(fname)
            
        if photo_file:
            ext = photo_file.name.split('.')[-1] if '.' in photo_file.name else "jpg"
            fname = f"{file_prefix}_photo.{ext}"
            save_path = VISIT_MEDIA_DIR / fname
            with open(save_path, "wb") as f:
                f.write(photo_file.getvalue())
            photo_path = str(fname)

        # 2. Determine New Status
        # Default to "✅ 방문" if not forced. 
        # If user selected a specific status in a dropdown, use that.
        new_status = forced_status if forced_status else ACTIVITY_STATUS_MAP["방문"]
        new_status = normalize_status(new_status)

        # 3. Create Visit Report Entry
        visit_entry = {
            "id": f"rep_{timestamp.timestamp()}",
            "timestamp": ts_str,
            "record_key": record_key,
            "content": content,
            "audio_path": audio_path,
            "photo_path": photo_path,
            "user_name": user_info.get("name"),
            "user_role": user_info.get("role"),
            "user_branch": user_info.get("branch"),
            "resulting_status": new_status # Link result
        }
        
        # 4. Update Status Entry
        status_entry = {
            "활동진행상태": new_status,
            "특이사항": content, # Sync notes
            "변경일시": ts_str,
            "변경자": user_info.get("name")
        }
        
        # 5. EXECUTE WRITES (Sequential)
        
        # A. Reports
        reports = load_json_file(VISIT_REPORT_FILE)
        reports.append(visit_entry)
        save_json_file(VISIT_REPORT_FILE, reports)
        
        # B. Status & History (Reuse save_activity_status for history logic)
        # We manually call internal save to avoid double loading
        _save_status_internal(record_key, status_entry)
        
        return True, "저장 완료"
        
    except Exception as e:
        print(f"CRITICAL ERROR in register_visit: {e}")
        return False, str(e)

def register_visit_batch(batch_list):
    """
    BATCH OPERATION: Register multiple visits efficiently.
    - batch_list: list of dicts {record_key, content, user_info, forced_status}
    
    1. Load all files once
    2. Process updates in memory
    3. Save files once
    """
    if not batch_list:
        return True, "No changes"
        
    try:
        # 1. Load data
        reports = load_json_file(VISIT_REPORT_FILE)
        if not isinstance(reports, list): reports = []
        
        from src import utils
        from dateutil import parser
        statuses = load_json_file(ACTIVITY_STATUS_FILE)
        
        ts_str = utils.get_now_kst_str()
        try:
            timestamp_kst_dt = parser.parse(ts_str)
            timestamp_float = timestamp_kst_dt.timestamp()
        except Exception:
            timestamp_float = 0.0
        
        # 2. Process changes
        for item in batch_list:
            record_key = item['record_key']
            content = item['content']
            user_info = item['user_info']
            forced_status = item.get('forced_status')
            
            # Determine Status
            new_status = forced_status if forced_status else ACTIVITY_STATUS_MAP["방문"]
            new_status = normalize_status(new_status)
            
            # Create Report Entry
            visit_entry = {
                "id": f"rep_{timestamp_float}_{item.get('record_key', 'unk')[:5]}",
                "timestamp": ts_str,
                "record_key": record_key,
                "content": content,
                "audio_path": None,
                "photo_path": None,
                "user_name": user_info.get("name"),
                "user_role": user_info.get("role"),
                "user_branch": user_info.get("branch"),
                "resulting_status": new_status
            }
            reports.append(visit_entry)
            
            # Update Status Entry
            old_status_data = statuses.get(record_key, {})
            new_status_data = {
                "활동진행상태": new_status,
                "특이사항": content,
                "변경일시": ts_str,
                "변경자": user_info.get("name")
            }
            statuses[record_key] = new_status_data
            
            # Log History if changed
            if old_status_data.get("활동진행상태") != new_status or \
               old_status_data.get("특이사항") != content:
                log_change_history(record_key, old_status_data, new_status_data, user_info.get("name"))
                
        # 3. Save files
        save_json_file(VISIT_REPORT_FILE, reports)
        save_json_file(ACTIVITY_STATUS_FILE, statuses)
        
        return True, f"{len(batch_list)}건 저장 완료"
        
    except Exception as e:
        print(f"CRITICAL ERROR in register_visit_batch: {e}")
        return False, str(e)

def update_visit_report(report_id, new_content, new_photo_file=None):
    """
    Update an existing visit report.
    - report_id: ID of the report to update
    - new_content: New text content (appended or replaced? Let's assume replace or user handles appending)
    - new_photo_file: Streamlit UploadedFile (optional)
    """
    try:
        reports = load_json_file(VISIT_REPORT_FILE)
        target_idx = next((i for i, r in enumerate(reports) if r.get("id") == report_id), -1)
        
        if target_idx == -1:
            return False, "리포트를 찾을 수 없습니다."
            
        report = reports[target_idx]
        
        # Update Content
        if new_content:
            report['content'] = new_content
            
        # Update Photo
        if new_photo_file:
            from src import utils
            from dateutil import parser
            ts_str = utils.get_now_kst_str()
            try:
                timestamp_kst = parser.parse(ts_str)
                file_prefix = f"{timestamp_kst.strftime('%Y%m%d_%H%M%S')}_update"
            except Exception:
                file_prefix = "update_photo"
                
            ext = new_photo_file.name.split('.')[-1] if '.' in new_photo_file.name else "jpg"
            fname = f"{file_prefix}_photo.{ext}"
            save_path = VISIT_MEDIA_DIR / fname
            
            with open(save_path, "wb") as f:
                f.write(new_photo_file.getvalue())
            
            report['photo_path'] = str(fname)
            
        # Prepare for save
        reports[target_idx] = report
        save_json_file(VISIT_REPORT_FILE, reports)
        
        return True, "수정 완료"
        
    except Exception as e:
        return False, str(e)

def _save_status_internal(record_key, new_data_dict):
    """
    Internal helper to save status and log history.
    [NEW] Automatically creates a visit report entry if status changes.
    """
    statuses = load_json_file(ACTIVITY_STATUS_FILE)
    old_data = statuses.get(record_key, {})
    
    statuses[record_key] = new_data_dict
    save_json_file(ACTIVITY_STATUS_FILE, statuses)
    
    # Log Change if different
    if old_data.get("활동진행상태") != new_data_dict.get("활동진행상태") or \
       old_data.get("특이사항") != new_data_dict.get("특이사항"):
           
        log_change_history(record_key, old_data, new_data_dict, new_data_dict.get("변경자"))
        
        # [NEW] Integration: Create a visit report for visibility in "Activity History"
        # Only if it's not already a "Visit" which is handled by register_visit
        if new_data_dict.get("활동진행상태") != ACTIVITY_STATUS_MAP.get("방문"):
            timestamp = datetime.now()
            ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            # We don't have full user_info here, but we have user_name (변경자)
            # We'll try to infer or just log with what we have.
            visit_entry = {
                "id": f"rep_sys_{timestamp.timestamp()}",
                "timestamp": ts_str,
                "record_key": record_key,
                "content": f"[시스템 자동] 활동 상태가 '{new_data_dict.get('활동진행상태')}'(으)로 변경되었습니다. (특이사항: {new_data_dict.get('특이사항', '-')})",
                "audio_path": None,
                "photo_path": None,
                "user_name": new_data_dict.get("변경자", "Unknown"),
                "resulting_status": new_data_dict.get("활동진행상태")
            }
            
            reports = load_json_file(VISIT_REPORT_FILE)
            if not isinstance(reports, list): reports = []
            reports.append(visit_entry)
            save_json_file(VISIT_REPORT_FILE, reports)

# Backward Compatibility & Direct Status Change (e.g. from Grid)
def save_activity_status(record_key, status, notes, user_name):
    """
    Save activity status for a record (Direct Update).
    Wraps _save_status_internal.
    """
    status = normalize_status(status)
    new_data = {
        "활동진행상태": status,
        "특이사항": notes,
        "변경일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "변경자": user_name
    }
    _save_status_internal(record_key, new_data)
    return True

def delete_visit_report(report_id):
    """지정된 ID의 방문/활동 이력을 삭제합니다."""
    reports = load_json_file(VISIT_REPORT_FILE)
    if not isinstance(reports, list): return False, "No data found."
    
    new_reports = [r for r in reports if r.get("id") != report_id]
    
    if len(new_reports) == len(reports):
        return False, "Report not found."
        
    save_json_file(VISIT_REPORT_FILE, new_reports)
    return True, "Deleted successfully."

# Read Methods
def get_visit_reports(record_key=None, user_name=None, user_branch=None, limit=100):
    reports = load_json_file(VISIT_REPORT_FILE)
    if not isinstance(reports, list): reports = []
    
    if record_key:
        reports = [r for r in reports if r.get("record_key") == record_key]
    if user_name:
        reports = [r for r in reports if r.get("user_name") == user_name]
    if user_branch:
        reports = [r for r in reports if r.get("user_branch") == user_branch]
        
    reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return reports[:limit]

def get_media_path(filename):
    if not filename: return None
    return str(VISIT_MEDIA_DIR / filename)
