import streamlit as st
import pandas as pd
import pandas as pd
import altair as alt
import os
import glob
import unicodedata
import streamlit.components.v1 as components
from datetime import datetime

# Import modularized components
from src import utils
from src.utils import load_system_config, save_system_config, embed_local_images
from src import data_loader
from src import map_visualizer
from src import report_generator
from src import activity_logger  # Activity logging and status tracking
from src import usage_logger  # Usage tracking for admin monitoring
from src import voc_manager  # VOC / Request Manager
from src.ai_scoring import calculate_ai_scores # [NEW] Expert Feat 1: AI Scoring

# --- Configuration & Theme ---
st.set_page_config(
    page_title="영업기회 관리 시스템",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [DESIGN] Inject Custom CSS for Modern UI
def inject_custom_css():
    st.markdown("""
    <style>
        /* Modern Dashboard Card */
        div[data-testid="stExpander"] details {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        .dashboard-card {
            background-color: white;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid #f0f0f0;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            margin-bottom: 10px;
            text-align: center; /* [FIX] Center Alignment */
        }
        .dashboard-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        }
        
        .card-header {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1a237e; /* Deep Blue */
            margin-bottom: 8px;
            display: flex;
            flex-direction: column; /* [FIX] Vertical Stack for Centering */
            justify-content: center;
            align-items: center;
        }
        
        .stat-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: #333;
            margin: 4px 0;
        }
        
        .stat-sub {
            font-size: 0.85rem;
            color: #666;
            display: flex;
            gap: 8px;
            justify-content: center; /* [FIX] Center Alignment */
        }
        
        .status-dot {
            height: 8px;
            width: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 4px;
        }
        .dot-green { background-color: #4CAF50; }
        .dot-red { background-color: #F44336; }
        .dot-gray { background-color: #9E9E9E; }
        
        /* Button Tweaks */
        .stButton button {
            border-radius: 6px;
            font-weight: 600;
            transition: all 0.2s;
        }
        .stButton button:hover {
            transform: translateY(-1px);
        }
        
        /* Active Branch Highlight */
        .branch-active {
            border: 2px solid #3F51B5 !important;
            background-color: #E8EAF6 !important;
        }
        
        /* [FIX] Feature Box Vertical Centering */
        .feature-box-centered {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 50px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 8px;
            background-color: white;
            color: #31333F;
            font-weight: 800;
            font-size: 0.85rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        /* Mobile Grid Card Styles */
        .card-tile {
            background-color: white;
            border: 1px solid #eee;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .card-tile:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-color: #3F51B5;
        }
        .card-title-grid {
            font-weight: 800;
            font-size: 0.95rem;
            color: #222;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-meta-grid {
            font-size: 0.75rem;
            color: #666;
            line-height: 1.4;
            margin-bottom: 5px;
        }
        .status-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            color: white;
            margin-bottom: 4px;
        }
        .status-open { background-color: #4CAF50; }
        .status-closed { background-color: #F44336; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# [SYSTEM] Master Reset Handler (Factory Reset for Session/Cache)
if "reset" in st.query_params:
    st.cache_data.clear()
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

# [FEATURE] Handle URL Actions (e.g. Visit from Map) & Session Persistence
# [FEATURE] Handle URL Actions (e.g. Visit from Map) & Session Persistence
# Refactored to use Session State for persistent Modal/Form behavior

# 1. Trigger from URL
if "visit_action" in st.query_params:
    try:
        q_title = st.query_params.get("title", "")
        q_addr = st.query_params.get("addr", "")
        
        # [FIX] Unicode Normalization (NFC) for consistency
        if q_title: q_title = unicodedata.normalize('NFC', q_title)
        if q_addr: q_addr = unicodedata.normalize('NFC', q_addr)
        
        # [FIX] Session Restoration from URL
        p_role = st.query_params.get("user_role", None)
        
        if p_role:
             if "user_role" not in st.session_state: st.session_state.user_role = p_role
             if "user_branch" in st.query_params: st.session_state.user_branch = st.query_params["user_branch"]
             if "user_manager_name" in st.query_params: st.session_state.user_manager_name = st.query_params["user_manager_name"]
             if "user_manager_code" in st.query_params: st.session_state.user_manager_code = st.query_params["user_manager_code"]
             
             # Admin Auth
             if "admin_auth" in st.query_params:
                 val = st.query_params["admin_auth"]
                 st.session_state.admin_auth = (str(val).lower() == 'true')

        if q_title:
            # Initialize Session State for Visit Form
            st.session_state.visit_active = True
            
            # [OVERHAUL] Use Explicit Key if available
            q_key = st.query_params.get("key", "")
            
            st.session_state.visit_data = {
                'title': q_title,
                'addr': q_addr,
                'key': q_key, # [NEW] Store explicit key
                'user': st.session_state.get('user_manager_name') or st.session_state.get('user_branch') or "Field Agent"
            }
            
            # [NEW] Immediate Status Update for "Visit Processing"
            # User Request: "방문처리 선택하면 지도상에 방문처리 마커 표시"
            # We should update the status to '방문' immediately when clicked on map.
            if q_key:
                u_name = st.session_state.get('user_manager_name') or st.session_state.get('user_branch') or "Unknown"
                activity_logger.save_activity_status(q_key, '방문', f"모바일 지도에서 방문 처리 ({u_name})", u_name)
                # Also log a system visit report? User said "방문 이력에 나오도록"
                activity_logger.save_visit_report(
                    record_key=q_key,
                    user_name=u_name,
                    user_branch=st.session_state.get('user_branch'),
                    content=f"[시스템] 모바일 지도에서 '방문' 상태로 변경했습니다.",
                    photo_path=None,
                    audio_path=None
                )
                st.toast(f"✅ {q_title} : 등록되었습니다.")
            
            # Clear params to prevent sticky state loop
            # This ensures subsequent interactions don't re-trigger this block
            st.query_params.clear()
            st.rerun()

    except Exception as e:
        st.error(f"Error processing visit action: {e}")
        st.query_params.clear() # Safety clear on error

# [NEW] Interest Action Handler
if "interest_action" in st.query_params:
    try:
        i_title = st.query_params.get("title", "")
        i_addr = st.query_params.get("addr", "")
        i_lat = st.query_params.get("lat", 0)
        i_lon = st.query_params.get("lon", 0)
        
        # Normalize
        if i_title: i_title = unicodedata.normalize('NFC', i_title)
        if i_addr: i_addr = unicodedata.normalize('NFC', i_addr)
        
        # Restore Session
        p_role = st.query_params.get("user_role", None)
        if p_role:
                if "user_role" not in st.session_state: st.session_state.user_role = p_role
                if "user_branch" in st.query_params: st.session_state.user_branch = st.query_params["user_branch"]
                if "user_manager_name" in st.query_params: st.session_state.user_manager_name = st.query_params["user_manager_name"]
                if "user_manager_code" in st.query_params: st.session_state.user_manager_code = st.query_params["user_manager_code"]

        # Log Interest
        usage_logger.log_interest(
            st.session_state.get('user_role'),
            st.session_state.get('user_manager_name') or st.session_state.get('user_branch') or "Unknown",
            st.session_state.get('user_branch'),
            i_title, i_addr, i_lat, i_lon
        )
        
        # [NEW] Also log to Visit History as "Interest Marked"
        # Use a specific status or just a log? User said "appear in visit history".
        # We'll create a system-generated visit report.
        u_name = st.session_state.get('user_manager_name') or st.session_state.get('user_branch') or "Unknown"
        if i_title and i_addr:
            # Generate key
            from src import utils
            row_key = utils.generate_record_key(i_title, i_addr)
            
            # 1. Update Status to 'Interest' (Optional, or just log?)
            # User said "Interest button selection -> Visit History".
            # Let's save it as a "관심" status update too?
            # "Interest" isn't in standard activity statuses usually (Open/Closed/Consulting...).
            # But we can add a report.
            activity_logger.save_visit_report(
                record_key=row_key,
                user_name=u_name,
                user_branch=st.session_state.get('user_branch'),
                content=f"[시스템] 모바일 지도에서 '관심 업체'로 등록했습니다.",
                photo_path=None,
                audio_path=None
            )
            
            st.toast(f"⭐ {i_title} : 등록되었습니다.")
            
        # Clean URL
        st.query_params.clear()
        # [FIX] Added Rerun to clear URL from browser bar immediately
        st.rerun()
    except Exception as e:
        st.error(f"Error processing interest: {e}")
        st.query_params.clear()



# 2. Render Form based on Session State
if st.session_state.get("visit_active"):
    v_data = st.session_state.visit_data
    q_title = v_data.get('title')
    q_addr = v_data.get('addr')
    q_key_explicit = v_data.get('key') # [NEW]
    visit_user = v_data.get('user')
    
    # Generate Key
    # [OVERHAUL] Priority: Explicit Key > Generated Key
    if q_key_explicit and str(q_key_explicit).strip():
        record_key = str(q_key_explicit).strip()
    else:
        # Fallback to generator
        record_key = utils.generate_record_key(q_title, q_addr)
    
    # [FEATURE] Visit Report Form (Persistent)
    with st.expander(f"📝 '{q_title}' 방문 결과 입력", expanded=True):
        st.info("방문 결과를 기록하세요. 기록 후 [저장] 버튼을 눌러주세요.")
        st.caption(f"🔧 Debug Info - Key: {record_key} | User: {visit_user}")
        
        # Add a Close button outside the form to cancel
        if st.button("닫기 (기록 취소)"):
            st.session_state.visit_active = False
            # [FIX] Clear params on explicit close
            st.query_params.clear()
            st.rerun()

        with st.form("visit_report_form"):
            rep_content = st.text_area("상세 내용 (필수)", height=100, placeholder="면담 내용, 고객 반응, 특이사항 등을 입력하세요.")
            
            c_audio, c_photo = st.columns(2)
            with c_audio:
                st.markdown("**🎤 음성 녹음**")
                try:
                    audio_val = st.audio_input("음성 녹음")
                except AttributeError:
                    st.caption("음성 녹음 미지원 (file_uploader 사용)")
                    audio_val = st.file_uploader("음성 파일 업로드", type=['wav', 'mp3', 'm4a'], label_visibility="collapsed")
                
            with c_photo:
                st.markdown("**📸 현장 사진**")
                # Camera input or Uploader
                try:
                    photo_val = st.camera_input("사진 촬영", label_visibility="collapsed")
                except AttributeError:
                    photo_val = None
                    
                if not photo_val:
                    photo_val = st.file_uploader("또는 사진 업로드", type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")

            submitted = st.form_submit_button("💾 방문 결과 저장", type="primary", use_container_width=True)
            
            if submitted:
                st.error(f"DEBUG: Submit Button Clicked! Key={record_key}") # Persistent
                if not rep_content:
                    st.error("내용을 입력해주세요.")
                else:
                    # User Info
                    u_info = {
                        "name": visit_user,
                        "role": st.session_state.get('user_role', 'unknown'),
                        "branch": st.session_state.get('user_branch', '')
                    }
                    
                    # Save Logic
                    try:
                        # [REDESIGN] Atomic Visit Registration
                        # [FIX] Add forced_status to ensure grid displays the visit
                        success, msg = activity_logger.register_visit(
                            record_key, 
                            rep_content, 
                            audio_val, 
                            photo_val, 
                            u_info,
                            forced_status="✅ 방문"  # Ensure status is saved to activity_status.json
                        )
                        
                        if success:
                            st.success("방문 결과가 저장되었습니다!")
                            
                            # [FIX] Force Data Reload for Grid
                            st.cache_data.clear()
                            
                            st.session_state.visit_active = False # Close form on success
                            st.toast(f"저장 완료! (User: {visit_user})", icon="💾")
                            
                            # [FIX] Clear params on success
                            st.query_params.clear()
                            
                            # Rerun to reflect changes
                            import time
                            time.sleep(0.3)
                            st.rerun()
                        else:
                            st.error(f"저장 중 오류가 발생했습니다: {msg}")
                    except Exception as e:
                        st.error(f"Error saving: {e}")
            


# [FIX] Force Streamlit Native Theme for Altair (High Contrast)
try:
    alt.themes.enable('streamlit')
except:
    pass # fallback

# [REMOVED] Premium CSS block removed to restore classic design

# Predefined Password Maps
BRANCH_PASSWORDS = {
    '중앙지사': 'central123',
    '강북지사': 'gangbuk456',
    '서대문지사': 'seodae789',
    '고양지사': 'goyang234',
    '의정부지사': 'uijeong567',
    '남양주지사': 'namyang890',
    '강릉지사': 'gangneung345',
    '원주지사': 'wonju678',
    '데모지사': 'demo2026'  # Demo account for recruiters
}

# For managers, use a simple pattern: first 3 chars of name + 1234
# Example: 김철수 -> kim1234, 이영희 -> lee1234
def get_manager_password(manager_name):
    """
    Generate simple password for manager.
    Uses first 3 characters (in lowercase romanization approximation) + 1234
    """
    # Simple Korean to English first syllable mapping
    first_syllable_map = {
        '김': 'kim', '이': 'lee', '박': 'park', '최': 'choi', '정': 'jung',
        '강': 'kang', '조': 'jo', '윤': 'yoon', '장': 'jang', '임': 'lim',
        '한': 'han', '오': 'oh', '서': 'seo', '신': 'shin', '권': 'kwon',
        '황': 'hwang', '안': 'ahn', '송': 'song', '류': 'ryu', '홍': 'hong',
        '전': 'jeon', '고': 'go', '문': 'moon', '양': 'yang', '손': 'son',
        '배': 'bae', '백': 'baek', '허': 'heo', '남': 'nam', '심': 'shim'
    }
    
    if manager_name and len(manager_name) > 0:
        first_char = manager_name[0]
        prefix = first_syllable_map.get(first_char, 'user')
        return f"{prefix}1234"
    return "user1234"

def inject_button_color_script():
    js = """
    <script>
        function applyStatusColors() {
            try {
                const buttons = window.parent.document.querySelectorAll('button');
                buttons.forEach(btn => {
                    const txt = btn.innerText.trim(); // [FIX] Trim whitespace
                    if (txt === '영업') {
                        btn.style.backgroundColor = '#AED581 !important';
                        btn.style.color = '#1B5E20 !important';
                        btn.style.borderColor = '#AED581 !important';
                    } else if (txt === '폐업') {
                        btn.style.backgroundColor = '#EF9A9A !important';
                        btn.style.color = '#B71C1C !important';
                        btn.style.borderColor = '#EF9A9A !important';
                    }
                });
            } catch(e) {}
        }
        
        // Initial Apply
        applyStatusColors();
        
        // Use a global variable on parent to track observer and prevent duplicates
        if (window.parent.statusButtonObserver) {
            window.parent.statusButtonObserver.disconnect();
        }
        
        window.parent.statusButtonObserver = new MutationObserver(() => {
            applyStatusColors();
        });
        
        window.parent.statusButtonObserver.observe(window.parent.document.body, { childList: true, subtree: true });
    </script>
    """
    components.html(js, height=0, width=0)

def mask_name(name):
    """
    Masks Korean names: 홍길동 -> 홍**, 이철 -> 이*
    """
    if not name or pd.isna(name):
        return name
    name_str = str(name)
    if len(name_str) <= 1:
        return name_str
    if len(name_str) == 2:
        return name_str[0] + "*"
    return name_str[0] + "*" * (len(name_str) - 2) + name_str[-1]

# State Update Callbacks
# State Update Callbacks
def update_branch_state(name):
    # [FIX] Force NFC to match selectbox options strictly
    normalized_name = unicodedata.normalize('NFC', name)
    st.session_state.sb_branch = normalized_name
    st.session_state.sb_manager = "전체"
    st.session_state.dash_branch = normalized_name
    st.session_state.page = 0 # [FIX] Reset page
    st.query_params.clear() # [FIX] Clear params
    
def update_manager_state(name):
    st.session_state.sb_manager = name
    st.session_state.page = 0 # [FIX] Reset page
    st.query_params.clear() # [FIX] Clear params

def update_branch_with_status(name, status):
    st.session_state.sb_branch = name
    st.session_state.sb_manager = "전체"
    st.session_state.dash_branch = name
    st.session_state.sb_status = status
    st.session_state.page = 0 # [FIX] Reset page
    st.query_params.clear() # [FIX] Clear params
    
def update_manager_with_status(name, status):
    st.session_state.sb_manager = name
    st.session_state.sb_status = status
    st.session_state.page = 0 # [FIX] Reset page
    st.query_params.clear() # [FIX] Clear params

# --- Sidebar Filters ---
with st.sidebar:
    # [FAILSAFE] Emergency Logout & Debug (Render First - Guaranteed Visibility)
    if st.session_state.get('user_role'):
         st.markdown(f"**🟢 [System] {st.session_state.get('user_role')} 접속중**")
         if st.button("🚨 로그아웃 (Emergency)", key="btn_logout_emergency", type="primary", use_container_width=True):
             st.session_state.clear()
             st.rerun()
         st.divider()
    
    # [UX] Filter Location Guide
    st.info("📊 **필터는 사이드바 아래쪽에 있습니다**")
    st.caption("👇 스크롤을 내려서 지사, 담당자, 업태 등을 선택하세요")
    with st.expander("💡 빠른 이동 팁", expanded=False):
        st.markdown("""
        - 사이드바를 **아래로 스크롤**하여 **🔍 조회 조건 설정** 섹션을 찾으세요
        - 데이터 로드 후 필터가 활성화됩니다
        - 필터를 사용하여 지사, 담당자, 업태, 영업상태 등을 선택할 수 있습니다
        """)
    
    st.markdown("---")

    st.header("⚙️ 설정 & 데이터")
    
    # [FEATURE] Placeholder for Admin Global Chart (Populated after data load)
    admin_chart_placeholder = st.sidebar.empty()
    
    st.sidebar.markdown("---")

    with st.sidebar.expander("📂 데이터 소스 및 API 설정", expanded=False):
        st.subheader("데이터 소스 선택")
        
        data_source = st.radio(
            "데이터 출처", 
            ["파일 업로드 (File)", "OpenAPI 연동 (Auto)"],
            index=0
        )
        
        # [FIX] Enhanced File Selection with 20260119 Priority
        local_zips = sorted(glob.glob(os.path.join("data", "*.zip")), key=os.path.getmtime, reverse=True)
        local_excels = sorted(glob.glob(os.path.join("data", "*.xlsx")), key=os.path.getmtime, reverse=True)
        
        # Force Priority for 20260119
        priority_file_match = [f for f in local_excels if '20260119' in f]
        if priority_file_match:
            # Move to front
            for p in priority_file_match:
                if p in local_excels: local_excels.remove(p)
            local_excels = priority_file_match + local_excels
            
        uploaded_dist = None
        use_local_dist = False

        if local_excels:
            use_local_dist = st.toggle("영업구역(Excel) 자동 로드", value=True)
            if use_local_dist:
                # Let user choose if multiple
                file_opts = [os.path.basename(f) for f in local_excels]
                sel_file_idx = 0
                
                # Try to default to the 20260119 one if present in opts
                for i, fname in enumerate(file_opts):
                    if '20260119' in fname:
                        sel_file_idx = i
                        break
                        
                sel_file = st.selectbox("사용할 영업구역 파일", file_opts, index=sel_file_idx)
                uploaded_dist = os.path.join("data", sel_file)
                
                if '20260119' in sel_file:
                     st.success(f"✅ **[최신]** 로드된 파일: {sel_file}")
                else:
                     st.warning(f"⚠️ 로드된 파일: {sel_file} (20260119 파일 권장)")
        
        if not use_local_dist:
            uploaded_dist = st.file_uploader("영업구역 데이터 (Excel)", type="xlsx", key="dist_uploader")

        uploaded_zip = []
        
        if data_source == "파일 업로드 (File)":
             if local_zips:
                 use_local_zip = st.toggle("인허가(Zip) 자동 로드", value=True)
                 if use_local_zip:
                     # Let user choose zip if multiple
                     zip_opts = [os.path.basename(f) for f in local_zips]
                     # [FIX] Allow multiple selection to mix data
                     sel_zips = st.multiselect("사용할 인허가 파일 (ZIP)", zip_opts, default=zip_opts)
                     uploaded_zip = [os.path.join("data", z) for z in sel_zips]
                     if sel_zips:
                         st.caption(f"선택됨: {', '.join(sel_zips)}")
                 else:
                     uploaded_zip = st.file_uploader("인허가 데이터 (ZIP)", type="zip", accept_multiple_files=True)
             else:
                  uploaded_zip = st.file_uploader("인허가 데이터 (ZIP)", type="zip", accept_multiple_files=True)
                 
        else: # OpenAPI
            st.info("🌐 지방행정 인허가 데이터 (LocalData)")
            
            default_auth_key = ""
            key_file_path = os.path.join(os.path.dirname(__file__), "오픈API", "api_key.txt")
            if os.path.exists(key_file_path):
                 try:
                     with open(key_file_path, "r", encoding="utf-8") as f:
                         default_auth_key = f.read().strip()
                 except: pass
                     
            api_auth_key = st.text_input("인증키 (AuthKey)", value=default_auth_key, type="password", help="공공데이터포털(data.go.kr)에서 발급받은 인증키")
            api_local_code = st.text_input("지역코드 (LocalCode)", value="3220000", help="예: 3220000 (강남구)")
            
            c_d1, c_d2 = st.columns(2)
            today = datetime.date.today()
            api_start_date = c_d1.date_input("시작일", value=today - datetime.timedelta(days=30))
            api_end_date = c_d2.date_input("종료일", value=today)
            
            fetch_btn = st.button("데이터 가져오기 (Fetch)")
            
            if fetch_btn and api_auth_key:
                with st.spinner("🌐 API 데이터 조회 중..."):
                    s_date = api_start_date.strftime("%Y%m%d")
                    e_date = api_end_date.strftime("%Y%m%d")
                    api_df, api_error = data_loader.fetch_openapi_data(api_auth_key, api_local_code, s_date, e_date)
                    
                    if api_error:
                        st.error(f"실패: {api_error}")
                    else:
                        st.success(f"성공! {len(api_df)}개 데이터 수신 완료")
                        st.session_state['api_fetched_df'] = api_df
            
            if 'api_fetched_df' in st.session_state:
                api_df = st.session_state['api_fetched_df']
                st.caption(f"✅ 수신된 데이터: {len(api_df)}건")




    with st.sidebar.expander("🎨 테마 설정", expanded=False):
        theme_mode = st.selectbox(
            "스타일 테마 선택", 
            ["기본 (Default)", "모던 다크 (Modern Dark)", "웜 페이퍼 (Warm Paper)", "고대비 (High Contrast)", "코퍼레이트 블루 (Corporate Blue)", "그린 에코 (Green Eco)"],
            index=0,
            label_visibility="collapsed"
        )
    
    # [FEATURE] Admin Mobile Filter Visibility Control
    # Only visible to Admin. Controls visibility of "Conditional Search" on mobile.
    if st.session_state.get('user_role') == 'admin':
        st.sidebar.divider()
        show_mobile_filter = st.sidebar.toggle("📱 모바일에서 필터 표시", value=True, help="끄면 모바일 화면에서 '조건조회' 창이 사라집니다.")
        if not show_mobile_filter:
            st.markdown("""
            <style>
            @media (max-width: 768px) {
                /* Try multiple selectors for robustness */
                div[data-testid="stExpander"]:has(#mobile-filter-marker),
                details:has(#mobile-filter-marker) {
                    display: none !important;
                }
            }
            </style>
            """, unsafe_allow_html=True)

    def apply_theme(theme):
        css = ""
        if theme == "모던 다크 (Modern Dark)":
            css = """
            <style>
                [data-testid="stAppViewContainer"] { background-color: #1E1E1E; color: #E0E0E0; }
                [data-testid="stSidebar"] { background-color: #252526; border-right: 1px solid #333; }
                [data-testid="stHeader"] { background-color: rgba(30,30,30,0.9); }
                .stMarkdown, .stText, h1, h2, h3, h4, h5, h6 { color: #E0E0E0 !important; }
                .stDataFrame { border: 1px solid #444; }
                div[data-testid="metric-container"] { background-color: #333333; border: 1px solid #444; color: #fff; padding: 10px; border-radius: 8px; }
            </style>
            """
        elif theme == "웜 페이퍼 (Warm Paper)":
            css = """
            <style>
                [data-testid="stAppViewContainer"] { background-color: #F5F5DC; color: #4A403A; }
                [data-testid="stSidebar"] { background-color: #E8E4D9; border-right: 1px solid #D8D4C9; }
                .stMarkdown, .stText, h1, h2, h3, h4, h5, h6 { color: #5C4033 !important; font-family: 'Georgia', serif; }
                div[data-testid="metric-container"] { background-color: #FFF8E7; border: 1px solid #D2B48C; color: #5C4033; padding: 10px; border-radius: 4px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
                .stButton button { background-color: #D2B48C !important; color: #fff !important; border-radius: 0px; }
            </style>
            """
        elif theme == "고대비 (High Contrast)":
            css = """
            <style>
                [data-testid="stAppViewContainer"] { background-color: #FFFFFF; color: #000000; }
                [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 2px solid #000000; }
                .stMarkdown, .stText, h1, h2, h3, h4, h5, h6 { color: #000000 !important; font-weight: 900 !important; }
                div[data-testid="metric-container"] { background-color: #FFFFFF; border: 2px solid #000000; color: #000000; padding: 15px; border-radius: 0px; }
                .stButton button { background-color: #000000 !important; color: #FFFFFF !important; border: 2px solid #000000; font-weight: bold; }
            </style>
            """
        elif theme == "코퍼레이트 블루 (Corporate Blue)":
            css = """
            <style>
                [data-testid="stAppViewContainer"] { background-color: #F0F4F8; color: #243B53; }
                [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #BCCCDC; }
                h1, h2, h3 { color: #102A43 !important; }
                div[data-testid="metric-container"] { background-color: #FFFFFF; border-left: 5px solid #334E68; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 15px; border-radius: 4px; }
                .stButton button { background-color: #334E68 !important; color: white !important; border-radius: 4px; }
            </style>
            """
        elif theme == "그린 에코 (Green Eco)":
            css = """
            <style>
                [data-testid="stAppViewContainer"] { background-color: #F1F8E9; color: #1B5E20; }
                [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #C5E1A5; }
                h1, h2, h3 { color: #2E7D32 !important; }
                div[data-testid="metric-container"] { background-color: #FFFFFF; border-bottom: 3px solid #66BB6A; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 15px; border-radius: 8px; }
                .stButton button { background-color: #2E7D32 !important; color: white !important; border-radius: 20px; box-shadow: 0 2px 4px rgba(46, 125, 50, 0.3); }
            </style>
            """
        else: # Default
            css = """
            <style>
                /* Global Font & Background */
                @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');
                
                html, body, [class*="css"] {
                    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
                }
                
                [data-testid="stAppViewContainer"] { 
                    background-color: #F8F9FA; 
                    color: #343A40; 
                }
                
                [data-testid="stSidebar"] { 
                    background-color: #FFFFFF; 
                    border-right: 1px solid #DEE2E6; 
                    box-shadow: 2px 0 12px rgba(0,0,0,0.03);
                }
                
                /* Headers */
                h1, h2, h3 { color: #212529 !important; font-weight: 700 !important; letter-spacing: -0.5px; }
                h4, h5, h6 { color: #495057 !important; font-weight: 600 !important; }
                
                /* Sidebar Headers & Text */
                [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
                     color: #212529 !important;
                }
                [data-testid="stSidebar"] .stMarkdown p {
                    color: #495057 !important;
                    font-size: 0.95rem;
                }
                
                /* Improved Visibility for Global Filters Section */
                /* We can't target specifically by ID easily in Streamlit, but we can style inputs */
                [data-testid="stSidebar"] .stSelectbox label, 
                [data-testid="stSidebar"] .stMultiSelect label,
                [data-testid="stSidebar"] .stTextInput label {
                    color: #343A40 !important;
                    font-weight: 600 !important;
                }
                
                /* Buttons */
                .stButton button { 
                    background-color: #228BE6 !important; 
                    color: #fff !important; 
                    border: none;
                    border-radius: 6px;
                    font-weight: 500;
                    transition: all 0.2s;
                }
                .stButton button:hover {
                    background-color: #1C7ED6 !important;
                    box-shadow: 0 4px 12px rgba(34, 139, 230, 0.3);
                    transform: translateY(-1px);
                }
                
                /* Metric Cards */
                div[data-testid="metric-container"] { 
                    background-color: #FFFFFF; 
                    border: 1px solid #E9ECEF; 
                    color: #495057; 
                    padding: 16px; 
                    border-radius: 12px; 
                    box-shadow: 0 4px 20px rgba(0,0,0,0.04); 
                    transition: transform 0.2s;
                }
                div[data-testid="metric-container"]:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
                }
                
                /* Expander */
                .streamlit-expanderHeader {
                    background-color: #FFFFFF;
                    border-radius: 8px;
                    border: 1px solid #E9ECEF;
                    color: #343A40;
                    font-weight: 600;
                }
                
                /* Dataframe */
                .stDataFrame {
                    border: 1px solid #DEE2E6;
                    border-radius: 8px;
                }
                
                /* Custom Highlight for Admin Section if it has a specific wrapper (Simulated) */
                hr { margin: 2rem 0; border-color: #DEE2E6; }
            </style>
            """
        st.markdown(css, unsafe_allow_html=True)

    apply_theme(theme_mode)
    
    st.sidebar.markdown("---")

    with st.sidebar.expander("🔑 카카오 지도 설정", expanded=False):
        st.warning("카카오 자바스크립트 키 필요")
        kakao_key = st.text_input("키 입력", type="password", key="kakao_api_key_v2")
        if kakao_key: kakao_key = kakao_key.strip()
        
        if kakao_key:
            st.success("✅ 활성화됨")
        else:
            st.caption("미입력 시: 기본 지도 사용")
            
    st.sidebar.markdown("---")
    show_manual = st.sidebar.toggle("📘 사용 설명서 보기", value=False)
    if show_manual:
        # Robust Path Resolution
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        manual_filename = "premium_user_manual.html"
        static_dir = os.path.join(BASE_DIR, "static")
        manual_path = os.path.join(static_dir, manual_filename)
        
        # [FIX] Robust find (Unicode Normalization)
        if not os.path.exists(manual_path) and os.path.exists(static_dir):
            for f in os.path.listdir(static_dir):
                if unicodedata.normalize('NFC', f) == unicodedata.normalize('NFC', manual_filename):
                    manual_path = os.path.join(static_dir, f)
                    break
        
        if os.path.exists(manual_path):
            with open(manual_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Embed Images
            html_content = embed_local_images(html_content, base_path=os.path.join(BASE_DIR, "static"))
            st.components.v1.html(html_content, height=1000, scrolling=True)
            st.sidebar.info("설명서 닫기: 스위치 OFF")
            st.stop()
        else:
            st.sidebar.error(f"설명서 파일이 없습니다. (경로: {manual_path})")
        
    # [LANDING] Show manual from landing page button
    if st.session_state.get('show_landing_manual', False):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        manual_filename = "premium_user_manual.html"
        static_dir = os.path.join(BASE_DIR, "static")
        manual_path = os.path.join(static_dir, manual_filename)
        
        # [FIX] Robust find (Unicode Normalization)
        if not os.path.exists(manual_path) and os.path.exists(static_dir):
            for f in os.listdir(static_dir):
                if unicodedata.normalize('NFC', f) == unicodedata.normalize('NFC', manual_filename):
                    manual_path = os.path.join(static_dir, f)
                    break
        
        if os.path.exists(manual_path):
            with open(manual_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Embed Images
            html_content = embed_local_images(html_content, base_path=os.path.join(BASE_DIR, "static"))
            
            # Show close button
            if st.button("❌ 설명서 닫기", type="primary"):
                st.session_state.show_landing_manual = False
                st.rerun()
            
            st.components.v1.html(html_content, height=1200, scrolling=True)
            st.stop()
        else:
            st.error("설명서를 찾을 수 없습니다.")
            if st.button("돌아가기"):
                st.session_state.show_landing_manual = False
                st.rerun()
            st.stop()


# --- Main Logic ---

# No title here - removed 파이프라인

raw_df = None
error = None

if uploaded_dist:
    if data_source == "파일 업로드 (File)" and uploaded_zip:
        with st.spinner("🚀 파일 분석 및 매칭중..."):
             # [FIX] Smart Cache Invalidation
             # Pass mtime if it's a local file path to force re-run on file update
             dist_mtime = None
             if isinstance(uploaded_dist, str) and os.path.exists(uploaded_dist):
                 dist_mtime = os.path.getmtime(uploaded_dist)
                 
             # [FIX] Unpack 4 values (df, mgr_info, error, stats)
             raw_df, mgr_info_list, error, stats = data_loader.load_and_process_data(uploaded_zip, uploaded_dist, dist_mtime=dist_mtime)
             
             if stats:
                 # [FEATURE] Store data stats in session state for later "Help" (?) query
                 st.session_state['data_load_stats'] = stats
             
    elif data_source == "OpenAPI 연동 (Auto)" and api_df is not None:
        with st.spinner("🌐 API 데이터 매칭중..."):
             # [FIX] Unpack 4 values
             # Pass mtime for consistency if using local dist file
             dist_mtime = None
             if isinstance(uploaded_dist, str) and os.path.exists(uploaded_dist):
                 dist_mtime = os.path.getmtime(uploaded_dist)
                 
             raw_df, mgr_info_list, error, stats = data_loader.process_api_data(api_df, uploaded_dist)
             
             if stats:
                 # Minimal toast for API
                 st.toast(f"API 데이터 매칭 완료: {stats.get('after',0):,}건", icon="🌐")

if error:
    st.error(f"오류 발생: {error}")

if raw_df is not None:
    
    # [FIX] Ensure '관리지사' has no NaNs, fill with '미지정' (Global for all sources)
    if '관리지사' in raw_df.columns:
        raw_df['관리지사'] = raw_df['관리지사'].fillna('미지정')
        raw_df.loc[raw_df['관리지사'].astype(str).str.strip() == '', '관리지사'] = '미지정'
    else:
        raw_df['관리지사'] = '미지정'

    # [FIX] Global NFC Normalization to prevent Mac/Windows mismatch
    for col in ['관리지사', 'SP담당', '사업장명', '소재지전체주소', '영업상태명', '업태구분명']:
        if col in raw_df.columns:
            raw_df[col] = raw_df[col].astype(str).apply(lambda x: unicodedata.normalize('NFC', x).strip() if x else x)
            
    # [FIX] HOT-RELOAD STATUS
    # Even if cached, we re-merge the latest JSON status to ensure freshness
    raw_df = data_loader.merge_activity_status(raw_df)

    # [REFACTOR] Centralized Branch List Calculation
    custom_branch_order = ['중앙지사', '강북지사', '서대문지사', '고양지사', '의정부지사', '남양주지사', '강릉지사', '원주지사']
    custom_branch_order = [unicodedata.normalize('NFC', b) for b in custom_branch_order]
    
    if raw_df is not None and not raw_df.empty:
        current_branches_raw = [unicodedata.normalize('NFC', str(b)) for b in raw_df['관리지사'].unique() if pd.notna(b)]
        
        global_branch_opts = [b for b in custom_branch_order if b in current_branches_raw]
        others = [b for b in current_branches_raw if b not in custom_branch_order]
        global_branch_opts.extend(others)
    else:
        global_branch_opts = custom_branch_order
    
    # [FEATURE] Admin Global Sidebar Chart (Populated via Placeholder)
    # Uses admin_chart_placeholder defined at top of sidebar
    if st.session_state.get('user_role') == 'admin':
         # [FIX] Removed locals() check that might fail in Streamlit runtime
         try:
             target_container = admin_chart_placeholder.container()
         except NameError:
             # Fallback: Render at bottom but visible
             target_container = st.sidebar
         
         with target_container:
            with st.expander("📊 글로벌 현황 (Global)", expanded=True):
                    g_total = len(raw_df)
                    g_visited = 0
                    if '활동진행상태' in raw_df.columns:
                        g_visited = len(raw_df[raw_df['활동진행상태'] == '방문'])
                    
                    c1, c2 = st.columns(2)
                    c1.metric("전체", f"{g_total:,}")
                    
                    delta_val = f"{(g_visited/g_total*100):.1f}%" if g_total > 0 else None
                    c2.metric("방문", f"{g_visited:,}", delta=delta_val)
                    
                    if g_total > 0:
                        prog = g_visited / g_total
                        st.progress(min(prog, 1.0))

    # -------------------------------------------------------------
    # [FEATURE] Role-Based Landing Page
    # -------------------------------------------------------------
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None  # None, 'admin', 'branch', 'manager'
        st.session_state.user_branch = None
        st.session_state.user_manager_name = None
        st.session_state.user_manager_code = None
        if 'show_manual_landing' not in st.session_state:
            st.session_state.show_manual_landing = False

    if st.session_state.user_role is None:
        st.markdown("""
            <style>
                [data-testid="stSidebar"] {display: none;}
                /* [RESPONSIVE] Web: Ultra-Slim (210px) with App Frame */
                /* [RESPONSIVE] Web: Standard Desktop (1000px) with App Frame */
                /* [RESPONSIVE] Web: Standard Desktop (1000px) with App Frame */
                [data-testid="stAppViewContainer"] .block-container { 
                    max-width: 1000px; 
                    padding-top: 2.5rem; /* Increased top padding to prevent cutting off */
                    padding-bottom: 1rem; /* [OPTIMIZATION] Reduced bottom padding */
                    margin: auto; 
                    border-left: 1px solid #E9ECEF;
                    border-right: 1px solid #E9ECEF;
                    box-shadow: 0 0 40px rgba(0,0,0,0.03);
                    background: #FFFFFF;
                    min-height: 100vh;
                }
                @media (max-width: 640px) {
                    [data-testid="stAppViewContainer"] .block-container { 
                        max-width: 100%; 
                        padding-left: 0.6rem; 
                        padding-right: 0.6rem; 
                        border: none;
                        box-shadow: none;
                    }
                }

                .hero-section {
                    text-align: center;
                    padding: 1.2rem 1rem; /* [OPTIMIZATION] Compact padding */
                    background: linear-gradient(135deg, #1A73E8 0%, #0d47a1 100%);
                    border-radius: 20px; /* Slightly reduced radius for compact feel */
                    color: white;
                    margin-bottom: 1rem; /* [OPTIMIZATION] Reduced margin */
                    box-shadow: 0 12px 24px rgba(0, 50, 100, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    position: relative;
                    overflow: hidden;
                }
                /* Subtle top slight highlight for 3D effect */
                .hero-section::before {
                    content: "";
                    position: absolute;
                    top: 0; left: 0; right: 0; height: 1px;
                    background: rgba(255, 255, 255, 0.3);
                }

                .hero-title { 
                    font-size: 1.6rem; /* [OPTIMIZATION] Reduced size */
                    font-weight: 900; 
                    margin-bottom: 0.4rem; /* [OPTIMIZATION] Reduced margin */
                    letter-spacing: -0.5px; 
                    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .hero-subtitle { 
                    font-size: 0.9rem; /* [OPTIMIZATION] Reduced size */
                    opacity: 0.95; 
                    font-weight: 400; 
                    line-height: 1.4; 
                    color: rgba(255, 255, 255, 0.9);
                }
                
                .expert-badge {
                    display: inline-block;
                    padding: 4px 10px;
                    background: rgba(255, 255, 255, 0.15);
                    backdrop-filter: blur(4px);
                    border-radius: 20px;
                    font-size: 0.65rem;
                    font-weight: 700;
                    margin-bottom: 0.5rem; /* [OPTIMIZATION] Reduced margin */
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }
                
                .feature-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 0.3rem;
                    margin-bottom: 0.4rem;
                }
                .feature-card {
                    background: #F8F9FA;
                    padding: 0.3rem;
                    border-radius: 6px;
                    text-align: center;
                    border: 1px solid #E9ECEF;
                }
                .feature-icon { font-size: 0.9rem; margin-bottom: 0px; }
                .feature-name { font-weight: 800; color: #212529; margin-bottom: 0px; font-size: 0.7rem; }
                .feature-desc { display: none; } /* Hide descriptions on micro-view */
                
                .login-container {
                    background: rgba(255, 255, 255, 0.8);
                    backdrop-filter: blur(8px);
                    padding: 0.3rem;
                    border-radius: 10px;
                    border: 1px solid #E9ECEF;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.02);
                }
                
                /* Enhanced Tab Styling */
                .stTabs [data-baseweb="tab-list"] {
                    justify-content: center;
                    gap: 0.8rem;
                    border-bottom: none; /* Removed bottom border for cleaner look */
                    margin-bottom: 1.0rem; /* [OPTIMIZATION] Reduced margin */
                }
                .stTabs [data-baseweb="tab"] {
                    height: 46px; /* [OPTIMIZATION] Reduced height */
                    padding: 0 1rem;
                    font-weight: 800;
                    font-size: 1.15rem; /* [OPTIMIZATION] Reduced size */
                    color: #495057;
                    background-color: #F8F9FA;
                    border-radius: 12px;
                    transition: all 0.2s ease;
                }
                .stTabs [aria-selected="true"] {
                    color: #228BE6 !important;
                    background-color: #E7F5FF !important;
                    border: 1px solid #D0EBFF;
                }
            </style>
            """, unsafe_allow_html=True)
            
        # Hero Section
        st.markdown(f"""
            <div class="hero-section">
                <div class="expert-badge">PREMIUM AI EXPERT SYSTEM</div>
                <div class="hero-title">영업기회 비서</div>
                <div class="hero-subtitle">데이터 분석과 인공지능이 제안하는 과학적인 영업 파트너</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Expert Feature Highlights (Flexbox for Perfect Centering)
        # Using custom HTML with flexbox prevents vertical alignment issues
        # and avoids 'Node removeChild' by keeping structure static and simple.
        st.markdown("""
            <div style="display: flex; gap: 1rem; margin-bottom: 1.5rem;">
                <div class="feature-box-centered" style="flex: 1;">
                    <div>🌡️ AI 기회 분석</div>
                </div>
                <div class="feature-box-centered" style="flex: 1;">
                    <div>⚡ 상권 밀집도</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
            
        # Login Section Title
        st.markdown("<h3 style='text-align: center; margin-bottom: 0.8rem; font-weight: 700; font-size: 1.3rem;'>🔑 시스템 로그인</h3>", unsafe_allow_html=True)
        
        # [FEATURE] System Notice (Centered)
        try:
            sys_config_notice = load_system_config()
            if sys_config_notice.get("show_notice") and sys_config_notice.get("notice_content"):
                with st.container():
                     st.info(f"📢 **{sys_config_notice.get('notice_title', '공지사항')}**: {sys_config_notice['notice_content']}")
        except: pass

        # Centered Login Tabs with better layout
        tab_mgr, tab_br, tab_adm = st.tabs(["👤 담당자", "🏢 지사", "👮 관리자"])
        
        with tab_mgr:
            with st.container(border=True):
                # Centered Form Layout
                c_main = st.columns([1, 15, 1])
                with c_main[1]:
                    sel_br_for_mgr = st.selectbox("소속 지사 선택", ["전체"] + global_branch_opts, key="login_br_sel")
                    
                    if raw_df is not None:
                        mgr_candidates = pd.DataFrame(mgr_info_list) if 'mgr_info_list' in locals() and mgr_info_list else raw_df.copy()
                        if sel_br_for_mgr != "전체":
                            mgr_candidates = mgr_candidates[mgr_candidates['관리지사'] == sel_br_for_mgr]
                        
                        if '영업구역 수정' in mgr_candidates.columns:
                            mgr_candidates['display'] = mgr_candidates.apply(lambda x: f"{mask_name(x['SP담당'])} ({x['영업구역 수정']})" if pd.notna(x['영업구역 수정']) and x['영업구역 수정'] else mask_name(x['SP담당']), axis=1)
                        else:
                            mgr_candidates['display'] = mgr_candidates['SP담당'].apply(mask_name)
                        
                        display_to_real_map = dict(zip(mgr_candidates['display'], mgr_candidates['SP담당']))
                        mgr_list = sorted(mgr_candidates['display'].unique().tolist())
                    else:
                        mgr_list = []
                        display_to_real_map = {}
                    
                    with st.form("login_manager_v3"):
                        s_manager_display = st.selectbox("담당자 성함", mgr_list, key="mgr_login_sel")
                        manager_pw = st.text_input("접속 패스워드", type="password", key="mgr_login_pw")
                        if st.form_submit_button("담당자 시스템 접속 🚀", type="primary", use_container_width=True):
                            p_name = display_to_real_map.get(s_manager_display)
                            
                            # Parse Code if present in display string for context
                            p_code = None
                            if s_manager_display and "(" in s_manager_display and ")" in s_manager_display:
                                p_code = s_manager_display.split("(")[1].replace(")", "").strip()
                                
                            if p_name:
                                if manager_pw == get_manager_password(p_name):
                                    st.session_state.user_role = 'manager'
                                    st.session_state.user_manager_name = p_name
                                    st.session_state.user_manager_code = p_code
                                    
                                    # Pre-set filters for better UX
                                    user_br_find = raw_df[raw_df['SP담당'] == p_name]['관리지사'].mode()
                                    if not user_br_find.empty:
                                        st.session_state.user_branch = user_br_find[0]
                                        st.session_state.sb_branch = user_br_find[0]
                                    st.session_state.sb_manager = p_name
                                    
                                    activity_logger.log_access('manager', p_name, 'login')
                                    usage_logger.log_usage('manager', p_name, st.session_state.get('user_branch', ''), 'login', {'manager_code': p_code})
                                    st.query_params.clear() # [FIX] Clear params
                                    st.rerun()
                                else: st.error("패스워드가 올바르지 않습니다.")
                            else: st.error("담당자 정보를 찾을 수 없습니다.")

        with tab_br:
            with st.container(border=True):
                # Centered Form Layout
                c_main = st.columns([1, 15, 1])
                with c_main[1]:
                    st.info("지사 산하 모든 담당자의 활동과 실적을 모니터링합니다.")
                    with st.form("login_branch_v3"):
                        s_branch = st.selectbox("지사 선택", global_branch_opts, key="br_login_sel")
                        branch_pw = st.text_input("지사 공용 패스워드", type="password", key="br_login_pw")
                        if st.form_submit_button("지사 통합 시스템 접속 🚀", type="primary", use_container_width=True):
                            if branch_pw == BRANCH_PASSWORDS.get(s_branch, ""):
                                st.session_state.user_role = 'branch'
                                st.session_state.user_branch = s_branch
                                st.session_state.sb_branch = s_branch # Pre-set filter
                                activity_logger.log_access('branch', s_branch, 'login')
                                usage_logger.log_usage('branch', s_branch, s_branch, 'login')
                                st.query_params.clear() # [FIX] Clear params
                                st.rerun()
                            else: st.error("패스워드가 올바르지 않습니다.")

        with tab_adm:
            with st.container(border=True):
                # Centered Form Layout
                c_main = st.columns([1, 15, 1])
                with c_main[1]:
                    st.warning("시스템 설정 및 전사 통합 데이터 관리를 위한 전용 채널입니다.")
                    with st.form("login_admin_v3"):
                        pw = st.text_input("최고 관리자 암호", type="password", key="adm_login_pw")
                        if st.form_submit_button("통합 관리 시스템 접속 👑", type="primary", use_container_width=True):
                            if pw == "admin1234!!":
                                st.session_state.user_role = 'admin'
                                st.session_state.admin_auth = True
                                activity_logger.log_access('admin', '관리자', 'login')
                                usage_logger.log_usage('admin', '관리자', '전체', 'login')
                                st.query_params.clear() # [FIX] Clear any params before rerun
                                st.rerun()
                            else: st.error("암호가 올바르지 않습니다.")

        # Footer
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; color: #ADB5BD; font-size: 0.85rem;'>ⓒ 2026 Field Sales Assistant System • Premium AI Expert Edition</div>", unsafe_allow_html=True)
        
        # Minimalist Guide Center Button
        c1, c2, c3 = st.columns([2, 1, 2])
        with c2:
            if st.button("📘 이용 가이드 보기", key="guide_btn_landing", use_container_width=True):
                st.switch_page("pages/99_사용_가이드.py")
        st.stop() # Stop here if no role



    # -------------------------------------------------------------
    # Main Logic (Authenticated)
    # -------------------------------------------------------------
    
    # [DEMO MODE] Show banner for demo account
    if st.session_state.get('user_branch') == '데모지사':
        st.info("🎮 **데모 모드**: 샘플 데이터로 구성되어 있습니다. 실제 서비스와 동일한 기능을 체험하실 수 있습니다.")
    
    # [FAILSAFE] Admin Dashboard on Main Page (For visibility guarantee)
    if st.session_state.get('user_role') == 'admin':
         st.success(f"🔐 관리자 모드 접속중")
         with st.expander("📊 글로벌 현황 및 제어 (Main Panel)", expanded=True):
             # Ensure raw_df is available
             current_raw = raw_df if 'raw_df' in locals() or 'raw_df' in globals() else pd.DataFrame()
             
             if not current_raw.empty:
                 g_total = len(current_raw)
                 g_visited = 0
                 if '활동진행상태' in current_raw.columns:
                     g_visited = len(current_raw[current_raw['활동진행상태'] == '방문'])
                 
                 c_m1, c_m2, c_m3 = st.columns([1, 2, 1])
                 with c_m1:
                     delta = f"{(g_visited/g_total*100):.1f}%" if g_total > 0 else "0%"
                     st.metric("진행률", delta)
                 with c_m2:
                     if g_total > 0:
                         st.progress(min(g_visited/g_total, 1.0))
                     st.caption(f"방문: {g_visited} / 전체: {g_total} 건")
                 with c_m3:
                     if st.button("로그아웃", key="btn_logout_main_panel", type="primary", use_container_width=True):
                         st.session_state.clear()
                         st.rerun()
             else:
                 st.warning("데이터 로드 전입니다.")

    # --- Apply Global Filters (Sidebar) ---
    # --- Sidebar Filters ---
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # [FEATURE] System Config & Info
        sys_config = load_system_config()
        if sys_config.get("data_standard_date"):
            st.warning(f"📅 데이터 기준: {sys_config['data_standard_date']}")
        
        # [FEATURE] Logout / Role Info
        role_map = {'admin': '👮 관리자', 'branch': '🏢 지사 관리자', 'manager': '👤 담당자'}
        cur_role_txt = role_map.get(st.session_state.user_role, 'Unknown')
        st.sidebar.info(f"접속: **{cur_role_txt}**")
        if st.session_state.user_role == 'branch':
            st.sidebar.caption(f"지사: {st.session_state.user_branch}")
        elif st.session_state.user_role == 'manager':
            st.sidebar.caption(f"담당: {st.session_state.user_manager_name}")

        if st.sidebar.button("로그아웃 (처음으로)", key="btn_logout", type="primary"):
            for key in ['user_role', 'user_branch', 'user_manager_name', 'user_manager_code', 'admin_auth', 'data_load_stats']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # [NEW] Hidden Data Load Stats (?) Trigger
        if 'data_load_stats' in st.session_state:
            st.sidebar.markdown("---")
            if st.sidebar.button("❓ 데이터 무결성 정보", help="클릭하여 서비스 데이터 로드 현황을 확인합니다."):
                stats = st.session_state['data_load_stats']
                diff = stats.get('before',0) - stats.get('after',0)
                st.toast(
                    f"📊 **데이터 로드 완료**\n\n"
                    f"- 통합: {stats.get('before',0):,}건\n"
                    f"- 최종: {stats.get('after',0):,}건\n"
                    f"- 제외: {diff:,}건",
                    icon="🔍"
                )

        # [SECURITY] Session-based Admin Auth
        if 'admin_auth' not in st.session_state:
            st.session_state.admin_auth = False
            
        # [FIX] Initialize variables globally to prevent NameError
        edit_mode = False
        custom_view_mode = False
            
        c_mode1, c_mode2 = st.columns(2)
        
        # [INIT] Initialize admin-related variables from session state
        admin_auth = st.session_state.get('admin_auth', False)
        edit_mode = False
        custom_view_mode = False
        custom_view_managers = []
        exclude_branches = []
        
        # [UX] Admin Settings Toggle (Config & VOC)
        if st.session_state.user_role == 'admin':
            if st.checkbox("⚙️ 관리자 통합 도구 (설정/VOC/뷰)", value=False):
                st.divider()
                adm_tab1, adm_tab2, adm_tab3 = st.tabs(["📢 공지/설정", "🗣️ VOC 관리", "🛠️ 뷰/로그"])
                
                with adm_tab1: # Notice & Config
                    curr_config = load_system_config()
                    with st.form("sys_config_form_v2"):
                        st.subheader("시스템 설정")
                        new_date = st.text_input("기준일", value=curr_config.get("data_standard_date", ""))
                        st.subheader("공지사항")
                        use_notice = st.checkbox("노출 ON", value=curr_config.get("show_notice", False))
                        n_title = st.text_input("제목", value=curr_config.get("notice_title", ""))
                        n_content = st.text_area("내용", value=curr_config.get("notice_content", ""))
                        if st.form_submit_button("설정 저장"):
                            save_system_config({"data_standard_date":new_date, "show_notice":use_notice, "notice_title":n_title, "notice_content":n_content})
                            st.rerun()

                with adm_tab2: # VOC Management
                    st.subheader("요청사항(VOC) 관리")
                    vocs = voc_manager.load_voc_requests()
                    
                    if not vocs:
                        st.info("접수된 요청사항이 없습니다.")
                    else:
                        # Separate active and completed VOCs
                        active_vocs = [v for v in vocs if v['status'] in ['New', 'In Progress']]
                        completed_vocs = [v for v in vocs if v['status'] == 'Done']
                        
                        # Tab for active and completed
                        voc_tab1, voc_tab2 = st.tabs([f"🔥 진행중 ({len(active_vocs)}건)", f"✅ 완료 이력 ({len(completed_vocs)}건)"])
                        
                        with voc_tab1:
                            st.caption("새로 접수되었거나 처리 중인 요청사항입니다.")
                            if not active_vocs:
                                st.info("처리할 요청사항이 없습니다.")
                            else:
                                for v in active_vocs:
                                    badge = voc_manager.get_status_badge(v['status'])
                                    priority_badge = "🔴" if v['priority'] == "High" else "🟡" if v['priority'] == "Normal" else "🟢"
                                    
                                    with st.expander(f"{badge} {priority_badge} {v['subject']} - {v['user_name']} ({v['region']})", expanded=True):
                                        st.write(f"**내용**: {v['content']}")
                                        st.caption(f"📅 작성: {v['timestamp']} | ⚠️ 중요도: {v['priority']} | 👤 요청자: {v['user_name']} ({v['user_role']})")
                                        
                                        c_up1, c_up2 = st.columns([3, 1])
                                        with c_up1:
                                            admin_note = st.text_area("💬 관리자 답변", value=v.get('admin_comment',''), key=f"note_{v['id']}", height=100)
                                        with c_up2:
                                            new_stat = st.selectbox("📊 상태", ["New", "In Progress", "Done"], 
                                                                   index=["New", "In Progress", "Done"].index(v['status']), 
                                                                   key=f"stat_{v['id']}")
                                        
                                        if st.button("✅ 업데이트", key=f"btn_{v['id']}", type="primary", use_container_width=True):
                                            voc_manager.update_voc_status(v['id'], new_stat, admin_note)
                                            st.success("업데이트 완료!")
                                            st.rerun()
                        
                        with voc_tab2:
                            st.caption("처리 완료된 요청사항 이력입니다. 삭제하면 영구적으로 제거됩니다.")
                            if not completed_vocs:
                                st.info("완료된 요청사항이 없습니다.")
                            else:
                                for v in completed_vocs:
                                    badge = voc_manager.get_status_badge(v['status'])
                                    priority_badge = "🔴" if v['priority'] == "High" else "🟡" if v['priority'] == "Normal" else "🟢"
                                    
                                    with st.expander(f"{badge} {priority_badge} {v['subject']} - {v['user_name']} ({v['region']})"):
                                        st.write(f"**요청 내용**: {v['content']}")
                                        st.caption(f"📅 작성: {v['timestamp']} | ⚠️ 중요도: {v['priority']} | 👤 요청자: {v['user_name']} ({v['user_role']})")
                                        
                                        if v.get('admin_comment'):
                                            st.success(f"**💬 관리자 답변**\n\n{v['admin_comment']}")
                                        else:
                                            st.warning("답변이 등록되지 않았습니다.")
                                        
                                        st.divider()
                                        
                                        col_edit, col_del = st.columns([1, 1])
                                        with col_edit:
                                            if st.button("📝 답변 수정", key=f"edit_{v['id']}", use_container_width=True):
                                                st.session_state[f"editing_{v['id']}"] = True
                                                st.rerun()
                                        
                                        with col_del:
                                            if st.button("🗑️ 완전 삭제", key=f"del_{v['id']}", type="secondary", use_container_width=True):
                                                if voc_manager.delete_voc_request(v['id']):
                                                    st.success("요청이 삭제되었습니다.")
                                                    st.rerun()
                                                else:
                                                    st.error("삭제 실패")
                                        
                                        # Edit mode
                                        if st.session_state.get(f"editing_{v['id']}", False):
                                            st.markdown("---")
                                            st.markdown("**답변 수정 모드**")
                                            edit_note = st.text_area("답변 수정", value=v.get('admin_comment',''), key=f"edit_note_{v['id']}", height=100)
                                            
                                            col_save, col_cancel = st.columns([1, 1])
                                            with col_save:
                                                if st.button("💾 저장", key=f"save_{v['id']}", type="primary", use_container_width=True):
                                                    voc_manager.update_voc_status(v['id'], v['status'], edit_note)
                                                    st.session_state[f"editing_{v['id']}"] = False
                                                    st.success("답변이 수정되었습니다.")
                                                    st.rerun()
                                            with col_cancel:
                                                if st.button("❌ 취소", key=f"cancel_{v['id']}", use_container_width=True):
                                                    st.session_state[f"editing_{v['id']}"] = False
                                                    st.rerun()

                with adm_tab3: # View & Logs
                    st.info("대시보드 뷰 컨트롤")
                    c_edit, c_view = st.columns(2)
                    with c_edit:
                         edit_mode = st.toggle("🛠️ 데이터 수정 모드", value=False)
                    with c_view:
                         custom_view_mode = st.toggle("👮 강제 뷰 모드", value=False)
                    
                    if custom_view_mode:
                        all_mgrs_raw = sorted(raw_df['SP담당'].dropna().unique())
                        custom_view_managers = st.multiselect("담당자 지정", all_mgrs_raw)
                        all_branches_raw = sorted(raw_df['관리지사'].dropna().unique())
                        exclude_branches = st.multiselect("지사 제외", all_branches_raw)

                    # [MOVED] Admin Log Viewer
                    st.divider()
                    st.markdown("#### 📊 관리 기록 조회 및 시각화")
                    log_tab1, log_tab2, log_tab3, log_tab4, log_tab5, log_tab6 = st.tabs(["📊 사용량 모니터링", "⭐ 관심 업체", "🚗 네비게이션 이력", "접속 로그", "활동 변경 이력", "조회 기록"])
                    
                    with log_tab1:
                        st.markdown("### 📊 사용량 모니터링 대시보드")
                        st.caption("담당자 및 지사의 실제 사용 패턴을 분석합니다.")
                        
                        # Period selector
                        col_period1, col_period2 = st.columns([1, 3])
                        with col_period1:
                            monitor_days = st.selectbox("조회 기간", [7, 14, 30, 60, 90], index=2, key="monitor_days")
                        
                        # Get usage statistics
                        stats = usage_logger.get_usage_stats(days=monitor_days)
                        
                        # Summary metrics
                        st.markdown("#### 📈 전체 요약")
                        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                        with metric_col1:
                            st.metric("총 활동 수", f"{stats['total_actions']:,}건")
                        with metric_col2:
                            st.metric("활성 사용자", f"{stats['unique_users']}명")
                        with metric_col3:
                            st.metric("활성 지사", f"{stats['unique_branches']}개")
                        with metric_col4:
                            avg_per_user = stats['total_actions'] / max(stats['unique_users'], 1)
                            st.metric("사용자당 평균", f"{avg_per_user:.1f}건")
                        
                        st.divider()
                        
                        # Two column layout for charts
                        chart_col1, chart_col2 = st.columns(2)
                        
                        with chart_col1:
                            st.markdown("#### 📊 활동 유형별 분포")
                            if stats['actions_by_type']:
                                action_df = pd.DataFrame(list(stats['actions_by_type'].items()), columns=['활동유형', '횟수'])
                                action_df = action_df.sort_values('횟수', ascending=False)
                                chart = alt.Chart(action_df).mark_bar().encode(
                                    x=alt.X('활동유형:N', sort='-y'),
                                    y='횟수:Q',
                                    tooltip=['활동유형', '횟수']
                                ).properties(height=300)
                                text = chart.mark_text(dy=-5).encode(text='횟수:Q')
                                st.altair_chart(chart + text, use_container_width=True)
                            else:
                                st.info("데이터가 없습니다.")
                        
                        with chart_col2:
                            st.markdown("#### 🏢 지사별 활동")
                            if stats['actions_by_branch']:
                                branch_df = pd.DataFrame(list(stats['actions_by_branch'].items()), columns=['지사', '횟수'])
                                branch_df = branch_df.sort_values('횟수', ascending=False)
                                chart = alt.Chart(branch_df).mark_bar().encode(
                                    x=alt.X('지사:N', sort='-y'),
                                    y='횟수:Q',
                                    tooltip=['지사', '횟수']
                                ).properties(height=300)
                                text = chart.mark_text(dy=-5).encode(text='횟수:Q')
                                st.altair_chart(chart + text, use_container_width=True)
                            else:
                                st.info("데이터가 없습니다.")
                        
                        st.divider()
                        
                        # Daily activity trend
                        st.markdown("#### 📅 일별 활동 추이")
                        if stats['daily_activity']:
                            daily_df = pd.DataFrame(list(stats['daily_activity'].items()), columns=['날짜', '활동수'])
                            daily_df['날짜'] = pd.to_datetime(daily_df['날짜'])
                            daily_df = daily_df.sort_values('날짜')
                            st.line_chart(daily_df.set_index('날짜'))
                        else:
                            st.info("데이터가 없습니다.")
                        
                        st.divider()
                        
                        # Top users table
                        st.markdown("#### 🏆 활동 상위 사용자 (Top 10)")
                        if stats['top_users']:
                            top_users_df = pd.DataFrame(stats['top_users'])
                            top_users_df.columns = ['사용자명', '지사', '역할', '활동수']
                            st.dataframe(top_users_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("데이터가 없습니다.")
                        
                        st.divider()
                        
                        # User detail search
                        st.markdown("#### 🔍 개별 사용자 상세 조회")
                        search_user = st.text_input("사용자명 입력", key="search_user_detail")
                        if search_user:
                            user_timeline = usage_logger.get_user_activity_timeline(search_user, days=7)
                            if user_timeline:
                                st.success(f"'{search_user}' 님의 최근 7일 활동 ({len(user_timeline)}건)")
                                timeline_df = pd.DataFrame(user_timeline)
                                # Select relevant columns
                                display_cols = ['timestamp', 'action', 'details']
                                if all(col in timeline_df.columns for col in display_cols):
                                    timeline_df = timeline_df[display_cols]
                                    timeline_df.columns = ['시간', '활동', '상세']
                                    st.dataframe(timeline_df, use_container_width=True, hide_index=True, height=300)
                            else:
                                st.warning(f"'{search_user}' 님의 활동 기록이 없습니다.")
                    
                    with log_tab2:
                        st.markdown("### ⭐ 관심 업체 추적")
                        st.caption("담당자들이 관심 표시한 업체를 추적하여 영업 타겟을 파악합니다.")
                        
                        # Period selector
                        col_int1, col_int2 = st.columns([1, 3])
                        with col_int1:
                            int_days = st.selectbox("조회 기간", [7, 14, 30, 60, 90], index=2, key="int_days")
                        
                        # Get interest statistics
                        int_stats = usage_logger.get_interest_stats(days=int_days)
                        int_history = usage_logger.get_interest_history(days=int_days)
                        
                        # Summary metrics
                        st.markdown("#### 📈 관심 업체 요약")
                        metric_col1, metric_col2, metric_col3 = st.columns(3)
                        with metric_col1:
                            st.metric("총 관심 표시", f"{int_stats['total_interests']:,}건")
                        with metric_col2:
                            st.metric("활동 담당자", f"{int_stats['unique_users']}명")
                        with metric_col3:
                            st.metric("관심 업체 수", f"{int_stats['unique_businesses']}곳")
                        
                        st.divider()
                        
                        # Charts
                        chart_col1, chart_col2 = st.columns(2)
                        
                        with chart_col1:
                            st.markdown("#### 👤 담당자별 관심 표시")
                            if int_stats['interests_by_user']:
                                user_int_df = pd.DataFrame(list(int_stats['interests_by_user'].items()), columns=['담당자', '횟수'])
                                user_int_df = user_int_df.sort_values('횟수', ascending=False)
                                chart = alt.Chart(user_int_df).mark_bar().encode(
                                    x=alt.X('담당자:N', sort='-y'),
                                    y='횟수:Q',
                                    tooltip=['담당자', '횟수']
                                ).properties(height=300)
                                text = chart.mark_text(dy=-5).encode(text='횟수:Q')
                                st.altair_chart(chart + text, use_container_width=True)
                            else:
                                st.info("데이터가 없습니다.")
                        
                        with chart_col2:
                            st.markdown("#### 🏢 지사별 관심 표시")
                            if int_stats['interests_by_branch']:
                                branch_int_df = pd.DataFrame(list(int_stats['interests_by_branch'].items()), columns=['지사', '횟수'])
                                branch_int_df = branch_int_df.sort_values('횟수', ascending=False)
                                chart = alt.Chart(branch_int_df).mark_bar().encode(
                                    x=alt.X('지사:N', sort='-y'),
                                    y='횟수:Q',
                                    tooltip=['지사', '횟수']
                                ).properties(height=300)
                                text = chart.mark_text(dy=-5).encode(text='횟수:Q')
                                st.altair_chart(chart + text, use_container_width=True)
                            else:
                                st.info("데이터가 없습니다.")
                        
                        st.divider()
                        
                        # Top businesses
                        st.markdown("#### 🎯 가장 많이 관심 받은 업체 (Top 20)")
                        if int_stats['top_businesses']:
                            top_int_df = pd.DataFrame(list(int_stats['top_businesses'].items()), columns=['업체명', '관심수'])
                            st.dataframe(top_int_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("데이터가 없습니다.")
                        
                        st.divider()
                        
                        # Detailed history table
                        st.markdown("#### 📋 상세 관심 업체 이력")
                        
                        # Filters
                        filter_col1, filter_col2 = st.columns(2)
                        with filter_col1:
                            filter_user_int = st.selectbox("담당자 필터", ["전체"] + list(int_stats['interests_by_user'].keys()) if int_stats['interests_by_user'] else ["전체"], key="int_filter_user")
                        with filter_col2:
                            filter_branch_int = st.selectbox("지사 필터", ["전체"] + list(int_stats['interests_by_branch'].keys()) if int_stats['interests_by_branch'] else ["전체"], key="int_filter_branch")
                        
                        # Apply filters
                        filtered_int_history = int_history
                        if filter_user_int != "전체":
                            filtered_int_history = [h for h in filtered_int_history if h['user_name'] == filter_user_int]
                        if filter_branch_int != "전체":
                            filtered_int_history = [h for h in filtered_int_history if h['user_branch'] == filter_branch_int]
                        
                        if filtered_int_history:
                            st.success(f"총 {len(filtered_int_history)}건의 관심 업체 이력")
                            int_history_df = pd.DataFrame(filtered_int_history)
                            int_history_df.columns = ['시간', '담당자', '지사', '업체명', '주소', '도로명주소', '위도', '경도']
                            st.dataframe(int_history_df, use_container_width=True, hide_index=True, height=400)
                            
                            # Export option
                            csv = int_history_df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="📥 CSV 다운로드",
                                data=csv,
                                file_name=f"interest_history_{int_days}days.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("조건에 맞는 관심 업체 이력이 없습니다.")
                        
                        st.divider()
                        
                        # Usage tip
                        st.info("""
                        💡 **활용 방법**
                        
                        1. 담당자별로 어떤 업체에 관심이 있는지 파악
                        2. 중복 관심 업체 = 높은 우선순위 타겟
                        3. 관심 표시 후 실제 계약 전환율 분석
                        4. 담당자별 관심 패턴 분석으로 영업 전략 수립
                        """)
                    
                    with log_tab3:
                        st.markdown("### 🚗 네비게이션 이력 추적")
                        st.caption("담당자들의 길찾기 사용 이력을 추적하여 실제 방문 의도를 파악합니다.")
                        
                        # Period selector
                        col_nav1, col_nav2 = st.columns([1, 3])


                        with col_nav1:
                            nav_days = st.selectbox("조회 기간", [7, 14, 30, 60, 90], index=2, key="nav_days")
                        
                        # Get navigation statistics
                        nav_stats = usage_logger.get_navigation_stats(days=nav_days)
                        nav_history = usage_logger.get_navigation_history(days=nav_days)
                        
                        # Summary metrics
                        st.markdown("#### 📈 네비게이션 요약")
                        metric_col1, metric_col2, metric_col3 = st.columns(3)
                        with metric_col1:
                            st.metric("총 길찾기 횟수", f"{nav_stats['total_navigations']:,}건")
                        with metric_col2:
                            st.metric("사용 담당자", f"{nav_stats['unique_users']}명")
                        with metric_col3:
                            st.metric("방문 예정 업체", f"{nav_stats['unique_businesses']}곳")
                        
                        st.divider()
                        
                        # Charts
                        chart_col1, chart_col2 = st.columns(2)
                        
                        with chart_col1:
                            st.markdown("#### 👤 담당자별 길찾기 사용")
                            if nav_stats['navigations_by_user']:
                                user_nav_df = pd.DataFrame(list(nav_stats['navigations_by_user'].items()), columns=['담당자', '횟수'])
                                user_nav_df = user_nav_df.sort_values('횟수', ascending=False)
                                chart = alt.Chart(user_nav_df).mark_bar().encode(
                                    x=alt.X('담당자:N', sort='-y'),
                                    y='횟수:Q',
                                    tooltip=['담당자', '횟수']
                                ).properties(height=300)
                                text = chart.mark_text(dy=-5).encode(text='횟수:Q')
                                st.altair_chart(chart + text, use_container_width=True)
                            else:
                                st.info("데이터가 없습니다.")
                        
                        with chart_col2:
                            st.markdown("#### 🏢 지사별 길찾기 사용")
                            if nav_stats['navigations_by_branch']:
                                branch_nav_df = pd.DataFrame(list(nav_stats['navigations_by_branch'].items()), columns=['지사', '횟수'])
                                branch_nav_df = branch_nav_df.sort_values('횟수', ascending=False)
                                chart = alt.Chart(branch_nav_df).mark_bar().encode(
                                    x=alt.X('지사:N', sort='-y'),
                                    y='횟수:Q',
                                    tooltip=['지사', '횟수']
                                ).properties(height=300)
                                text = chart.mark_text(dy=-5).encode(text='횟수:Q')
                                st.altair_chart(chart + text, use_container_width=True)
                            else:
                                st.info("데이터가 없습니다.")
                        
                        st.divider()
                        
                        # Top businesses
                        st.markdown("#### 🎯 가장 많이 조회된 업체 (Top 20)")
                        if nav_stats['top_businesses']:
                            top_biz_df = pd.DataFrame(list(nav_stats['top_businesses'].items()), columns=['업체명', '조회수'])
                            st.dataframe(top_biz_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("데이터가 없습니다.")
                        
                        st.divider()
                        
                        # Detailed history table
                        st.markdown("#### 📋 상세 네비게이션 이력")
                        
                        # Filters
                        filter_col1, filter_col2 = st.columns(2)
                        with filter_col1:
                            filter_user = st.selectbox("담당자 필터", ["전체"] + list(nav_stats['navigations_by_user'].keys()) if nav_stats['navigations_by_user'] else ["전체"], key="nav_filter_user")
                        with filter_col2:
                            filter_branch = st.selectbox("지사 필터", ["전체"] + list(nav_stats['navigations_by_branch'].keys()) if nav_stats['navigations_by_branch'] else ["전체"], key="nav_filter_branch")
                        
                        # Apply filters
                        filtered_history = nav_history
                        if filter_user != "전체":
                            filtered_history = [h for h in filtered_history if h['user_name'] == filter_user]
                        if filter_branch != "전체":
                            filtered_history = [h for h in filtered_history if h['user_branch'] == filter_branch]
                        
                        if filtered_history:
                            st.success(f"총 {len(filtered_history)}건의 네비게이션 이력")
                            history_df = pd.DataFrame(filtered_history)
                            history_df.columns = ['시간', '담당자', '지사', '업체명', '주소', '위도', '경도']
                            st.dataframe(history_df, use_container_width=True, hide_index=True, height=400)
                            
                            # Export option
                            csv = history_df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="📥 CSV 다운로드",
                                data=csv,
                                file_name=f"navigation_history_{nav_days}days.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("조건에 맞는 네비게이션 이력이 없습니다.")
                        
                        st.divider()
                        
                        # Conversion tracking note
                        st.info("""
                        💡 **성공율 분석 방법**
                        
                        1. 이 네비게이션 이력을 CSV로 다운로드
                        2. 계약 완료 데이터와 업체명/주소 매칭
                        3. 네비게이션 사용 → 계약 전환율 계산
                        4. 담당자별/지사별 성공율 비교 분석
                        """)


                    with log_tab4:
                        st.caption("최근 접속 로그 (최대 50건)")
                        access_logs = activity_logger.get_access_logs(limit=50)
                        if access_logs:
                            log_df = pd.DataFrame(access_logs)
                            st.dataframe(log_df[::-1], use_container_width=True, height=200)
                        else:
                            st.info("로그 없음")

                    with log_tab5:
                        st.caption("최근 변경 이력")
                        change_history = activity_logger.get_change_history(limit=50)
                        if change_history:
                            history_df = pd.DataFrame(change_history)
                            st.dataframe(history_df[::-1], use_container_width=True, height=200)
                        else:
                            st.info("이력 없음")

                    with log_tab6:
                        st.caption("조회 기록")
                        view_logs = activity_logger.get_view_logs(limit=50)
                        if view_logs:
                            view_df = pd.DataFrame(view_logs)
                            st.dataframe(view_df[::-1], use_container_width=True, height=200)
                        else:

                            st.info("기록 없음")

        


        
        st.divider()
        
        # [FIX] Initialize filter variables globally (Default: All)
        sel_branch = "전체"
        sel_manager = "전체"
        sel_manager_label = "전체"
        sel_types = []
        selected_area_code = None
        only_hospitals = False
        only_large_area = False
        type_col = '업태구분명' if '업태구분명' in raw_df.columns else raw_df.columns[0]
        
        # [FIX] Additional missing initializations
        sel_permit_ym = "전체"
        sel_close_ym = "전체"
        sel_status = "전체"
        only_with_phone = False
        # [FIX] Additional missing initializations
        sel_permit_ym = "전체"
        sel_close_ym = "전체"
        sel_status = "전체"
        only_with_phone = False
        address_search = ""  # Address search filter
        
        # [NEW] Initialize Date Filter from Session State (for filtering logic before UI render)
        if 'global_date_range' not in st.session_state:
            st.session_state.global_date_range = ()
        global_date_range = st.session_state.global_date_range
        
        if raw_df is not None and not raw_df.empty:
            filter_df = raw_df.copy()
            
            # [SECURITY] Hard Filter for Manager Role
            # This ensures sidebar options are restricted even if UI logic fails.
            if st.session_state.user_role == 'manager':
                 if st.session_state.user_manager_code:
                      if '영업구역 수정' in filter_df.columns:
                          filter_df = filter_df[filter_df['영업구역 수정'] == st.session_state.user_manager_code]
                      else:
                          filter_df = filter_df[filter_df['SP담당'] == st.session_state.user_manager_name]
                 elif st.session_state.user_manager_name:
                      filter_df = filter_df[filter_df['SP담당'] == st.session_state.user_manager_name]
        else:
            filter_df = pd.DataFrame()
        
        # [SECURITY] Global Filter Visibility (Admin Only)
        st.markdown("### 🔍 조회 조건 설정")
        
        # [FEATURE] Global Date Range Filter (Moved to Conditional Search Expander)
        # Old location removed. Now handled via session state at top and UI rendered later.
        global_date_range = st.session_state.get('global_date_range', ())
        st.markdown("---")
            
        # 1. Branch
        custom_branch_order = ['중앙지사', '강북지사', '서대문지사', '고양지사', '의정부지사', '남양주지사', '강릉지사', '원주지사']
        custom_branch_order = [unicodedata.normalize('NFC', b) for b in custom_branch_order]
        current_branches_in_raw = [unicodedata.normalize('NFC', str(b)) for b in raw_df['관리지사'].unique() if pd.notna(b)]
        sorted_branches_for_filter = [b for b in custom_branch_order if b in current_branches_in_raw]
        
        # [FEATURE] Add 미지정 option for admin users
        if '미지정' in current_branches_in_raw and '미지정' not in sorted_branches_for_filter:
            sorted_branches_for_filter.append('미지정')
        
        others_for_filter = [b for b in current_branches_in_raw if b not in custom_branch_order]
        sorted_branches_for_filter.extend(others_for_filter)
        sorted_branches_for_filter = [unicodedata.normalize('NFC', b) for b in sorted_branches_for_filter]



        st.markdown("##### 🏢 지사 선택")
        
        # [ROLE_CONSTRAINT] Branch Selection
        branch_opts = ["전체"] + sorted_branches_for_filter
        
        # Default logic
        if 'sb_branch' not in st.session_state: st.session_state.sb_branch = "전체"
        
        # Force overrides
        disabled_branch = False
        if st.session_state.user_role == 'branch' or st.session_state.user_role == 'manager':
            # Lock to user's branch
            if st.session_state.user_branch:
                st.session_state.sb_branch = st.session_state.user_branch
                disabled_branch = True
        
        if st.session_state.sb_branch != "전체":
                st.session_state.sb_branch = unicodedata.normalize('NFC', st.session_state.sb_branch)
        
        def reset_manager_filter():
            st.session_state.sb_manager = "전체"
            st.session_state.page = 0 # [FIX] Reset pagination
            st.query_params.clear()
            
        sel_branch = st.selectbox(
            "관리지사 선택", 
            branch_opts, 
            index=branch_opts.index(st.session_state.sb_branch) if st.session_state.sb_branch in branch_opts else 0,
            key="sb_branch",
            on_change=reset_manager_filter,
            disabled=disabled_branch
        )

        if sel_branch != "전체":
            filter_df = filter_df[filter_df['관리지사'] == sel_branch]
        
        # 2. Manager
        has_area_code = '영업구역 수정' in filter_df.columns
        
        st.markdown("##### 🧑‍💻 영업구역 (담당자) 선택")
        
        if has_area_code:
                temp_df = filter_df[['영업구역 수정', 'SP담당']].dropna(subset=['SP담당']).copy()
                # Handle potential NaN in code
                temp_df['영업구역 수정'] = temp_df['영업구역 수정'].fillna('')
                temp_df['label'] = temp_df.apply(lambda x: f"{x['영업구역 수정']} ({x['SP담당']})" if x['영업구역 수정'] else x['SP담당'], axis=1)
                temp_df = temp_df.sort_values(['SP담당', '영업구역 수정'])
                manager_opts = ["전체"] + list(temp_df['label'].unique())
                # Map label back to data
                label_map_code = dict(zip(temp_df['label'], temp_df['영업구역 수정']))
                label_map_name = dict(zip(temp_df['label'], temp_df['SP담당']))
        else:
            manager_opts = ["전체"] + sorted(list(filter_df['SP담당'].dropna().unique()))
        
        if 'sb_manager' not in st.session_state: st.session_state.sb_manager = "전체"

        def on_manager_change():
             st.session_state.page = 0
             st.query_params.clear()

        # [ROLE_CONSTRAINT] Manager (Admin can always change)
        sel_manager_label = st.selectbox(
            "영업구역/담당", 
            manager_opts, 
            index=manager_opts.index(st.session_state.get('sb_manager', "전체")) if st.session_state.get('sb_manager') in manager_opts else 0,
            key="sb_manager",
            on_change=on_manager_change, # [FIX] Reset page & params
            disabled=False # Admin can always change
        )
        
        sel_manager = "전체" 
        selected_area_code = None 
        
        if sel_manager_label != "전체":
            if has_area_code:
                # Reverse lookup
                selected_area_code = label_map_code.get(sel_manager_label)
                selected_name_only = label_map_name.get(sel_manager_label)
                
                if selected_area_code:
                    filter_df = filter_df[filter_df['영업구역 수정'] == selected_area_code]
                    sel_manager = selected_name_only
                else:
                    # No code, just name
                    filter_df = filter_df[filter_df['SP담당'] == selected_name_only]
                    sel_manager = selected_name_only
            else:
                filter_df = filter_df[filter_df['SP담당'] == sel_manager_label]
                sel_manager = sel_manager_label

            if sel_manager != "전체":
                sel_manager = unicodedata.normalize('NFC', sel_manager)
                
        # 3. Type
        st.markdown("##### 🏥 병원/의원 필터")
        c_h1, c_h2 = st.columns(2)
        with c_h1:
            only_hospitals = st.toggle("🏥 병원 관련만 보기", value=False)
        with c_h2:
            only_large_area = st.toggle("🏗️ 100평 이상만 보기", value=False)
        
        # [FEATURE] Medium Area Filter
        only_medium_area = st.toggle("🏗️ 10평 ~ 100평 미만", value=False)
        
        try:
            available_types = sorted(list(filter_df[type_col].dropna().unique()))
        except:
            available_types = []
            
        if not available_types and not filter_df.empty:
            available_types = sorted(list(raw_df[type_col].dropna().unique()))
            
        with st.expander("📂 업태(업종) 필터 (펼치기/접기)", expanded=False):
            sel_types = st.multiselect(
                "업태를 선택하세요 (복수 선택 가능)", 
                available_types,
                placeholder="전체 선택 (비어있으면 전체)",
                label_visibility="collapsed"
            )
        
        # 4. Date
        st.markdown("##### 📅 날짜 필터 (연-월)")

        # [FEATURE] Quick Filters (New/Closed 9 Days)
        # Initialize Session State for Quick Filter
        if 'admin_quick_filter' not in st.session_state:
            st.session_state.admin_quick_filter = None

        qf_col1, qf_col2 = st.columns(2)
        # Use pandas for robust date handling
        today_ref = pd.Timestamp.now().date()
        target_date = (pd.Timestamp.now() - pd.Timedelta(days=9)).date()
        
        with qf_col1:
            # Toggle logic
            is_active_new = st.session_state.admin_quick_filter == 'new_7d'
            if st.button(f"✨ 신규 (9일){' ✅' if is_active_new else ''}", use_container_width=True, help="최근 9일 이내 개업(인허가)된 건만 봅니다."):
                st.session_state.admin_quick_filter = None if is_active_new else 'new_7d'
                st.rerun()
        with qf_col2:
            is_active_closed = st.session_state.admin_quick_filter == 'closed_7d'
            if st.button(f"🚪 폐업 (9일){' ✅' if is_active_closed else ''}", use_container_width=True, help="최근 9일 이내 폐업된 건만 봅니다."):
                st.session_state.admin_quick_filter = None if is_active_closed else 'closed_7d'
                st.rerun()

        # Apply Quick Filter Logic
        if st.session_state.admin_quick_filter == 'new_7d':
             st.info(f"✨ 최근 9일 ({target_date} ~) 신규 인허가 건")
             if '인허가일자' in filter_df.columns:
                 filter_df = filter_df[filter_df['인허가일자'].dt.date >= target_date]
             
        elif st.session_state.admin_quick_filter == 'closed_7d':
             st.info(f"🚪 최근 9일 ({target_date} ~) 폐업 건")
             if '폐업일자' in filter_df.columns:
                 filter_df = filter_df[filter_df['폐업일자'].dt.date >= target_date]

        def get_ym_options(column):
            if column not in raw_df.columns: return []
            dates = raw_df[column].dropna()
            if dates.empty: return []
            return sorted(dates.dt.strftime('%Y-%m').unique(), reverse=True)

        permit_ym_opts = ["전체"] + get_ym_options('인허가일자')
        if 'sb_permit_ym' not in st.session_state: st.session_state.sb_permit_ym = "전체"
        sel_permit_ym = st.selectbox(
            "인허가일자 (월별)", 
            permit_ym_opts,
            index=permit_ym_opts.index(st.session_state.get('sb_permit_ym', "전체")) if st.session_state.get('sb_permit_ym') in permit_ym_opts else 0,
            key="sb_permit_ym"
        )
        
        close_ym_opts = ["전체"] + get_ym_options('폐업일자')
        if 'sb_close_ym' not in st.session_state: st.session_state.sb_close_ym = "전체"
        sel_close_ym = st.selectbox(
            "폐업일자 (월별)", 
            close_ym_opts,
            index=close_ym_opts.index(st.session_state.get('sb_close_ym', "전체")) if st.session_state.get('sb_close_ym') in close_ym_opts else 0,
            key="sb_close_ym"
        )
        
        # [FEATURE] Modification Period Filter (Requested by User)
        st.markdown("##### 📅 수정 기간 (기간 선택)")
        mod_range = st.date_input(
            "시작일 - 종료일",
            value=[],
            help="데이터의 최종 수정일(인허가/폐업/활동) 기준",
            key="sb_mod_period"
        )
        
        # 5. Status
        st.markdown("##### 영업상태")
        status_opts = ["전체"] + sorted(list(raw_df['영업상태명'].unique()))
        
        if 'sb_status' not in st.session_state: st.session_state.sb_status = "전체"
        
        sel_status = st.selectbox(
            "영업상태", 
            status_opts, 
            index=status_opts.index(st.session_state.get('sb_status', "전체")) if st.session_state.get('sb_status') in status_opts else 0,
            key="sb_status"
        )
        
        def reset_page():
            st.session_state.page = 0
            
        st.markdown("##### 📞 전화번호 필터")
        only_with_phone = st.toggle("전화번호 있는 것만 보기", value=False, on_change=reset_page)
        
        st.markdown("---")
        
        # [FEATURE] Address search
        st.markdown("##### 🔍 주소 검색")
        address_search = st.text_input("주소 검색 (예: 인천/삼산동)", value="", placeholder="주소 또는 업체명 입력...")
    # [LOGGING] View/Filter Logging
    # We track changes in key filters
    
    current_filters = {
        'branch': sel_branch,
        'manager': sel_manager, 
        'types': str(sorted(sel_types)) if sel_types else "All",
        'status': sel_status,
        'search': address_search
    }
    
    # Initialize previous state if not exists
    if 'prev_view_filters' not in st.session_state:
        st.session_state.prev_view_filters = current_filters
    
    # Check for changes
    filter_changes = []
    prev_filters = st.session_state.prev_view_filters
    
    if prev_filters['branch'] != current_filters['branch']:
        filter_changes.append(f"지사 변경: {prev_filters['branch']} -> {current_filters['branch']}")
        
    if prev_filters['manager'] != current_filters['manager']:
        filter_changes.append(f"담당자 변경: {prev_filters['manager']} -> {current_filters['manager']}")
        
    if prev_filters['status'] != current_filters['status']:
        filter_changes.append(f"영업상태 변경: {current_filters['status']}")

    if prev_filters['search'] != current_filters['search'] and current_filters['search']:
         filter_changes.append(f"검색어: {current_filters['search']}")

    if filter_changes:
        # User Info
        u_role = st.session_state.get('user_role', 'Unknown')
        u_name = st.session_state.get('user_manager_name') or st.session_state.get('user_branch') or '관리자'
        u_branch = st.session_state.get('user_branch', '')
        
        # Log to both systems
        activity_logger.log_view(u_role, u_name, "필터/검색", ", ".join(filter_changes))
        usage_logger.log_usage(u_role, u_name, u_branch, 'filter_change', {'changes': filter_changes})
        
        # Update State
        st.session_state.prev_view_filters = current_filters

    # Data Filtering
    base_df = raw_df.copy()
    
    # Get current branch selection
    current_branch_filter = st.session_state.get('sb_branch', "전체")
    
    # [REVERT] Exclude '미지정' unless explicitly selected (Previous behavior)
    # [FIX] REMOVED aggressive 'Unassigned' filter that was hiding valid 'Touched' records for Managers.
    # The Security Filter below (lines 1515+) is sufficient and more accurate.
    # if st.session_state.user_role != 'admin' or (st.session_state.user_role == 'admin' and current_branch_filter not in ["전체", "미지정"]):
    #      base_df = base_df[base_df['관리지사'] != '미지정']

        
    # Debug: show total records after 미지정 filter
    if st.session_state.user_role == 'admin':
        st.sidebar.caption(f"🔍 전체 데이터: {len(base_df)}건 (미지정 필터 후)")
    
    # [FEATURE] Add 최종수정시점 column (Last Modified Date)
    # Use the most recent date from 인허가일자 or 폐업일자, or current date if both are missing
    # [OPTIMIZATION] '최종수정시점' is now pre-calculated in data_loader using vectorized operations
    # We no longer need the slow row-by-row apply here.
    if '최종수정시점' not in base_df.columns:
        base_df['최종수정시점'] = pd.Timestamp.now()

    # [SECURITY] Hard Filter for Manager Role (Main Data)
    # [FIX] Also include records where the user has logged activity (e.g. Recommended Course visits)
    # This prevents visited items from disappearing if they are not assigned or assigned to others.
    
    # 1. Get keys touched by user
    touched_keys = []
    if st.session_state.user_role in ['manager', 'branch']:
        u_name = st.session_state.get('user_manager_name') or st.session_state.get('user_branch')
        if u_name:
            touched_keys = activity_logger.get_user_activity_keys(u_name)

    if st.session_state.user_role == 'manager':
            # Create mask for assignment
            mask_assigned = pd.Series(False, index=base_df.index)
            
            if st.session_state.user_manager_code:
                if '영업구역 수정' in base_df.columns:
                    mask_assigned = (base_df['영업구역 수정'] == st.session_state.user_manager_code)
                else:
                    mask_assigned = (base_df['SP담당'] == st.session_state.user_manager_name)
            elif st.session_state.user_manager_name:
                mask_assigned = (base_df['SP담당'] == st.session_state.user_manager_name)
            
            # Create mask for activity
            mask_touched = pd.Series(False, index=base_df.index)
            if touched_keys:
                 # [OPTIMIZATION] Vectorized Key Generation
                 # Replacing slow apply() with vectorized string concatenation
                 temp_name = base_df['사업장명'].fillna("").astype(str)
                 temp_addr = base_df['소재지전체주소'].fillna("").astype(str)
                 
                 # Strict NFC normalization is hard in vectorization without apply, 
                 # but most data is consistent.
                 # If key mismatch occurs, we might need a faster apply.
                 # Let's use list comp which is faster than pd.apply
                 temp_keys = [unicodedata.normalize('NFC', f"{n}_{a}") for n, a in zip(temp_name, temp_addr)]
                 mask_touched = pd.Series(temp_keys, index=base_df.index).isin(touched_keys)
            
            base_df = base_df[mask_assigned | mask_touched]
                
    # [SECURITY] Hard Filter for Branch Role
    if st.session_state.user_role == 'branch':
        if st.session_state.user_branch:
             # Normalize just in case
             u_branch = unicodedata.normalize('NFC', st.session_state.user_branch)
             
             mask_assigned = (base_df['관리지사'] == u_branch)
             
             mask_touched = pd.Series(False, index=base_df.index)
             if touched_keys:
                 temp_name = base_df['사업장명'].fillna("").astype(str)
                 temp_addr = base_df['소재지전체주소'].fillna("").astype(str)
                 temp_keys = [unicodedata.normalize('NFC', f"{n}_{a}") for n, a in zip(temp_name, temp_addr)]
                 mask_touched = pd.Series(temp_keys, index=base_df.index).isin(touched_keys)
                 
             base_df = base_df[mask_assigned | mask_touched]
    
    # [FEATURE] Admin Custom Dashboard Override
    if custom_view_mode and admin_auth and (custom_view_managers or exclude_branches):
        if custom_view_managers:
            base_df = base_df[base_df['SP담당'].isin(custom_view_managers)]
            
        if exclude_branches:
            base_df = base_df[~base_df['관리지사'].isin(exclude_branches)]
            
        msg = "👮 관리자 지정 뷰: "
        if custom_view_managers: msg += f"담당자 {len(custom_view_managers)}명 포함"
        if custom_view_managers and exclude_branches: msg += " & "
        if exclude_branches: msg += f"지사 {len(exclude_branches)}곳 제외"
        
        st.toast(msg, icon="👮")
        
    else:
        # Standard Sidebar Filters
        # [FIX] Source of Truth is Session State (for Immediate Button Response)
        # [FIX] Only Admin can use Sidebar Branch Filter. 
        # Non-admins (Branch/Manager) are already filtered by Security Filter above.
        # If we check sb_branch for them, stale session state might cause conflict (0 results).
        if st.session_state.user_role == 'admin':
            current_branch_filter = st.session_state.get('sb_branch', "전체")
        else:
            current_branch_filter = "전체"
        
        if current_branch_filter != "전체":
            # [FIX] Normalize comparison for Mac/Excel compatibility
            norm_sel_branch = unicodedata.normalize('NFC', current_branch_filter)
            base_df = base_df[base_df['관리지사'] == norm_sel_branch]
            
            # Debug log for admin
            if st.session_state.user_role == 'admin':
                st.sidebar.caption(f"📊 필터: {norm_sel_branch} | 결과: {len(base_df)}건")
            
        if selected_area_code:
            base_df = base_df[base_df['영업구역 수정'] == selected_area_code]
        elif sel_manager != "전체": 
            norm_sel_manager = unicodedata.normalize('NFC', sel_manager)
            base_df = base_df[base_df['SP담당'] == norm_sel_manager]
            
    # Common Filters (Applied to both modes)
    if only_hospitals:
        mask = base_df[type_col].astype(str).str.contains('병원|의원', na=False)
        if '개방서비스명' in base_df.columns:
            mask = mask | base_df['개방서비스명'].astype(str).str.contains('병원|의원', na=False)
        base_df = base_df[mask]
        
    if only_large_area:
        if '소재지면적' in base_df.columns:
             base_df['temp_area'] = pd.to_numeric(base_df['소재지면적'], errors='coerce').fillna(0)
             base_df = base_df[base_df['temp_area'] >= 330.58]
    
    if sel_types:
        base_df = base_df[base_df[type_col].isin(sel_types)]
        
    if sel_permit_ym != "전체":
        base_df = base_df[base_df['인허가일자'].dt.strftime('%Y-%m') == sel_permit_ym]
        
    if sel_close_ym != "전체":
        base_df = base_df[base_df['폐업일자'].dt.strftime('%Y-%m') == sel_close_ym]
        
    if only_with_phone:
        base_df = base_df[base_df['소재지전화'].notna() & (base_df['소재지전화'] != "")]
    
    # [FEATURE] Global Date Range Filter (최종수정일 기준)
    # Applied to base_df so it affects ALL tabs (Map, Stats, Mobile, Grid)
    if 'global_date_range' in st.session_state and len(st.session_state.global_date_range) == 2:
        g_start, g_end = st.session_state.global_date_range
        
        # Ensure '최종수정시점' is valid datetime
        if '최종수정시점' in base_df.columns:
             # Fast check type
             if not pd.api.types.is_datetime64_any_dtype(base_df['최종수정시점']):
                  base_df['최종수정시점'] = pd.to_datetime(base_df['최종수정시점'], errors='coerce')
             
             base_df = base_df[
                 (base_df['최종수정시점'].dt.date >= g_start) & 
                 (base_df['최종수정시점'].dt.date <= g_end)
             ]
             
             # Show filter info for debugging/confirmation
             st.sidebar.success(f"🗓️ 기간 필터 적용: {g_start} ~ {g_end} ({len(base_df):,}건)")

    
    # [FEATURE] Area Filter Logic
    if only_large_area:
         if '평수' in base_df.columns:
             base_df = base_df[base_df['평수'] >= 100]
             
    if only_medium_area:
         if '평수' in base_df.columns:
             base_df = base_df[(base_df['평수'] >= 10) & (base_df['평수'] < 100)]

    # [FEATURE] Address search filter - simplified with OR logic
    if address_search:
        # Split search keywords by / or space
        import re
        # [FIX] Normalize input for Mac users (NFD -> NFC)
        search_norm = unicodedata.normalize('NFC', address_search.strip())
        keywords = re.split(r'[/\s]+', search_norm)
        keywords = [k for k in keywords if k]  # Remove empty strings
        
        if keywords:
            # Create a mask that checks if ANY keyword is present (OR logic)
            mask = pd.Series([False] * len(base_df), index=base_df.index)
            for keyword in keywords:
                keyword_mask = (
                    base_df['소재지전체주소'].astype(str).apply(lambda x: unicodedata.normalize('NFC', x)).str.contains(keyword, case=False, na=False, regex=False) |
                    base_df['사업장명'].astype(str).apply(lambda x: unicodedata.normalize('NFC', x)).str.contains(keyword, case=False, na=False, regex=False)
                )
                mask = mask | keyword_mask  # OR logic: any keyword match
            base_df = base_df[mask]
            
            # Debug: Search Result Count for Admin
            if st.session_state.user_role == 'admin':
                 st.sidebar.caption(f"🔎 검색 결과: {len(base_df)}건")
        
    df = base_df.copy()
    if sel_status != "전체":
        df = df[df['영업상태명'] == sel_status]

    # Edit Mode
    # Edit Mode
    if edit_mode:
        if not admin_auth:
             st.warning("🔒 관리자 권한이 필요합니다. 사이드바 설정 메뉴에서 암호를 입력해주세요.")
             st.stop()
             
        # Authorized Logic
        st.title("🛠️ 영업구역 및 담당자 수정")
        st.info("💡 '관리지사'와 '영업구역(코드)'을 수정할 수 있습니다. 수정을 완료한 후 **[💾 수정본 다운로드]** 버튼을 눌러 저장하세요.")
        
        # [FEATURE] Enhanced Filters
        st.markdown("##### 🛠️ 편의 도구: 수정 대상 필터링")
        
        # 1. Scope Override
        ignore_global = st.checkbox("🔓 Sidebar 공통 필터 무시 (전체 데이터 불러오기)", value=False, help="체크 시 사이드바의 필터를 무시하고 전체 데이터를 대상으로 검색합니다.")
        
        if ignore_global:
            edit_target_df = raw_df.copy()
        else:
            edit_target_df = df.copy()
            
        c_e1, c_e2 = st.columns(2)
        
        # 2. Branch Filter
        with c_e1:
             all_branches_edit = sorted(edit_target_df['관리지사'].dropna().unique())
             sel_edit_branches = st.multiselect("1. 수정할 지사 선택 (복수 가능)", all_branches_edit, placeholder="전체 (미선택 시)")
             
        if sel_edit_branches:
            edit_target_df = edit_target_df[edit_target_df['관리지사'].isin(sel_edit_branches)]
            
        # 3. Manager Filter (Dynamic based on Branch)
        with c_e2:
             all_managers_edit = sorted(edit_target_df['SP담당'].dropna().unique())
             sel_edit_managers = st.multiselect("2. 수정할 담당자 선택 (복수 가능)", all_managers_edit, placeholder="전체 (미선택 시)")
             
        if sel_edit_managers:
            edit_target_df = edit_target_df[edit_target_df['SP담당'].isin(sel_edit_managers)]
            
        branche_opts = ['중앙지사', '강북지사', '서대문지사', '고양지사', '의정부지사', '남양주지사', '강릉지사', '원주지사']
        
        column_config = {
             "관리지사": st.column_config.SelectboxColumn("관리지사 (선택)", options=branche_opts, required=True, width="medium"),
             "영업구역 수정": st.column_config.TextColumn("영업구역 (Code)", width="medium", help="영업구역 코드 (예: G000407)"),
             "SP담당": st.column_config.TextColumn("SP실명 (담당자)", disabled=True, width="medium"),
             "사업장명": st.column_config.TextColumn("사업장명", disabled=True),
             "소재지전체주소": st.column_config.TextColumn("주소", disabled=True),
        }
        
        available_cols = edit_target_df.columns.tolist()
        base_cols = ['사업장명', '영업상태명', '관리지사']
        if '영업구역 수정' in available_cols:
            base_cols.append('영업구역 수정')
            
        base_cols.append('SP담당')
        base_cols.extend(['소재지전체주소', '업태구분명'])
        
        cols_to_show = [c for c in base_cols if c in available_cols]
        
        editable_cols = ['관리지사', '영업구역 수정']
        disabled_cols = [c for c in cols_to_show if c not in editable_cols]
        
        edited_df = st.data_editor(
            edit_target_df[cols_to_show],
            column_config=column_config,
            use_container_width=True,
            num_rows="fixed",
            hide_index=True,
            height=600,
            disabled=disabled_cols
        )
        
        st.success(f"총 {len(edited_df)}건의 데이터가 표시되었습니다.")
        
        csv_edit = edited_df.to_csv(index=False, encoding='cp949').encode('cp949')
        st.download_button(
            label="💾 수정된 데이터 다운로드 (CSV)",
            data=csv_edit,
            file_name="영업기회_수정본.csv",
            mime="text/csv",
            type="primary"
        )
        
        st.stop() 
        
    # Handle Query Parameters for Actions (e.g., Visit Report)
    # [REMOVED] Dead code block for q_action == "visit" removed. Logic moved to top.
    try:
        pass 
    except Exception as e:
        st.error(f"Action Error: {e}")
        
    try:
        pass # Placeholder for original try-except block if it existed
    except Exception as e:
        st.error(f"Action Error: {e}") 
        
    # Dashboard
    custom_branch_order = ['중앙지사', '강북지사', '서대문지사', '고양지사', '의정부지사', '남양주지사', '강릉지사', '원주지사']
    # [FIX] Normalize constants
    custom_branch_order = [unicodedata.normalize('NFC', b) for b in custom_branch_order]
    
    try:
        current_branches = list(base_df['관리지사'].unique())
        sorted_branches = [b for b in custom_branch_order if b in current_branches]
        others = [b for b in current_branches if b not in custom_branch_order]
        sorted_branches.extend(others)
    except:
        sorted_branches = []
    
    # [FEATURE] Usage Guide Section
    with st.expander("📖 사용안내 (클릭하여 접기/펼치기)", expanded=False):
        st.markdown("""
        <div style="background-color: #f8f9fa; border-left: 4px solid #4CAF50; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
            <p style="font-size: 0.95rem; line-height: 1.6; color: #333;">
            이 데이터는 <b>행정안전부 공공데이터</b>로 1월 변동분(신규영업, 폐업, 변동이슈발생)데이터 입니다. <br>
            지사별, 담당구역별 <b>영업(신규인허가 또는 변경이슈)</b>, <b>폐업(폐업등록)</b>된 시설로 지사/담당자별 조건 조회기능이 있으며, 
            <b>신규/폐업(15일)</b> 체크박스 선택시 이슈 발생일로부터 15일이내 인것만 볼수 있으며, <b>병원, 100평</b> 다중조건 기능도 사용하실수 있습니다. <br>
            특히 시설 위치를 <b>웹 지도</b>로 영업/폐업 각각 볼수 있으며 시설 선택시 기본정보 및 <b>카카오 네비게이션</b> 연결기능을 사용할수 있습니다. <br>
            웹, 모바일에서 활용할수 있는 <b>모바일리스트, 데이터 그리드</b> 기능이 있어 필요시 다운로드 활용 가능합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # [FEATURE] Local AI Activity Guide (Restored & Moved)
    # Only show for Manager/Branch roles to provide personalized insight
    if st.session_state.user_role in ['manager', 'branch'] and not df.empty:
        # Calculate stats (Last 15 days)
        ai_now = pd.Timestamp.now()
        ai_cutoff = ai_now - pd.Timedelta(days=15)
        
        ai_df = df.copy() # Use the currently filtered df

        # Helper to count recent events
        def count_recent_events(col_name):
            if col_name in ai_df.columns:
                series = ai_df[col_name]
                if not pd.api.types.is_datetime64_any_dtype(series):
                    series = pd.to_datetime(series, errors='coerce')
                return len(series[series >= ai_cutoff])
            return 0

        cnt_new = count_recent_events('인허가일자')
        cnt_closed = count_recent_events('폐업일자')
        cnt_mod = count_recent_events('최종수정시점')

        user_display_name = st.session_state.user_manager_name or st.session_state.user_branch or "담당자"

        # Generate Message
        guide_msg = f"**{user_display_name}**님, 최근 15일간 데이터 분석 결과입니다.\n\n"
        stats_msg = []
        if cnt_new > 0: stats_msg.append(f"🆕 **신규 인허가 {cnt_new}건**")
        if cnt_closed > 0: stats_msg.append(f"🚫 **폐업 {cnt_closed}건**")
        if cnt_mod > 0: stats_msg.append(f"🔄 **정보 수정 {cnt_mod}건**")

        if not stats_msg:
            guide_msg += "최근 15일간 감지된 주요 변동 사항(신규/폐업/수정)이 없습니다."
        else:
            guide_msg += ", ".join(stats_msg) + "이(가) 감지되었습니다."

        # Recommend Strategy
        recommendation = ""
        if cnt_new > 0:
            recommendation = "💡 **AI 추천**: 신규 인허가 업체는 초기 진입 선점이 가장 중요합니다. 최근 등록된 업체를 **최우선 방문**하여 경쟁사보다 먼저 컨택하세요."
        elif cnt_closed > 0 and cnt_closed >= cnt_mod:
            recommendation = "💡 **AI 추천**: 폐업이 발생하는 구역은 시장 변화의 신호일 수 있습니다. **자산 회수** 기회를 점검하거나, 해당 상권의 경쟁 구도 변화를 분석해보세요."
        elif cnt_mod > 0:
            recommendation = "💡 **AI 추천**: 정보가 수정된 업체는 영업 환경이나 담당자가 변경되었을 가능성이 높습니다. **재컨택**을 통해 변동 사항을 확인하고 관계를 강화하세요."
        else:
            recommendation = "💡 **AI 추천**: 특이사항이 없는 안정적인 시기입니다. **기존 우수 고객(Key Account)** 관리와 잠재 고객 발굴을 위한 정기 순회 활동을 권장합니다."

        st.info(guide_msg + "\n\n" + recommendation, icon="🤖")

    # [DASHBOARD] Branch Status Cards (Hide for Manager role)
    if st.session_state.user_role != 'manager':
        with st.expander("🏭 지사별 현황", expanded=True):
            
            if 'dash_branch' not in st.session_state:
                st.session_state.dash_branch = sorted_branches[0] if sorted_branches else None
                
            # [DESIGN] Modern Grid Layout
            # Grid of 4 columns
            if not sorted_branches:
                st.info("표시할 지사 데이터가 없습니다.")
            else:
                # Prepare grid - Single Row
                n_cols = len(sorted_branches)
                
                # Active Branch Logic (Source of Truth)
                if sel_branch != "전체":
                    raw_dashboard_branch = sel_branch
                else:
                    raw_dashboard_branch = st.session_state.get('sb_branch', "전체")
                sel_dashboard_branch = unicodedata.normalize('NFC', raw_dashboard_branch)

                cols = st.columns(n_cols)
                for idx, b_name in enumerate(sorted_branches):
                    with cols[idx]:
                        # 1. Calculate Stats
                        b_df = base_df[base_df['관리지사'] == b_name]
                        b_total = len(b_df)
                        count_active = len(b_df[b_df['영업상태명'] == '영업/정상'])
                        count_closed = len(b_df[b_df['영업상태명'] == '폐업'])
                        
                        # 2. Determine Style
                        is_selected = (b_name == sel_dashboard_branch)
                        card_class = "dashboard-card branch-active" if is_selected else "dashboard-card"
                        
                        # 3. Render Card HTML
                        disp_name = b_name.replace("지사", "")
                        card_html = f"""
                        <div class="{card_class}">
                            <div class="card-header">
                                {disp_name}
                                <span style="font-size:1.2rem; color:#333;">{b_total}</span>
                            </div>
                            <div class="stat-sub">
                                <span style="color:#2E7D32; font-weight:600;"><span class="status-dot dot-green"></span>{count_active}</span>
                                <span style="color:#F44336; font-weight:600; margin-left:8px;"><span class="status-dot dot-red"></span>{count_closed}</span>
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                        # 4. Interaction Buttons
                        if is_selected:
                            b_c1, b_c2 = st.columns(2)
                            with b_c1:
                                st.button("영업", key=f"btn_act_{b_name}", on_click=update_branch_with_status, args=(b_name, '영업/정상'), use_container_width=True, type="primary")
                            with b_c2:
                                st.button("폐업", key=f"btn_cls_{b_name}", on_click=update_branch_with_status, args=(b_name, '폐업'), use_container_width=True)
                        else:
                            st.button("👆 선택", key=f"btn_sel_{b_name}", on_click=update_branch_state, args=(b_name,), use_container_width=True)
    
    st.markdown("---")
    
    if not base_df.empty:

        # [FIX] Force Source of Truth for Header Text
        if sel_branch != "전체":
            current_br_name = sel_branch
        else:
            current_br_name = sel_dashboard_branch if sel_dashboard_branch and sel_dashboard_branch != "전체" else "전체"
        
        # [FIX] Strict Normalization for Manager Section
        current_br_name = unicodedata.normalize('NFC', current_br_name)
        
        
        with st.expander(f"👤 {current_br_name} 영업담당 현황", expanded=True):
        
            if current_br_name != "전체":
                # [FIX] Decouple from base_df to ensure Header-Content Match
                # We go back to raw_df and filter explicitly for the request branch.
                # This bypasses any Sidebar lag that might have filtered base_df to the wrong branch. (e.g. Gangbuk)
                
                # 1. Start with Raw (but respect Role!)
                mgr_df = raw_df[raw_df['관리지사'].astype(str).apply(lambda x: unicodedata.normalize('NFC', x)) == current_br_name].copy()
                
                # [SECURITY] Re-Apply Manager Filter here because we started from raw_df
                if st.session_state.user_role == 'manager':
                    if st.session_state.user_manager_code:
                        if '영업구역 수정' in mgr_df.columns:
                            mgr_df = mgr_df[mgr_df['영업구역 수정'] == st.session_state.user_manager_code]
                        else:
                            mgr_df = mgr_df[mgr_df['SP담당'] == st.session_state.user_manager_name]
                    elif st.session_state.user_manager_name:
                        mgr_df = mgr_df[mgr_df['SP담당'] == st.session_state.user_manager_name]
                
                # 2. Re-apply Common Filters (Date, Type, Status) if they exist
                # This ensures the manager view is still relevant, just correctly branched.
                if sel_permit_ym != "전체":
                    mgr_df = mgr_df[mgr_df['인허가일자'].dt.strftime('%Y-%m') == sel_permit_ym]
                if sel_close_ym != "전체":
                    mgr_df = mgr_df[mgr_df['폐업일자'].dt.strftime('%Y-%m') == sel_close_ym]
                if sel_status != "전체":
                    mgr_df = mgr_df[mgr_df['영업상태명'] == sel_status]
                if only_hospitals:
                    mask = mgr_df[type_col].astype(str).str.contains('병원|의원', na=False)
                    if '개방서비스명' in mgr_df.columns:
                        mask = mask | mgr_df['개방서비스명'].astype(str).str.contains('병원|의원', na=False)
                    mgr_df = mgr_df[mask]
            else:
                mgr_df = base_df.copy()
                
            manager_items = [] 
            
            if '영업구역 수정' in mgr_df.columns:
                # [FIX] Do NOT dropna. Keep managers even if they lack a code.
                # [FIX] Exclude 'Unassigned' or NaN names explicitly to prevent ghost cards
                temp_g = mgr_df[['영업구역 수정', 'SP담당']].drop_duplicates()
                temp_g = temp_g.dropna(subset=['SP담당'])
                temp_g = temp_g[temp_g['SP담당'] != '미지정']
                
                temp_g['영업구역 수정'] = temp_g['영업구역 수정'].fillna('')
                
                # [UX] Sort by Name first to match Sidebar order, then Code.
                # This makes it easier to find people.
                temp_g = temp_g.sort_values(by=['SP담당', '영업구역 수정'])
                
                for _, r in temp_g.iterrows():
                    code = r['영업구역 수정']
                    name = r['SP담당']
                    # If code exists, show it. If not, just show Name.
                    if code:
                        label = f"{code} ({name})"
                    else:
                        label = name
                        
                    manager_items.append({'label': label, 'code': code if code else None, 'name': name})
                    
            else:
                unique_names = sorted(mgr_df['SP담당'].dropna().unique())
                for name in unique_names:
                    manager_items.append({'label': name, 'code': None, 'name': name})
            
            m_cols = st.columns(8)
            for i, item in enumerate(manager_items):
                col_idx = i % 8
                
                if item['code']:
                    m_sub_df = mgr_df[mgr_df['영업구역 수정'] == item['code']]
                    target_val = item['code']
                    use_code_filter = True
                else:
                    m_sub_df = mgr_df[mgr_df['SP담당'] == item['name']]
                    target_val = item['name']
                    use_code_filter = False
                    
                mgr_label = item['label']
                m_total = len(m_sub_df)
                
                m_active = len(m_sub_df[m_sub_df['영업상태명'] == '영업/정상'])
                m_closed = len(m_sub_df[m_sub_df['영업상태명'] == '폐업'])
                with m_cols[col_idx]:
                      current_sb_manager = st.session_state.get('sb_manager', "전체")
                      is_selected = (current_sb_manager == mgr_label)
                      
                      # [FEATURE] Clickable Zone/Manager Button
                      # User requested to click "Zone Number" to filter.
                      btn_type = "primary" if is_selected else "secondary"
                      
                      unique_key_suffix = item['code'] if item['code'] else item['name']
                      
                      # Determine display label (Name or Code)
                      # If just name, it's name. If Code (Name), maybe just Code?
                      # User said "Zone Number". But keeping full label is safer for mapping.
                      if st.button(mgr_label, key=f"btn_sel_mgr_{unique_key_suffix}", type=btn_type, use_container_width=True, on_click=update_manager_state, args=(mgr_label,)):
                          pass
                      
                      border_color_mgr = "#2E7D32" if is_selected else "#e0e0e0"
                      bg_color_mgr = "#e8f5e9" if is_selected else "#ffffff"
                      
                      # Card without the Title (since Button acts as title)
                      manager_card_html = f'<div class="metric-card" style="margin-top:-5px; margin-bottom:4px; padding: 10px 5px; text-align: center; border: 2px solid {border_color_mgr}; border-top: none; border-radius: 0 0 8px 8px; background-color: {bg_color_mgr};"><div class="metric-value" style="color:#333; font-size: 1.1rem; font-weight:bold;">{m_total:,}</div><div class="metric-sub" style="font-size:0.75rem; margin-top:4px;"><span style="color:#2E7D32">영업 {m_active}</span> / <span style="color:#d32f2f">폐업 {m_closed}</span></div></div>'
                      st.markdown(manager_card_html, unsafe_allow_html=True)
                      
                      # [UX] Only show Action Buttons if Selected
                      if is_selected:
                          m_c1, m_c2 = st.columns(2)
                          with m_c1:
                              st.button("영업", key=f"btn_mgr_active_{unique_key_suffix}", on_click=update_manager_with_status, args=(mgr_label, '영업/정상'), use_container_width=True)
                          with m_c2:
                              st.button("폐업", key=f"btn_mgr_closed_{unique_key_suffix}", on_click=update_manager_with_status, args=(mgr_label, '폐업'), use_container_width=True)


    st.markdown("---")

    # [LAYOUT] Tab Structure Re-implementation for Compatibility (v1.31.0)
    # Using a high-persistence Radio Navigation to prevent Tab Jumping
    nav_labels = ["🗺️ 지도 & 분석", "📈 상세통계", "📱 모바일 리스트", "📋 데이터 그리드", "🗣️ 관리자에게 요청하기", "📝 활동 이력"]
    if st.session_state.user_role == 'admin':
        nav_labels.append("👁️ 모니터링")
        
    # CSS for Tab-like Radio Buttons
    st.markdown("""
    <style>
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex;
            flex-direction: row;
            justify-content: flex-start;
            gap: 10px;
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 12px;
            border: 1px solid #ddd;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label {
            background-color: white;
            padding: 5px 15px;
            border-radius: 8px;
            border: 1px solid #ddd;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
            margin: 0;
        }
    </style>
    """, unsafe_allow_html=True)

    active_nav = st.radio("Navigation", nav_labels, horizontal=True, label_visibility="collapsed", key="v131_main_nav")
    
    # [LAYOUT] Conditional Tab Execution (v1.31.0 Persistence Fix)
    
    # [TAB] Activity History
    if active_nav == "📝 활동 이력":
        st.subheader("📝 활동 이력 관리")
        
        # [SECURITY] Role-based access control
        if st.session_state.user_role == 'admin':
            # Admin sees all reports
            all_reports = activity_logger.get_visit_reports(limit=200)
            st.caption("🔓 관리자 권한: 전체 활동 이력 조회 (방문, 상담중, 관심 등 모든 기록)")
        elif st.session_state.user_role == 'manager':
            # Manager sees only their own reports
            user_name = st.session_state.get('user_manager_name')
            all_reports = activity_logger.get_visit_reports(user_name=user_name, limit=200)
            st.caption(f"🔒 담당자 '{user_name}' 님의 활동 이력 (방문, 상담, 관심 등)")
        elif st.session_state.user_role == 'branch':
            # Branch user sees only their branch reports
            user_branch = st.session_state.get('user_branch')
            all_reports = activity_logger.get_visit_reports(user_branch=user_branch, limit=200)
            st.caption(f"🔒 '{user_branch}' 지사의 활동 이력 (방문, 상담, 관심 등)")
        else:
            # Unknown role - no access
            all_reports = []
            st.warning("⚠️ 권한이 없습니다.")
        
        if all_reports:
            # [NEW] Filter Section
            st.markdown("### 🔍 필터")
            col_f1, col_f2, col_f3 = st.columns(3)
            
            with col_f1:
                branches = ["전체"] + sorted(list(set([r.get('user_branch', '') for r in all_reports if r.get('user_branch')])))
                sel_branch = st.selectbox("🏢 지사", branches, key="visit_branch_filter")
            
            with col_f2:
                managers = ["전체"] + sorted(list(set([r.get('user_name', '') for r in all_reports if r.get('user_name')])))
                sel_manager = st.selectbox("👤 담당자", managers, key="visit_manager_filter")
            
            with col_f3:
                period_opts = ["전체", "최근 7일", "최근 30일", "최근 90일"]
                sel_period = st.selectbox("📅 기간", period_opts, key="visit_period_filter")
            
            # Apply filters
            filtered_reports = all_reports
            
            # Branch filter
            if sel_branch != "전체":
                filtered_reports = [r for r in filtered_reports if r.get('user_branch') == sel_branch]
            
            # Manager filter
            if sel_manager != "전체":
                filtered_reports = [r for r in filtered_reports if r.get('user_name') == sel_manager]
            
            # Period filter
            if sel_period != "전체":
                from datetime import datetime, timedelta
                days_map = {"최근 7일": 7, "최근 30일": 30, "최근 90일": 90}
                cutoff_days = days_map[sel_period]
                cutoff_date = datetime.now() - timedelta(days=cutoff_days)
                
                filtered_reports = [
                    r for r in filtered_reports 
                    if datetime.strptime(r.get('timestamp', '2020-01-01 00:00:00'), "%Y-%m-%d %H:%M:%S") >= cutoff_date
                ]
            
            st.markdown(f"**📋 조회 결과: {len(filtered_reports)}건**")
            st.divider()
            
            # [IMPROVED] Card-style layout
            if filtered_reports:
                for idx, rep in enumerate(filtered_reports):
                    # Card header with status badge
                    status_badge = rep.get('resulting_status', '')
                    header = f"**{idx+1}.** 🏢 {rep.get('user_branch', 'N/A')} | 👤 {rep.get('user_name')} | 📅 {rep.get('timestamp')} | 상태: {status_badge}"
                    
                    with st.expander(header, expanded=False):
                        # Content display
                        st.markdown("**📝 방문 내용:**")
                        st.info(rep.get('content', ''))
                        
                        # Media display
                        media_col1, media_col2 = st.columns(2)
                        
                        with media_col1:
                            if rep.get("audio_path"):
                                audio_p = activity_logger.get_media_path(rep.get("audio_path"))
                                if audio_p and os.path.exists(audio_p):
                                    st.markdown("**🎤 음성 녹음:**")
                                    st.audio(audio_p)
                        
                        with media_col2:
                            if rep.get("photo_path"):
                                photo_p = activity_logger.get_media_path(rep.get("photo_path"))
                                if photo_p and os.path.exists(photo_p):
                                    try:
                                        st.markdown("**📸 현장 사진:**")
                                        st.image(photo_p, use_container_width=True)
                                    except:
                                        st.caption(f"⚠️ 이미지 로드 실패: {rep.get('photo_path')}")
                        
                        st.divider()
                        
                        # [NEW] Action buttons in columns
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        
                        with btn_col1:
                            if st.button("✏️ 내용 수정", key=f"edit_content_{rep['id']}", use_container_width=True):
                                st.session_state[f"edit_mode_{rep['id']}"] = True
                        
                        with btn_col2:
                            if st.button("📸 사진 추가", key=f"add_photo_{rep['id']}", use_container_width=True):
                                st.session_state[f"photo_mode_{rep['id']}"] = True
                        
                        with btn_col3:
                            if st.button("🔄 상태 변경", key=f"status_change_{rep['id']}", use_container_width=True):
                                st.session_state[f"status_mode_{rep['id']}"] = True
                        
                        # [FEATURE] Edit mode - Content
                        if st.session_state.get(f"edit_mode_{rep['id']}", False):
                            with st.form(key=f"form_edit_{rep['id']}"):
                                st.caption("📝 방문 내용을 수정하세요")
                                new_text = st.text_area("내용", value=rep.get("content", ""), height=150)
                                
                                col_save, col_cancel = st.columns(2)
                                if col_save.form_submit_button("💾 저장", use_container_width=True):
                                    succ, msg = activity_logger.update_visit_report(rep['id'], new_text, None)
                                    if succ:
                                        st.success("✅ 수정되었습니다!")
                                        st.session_state[f"edit_mode_{rep['id']}"] = False
                                        st.rerun()
                                    else:
                                        st.error(f"❌ 오류: {msg}")
                                
                                if col_cancel.form_submit_button("취소", use_container_width=True):
                                    st.session_state[f"edit_mode_{rep['id']}"] = False
                                    st.rerun()
                        
                        # [FEATURE] Photo mode
                        if st.session_state.get(f"photo_mode_{rep['id']}", False):
                            with st.form(key=f"form_photo_{rep['id']}"):
                                st.caption("📸 사진을 추가하세요")
                                new_photo = st.file_uploader("사진 선택", type=['jpg', 'png', 'jpeg'], key=f"uploader_{rep['id']}")
                                
                                col_save, col_cancel = st.columns(2)
                                if col_save.form_submit_button("💾 저장", use_container_width=True):
                                    if new_photo:
                                        succ, msg = activity_logger.update_visit_report(rep['id'], None, new_photo)
                                        if succ:
                                            st.success("✅ 사진이 추가되었습니다!")
                                            st.session_state[f"photo_mode_{rep['id']}"] = False
                                            st.rerun()
                                        else:
                                            st.error(f"❌ 오류: {msg}")
                                    else:
                                        st.warning("사진을 선택해주세요")
                                
                                if col_cancel.form_submit_button("취소", use_container_width=True):
                                    st.session_state[f"photo_mode_{rep['id']}"] = False
                                    st.rerun()
                        
                        # [FEATURE] Status change mode
                        if st.session_state.get(f"status_mode_{rep['id']}", False):
                            with st.form(key=f"form_status_{rep['id']}"):
                                st.caption("🔄 활동 상태를 변경하세요")
                                status_opts = list(activity_logger.ACTIVITY_STATUS_MAP.values())
                                current_status = rep.get('resulting_status', '')
                                current_idx = status_opts.index(current_status) if current_status in status_opts else 0
                                
                                new_status = st.selectbox("새 상태", status_opts, index=current_idx)
                                status_note = st.text_area("변경 사유 (선택)", placeholder="상태 변경 사유를 입력하세요")
                                
                                col_save, col_cancel = st.columns(2)
                                if col_save.form_submit_button("💾 저장", use_container_width=True):
                                    # Update activity status
                                    record_key = rep.get('record_key')
                                    current_user = st.session_state.get('user_manager_name') or st.session_state.get('user_branch') or '관리자'
                                    
                                    activity_logger.save_activity_status(
                                        record_key=record_key,
                                        status=new_status,
                                        notes=status_note or rep.get('content', ''),
                                        user_name=current_user
                                    )
                                    
                                    st.success(f"✅ 상태가 '{new_status}'로 변경되었습니다!")
                                    st.session_state[f"status_mode_{rep['id']}"] = False
                                    st.cache_data.clear()
                                    st.rerun()
                                
                                if col_cancel.form_submit_button("취소", use_container_width=True):
                                    st.session_state[f"status_mode_{rep['id']}"] = False
                                    st.rerun()
            else:
                st.info("선택한 조건에 맞는 방문 기록이 없습니다.")
        else:
            st.info("작성된 방문 리포트가 없습니다.")
    
    # [TAB] Admin Monitoring Dashboard (Only for Admin)
    if st.session_state.user_role == 'admin' and active_nav == "👁️ 모니터링":
        st.subheader("👁️ 시스템 활동 모니터링")
        
        # Period selection
        col_p1, col_p2 = st.columns([3, 1])
        with col_p1:
            period_days = st.selectbox(
                "📅 조회 기간",
                [7, 30, 90],
                format_func=lambda x: f"최근 {x}일",
                key="monitor_period"
            )
        with col_p2:
            if st.button("🔄 새로고침", use_container_width=True):
                st.rerun()
        
        st.divider()
        
        # Get usage statistics
        usage_stats = usage_logger.get_usage_stats(days=period_days)
        
        # Top metrics
        st.markdown("### 📊 전체 활동 요약")
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric("총 활동 수", f"{usage_stats['total_actions']:,}건")
        with metric_col2:
            st.metric("활성 사용자", f"{usage_stats['unique_users']}명")
        with metric_col3:
            st.metric("활성 지사", f"{usage_stats['unique_branches']}개")
        with metric_col4:
            visit_reports = activity_logger.get_visit_reports(limit=1000)
            st.metric("방문 리포트", f"{len(visit_reports)}건")
        
        st.divider()
        
        # User activity table
        st.markdown("### 👥 사용자별 활동")
        
        if usage_stats['top_users']:
            # Create dataframe from top_users
            top_users_df = pd.DataFrame(usage_stats['top_users'])
            top_users_df.columns = ['사용자명', '지사', '역할', '활동수']
            top_users_df = top_users_df.sort_values('활동수', ascending=False)
            
            # Display as formatted table
            st.dataframe(
                top_users_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Bar chart
            fig_users = alt.Chart(top_users_df.head(10)).mark_bar().encode(
                x=alt.X('활동수:Q', title='활동 횟수'),
                y=alt.Y('사용자명:N', sort='-x', title='사용자'),
                color=alt.Color('지사:N', legend=alt.Legend(title="지사")),
                tooltip=['사용자명', '지사', '역할', '활동수']
            ).properties(height=400)
            
            st.altair_chart(fig_users, use_container_width=True)
        else:
            st.info("활동 데이터가 없습니다.")
        
        st.divider()
        
        # Branch activity
        col_b1, col_b2 = st.columns(2)
        
        with col_b1:
            st.markdown("### 🏢 지사별 활동")
            if usage_stats['actions_by_branch']:
                branch_df = pd.DataFrame(
                    list(usage_stats['actions_by_branch'].items()),
                    columns=['지사', '활동수']
                ).sort_values('활동수', ascending=False)
                
                st.dataframe(branch_df, use_container_width=True, hide_index=True)
            else:
                st.info("데이터 없음")
        
        with col_b2:
            st.markdown("### 📋 활동 유형별")
            if usage_stats['actions_by_type']:
                action_df = pd.DataFrame(
                    list(usage_stats['actions_by_type'].items()),
                    columns=['유형', '횟수']
                ).sort_values('횟수', ascending=False)
                
                st.dataframe(action_df, use_container_width=True, hide_index=True)
            else:
                st.info("데이터 없음")
        
        st.divider()
        
        # Visit report statistics by user
        st.markdown("### 📝 방문 리포트 현황")
        
        if visit_reports:
            # Group by user
            visit_by_user = {}
            for rep in visit_reports:
                u_name = rep.get('user_name', 'Unknown')
                u_branch = rep.get('user_branch', '')
                
                if u_name not in visit_by_user:
                    visit_by_user[u_name] = {'branch': u_branch, 'count': 0}
                visit_by_user[u_name]['count'] += 1
            
            # Convert to DataFrame
            visit_stats_df = pd.DataFrame([
                {'사용자명': k, '지사': v['branch'], '방문 리포트 수': v['count']}
                for k, v in visit_by_user.items()
            ]).sort_values('방문 리포트 수', ascending=False)
            
            col_v1, col_v2 = st.columns([2, 1])
            
            with col_v1:
                st.dataframe(visit_stats_df, use_container_width=True, hide_index=True)
            
            with col_v2:
                # Pie chart
                fig_pie = alt.Chart(visit_stats_df.head(10)).mark_arc().encode(
                    theta='방문 리포트 수:Q',
                    color='사용자명:N',
                    tooltip=['사용자명', '지사', '방문 리포트 수']
                ).properties(height=300)
                
                st.altair_chart(fig_pie, use_container_width=True)
        else:
            st.info("방문 리포트가 없습니다.")
        
        st.divider()
        
        # Recent activity timeline
        st.markdown("### ⏱️ 최근 활동 타임라인")
        
        recent_logs = usage_logger.get_usage_logs(days=period_days)
        
        if recent_logs:
            # Show last 30 activities
            for log in sorted(recent_logs, key=lambda x: x['timestamp'], reverse=True)[:30]:
                timestamp = log['timestamp']
                user_name = log['user_name']
                branch = log['user_branch']
                action = log['action']
                
                st.caption(f"🕐 {timestamp} | 👤 {user_name} ({branch}) - **{action}**")
        else:
            st.info("활동 로그가 없습니다.")



    # [TAB] Map & Analysis
    if active_nav == "🗺️ 지도 & 분석":
        # Log tab access
        
        with st.expander("🗺️ 조건조회", expanded=True):
            # Marker for Mobile Visibility Control
            st.markdown('<div id="mobile-filter-marker"></div>', unsafe_allow_html=True)
            # st.subheader("🗺️ 조건조회")
            
            # [MOVED] Global Date Range Filter
            st.markdown("##### 🕵️ 기간 조회 (최종수정일 기준)")
            st.caption("전체 탭(지도, 통계, 리스트)에 공통 적용됩니다.")
            st.date_input(
                "조회 기간 선택",
                value=(),
                label_visibility="collapsed",
                key="global_date_range"
            )
            st.divider()

            # [MOVED] AI Analysis Block removed from here


            # [FEATURE] Condition View Toolbar (Quick Filters)
            # [UX] Mobile-Friendly Layout: Strict 2x3 Grid
            
            # [NEW] Expert Feature: Sales Opportunity Discovery Mode
            st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)
            opp_mode = st.toggle("🚀 영업기회 발굴 모드 (최근 15일 신규/폐업 감지)", value=False, help="최근 15일 이내의 신규 인허가 또는 폐업 리스트만 집중적으로 보여줍니다. 빠른 기회 포착을 위해 사용하세요.")
            
            if opp_mode:
                st.caption("✅ **발굴 모드 활성화됨**: 최근 15일간의 변화(신규/폐업)만 필터링합니다.")
                # Force flags for logic downstream or calculate mask immediately
                q_new = False # Ignore manual checkbox visually (or logical override)
                q_closed = False 
            else:
                # Row 1: Date Filters
                st.markdown("<div style='margin-bottom: -10px;'></div>", unsafe_allow_html=True) # Spacer
                c_q_r1_1, c_q_r1_2 = st.columns(2)
                with c_q_r1_1: q_new = st.checkbox("🆕 신규(15일)", value=False, help="최근 15일 이내 개업(인허가)된 건")
                with c_q_r1_2: q_closed = st.checkbox("🚫 폐업(15일)", value=False, help="최근 15일 이내 폐업된 건")

            # Row 2: Property Filters
            c_q_r2_1, c_q_r2_2 = st.columns(2)
            with c_q_r2_1: q_hosp = st.checkbox("🏥 병원만", value=False)
            with c_q_r2_2: q_large = st.checkbox("🏗️ 100평↑", value=False)

            # remove divider to save space
            
            # [FIX] CRITICAL: Use base_df (filtered by Sidebar) instead of raw df
            # This ensures Map respects Branch/Manager/Address filters from Sidebar.
            map_df_base = base_df.dropna(subset=['lat', 'lon']).copy()

            # [FEATURE] Apply Quick Filters (Pre-Filtering for Dynamic Dropdowns)
            # 1. Date Filters (OR Logic: New OR Closed)
            date_mask = pd.Series([False] * len(map_df_base), index=map_df_base.index)
            has_date_filter = False

            if opp_mode:
                # [LOGIC] Opportunity Mode: 15 Days New OR Closed
                has_date_filter = True
                
                # New (15 Days)
                if '인허가일자' in map_df_base.columns:
                     map_df_base['인허가일자'] = pd.to_datetime(map_df_base['인허가일자'], errors='coerce')
                     cutoff_opp = pd.Timestamp.now() - pd.Timedelta(days=15)
                     date_mask = date_mask | (map_df_base['인허가일자'] >= cutoff_opp)
                     
                # Closed (15 Days)
                if '폐업일자' in map_df_base.columns:
                     map_df_base['폐업일자'] = pd.to_datetime(map_df_base['폐업일자'], errors='coerce')
                     cutoff_opp = pd.Timestamp.now() - pd.Timedelta(days=15)
                     date_mask = date_mask | (map_df_base['폐업일자'] >= cutoff_opp)
                     
            else:
                # Standard Logic
                if q_new:
                     has_date_filter = True
                     if '인허가일자' in map_df_base.columns:
                         map_df_base['인허가일자'] = pd.to_datetime(map_df_base['인허가일자'], errors='coerce')
                         # [FIX] Changed to 15 days
                         cutoff_new = pd.Timestamp.now() - pd.Timedelta(days=15)
                         
                         # [LOGIC] "New" implies Sales Opportunity. Exclude "Closed" status to remove noise.
                         # User Complaint: "New selected but Closed appears" -> Filter out '폐업' for New items.
                         new_cond = (map_df_base['인허가일자'] >= cutoff_new)
                         if '영업상태명' in map_df_base.columns:
                             new_cond = new_cond & (map_df_base['영업상태명'] != '폐업')
                             
                         date_mask = date_mask | new_cond
    
                if q_closed:
                     has_date_filter = True
                     if '폐업일자' in map_df_base.columns:
                         map_df_base['폐업일자'] = pd.to_datetime(map_df_base['폐업일자'], errors='coerce')
                         # [FIX] Changed to 15 days
                         cutoff_closed = pd.Timestamp.now() - pd.Timedelta(days=15)
                         date_mask = date_mask | (map_df_base['폐업일자'] >= cutoff_closed)

            if has_date_filter:
                map_df_base = map_df_base[date_mask]

            # 2. Property Filters (AND Logic)
            if q_hosp:
                 if '업태구분명' in map_df_base.columns:
                     map_df_base = map_df_base[map_df_base['업태구분명'].astype(str).str.contains('병원|의원', na=False)]

            if q_large:
                 if '소재지면적' in map_df_base.columns:
                     map_df_base['소재지면적_ad'] = pd.to_numeric(map_df_base['소재지면적'], errors='coerce').fillna(0)
                     map_df_base = map_df_base[map_df_base['소재지면적_ad'] >= 330.0]

            # Reduced spacing here

            # [UX] Mobile-Friendly Layout: 2x2 Grid for Selectboxes
            c_f_r1_1, c_f_r1_2 = st.columns(2)

            # [Dynamic Dropdowns]
            # Logic: Type Selection should filter Region/Manager lists.
            # We need to peek at the current 'map_biz_type' from session state if available
            current_map_type = st.session_state.get('map_biz_type', "전체")

            # [REMOVED] Local Branch/Manager Dropdowns (User Request)
            # Defaulting to "전체" to maintain logic flow
            sel_map_region = "전체"
            sel_map_sales = "전체"
            
            # Placeholder for layout if needed, or just remove columns usage
            # Filter base for options based on Type (if selected)
            options_source_df = map_df_base.copy()
            if current_map_type != "전체" and '업태구분명' in options_source_df.columns:
                options_source_df = options_source_df[options_source_df['업태구분명'] == current_map_type]

            # Re-using columns for Type logic or just skipping
            # with c_f_r1_1: ... removed
            # with c_f_r1_2: ... removed

            c_f_r2_1, c_f_r2_2 = st.columns(2)
            with c_f_r2_1:
                # Business Type Options - Should these be filtered by Region?
                # User asked for "Type selection -> Dynamic".
                # Usually, Type list comes from the Quick-filtered Base.
                map_type_col = '업태구분명' if '업태구분명' in map_df_base.columns else map_df_base.columns[0]
                try:
                    # Type options come from the filters BEFORE Type selection (to allow changing type)
                    # But should reflect Region selection? "Dynamic" implies full cross-filtering.
                    # Let's try to filter Type options by Region if Region is selected.
                    type_source_df = map_df_base
                    if sel_map_region != "전체":
                        type_source_df = type_source_df[type_source_df['관리지사'] == sel_map_region]

                    map_type_opts = ["전체"] + sorted(list(type_source_df[map_type_col].dropna().unique()))
                except:
                    map_type_opts = ["전체"]
                sel_map_type = st.selectbox("업종(업태)", map_type_opts, key="map_biz_type")

            with c_f_r2_2:
                 # Status Dropdown (Public)
                 map_status_opts = ["전체", "영업/정상", "폐업"]
                 sel_map_status = st.selectbox("영업상태 (공공)", map_status_opts, key="map_status_filter")
            
            # [FEATURE] Activity Status Filter (Internal)
            st.markdown("##### 📍 활동 상태별 필터")
            
            # Using st.pills for cleaner UI (Streamlit 1.40+)
            activity_options = list(activity_logger.ACTIVITY_STATUS_MAP.values()) + ["⭐ 관심"]

            # st.pills handles selection state automatically via key
            # It returns the list of selected options
            sel_act_statuses = st.pills(
                "활동 상태 선택",
                options=activity_options,
                selection_mode="multi",
                key="map_sel_act_statuses",
                label_visibility="collapsed"
            )

            # Final Filtering
            map_df = map_df_base.copy()
            if sel_map_region != "전체": map_df = map_df[map_df['관리지사'] == sel_map_region]
            if sel_map_sales != "전체": map_df = map_df[map_df['SP담당'] == sel_map_sales]
            if sel_map_type != "전체": map_df = map_df[map_df['업태구분명'] == sel_map_type]
            if sel_map_status != "전체": map_df = map_df[map_df['영업상태명'] == sel_map_status]
            
            # Apply activity status filter
            if sel_act_statuses:
                mask = pd.Series([False] * len(map_df), index=map_df.index)
                for s in sel_act_statuses:
                    if s == "⭐ 관심":
                        mask = mask | map_df['활동진행상태'].astype(str).str.contains("관심", na=False)
                    else:
                        mask = mask | (map_df['활동진행상태'] == s)
                map_df = map_df[mask]
            
            # [OVERHAUL] Pre-calculate record_key for Map
            # This ensures the key sent from Map matches the key used in Grid
            if not map_df.empty:
                map_df['record_key'] = map_df.apply(lambda row: utils.generate_record_key(row.get('사업장명'), row.get('소재지전체주소')), axis=1)

            st.markdown(f"**📍 조회된 업체**: {len(map_df):,} 개")

            # [FEATURE] Visible Filter Summary for Verification
            filter_summary = []
            if sel_map_region != "전체": filter_summary.append(f"지사:{sel_map_region}")
            if sel_map_sales != "전체": filter_summary.append(f"담당:{sel_map_sales}")
            if sel_map_type != "전체": filter_summary.append(f"업종:{sel_map_type}")
            if sel_map_status != "전체": filter_summary.append(f"상태:{sel_map_status}")

            if filter_summary:
                st.caption(f"ℹ️ 적용된 필터: {', '.join(filter_summary)}")

            # Reduced Spacing

            if len(map_df) > 5000:
                st.info(f"ℹ️ 데이터가 많아({len(map_df):,}건) 클러스터링되어 표시됩니다. 지도를 확대하면 개별 마커가 보입니다.")

        st.markdown("#### 🗺️ 지도")
        
        # [NEW] Expert Feat 1: AI Scoring
        if not map_df.empty:
            map_df = calculate_ai_scores(map_df)
            
        # [NEW] Expert Feat 2: Heatmap Toggle
        use_heatmap = st.checkbox("🌡️ 상권 밀집도(히트맵) 보기", value=False)
        
        # Prepare User Context for Session Persistence
        user_context = {
            "user_role": st.session_state.get("user_role", ""),
            "user_branch": st.session_state.get("user_branch", ""),
            "user_manager_name": st.session_state.get("user_manager_name", ""),
            "user_manager_code": st.session_state.get("user_manager_code", ""),
            "admin_auth": str(st.session_state.get("admin_auth", 'false')).lower()
        }
        
        if not map_df.empty:
            if kakao_key:
                # Pass heatmap flag to visualizer
                map_visualizer.render_kakao_map(map_df, kakao_key, use_heatmap=use_heatmap, user_context=user_context)
            else:
                map_visualizer.render_folium_map(map_df, use_heatmap=use_heatmap, user_context=user_context) # [FIX] Correct function name
        else:
            st.warning("표시할 데이터가 없습니다.")
            
    # [TAB] Detailed Stats
    if active_nav == "📈 상세통계":
        st.subheader("📈 다차원 상세 분석")
        
        # [FEATURE] 15-Day Daily Trend Chart
        st.markdown("##### 📅 최근 15일 영업/폐업 추이")
        try:
            # 1. Prepare Data
            trend_end_date = pd.Timestamp.now().normalize()
            trend_start_date = trend_end_date - pd.Timedelta(days=14) # 15 days inclusive: [Today-6, Today]
            
            trend_data = []
            
            # Open (In-license)
            if '인허가일자' in base_df.columns:
                 open_7d = base_df[
                     (base_df['인허가일자'] >= trend_start_date) & 
                     (base_df['인허가일자'] <= trend_end_date + pd.Timedelta(days=1)) 
                 ].copy()
                 if not open_7d.empty:
                     daily_open = open_7d.groupby(open_7d['인허가일자'].dt.date).size().reset_index(name='count')
                     daily_open['status'] = '영업'
                     daily_open.rename(columns={'인허가일자': 'date'}, inplace=True)
                     trend_data.append(daily_open)
            
            # Closed
            if '폐업일자' in base_df.columns:
                 close_7d = base_df[
                     (base_df['폐업일자'] >= trend_start_date) & 
                     (base_df['폐업일자'] <= trend_end_date + pd.Timedelta(days=1))
                 ].copy()
                 if not close_7d.empty:
                     daily_close = close_7d.groupby(close_7d['폐업일자'].dt.date).size().reset_index(name='count')
                     daily_close['status'] = '폐업'
                     daily_close.rename(columns={'폐업일자': 'date'}, inplace=True)
                     trend_data.append(daily_close)
            
            if trend_data:
                trend_df = pd.concat(trend_data, ignore_index=True)
                trend_df['date'] = pd.to_datetime(trend_df['date'])
                # [FIX] Create formatted string for x-axis to prevent duplicates (Altair Ordinal Issue)
                trend_df['date_str'] = trend_df['date'].dt.strftime('%m-%d')
                
                # [FIX] Explicitly define sort order using a list for Ordinal Axis
                # 'sort="date"' caused an error because "date" is not an encoding channel or "ascending"/"descending".
                # Providing the sorted array of strings guarantees correct order.
                sorted_date_strs = sorted(trend_df['date'].unique())
                sorted_date_strs = [pd.Timestamp(d).strftime('%m-%d') for d in sorted_date_strs]

                # 2. Visualize
                trend_chart = alt.Chart(trend_df).mark_bar().encode(
                    x=alt.X('date_str:O', sort=sorted_date_strs, axis=alt.Axis(title='날짜 (2026)')), # Explicit sort list
                    y=alt.Y('count:Q', title='건수'),
                    color=alt.Color('status:N', 
                                    scale=alt.Scale(domain=['영업', '폐업'], range=['#AED581', '#EF9A9A']), 
                                    legend=alt.Legend(title="구분")),
                    tooltip=['date_str', 'status', 'count']
                ).properties(
                    height=200
                )
                
                # Add text labels on bars
                text = trend_chart.mark_text(dy=-5, fontSize=10).encode(
                    text='count:Q'
                )
                
                st.altair_chart(trend_chart + text, use_container_width=True)
            else:
                st.info("최근 7일간 변동 데이터가 없습니다.")
                
        except Exception as e:
            st.error(f"차트 생성 중 오류가 발생했습니다: {e}")
            
        st.markdown("---")
        
        now = datetime.now()
        if '인허가일자' in df.columns:
            valid_dates = df.dropna(subset=['인허가일자']).copy()
            if not valid_dates.empty:
                if not pd.api.types.is_datetime64_any_dtype(valid_dates['인허가일자']):
                     valid_dates['인허가일자'] = pd.to_datetime(valid_dates['인허가일자'], errors='coerce')
                
                valid_dates['business_years'] = (now - valid_dates['인허가일자']).dt.days / 365.25
                avg_age = valid_dates['business_years'].mean()
            else:
                avg_age = 0
        else:
            avg_age = 0
            
        if '평수' not in df.columns:
             if '소재지면적' in df.columns:
                 df['평수'] = pd.to_numeric(df['소재지면적'], errors='coerce').fillna(0) / 3.3058
             else:
                 df['평수'] = 0
        
        avg_area = df['평수'].mean()
        
        def extract_dong(addr):
             if pd.isna(addr): return "미상"
             tokens = addr.split()
             for t in tokens:
                 if t.endswith('동') or t.endswith('읍') or t.endswith('면'):
                     return t
             return "기타"
             
        df['dong'] = df['소재지전체주소'].astype(str).apply(extract_dong)
        top_dong = df['dong'].value_counts().idxmax() if not df.empty else "-"
        
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("평균 업력 (운영기간)", f"{avg_age:.1f}년")
        with m2: st.metric("평균 매장 규모", f"{avg_area:.1f}평")
        with m3: st.metric("최대 밀집 지역", top_dong)
        with m4: st.metric("현재 조회수", f"{len(df):,}개")
        
        st.divider()
        
        # [UX] Boxed Layout for Branch Status with Clean Tone
        with st.container(border=True):
            st.markdown("##### 🏢 지사별 업체 분포 (선택된 영업상태 기준)")
            
            if not df.empty:
                # [MODIFIED] Single-row layout for Detailed Branch Distribution
                st.markdown("**지사별 점유율 (Rank)**")
                bar_chart_base = alt.Chart(df).encode(
                    x=alt.X("관리지사", sort="-y", title=" "),
                    y=alt.Y("count()", title="업체 수"),
                    color=alt.Color("관리지사", legend=None), 
                    tooltip=["관리지사", "count()"]
                ).properties(height=250)
                
                bar_chart = bar_chart_base.mark_bar(cornerRadius=3)
                bar_text = bar_chart_base.mark_text(align='center', dy=-10, color='black').encode(
                    text=alt.Text("count()", format=",.0f")
                )
                
                final_rank_chart = (bar_chart + bar_text).configure_view(stroke=None).configure(background='#F8F9FA')
                st.altair_chart(final_rank_chart, use_container_width=True, theme=None)
                
                st.divider()
                
                # [MODIFIED] Full-width Stacked Chart
                st.markdown("**지사별 영업상태 누적 (Stacked)**")
                df_stacked = df[df['영업상태명'].isin(['영업/정상', '폐업'])]
                
                bar_base = alt.Chart(df_stacked).encode(
                    x=alt.X("관리지사", sort=custom_branch_order, title=None),
                    y=alt.Y("count()", title="업체 수"),
                    color=alt.Color("영업상태명", scale=alt.Scale(domain=['영업/정상', '폐업'], range=['#2E7D32', '#d32f2f']), legend=alt.Legend(title="상태")),
                    tooltip=["관리지사", "영업상태명", "count()"]
                ).properties(height=250)
                
                stacked_bar = bar_base.mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                final_stack_chart = stacked_bar.interactive().configure_view(stroke=None).configure(background='#F8F9FA')
                st.altair_chart(final_stack_chart, use_container_width=True, theme=None)
            
                st.markdown("##### 👤 영업담당별 실적 Top 10")
                mgr_counts = df['SP담당'].value_counts().head(10).reset_index()
                mgr_counts.columns = ['SP담당', 'count']
                
                mgr_chart = alt.Chart(mgr_counts).mark_bar(color="#4DB6AC", cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
                    x=alt.X("count", title="업체 수"),
                    y=alt.Y("SP담당", sort='-x', title=None),
                    tooltip=["SP담당", "count"]
                ).properties(height=200)
                
                mgr_text = mgr_chart.mark_text(dx=5, align='left', color='black').encode(
                    text=alt.Text("count", format=",.0f")
                )
                
                st.altair_chart((mgr_chart + mgr_text).configure_view(stroke=None).configure(background='#F8F9FA'), use_container_width=True, theme=None)
            
            else:
                st.info("조건에 맞는 데이터가 없습니다.")

        st.divider()
        st.markdown("##### 🏘️ 행정동(읍/면/동)별 상위 TOP 20")
        dong_counts = df['dong'].value_counts().reset_index()
        dong_counts.columns = ['행정구역', '업체수']
        
        top20 = dong_counts.head(20)
        
        dong_chart = alt.Chart(top20).mark_bar(color="#7986CB").encode(
            x=alt.X('업체수', title="업체 수"),
            y=alt.Y('행정구역', sort='-x', title=None),
            tooltip=['행정구역', '업체수']
        )
        
        dong_text = dong_chart.mark_text(dx=5, align='left', color='black').encode(
             text=alt.Text("업체수", format=",.0f")
        )
        
        st.altair_chart((dong_chart + dong_text), use_container_width=True)

    # [TAB] Mobile List
    if active_nav == "📱 모바일 리스트":
        st.subheader("📱 영업 공략 리스트")
        
        keyword = st.text_input("검색", placeholder="업체명 또는 주소...")
            
        # Use base_df instead of df to show all statuses (including closed)
        m_df = base_df.copy()
        
        if keyword: m_df = m_df[m_df['사업장명'].str.contains(keyword, na=False) | m_df['소재지전체주소'].str.contains(keyword, na=False)]
        
        st.caption(f"조회 결과: {len(m_df):,}건")
        
        ITEMS_PER_PAGE = 50 
        if 'page' not in st.session_state: st.session_state.page = 0
        total_pages = max(1, (len(m_df)-1)//ITEMS_PER_PAGE + 1)
        
        start = st.session_state.page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_df = m_df.iloc[start:end]
        
        col_p, col_n = st.columns([1,1])
        with col_p:
            if st.button("Previous Pages") and st.session_state.page > 0:
                st.session_state.page -= 1
                st.rerun()
        with col_n:
            if st.button("Next Pages"):
                st.session_state.page += 1
                st.rerun()
        # [FEATURE] Responsive 6-Column Grid
        row_step = 6
        for i in range(0, len(page_df), row_step):
            cols = st.columns(row_step)
            for j in range(row_step):
                if i + j < len(page_df):
                    idx = page_df.index[i + j]
                    row = page_df.iloc[i + j]
                    
                    with cols[j]:
                        status_cls = "status-open" if row['영업상태명'] == '영업/정상' else "status-closed"
                        tel = row['소재지전화'] if pd.notna(row['소재지전화']) else ""
                        
                        def fmt_date(d):
                            if pd.isna(d): return ""
                            try:
                                return d.strftime('%y-%m-%d') # Shorter year for grid
                            except:
                                return ""

                        permit_date = fmt_date(row.get('인허가일자'))
                        last_modified = fmt_date(row.get('최종수정시점'))
                        
                        # Compact Card HTML
                        card_html = f"""
                        <div class="card-tile">
                            <div class="status-badge {status_cls}">{row['영업상태명']}</div>
                            <div class="card-title-grid" title="{row['사업장명']}">{row['사업장명']}</div>
                            <div class="card-meta-grid">
                                {row['업태구분명']} | {row['평수']}평<br>
                                {row['관리지사']} ({row['SP담당']})<br>
                                <span style="color:#7C4DFF">🔄 {last_modified or '-'}</span> | 
                                <span style="color:#1565C0">✨ {permit_date or '-'}</span>
                            </div>
                            <div style="font-size:0.7rem; color:#888; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; height:32px; margin-bottom:10px;">
                                {row['소재지전체주소']}
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                        # Mini Action Buttons
                        b1, b2, b3 = st.columns([1,1,1])
                        with b1:
                            if tel: st.link_button("📞", f"tel:{tel}", use_container_width=True)
                            else: st.button("📞", disabled=True, key=f"nc_{idx}", use_container_width=True)
                        with b2:
                             st.link_button("🗺️", f"https://map.naver.com/v5/search/{row['소재지전체주소']}", use_container_width=True)
                        with b3:
                             st.link_button("🔍", f"https://search.naver.com/search.naver?query={row['사업장명']}", use_container_width=True)
    
    # [TAB] Data Grid
    if active_nav == "📋 데이터 그리드":
        st.markdown("### 📋 전체 데이터")
        
        custom_branch_order = [
            '중앙지사', '강북지사', '서대문지사', '고양지사', '의정부지사', 
            '남양주지사', '강릉지사', '원주지사', '미지정'
        ]
        df['관리지사'] = pd.Categorical(df['관리지사'], categories=custom_branch_order, ordered=True)
        
        grid_df = df.copy()
        
        start_row_count = len(grid_df)
        
        
        # [OPTIMIZATION] Bulk Load Activity Status
        # Load the JSON file ONCE to avoid IO for every row
        try:
            status_data = activity_logger.load_json_file(activity_logger.ACTIVITY_STATUS_FILE)
            if not isinstance(status_data, dict):
                status_data = {}
        except Exception as e:
            status_data = {}

        # Add activity status and notes from storage (Optimized)
        grid_df['record_key'] = grid_df.apply(lambda row: activity_logger.get_record_key(row), axis=1)
        
        # Helper to safely get data from loaded dict
        def get_status_val(k, field):
            return status_data.get(k, {}).get(field, '')

        grid_df['활동진행상태'] = grid_df['record_key'].apply(lambda k: get_status_val(k, '활동진행상태')).astype(str)
        grid_df['특이사항'] = grid_df['record_key'].apply(lambda k: get_status_val(k, '특이사항')).astype(str)
        grid_df['상태변경일시'] = grid_df['record_key'].apply(lambda k: get_status_val(k, '변경일시')).astype(str)
        grid_df['상태변경자'] = grid_df['record_key'].apply(lambda k: get_status_val(k, '변경자')).astype(str)
        
        # [DEBUG] Key Comparison - Removed by user request
        # with st.expander("🕵️ 데이터 키 정밀 분석 (Debug)", expanded=True):
        #     pass
        
        if '인허가일자' in grid_df.columns:
            grid_df['인허가일자'] = grid_df['인허가일자'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else "")
            
        if '폐업일자' in grid_df.columns:
            grid_df['폐업일자'] = grid_df['폐업일자'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else "")
        
        if '최종수정시점' in grid_df.columns:
            grid_df['최종수정시점'] = grid_df['최종수정시점'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else "")


        grid_df = grid_df.sort_values(by=['관리지사', 'SP담당', '업태구분명'])
        
        # [LAYOUT] Data Grid & VOC
        
        # Get current user info & Prep Columns
        current_user = st.session_state.get('user_manager_name') or st.session_state.get('user_branch') or '관리자'
        
        
        display_cols = [
            '활동진행상태', # Moved to first position
            '관리지사', 'SP담당', '업태구분명', '사업장명', 
            '소재지전체주소', '소재지전화', '평수', 
            '특이사항', '상태변경일시', '상태변경자',
            '최종수정시점', '인허가일자', '폐업일자', 'record_key'
        ]
        
        # [FEATURE] Activity Status Filter & Visualization
        # [FEATURE] Activity Status Filter & Visualization
        
        # [MIGRATION] Convert plain status to Emoji status for display consistency
        # Use Centralized Normalizer
        if '활동진행상태' in grid_df.columns:
            grid_df['활동진행상태'] = grid_df['활동진행상태'].apply(activity_logger.normalize_status)

        # Layout: Filter & Search
        c_filter, c_search = st.columns([1, 1])
        
        status_filter_opts = list(activity_logger.ACTIVITY_STATUS_MAP.values())
        
        with c_filter:
            sel_grid_status = st.multiselect("진행상태 필터", status_filter_opts, placeholder="전체 보기 (미선택 시)", key="grid_status_multiselect")
        
        with c_search:
            grid_search_kw = st.text_input("검색 (업체명/주소/상태/특이사항)", placeholder="검색어 입력", key="grid_search_input")
        
        with st.expander("📊 활동 현황 분석 (차트 보기)", expanded=False):
            st.markdown("##### 📊 활동 현황 분석")
            
            c_chart1, c_chart2 = st.columns([1, 2])
            
            # Prepare Data for Charts (Use grid_df before final filtering for global view)
            chart_data = grid_df['활동진행상태'].value_counts().reset_index()
            chart_data.columns = ['status', 'count']
            chart_data = chart_data[chart_data['status'] != ''] # Exclude empty
            
            with c_chart1:
                if not chart_data.empty:
                    # Donut Chart
                    base = alt.Chart(chart_data).encode(
                        theta=alt.Theta("count", stack=True),
                        color=alt.Color("status", scale=alt.Scale(
                            domain=list(activity_logger.ACTIVITY_STATUS_MAP.values()), 
                            range=['#29B6F6', '#FFB74D', '#5C6BC0', '#E57373', '#81C784']
                        ), legend=None)
                    )
                    pie = base.mark_arc(outerRadius=80, innerRadius=40)
                    text = base.mark_text(radius=100).encode(
                        text=alt.Text("count", format=",.0f"),
                        order=alt.Order("status"),
                        color=alt.value("black")
                    )
                    st.altair_chart(pie + text, use_container_width=True)
                else:
                    st.caption("집계된 활동 내역이 없습니다.")
                    
            with c_chart2:
                if not chart_data.empty:
                    # Bar Chart
                    bar_chart = alt.Chart(chart_data).mark_bar().encode(
                        x=alt.X('count', title='건수'),
                        y=alt.Y('status', sort='-x', title='상태'),
                        color=alt.Color('status', legend=None),
                        tooltip=['status', 'count']
                    )
                    st.altair_chart(bar_chart, use_container_width=True)
        
        # [DEBUG] Check Mapping Results
        st.caption(f"🔧 Debug Statuses: {sorted(grid_df['활동진행상태'].unique())}")
        
        # Apply Filters to Grid Display (Status AND Search)
        if sel_grid_status:
            grid_df = grid_df[grid_df['활동진행상태'].isin(sel_grid_status)]
            
        if grid_search_kw:
            grid_df = grid_df[
                grid_df['사업장명'].astype(str).str.contains(grid_search_kw, na=False) | 
                grid_df['소재지전체주소'].astype(str).str.contains(grid_search_kw, na=False) |
                grid_df['활동진행상태'].astype(str).str.contains(grid_search_kw, na=False) |
                grid_df['특이사항'].astype(str).str.contains(grid_search_kw, na=False)
            ]
            
        st.divider()

        
        # Create display dataframe AFTER filtering
        final_cols = [c for c in display_cols if c in grid_df.columns]
        df_display = grid_df[final_cols].reset_index(drop=True)
        
        # [CLEANUP] Replace NaN and None values with empty string for clean display
        # Convert categorical columns to object type first to avoid TypeError
        for col in df_display.columns:
            if pd.api.types.is_categorical_dtype(df_display[col]):
                df_display[col] = df_display[col].astype('object')
        
        df_display = df_display.fillna('')
        df_display = df_display.replace(['None', 'nan', 'NaN'], '')
        
        # [FIX] Use Categorical Dtype to FORCE Dropdown in Data Editor
        # This is more robust than column_config.SelectboxColumn alone
        valid_statuses = sorted(list(set([""] + list(activity_logger.ACTIVITY_STATUS_MAP.values()))))
        df_display['활동진행상태'] = pd.Categorical(df_display['활동진행상태'], categories=valid_statuses, ordered=True)

        # Render Editable Grid
        st.caption(f"총 {len(df_display):,}건 (수정 가능)")
        
        edited_df = st.data_editor(
            df_display, 
            use_container_width=True, 
            height=600,
            column_config={
                "평수": st.column_config.NumberColumn(format="%.1f평"),
                "활동진행상태": st.column_config.SelectboxColumn(
                    "활동상태",
                    options=sorted(list(set([""] + list(activity_logger.ACTIVITY_STATUS_MAP.values())))),
                    width="medium",
                    required=False
                ),
                "특이사항": st.column_config.TextColumn(
                    "상세내역(상담이력을 활동내역에 더블클릭하여 등록해 주세요)",
                    help="상담이력을 활동내역에 더블클릭하여 등록해 주세요",
                    max_chars=500
                ),
                "record_key": None,  # Hide this column
                "상태변경일시": st.column_config.TextColumn("변경일시", disabled=True),
                "상태변경자": st.column_config.TextColumn("변경자", disabled=True)
            },
            hide_index=True,
            key="data_grid_editor"
        )
        
        # Save button and Download
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 변경사항 저장", use_container_width=True):
                # [OPTIMIZATION] Changes handled inside loop
                saved_count = 0
                debug_log = []
                
                for idx, row in edited_df.iterrows():
                    orig_row = df_display.iloc[idx]
                    
                    if (row['활동진행상태'] != orig_row['활동진행상태'] or 
                        row['특이사항'] != orig_row['특이사항']):
                        
                        # [FIX] Sanitize status using centralized normalization
                        # We want to store just the status or the emoji status? 
                        # User seems to prefer Emoji status in UI.
                        # For consistency, let's keep what the UI has.
                        # But `save_activity_status` expects what? String.
                        # Let's save the FULL string (with Emoji) to avoid ambiguity.
                        raw_status = row['활동진행상태']
                            
                        # Debug Log
                        debug_log.append(f"Saving: {row.get('사업장명')} ({row['record_key']}) -> {raw_status}")
                        
                        # [REDESIGN] Atomic Handling
                        # 1. Prepare User Info
                        u_info = {
                            "name": current_user,
                            "role": st.session_state.get('user_role', 'unknown'),
                            "branch": st.session_state.get('user_branch', '')
                        }
                        
                        # 2. Check if this is a Visit Registration
                        if "방문" in raw_status:
                             # Register Visit (Atomic: Report + Status + History)
                             sys_note = f"[시스템 자동] 데이터 그리드에서 '방문' 상태로 변경됨. (특이사항: {row['특이사항']})"
                             activity_logger.register_visit(
                                 row['record_key'], 
                                 sys_note, 
                                 None, None, # No media
                                 u_info,
                                 forced_status=raw_status # Persist the exact status string
                             )
                        # [NEW] Check if this is an Interest Registration
                        elif "관심" in raw_status:
                             # Register Interest (Status + Interest Log + Visit History Draft)
                             # 1. Status Update
                             activity_logger.save_activity_status(
                                row['record_key'],
                                raw_status,
                                row['특이사항'],
                                current_user
                            )
                            # 2. Log Interest explicitly if not already? 
                            # (Optional, but user asked for "Interest" to be tracked. 
                            # Grid edit might not have lat/lon easily, so skip spatial log, just status/visit history.)
                             activity_logger.save_visit_report(
                                record_key=row['record_key'],
                                user_name=current_user,
                                user_branch=st.session_state.get('user_branch'),
                                content=f"[시스템] 데이터 그리드에서 '관심' 상태로 변경했습니다.",
                                photo_path=None,
                                audio_path=None
                            )
                        else:
                             # Just Status Update (Atomic: Status + History)
                             # [NEW] Report generation now handled internally by activity_logger.py
                             activity_logger.save_activity_status(
                                row['record_key'],
                                raw_status,
                                row['특이사항'],
                                current_user
                            )
                        
                        saved_count += 1
                
                if saved_count > 0:
                    st.toast(f"✅ {saved_count}건 등록되었습니다.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.info("변경된 항목이 없습니다.")
        
        with col2:
            st.download_button("📥 CSV 다운로드", df_display.to_csv(index=False).encode('utf-8-sig'), "영업기회_처리결과.csv", "text/csv", use_container_width=True)
    
    # [TAB] VOC Request (Admin + Users)
    # [FIX] Allow Admin to see the tab content (as View Mode)
    # [TAB] VOC Request (Admin + Users)
    # [FIX] Allow Admin to see the tab content (as View Mode)
    if active_nav == "🗣️ 관리자에게 요청하기":
        st.subheader("🗣️ 관리자에게 요청하기 (VOC)")
        
        if st.session_state.user_role == 'admin':
            st.info("👮 관리자 모드: 접수된 요청 내역을 확인합니다.")
            # Admin view implementation can be added here
            all_requests = voc_manager.load_voc_requests()
            if all_requests:
                st.dataframe(all_requests)
            else:
                st.info("접수된 요청이 없습니다.")
        else:
            # User View (Original Logic)
            
            # Show existing requests first
            st.markdown("### 📋 나의 요청 내역")
            
            # Load all requests and filter by current user
            all_requests = voc_manager.load_voc_requests()
            u_name = st.session_state.user_manager_name or st.session_state.user_branch or "Unknown"
            my_requests = [req for req in all_requests if req.get('user_name') == u_name]
            
            if my_requests:
                for req in my_requests:
                    # Status badge
                    status_badge = voc_manager.get_status_badge(req['status'])
                    priority_emoji = "🔴" if req['priority'] == "High" else "🟡" if req['priority'] == "Normal" else "🟢"
                    
                    with st.expander(f"{status_badge} {priority_emoji} {req['subject']} - {req['timestamp']}", expanded=(req['status'] == 'New')):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.caption(f"**요청 ID:** {req['id']}")
                            st.caption(f"**등록일시:** {req['timestamp']}")
                        with col2:
                            st.caption(f"**상태:** {status_badge}")
                            st.caption(f"**중요도:** {priority_emoji} {req['priority']}")
                        
                        st.markdown("**📄 요청 내용:**")
                        st.info(req['content'])
                        
                        # Show admin comment if exists
                        if req.get('admin_comment') and req['admin_comment'].strip():
                            st.markdown("**💬 관리자 답변:**")
                            st.success(req['admin_comment'])
                        elif req['status'] != 'New':
                            st.caption("_관리자가 아직 답변을 작성하지 않았습니다._")
            else:
                st.info("아직 등록한 요청이 없습니다.")
            
            st.markdown("---")
            st.markdown("### ✍️ 새 요청 등록")
            st.info("건의사항, 오류 제보, 기능 요청 등을 관리자에게 전달할 수 있습니다.")
            
            with st.form("voc_request_form"):
                voc_subj = st.text_input("📝 제목", placeholder="요청 제목을 입력하세요")
                voc_cont = st.text_area("📄 내용", placeholder="상세 내용을 입력하세요...", height=200)
                voc_pri = st.select_slider("⚠️ 중요도", options=["Low", "Normal", "High"], value="Normal")
                
                col_submit, col_reset = st.columns([1, 1])
                with col_submit:
                    submitted = st.form_submit_button("📤 요청 등록", type="primary", use_container_width=True)
                with col_reset:
                    reset = st.form_submit_button("🔄 초기화", use_container_width=True)
                
                if submitted:
                    if voc_subj and voc_cont:
                        u_name = st.session_state.user_manager_name or st.session_state.user_branch or "Unknown"
                        u_region = st.session_state.user_branch or "Unknown"
                        if voc_manager.add_voc_request(st.session_state.user_role, u_name, u_region, voc_subj, voc_cont, voc_pri):
                            st.success("✅ 요청이 성공적으로 접수되었습니다. 관리자가 확인 후 답변드리겠습니다.")
                            st.rerun()
                        else:
                            st.error("❌ 요청 등록에 실패했습니다. 다시 시도해주세요.")
                    else:
                        st.warning("⚠️ 제목과 내용을 모두 입력해주세요.")

else:
    st.info("👈 사이드바에서 데이터를 업로드하거나, '자동 감지' 기능을 확인하세요.")
    st.markdown("### 🚀 시작하기\n1. **자동 모드**: `data/` 폴더에 파일이 있으면 자동으로 불러옵니다.\n2. **수동 모드**: 언제든지 사이드바에서 파일을 직접 업로드할 수 있습니다.\n\n> **Tip**: 모바일 접속 시 '홈 화면에 추가'하여 앱처럼 사용하세요!", unsafe_allow_html=True)

    # [FIX] Global Injection of Button Status Colors
    # Calling it at the end ensures all UI elements are rendered and observer is attached.
    inject_button_color_script()

# Main execution completed by top-level script
pass
