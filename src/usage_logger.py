import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Storage directory
BASE_DIR = Path(os.path.abspath(__file__)).parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)

USAGE_LOG_FILE = STORAGE_DIR / "usage_logs.json"

def load_json_file(filepath):
    """Load JSON file, return empty list if not exists"""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_json_file(filepath, data):
    """Save data to JSON file"""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

# ===== USAGE LOGGING =====

def log_usage(user_role, user_name, user_branch, action, details=None):
    """
    Log user usage activity
    
    Args:
        user_role: 'admin', 'branch', 'manager'
        user_name: User's name
        user_branch: User's branch
        action: Action type (login, logout, search, filter, tab_change, map_view, export, etc.)
        details: Additional details (dict)
    """
    logs = load_json_file(USAGE_LOG_FILE)
    
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_role": user_role,
        "user_name": user_name,
        "user_branch": user_branch,
        "action": action,
        "details": details or {}
    }
    
    logs.append(log_entry)
    
    # Keep only last 10000 entries
    if len(logs) > 10000:
        logs = logs[-10000:]
    
    save_json_file(USAGE_LOG_FILE, logs)

def get_usage_logs(days=30, user_name=None, user_branch=None, action=None):
    """
    Get usage logs with filters
    
    Args:
        days: Number of days to look back
        user_name: Filter by user name
        user_branch: Filter by branch
        action: Filter by action type
    """
    logs = load_json_file(USAGE_LOG_FILE)
    
    if not logs:
        return []
    
    # Convert to DataFrame for easier filtering
    df = pd.DataFrame(logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter by date
    cutoff_date = datetime.now() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date]
    
    # Apply filters
    if user_name:
        df = df[df['user_name'] == user_name]
    if user_branch:
        df = df[df['user_branch'] == user_branch]
    if action:
        df = df[df['action'] == action]
    
    return df.to_dict('records')

def get_usage_stats(days=30):
    """
    Get usage statistics for admin dashboard
    
    Returns:
        dict with various statistics
    """
    logs = load_json_file(USAGE_LOG_FILE)
    
    if not logs:
        return {
            "total_actions": 0,
            "unique_users": 0,
            "actions_by_type": {},
            "actions_by_user": {},
            "actions_by_branch": {},
            "daily_activity": {},
            "hourly_activity": {}
        }
    
    df = pd.DataFrame(logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter by date
    cutoff_date = datetime.now() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date]
    
    # Calculate statistics
    stats = {
        "total_actions": len(df),
        "unique_users": df['user_name'].nunique(),
        "unique_branches": df['user_branch'].nunique(),
        
        # Actions by type
        "actions_by_type": df['action'].value_counts().to_dict(),
        
        # Actions by user (top 20)
        "actions_by_user": df['user_name'].value_counts().head(20).to_dict(),
        
        # Actions by branch
        "actions_by_branch": df['user_branch'].value_counts().to_dict(),
        
        # Daily activity (last 30 days)
        "daily_activity": df.groupby(df['timestamp'].dt.date).size().to_dict(),
        
        # Hourly activity (0-23)
        "hourly_activity": df.groupby(df['timestamp'].dt.hour).size().to_dict(),
        
        # Most active users (with details)
        "top_users": df.groupby(['user_name', 'user_branch', 'user_role']).size().reset_index(name='count').sort_values('count', ascending=False).head(10).to_dict('records')
    }
    
    # Convert date keys to strings for JSON serialization
    stats['daily_activity'] = {str(k): v for k, v in stats['daily_activity'].items()}
    
    return stats

