import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
try:
    import streamlit as st
    from streamlit_gsheets import GSheetsConnection
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

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
                from src import utils
                backup_path = filepath.with_suffix(f".bak_{utils.get_now_kst_str().replace(' ', '_').replace(':', '')}")
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
        
        # [NEW] Sync to GSheet if it's one of the persistent files
        if filepath.name in ["activity_status.json", "visit_reports.json", "change_history.json"]:
            sync_to_gsheet(filepath.name, data)
            
        return True
    except Exception as e:
        print(f"DEBUG: Error saving {filepath}: {e}")
        # Try to clean up temp
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except: pass
        return False


def sync_to_gsheet(filename, data):
    """Sync specific JSON data to Google Sheets for persistence"""
    if not HAS_GSHEETS: return
    
    # We only sync in Streamlit context
    try:
        # Check if secrets/connection is configured
        if "connections" not in st.secrets or "gsheets" not in st.secrets.connections:
            st.warning("⚠️ 구글 시트 연결 설정(Secrets)이 누락되었습니다. 데이터가 서버에만 저장됩니다.")
            return
            
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Determine Worksheet Name
        ws_name = filename.split('.')[0] # e.g. activity_status
        
        # Convert to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # For dict-based statuses, flatten or convert to rows
            rows = []
            for k, v in data.items():
                row = {"record_key": k}
                row.update(v)
                rows.append(row)
            df = pd.DataFrame(rows)
        else:
            return
            
        # Update Spreadsheet (Requires Service Account in Secrets)
        # Note: clear=True to replace previous state
        conn.update(worksheet=ws_name, data=df)
        st.toast(f"✅ 구글 시트 동기화 완료: {ws_name}")
        
    except Exception as e:
        st.error(f"❌ 구글 시트 동기화 실패 ({filename}): {e}")
        print(f"DEBUG: GSheet Sync Error ({filename}): {e}")

def check_gsheet_connection():
    """Verify if GSheet connection is correctly configured and accessible"""
    if not HAS_GSHEETS:
        return False, "streamlit-gsheets 라이브러리가 설치되지 않았습니다."
        
    try:
        if "connections" not in st.secrets or "gsheets" not in st.secrets.connections:
            return False, "Streamlit Secrets에 'connections.gsheets' 설정이 없습니다."
            
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # [DEBUG] Log spreadsheet info to terminal
        try:
            ss_url = st.secrets.connections.gsheets.get("spreadsheet", "N/A")
            # [ROBUST] Extract ID from URL if provided as full link
            if "docs.google.com/spreadsheets/d/" in ss_url:
                ss_id = ss_url.split("/d/")[1].split("/")[0]
                print(f"[GSheet Debug] Extracted ID: {ss_id}")
            print(f"[GSheet Debug] Targeting: {ss_url[:15]}...")
        except:
            pass

        # [NEW] Try to get all worksheet names to verify existence using internal client
        try:
            # streamlit-gsheets stores the internal client in _conn
            if hasattr(conn, "_conn") and hasattr(conn._conn, "spreadsheet"):
                spreadsheet = conn._conn.spreadsheet
                worksheets = spreadsheet.worksheets()
                ws_names = [ws.title for ws in worksheets]
                print(f"[GSheet Debug] Found Worksheets: {ws_names}")
                
                # Check for activity_status
                if "activity_status" in ws_names:
                    # If it exists, try reading specifically
                    df = conn.read(worksheet="activity_status", ttl="0s", nrows=1)
                    return True, f"연결 성공! (워크시트 목록: {', '.join(ws_names)})"
                else:
                    return False, f"연결 실패: 'activity_status' 탭을 찾을 수 없습니다.\n\n현재 탭 목록: `{ws_names}`"
            else:
                # Fallback to standard read if internal access fails
                df = conn.read(worksheet="activity_status", ttl="0s", nrows=1)
                return True, "연결 성공! (데이터 읽기 확인 완료)"
                
        except Exception as read_e:
            error_msg = str(read_e)
            full_error = repr(read_e)
            if "400" in error_msg:
                # Try to get generic info if specific worksheet fails
                try:
                    metadata = conn.read(ttl="0s", nrows=1)
                    return False, f"연결 실패 (HTTP 400): 시트 구조는 보이나 특정 탭 읽기 실패.\n\n**상세 오류**: `{full_error}`"
                except:
                    return False, f"연결 실패 (HTTP 400): 시트 접근 자체가 거부되었습니다.\n\n**상세 오류**: `{full_error}`\n\n**해결법**: 1. 시트 URL이 정확한지 확인. 2. 서비스 계정 권한 확인."
            return False, f"연결 실패: {error_msg}\n\n`{full_error}`"
            
    except Exception as e:
        return False, f"설정 오류: {str(e)}\n\n(참고: 서비스 계정 이메일이 시트에 '편집자'로 공유되었는지 확인하세요.)"


