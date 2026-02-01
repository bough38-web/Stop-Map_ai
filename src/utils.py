
import unicodedata

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
        # Remove quotes and massive whitespace
        s = s.replace('"', '').replace("'", "").replace('\n', ' ')
        return s.strip()

    c_title = clean(title)
    c_addr = clean(addr)
    return f"{c_title}_{c_addr}"
