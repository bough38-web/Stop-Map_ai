import pandas as pd
import re
import unicodedata
import os
import json
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher

# Check for rapidfuzz for better performance, fallback to difflib
try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

# Coordinate Conversion
try:
    from pyproj import Transformer
    # EPSG:5174 (Modified Bessel Middle) to EPSG:4326 (WGS84 Lat/Lon)
    transformer = Transformer.from_crs("epsg:5174", "epsg:4326", always_xy=True)
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False
    transformer = None

def normalize_address(address):
    """
    Normalizes a Korean address string.
    Removes special characters, standardizes region names.
    """
    if pd.isna(address):
        return None
    
    address = str(address).strip()
    
    # Remove everything in brackets (e.g., (Apt 101), (Bldg B))
    address = re.sub(r'\([^)]*\)', '', address)
    
    # Standardize
    address = address.replace('강원특별자치도', '강원도')
    address = address.replace('세종특별자치시', '세종시')
    address = address.replace('서울특별시', '서울시')
    address = address.replace('  ', ' ') # Double spaces
    address = address.replace('-', '')
    
    if '*' in address or len(address) < 8:  # Too short or masked
        return None
        
    return address.strip()

def parse_coordinates_row(row, x_col, y_col):
    """
    Helper to parse and convert coordinates.
    """
    try:
        if not x_col or not y_col:
            return None, None
            
        x_val = row.get(x_col)
        y_val = row.get(y_col)
        
        if pd.isna(x_val) or pd.isna(y_val):
            return None, None
            
        x = float(x_val)
        y = float(y_val)
        
        # Heuristic: If values are small (lat/lon like), return as is
        if 120 < x < 140 and 30 < y < 45:
            return y, x # Lat, Lon
            
        # Conversion
        if HAS_PYPROJ:
            lon, lat = transformer.transform(x, y)
            # Sanity check for Korea
            if 30 < lat < 45 and 120 < lon < 140:
                return lat, lon
                
    except:
        return None, None
    return None, None

def get_best_match(address, choices, vectorizer, tfidf_matrix, threshold=0.7):
    """
    Finds the best matching address from a list of choices using TF-IDF and Levenshtein/RapidFuzz.
    """
    if pd.isna(address):
        return None

    # 1. TF-IDF Cosine Similarity (Fast Filter)
    try:
        # Use only first element if it's a list/series
        if isinstance(address, pd.Series): address = address.iloc[0]
            
        tfidf_vec = vectorizer.transform([str(address)])
        cosine_sim = cosine_similarity(tfidf_vec, tfidf_matrix).flatten()
        # Get top candidate
        best_idx = cosine_sim.argmax()
        best_cosine_score = cosine_sim[best_idx]
        
        # [FIX] Add Similarity Threshold to prevent incorrect matches
        # e.g. "Busan" matching "Gangneung" because both have "dong"
        # Threshold 0.4 seems reasonable for address matching
        if best_cosine_score < 0.4:
            return None
            
    except Exception:
        best_cosine_score = 0
        best_idx = -1

    # Optimization: If cosine score is very high, trust it.
    if best_cosine_score >= 0.85:
        return choices[best_idx]

    # 2. Refine with Edit Distance
    # Only check top N candidates from TF-IDF
    top_n = 5
    top_indices = cosine_sim.argsort()[-top_n:][::-1]
    
    best_score = 0
    best_match = None
    
    for idx in top_indices:
        choice = choices[idx]
        
        if HAS_RAPIDFUZZ:
            # RapidFuzz: 0-100 scale, normalize to 0-1
            score = fuzz.ratio(str(address), str(choice)) / 100.0
        else:
            # Difflib: 0-1 scale
            score = SequenceMatcher(None, str(address), str(choice)).ratio()
            
        if score > best_score:
            best_score = score
            best_match = choice
            
    # Combine signals: Max of cosine and edit distance logic
    # Actually, edit distance is usually better for small typos.
    final_score = max(best_score, best_cosine_score)
    
    if final_score >= threshold:
        return best_match
    
    return None

def calculate_area(row):
    val = row.get('소재지면적', 0)
    if pd.isna(val) or val == 0: val = row.get('총면적', 0)
    try:
        return round(float(val) / 3.3058, 1)
    except:
        return 0

# --- System Configuration ---
DATA_DIR = "data"
CONFIG_FILE = os.path.join(DATA_DIR, "system_config.json")

def load_system_config():
    """Load system configuration (notices, data dates)"""
    default_config = {
        "notice_title": "",
        "notice_content": "",
        "show_notice": False,
        "data_standard_date": ""
    }
    if not os.path.exists(CONFIG_FILE):
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config

def save_system_config(config):
    """Save system configuration"""
    try:
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

import base64
def embed_local_images(html_content, base_path=""):
    """
    Replace local image src with base64 embedded data.
    Assumes images are in 'assets/'.
    """
    def replace_match(match):
        src = match.group(1)
        # Check if local file
        if not src.startswith("http") and not src.startswith("data:"):
            # Construct full path
            # If src is 'assets/img.png', and base_path is project root, it should work.
            full_path = src
            if base_path:
                full_path = os.path.join(base_path, src)
            
            if os.path.exists(full_path):
                try:
                    ext = full_path.split('.')[-1].lower()
                    mime_type = f"image/{ext}"
                    if ext == 'jpg': mime_type = "image/jpeg"
                    if ext == 'svg': mime_type = "image/svg+xml"
                    
                    with open(full_path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode()
                        return f'src="data:{mime_type};base64,{encoded}"'
                except Exception as e:
                    print(f"Error checking image {full_path}: {e}")
                    pass
        return match.group(0) # No change

    # Regex to find src="..."
    # We look for src="([^"]+)"
    pattern = r'src="([^"]+)"'
    return re.sub(pattern, replace_match, html_content)

def generate_record_key(title, addr):
    """
    Generate a normalized, consistent record key from Title and Address.
    This function MUST be used by both the frontend (app.py) and backend (activity_logger.py)
    to ensure data consistency.
    """
    def clean(s):
        if s is None: return ""
        s = str(s)
        if s.lower() == 'nan': return ""
        # Normalize unicode (e.g. separate jamo)
        s = unicodedata.normalize('NFC', s)
        # Remove quotes and ALL whitespace for robustness
        # This fixes issues where "City A" != "CityA"
        s = s.replace('"', '').replace("'", "").replace('\n', '').replace(' ', '')
        return s.strip()

    c_title = clean(title)
    c_addr = clean(addr)
    return f"{c_title}_{c_addr}"