def pull_from_gsheet():
    """Download data from Google Sheets to local storage (Initial Sync)"""
    if not HAS_GSHEETS: return
    
    try:
        if "connections" not in st.secrets or "gsheets" not in st.secrets.connections:
            return
            
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        files_to_sync = {
            "activity_status": ACTIVITY_STATUS_FILE,
            "visit_reports": VISIT_REPORT_FILE,
            "change_history": CHANGE_HISTORY_FILE
        }
        
        for ws_name, local_path in files_to_sync.items():
            try:
                df = conn.read(worksheet=ws_name, ttl="0s")
                if df is not None and not df.empty:
                    # Convert back to JSON structure
                    if ws_name == "activity_status":
                        # Dict by record_key
                        new_data = {}
                        for _, row in df.iterrows():
                            d = row.to_dict()
                            key = d.pop("record_key", None)
                            if key: new_data[key] = d
                    else:
                        # List of dicts
                        new_data = df.to_dict(orient="records")
                    
                    # Save locally
                    save_json_file(local_path, new_data)
                    # print(f"DEBUG: Pulled '{ws_name}' from Google Sheets to {local_path}")
            except Exception as inner_e:
                print(f"DEBUG: Pulled error for {ws_name}: {inner_e}")
                
    except Exception as e:
        print(f"DEBUG: GSheet Pull Error: {e}")
        return False, str(e)

def push_to_gsheet():
    """Manually push all local data to Google Sheets (Full Sync)"""
    if not HAS_GSHEETS: return False, "GSheet 라이브러리 미설치"
    
    try:
        files_to_sync = {
            "activity_status.json": load_json_file(ACTIVITY_STATUS_FILE),
            "visit_reports.json": load_json_file(VISIT_REPORT_FILE),
            "change_history.json": load_json_file(CHANGE_HISTORY_FILE)
        }
        
        success_count = 0
        for filename, data in files_to_sync.items():
            if data:
                # Reuse existing sync_to_gsheet logic
                sync_to_gsheet(filename, data)
                success_count += 1
        
        return True, f"{success_count}개 항목 동기화 완료"
    except Exception as e:
        return False, str(e)


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
    """
    Save activity status for a record (Direct Update).
    Automatically creates a visit report entry if status changes for visibility.
    """
    from src import utils
    status = normalize_status(status)
    
    statuses = load_json_file(ACTIVITY_STATUS_FILE)
    old_data = statuses.get(record_key, {})
    
    ts_str = utils.get_now_kst_str()
    
    new_data = {
        "활동진행상태": status,
        "특이사항": notes,
        "변경일시": ts_str,
        "변경자": user_name
    }
    
    statuses[record_key] = new_data
    save_json_file(ACTIVITY_STATUS_FILE, statuses)
    
    # Log Change if different
    if old_data.get("활동진행상태") != status or old_data.get("특이사항") != notes:
        log_change_history(record_key, old_data, new_data, user_name)
        
        # [NEW] Integration: Create a visit report for visibility in "Activity History"
        # Only if it's not already a "Visit" which is handled by register_visit
        if status != ACTIVITY_STATUS_MAP.get("방문"):
            # Use string ID for consistency
            id_str = ts_str.replace("-", "").replace(" ", "_").replace(":", "").replace("+", "_")
            visit_entry = {
                "id": f"rep_sys_{id_str}_{record_key[:5]}",
                "timestamp": ts_str,
                "record_key": record_key,
                "content": f"[시스템 자동] 활동 상태가 '{status}'(으)로 변경되었습니다. (특이사항: {notes or '-'})",
                "audio_path": None,
                "photo_path": None,
                "user_name": user_name,
                "resulting_status": status
            }
            
            reports = load_json_file(VISIT_REPORT_FILE)
            if not isinstance(reports, list): reports = []
            reports.append(visit_entry)
            save_json_file(VISIT_REPORT_FILE, reports)
            
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
        id_str = ts_str.replace("-", "").replace(" ", "_").replace(":", "").replace("+", "_")
        visit_entry = {
            "id": f"rep_{id_str}_{record_key[:5]}",
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
        
        # B. Status & History
        status_entry = {
            "활동진행상태": new_status,
            "특이사항": content, # Sync notes
            "변경일시": ts_str,
            "변경자": user_info.get("name")
        }
        
        statuses = load_json_file(ACTIVITY_STATUS_FILE)
        old_data = statuses.get(record_key, {})
        statuses[record_key] = status_entry
        save_json_file(ACTIVITY_STATUS_FILE, statuses)
        
        # Log History if changed
        if old_data.get("활동진행상태") != new_status or old_data.get("특이사항") != content:
            log_change_history(record_key, old_data, status_entry, user_info.get("name"))
        
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