def get_user_activity_timeline(user_name, days=7):
    """
    Get detailed activity timeline for a specific user
    """
    logs = load_json_file(USAGE_LOG_FILE)
    
    if not logs:
        return []
    
    df = pd.DataFrame(logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter by user and date
    cutoff_date = datetime.now() - timedelta(days=days)
    df = df[(df['user_name'] == user_name) & (df['timestamp'] >= cutoff_date)]
    
    # Sort by timestamp descending
    df = df.sort_values('timestamp', ascending=False)
    
    return df.to_dict('records')

def log_navigation(user_role, user_name, user_branch, business_name, address, lat, lon):
    """
    Log navigation/route request to a specific business
    
    Args:
        user_role: User's role
        user_name: User's name
        user_branch: User's branch
        business_name: Target business name
        address: Business address
        lat: Latitude
        lon: Longitude
    """
    log_usage(user_role, user_name, user_branch, 'navigation', {
        'business_name': business_name,
        'address': address,
        'lat': lat,
        'lon': lon
    })

def get_navigation_history(days=30, user_name=None, user_branch=None):
    """
    Get navigation history with business details
    
    Returns list of navigation events with:
    - timestamp
    - user info
    - business name
    - address
    - coordinates
    """
    logs = load_json_file(USAGE_LOG_FILE)
    
    if not logs:
        return []
    
    # Filter for navigation actions only
    nav_logs = [log for log in logs if log.get('action') == 'navigation']
    
    if not nav_logs:
        return []
    
    df = pd.DataFrame(nav_logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter by date
    cutoff_date = datetime.now() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date]
    
    # Apply filters
    if user_name:
        df = df[df['user_name'] == user_name]
    if user_branch:
        df = df[df['user_branch'] == user_branch]
    
    # Extract business details from details column
    result = []
    for _, row in df.iterrows():
        details = row.get('details', {})
        result.append({
            'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'user_name': row['user_name'],
            'user_branch': row['user_branch'],
            'business_name': details.get('business_name', ''),
            'address': details.get('address', ''),
            'lat': details.get('lat', 0),
            'lon': details.get('lon', 0)
        })
    
    return result

def get_navigation_stats(days=30):
    """
    Get navigation statistics for visualization
    
    Returns:
        dict with navigation-specific statistics
    """
    nav_history = get_navigation_history(days=days)
    
    if not nav_history:
        return {
            'total_navigations': 0,
            'unique_users': 0,
            'unique_businesses': 0,
            'navigations_by_user': {},
            'navigations_by_branch': {},
            'top_businesses': []
        }
    
    df = pd.DataFrame(nav_history)
    
    stats = {
        'total_navigations': len(df),
        'unique_users': df['user_name'].nunique(),
        'unique_businesses': df['business_name'].nunique(),
        
        # Navigations by user
        'navigations_by_user': df['user_name'].value_counts().to_dict(),
        
        # Navigations by branch
        'navigations_by_branch': df['user_branch'].value_counts().to_dict(),
        
        # Top visited businesses
        'top_businesses': df['business_name'].value_counts().head(20).to_dict(),
        
        # Daily navigation trend
        'daily_navigations': df.groupby(pd.to_datetime(df['timestamp']).dt.date).size().to_dict()
    }
    
    # Convert date keys to strings
    stats['daily_navigations'] = {str(k): v for k, v in stats['daily_navigations'].items()}
    
    return stats

def log_interest(user_role, user_name, user_branch, business_name, address, road_address, lat, lon):
    """
    Log when a user marks a business as interesting
    
    Args:
        user_role: User's role
        user_name: User's name
        user_branch: User's branch
        business_name: Business name
        address: Full address
        road_address: Road address
        lat: Latitude
        lon: Longitude
    """
    log_usage(user_role, user_name, user_branch, 'interest', {
        'business_name': business_name,
        'address': address,
        'road_address': road_address,
        'lat': lat,
        'lon': lon
    })

def get_interest_history(days=30, user_name=None, user_branch=None):
    """
    Get interest marking history with business details
    
    Returns list of interest events with:
    - timestamp
    - user info
    - business name
    - address
    - coordinates
    """
    logs = load_json_file(USAGE_LOG_FILE)
    
    if not logs:
        return []
    
    # Filter for interest actions only
    interest_logs = [log for log in logs if log.get('action') == 'interest']
    
    if not interest_logs:
        return []
    
    df = pd.DataFrame(interest_logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter by date
    cutoff_date = datetime.now() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date]
    
    # Apply filters
    if user_name:
        df = df[df['user_name'] == user_name]
    if user_branch:
        df = df[df['user_branch'] == user_branch]
    
    # Extract business details from details column
    result = []
    for _, row in df.iterrows():
        details = row.get('details', {})
        result.append({
            'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'user_name': row['user_name'],
            'user_branch': row['user_branch'],
            'business_name': details.get('business_name', ''),
            'address': details.get('address', ''),
            'road_address': details.get('road_address', ''),
            'lat': details.get('lat', 0),
            'lon': details.get('lon', 0)
        })
    
    return result

def get_interest_stats(days=30):
    """
    Get interest statistics for visualization
    
    Returns:
        dict with interest-specific statistics
    """
    interest_history = get_interest_history(days=days)
    
    if not interest_history:
        return {
            'total_interests': 0,
            'unique_users': 0,
            'unique_businesses': 0,
            'interests_by_user': {},
            'interests_by_branch': {},
            'top_businesses': [],
            'daily_interests': {}
        }
    
    df = pd.DataFrame(interest_history)
    
    stats = {
        'total_interests': len(df),
        'unique_users': df['user_name'].nunique(),
        'unique_businesses': df['business_name'].nunique(),
        
        # Interests by user
        'interests_by_user': df['user_name'].value_counts().to_dict(),
        
        # Interests by branch
        'interests_by_branch': df['user_branch'].value_counts().to_dict(),
        
        # Top interested businesses
        'top_businesses': df['business_name'].value_counts().head(20).to_dict(),
        
        # Daily interest trend
        'daily_interests': df.groupby(pd.to_datetime(df['timestamp']).dt.date).size().to_dict()
    }
    
    # Convert date keys to strings
    stats['daily_interests'] = {str(k): v for k, v in stats['daily_interests'].items()}
    
    return stats
