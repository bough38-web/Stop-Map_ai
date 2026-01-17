import streamlit as st
import pandas as pd
import altair as alt
import utils
import os

# --- Configuration & Theme ---
st.set_page_config(
    page_title="영업기회 관리 시스템",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium & Mobile Feel
st.markdown("""
<style>
    /* Global Font & Colors */
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }
    
    /* Main Container Padding */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 3rem;
    }

    /* Metrics Styling */
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
        border: 1px solid #e0e0e0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #2c3e50;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #4CAF50;
    }

    /* Small Dashboard Card */
    .small-card {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        margin-bottom: 5px;
    }
    .small-card-title { font-size: 0.85rem; color: #555 !important; font-weight: 600; margin-bottom: 2px; }
    .small-card-value { font-size: 1.1rem; color: #333 !important; font-weight: 700; }
    .small-card-active { color: #2E7D32 !important; font-size: 0.8rem; }
    
    /* Ensure text visibility on forced white backgrounds */
    .metric-label { color: #555 !important; }
    .metric-value { color: #333 !important; }

    /* Mobile Card Styling */
    .card-container {
        background-color: white;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 16px;
        border-left: 5px solid #2E7D32;
        transition: transform 0.2s;
    }
    .card-container:active {
        transform: scale(0.98);
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .card-badges {
        display: flex;
        gap: 5px;
    }
    .status-badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-open { background-color: #e8f5e9; color: #2e7d32; }
    .status-closed { background-color: #ffebee; color: #c62828; }
    
    .card-meta {
        font-size: 0.85rem;
        color: #555;
        margin-bottom: 8px;
    }
    .card-address {
        font-size: 0.85rem;
        color: #777;
        margin-bottom: 12px;
        display: flex;
        align-items: start;
        gap: 5px;
    }
    
    /* Action Buttons Area */
    .card-actions {
        display: flex;
        gap: 10px;
        margin-top: 10px;
        border-top: 1px solid #eee;
        padding-top: 10px;
    }
    
    /* Tabs Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        border-bottom: 2px solid #2E7D32;
        color: #2E7D32;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ 설정 & 데이터")
    
    # Check Local Data
    local_zip, local_dist = utils.get_local_data_paths()
    use_local = False
    
    if local_zip and local_dist:
        st.success("✅ 로컬 데이터 자동 감지됨")
        use_local = st.toggle("자동 감지된 데이터 사용", value=True)
        if use_local:
            st.caption(f"ZIP: {os.path.basename(local_zip)}")
            st.caption(f"Dist: {os.path.basename(local_dist)}")
    
    if not use_local:
        uploaded_zip = st.file_uploader("인허가 데이터 (ZIP)", type="zip")
        uploaded_dist = st.file_uploader("영업구역 데이터 (Excel)", type="xlsx")
    else:
        uploaded_zip = local_zip
        uploaded_dist = local_dist

    st.markdown("---")
    
    # Kakao API Key (Global Sidebar)
    # Kakao API Key (Global Sidebar)
    st.warning("🔑 카카오 지도 설정")
    kakao_key = st.text_input("카카오 Javascript 키 입력", type="password", key="kakao_api_key_v2")
    
    if kakao_key:
        st.success("카카오 지도가 활성화되었습니다.")
    else:
        st.caption("키 미입력 시 오픈스트리트맵(OSM)으로 표시됩니다.")
        
    st.markdown("---")
    st.caption("Developed by Antigravity")

# --- Main Logic ---

st.title("💼 영업기회 파이프라인")

if uploaded_zip and uploaded_dist:
    # Load Data
    with st.spinner("🚀 데이터를 분석하고 매칭중입니다..."):
        raw_df, error = utils.load_and_process_data(uploaded_zip, uploaded_dist)
    
    if error:
        st.error(f"데이터 로드 실패: {error}")
        st.stop()
        
    # --- Apply Global Filters (Sidebar) ---
    with st.sidebar:
        st.header("🔍 공통 필터")
        
        # Temp DF for cascading options
        filter_df = raw_df.copy()
        
        # 1. Branch
        branch_opts = ["전체"] + sorted(list(raw_df['관리지사'].unique()))
        sel_branch = st.selectbox("관리지사 선택", branch_opts)
        
        if sel_branch != "전체":
            filter_df = filter_df[filter_df['관리지사'] == sel_branch]
        
        # 2. Manager (Filtered by Branch)
        manager_opts = ["전체"] + sorted(list(filter_df['SP담당'].unique()))
        sel_manager = st.selectbox("담당자 선택", manager_opts)
        
        if sel_manager != "전체":
            filter_df = filter_df[filter_df['SP담당'] == sel_manager]
            
        # 3. Business Type (Filtered by Branch & Manager)
        # Handle case where column might be missing or different name provided by utils
        type_col = '업태구분명' if '업태구분명' in raw_df.columns else raw_df.columns[0] # Fallback
        
        # Get available types based on previous filters
        # Improve Robustness: If filtering emptied the list, show all types for the branch (or all global if that fails)
        try:
            available_types = sorted(list(filter_df[type_col].dropna().unique()))
        except:
            available_types = []
            
        if not available_types and not filter_df.empty:
             # Try getting from raw_df if something went wrong with column name
             available_types = sorted(list(raw_df[type_col].dropna().unique()))
             
        # Expander for Business Type
        with st.expander("📂 업태(업종) 필터 (펼치기/접기)", expanded=False):
            # Multiselect behaves like "chips" or "bubbles"
            sel_types = st.multiselect(
                "업태를 선택하세요 (복수 선택 가능)", 
                available_types,
                placeholder="전체 선택 (비어있으면 전체)",
                label_visibility="collapsed"
            )
            
        
    # Filter Data Globally
    df = raw_df.copy()
    if sel_branch != "전체":
        df = df[df['관리지사'] == sel_branch]
    if sel_manager != "전체":
        df = df[df['SP담당'] == sel_manager]
        
    # Apply Type Filter
    if sel_types:
        df = df[df[type_col].isin(sel_types)]
        
    # --- Dashboard UI ---
    
    # 1. Define Sort Order
    target_order_keywords = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
    all_branches = df['관리지사'].unique()
    
    def branch_sort_key(b_name):
        for i, k in enumerate(target_order_keywords):
            if k in b_name: return i
        return 999 
    sorted_branches = sorted([b for b in all_branches if b != '미지정'], key=branch_sort_key)
    
    # 2. Level 1: Branch Dashboard
    st.markdown("### 🏢 지사별 현황 (클릭하여 상세 조회)")
    
    # Interactive Selector
    try:
        default_br = sorted_branches[0] if sorted_branches else "전체"
    except:
        default_br = "전체"
        
    sel_dashboard_branch = st.radio(
        "지사 선택", 
        sorted_branches, 
        index=0, 
        horizontal=True, 
        key="dash_branch_select",
        label_visibility="collapsed"
    )
    
    # Grid of Branch Stats
    cols = st.columns(len(sorted_branches) if sorted_branches else 1)
    for i, col in enumerate(cols):
        if i < len(sorted_branches):
            b_name = sorted_branches[i]
            b_df = df[df['관리지사'] == b_name]
            b_total = len(b_df)
            b_active = len(b_df[b_df['영업상태명'] == '영업/정상'])
            
            # Highlight selected
            bg_color = "#e8f5e9" if b_name == sel_dashboard_branch else "#ffffff"
            border_color = "#2E7D32" if b_name == sel_dashboard_branch else "#e0e0e0"
            
            with col:
                st.markdown(f"""
                <div style="background-color: {bg_color}; border: 2px solid {border_color}; border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="font-weight:bold; font-size:0.9rem; margin-bottom:5px; color:#333;">{b_name}</div>
                    <div style="font-size:1.2rem; font-weight:bold; color:#000;">{b_total:,}</div>
                    <div style="font-size:0.8rem; color:#2E7D32;">(영업: {b_active:,})</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 3. Level 2: Manager Status (Drill Down)
    if sel_dashboard_branch:
        st.markdown(f"### 👤 {sel_dashboard_branch} 영업담당 현황")
        mgr_df = df[df['관리지사'] == sel_dashboard_branch]
        managers = sorted(mgr_df['SP담당'].unique())
        
        m_cols = st.columns(4)
        for i, mgr in enumerate(managers):
            col_idx = i % 4
            m_sub_df = mgr_df[mgr_df['SP담당'] == mgr]
            m_total = len(m_sub_df)
            m_active = len(m_sub_df[m_sub_df['영업상태명'] == '영업/정상'])
            
            with m_cols[col_idx]:
                 st.markdown(f"""
                <div class="metric-card" style="margin-bottom:10px;">
                    <div class="metric-label" style="color:#555;">{mgr}</div>
                    <div class="metric-value" style="color:#333;">{m_total:,}</div>
                    <div class="metric-sub">영업가능: {m_active:,}건</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🗺️ 지도 & 분석", "📱 모바일 리스트", "📋 데이터 그리드"])

    # --- Tab 1: Map & Analytics ---
    with tab1:
        st.subheader("🗺️ 지역별 영업기회 분석")
        
        # (Kakao Key input moved to Global Sidebar)
        
        # 1. Filters Setup
        map_status_opts = ["전체"] + sorted(list(df['영업상태명'].unique()))
        map_status_opts = ["전체"] + sorted(list(df['영업상태명'].unique()))
        map_default = "영업/정상" if "영업/정상" in map_status_opts else "전체"
        
        st.markdown("##### 🏷️ 영업상태")
        try: idx = map_status_opts.index(map_default)
        except: idx = 0
        sel_map_status = st.radio("영업상태 선택", map_status_opts, index=idx, key="map_status_radio", horizontal=True, label_visibility="collapsed")
        if not sel_map_status: sel_map_status = "전체"

        c_f1, c_f2 = st.columns(2)
        with c_f1:
            map_region_opts = ["전체"] + sorted(list(df['관리지사'].unique()))
            sel_map_region = st.selectbox("관리지사", map_region_opts, key="map_region")
        with c_f2:
            map_sales_opts = ["전체"] + sorted(list(df['SP담당'].unique()))
            sel_map_sales = st.selectbox("담당자", map_sales_opts, key="map_sales")
            
        # 2. Prepare Data
        map_df = df.dropna(subset=['lat', 'lon']).copy()
        
        if sel_map_status != "전체": map_df = map_df[map_df['영업상태명'] == sel_map_status]
        if sel_map_region != "전체": map_df = map_df[map_df['관리지사'] == sel_map_region]
        if sel_map_sales != "전체": map_df = map_df[map_df['SP담당'] == sel_map_sales]
            
        st.markdown(f"**📍 조회된 업체**: {len(map_df):,} 개")
        st.markdown("---")
        
        # 3. Layout: Map and Analysis
        col_map, col_chart = st.columns([1.8, 1])
        
        with col_map:
            st.markdown("#### 🗺️ 지도")
            if not map_df.empty:
                # KAKAO MAP COMPONENT
                if kakao_key:
                    # Limit for performance
                    limit = 3000
                    if len(map_df) > limit:
                        st.warning(f"⚠️ 데이터가 많아 상위 {limit:,}개만 지도에 표시합니다.")
                        display_df = map_df.head(limit)
                    else:
                        display_df = map_df
                        
                    # Prepare JSON
                    display_df = display_df.copy()
                    display_df['title'] = display_df['사업장명']
                    display_df['addr'] = display_df['소재지전체주소'].fillna('')
                    display_df['tel'] = display_df['소재지전화'].fillna('')
                    display_df['status'] = display_df['영업상태명']
                    
                    # Add Clousre Date
                    def format_close_date(d):
                        if pd.isna(d): return ''
                        s = str(d).replace('.0', '').strip()[:10] # YYYY-MM-DD
                        return s
                    
                    if '폐업일자' in display_df.columns:
                        display_df['close_date'] = display_df['폐업일자'].apply(format_close_date)
                    else:
                        display_df['close_date'] = ''
                    
                    map_data = display_df[['lat', 'lon', 'title', 'status', 'addr', 'tel', 'close_date']].to_dict(orient='records')
                    
                    import json
                    json_data = json.dumps(map_data)
                    
                    import streamlit.components.v1 as components
                    st.markdown("""
                    <div style="background-color: #e3f2fd; border-left: 5px solid #2196F3; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                        <small><b>💡 지도 표시 문제 해결:</b> 지도가 보이지 않거나 백지 상태라면? <br>
                        1. <a href="https://developers.kakao.com/console/app" target="_blank">Kakao Developers</a> > 내 애플리케이션 > [플랫폼] > [Web] 수정 <br>
                        2. <b>사이트 도메인</b>에 현재 주소를 반드시 등록해야 합니다.<br>
                        (로컬 실행 시: <code>http://localhost:8501</code> 또는 <code>http://127.0.0.1:8501</code>)
                        </small>
                    </div>
                    """, unsafe_allow_html=True)

                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8"/>
                        <style>
                            html, body {{ width:100%; height:100%; margin:0; padding:0; overflow:hidden; }} 
                            #map {{ width: 100%; height: 500px; border: 1px solid #ddd; background-color: #f8f9fa; }}
                            #error-msg {{ 
                                display: none; 
                                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                                text-align: center; color: #d32f2f; background: rgba(255,255,255,0.9); padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.15); border: 1px solid #ef9a9a;
                            }}
                            .retry-btn {{
                                margin-top: 15px;
                                padding: 8px 16px;
                                background-color: #2196F3;
                                color: white;
                                border: none;
                                border-radius: 4px;
                                cursor: pointer;
                            }}
                        </style>
                    </head>
                    <body>
                        <div id="map"></div>
                        <div id="error-msg">
                            <h3 style="margin-top:0;">⚠️ 지도를 불러오지 못했습니다</h3>
                            <p id="error-desc" style="font-size:14px; line-height:1.6;">
                                Kakao Maps SDK 스크립트 로드에 실패했습니다.<br>
                                가장 흔한 원인은 <b>'사이트 도메인 미등록'</b> 입니다.
                            </p>
                            <div style="background:#fff3e0; padding:10px; border-radius:4px; font-size:12px; text-align:left; margin:10px 0;">
                                <b>확인 사항:</b><br>
                                1. Kakao Developers > 내 앱 > 플랫폼 > Web<br>
                                2. 사이트 도메인에 <code>http://localhost:8501</code> 등록 확인<br>
                                3. API 키({kakao_key[:4]}...)가 올바른지 확인
                            </div>
                            <small id="debug-info" style="color:#666; display:block; margin-top:5px;"></small>
                            <button class="retry-btn" onclick="location.reload()">새로고침</button>
                        </div>
                        
                        <!-- Force HTTPS protocol and add onerror handler -->
                        <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_key}&libraries=services,clusterer,drawing&autoload=false"
                                onerror="handleScriptError()"></script>
                        
                        <script>
                            function handleScriptError() {{
                                var errorBox = document.getElementById('error-msg');
                                var debugBox = document.getElementById('debug-info');
                                errorBox.style.display = 'block';
                                debugBox.innerText = "Debug: Script failed to load (Network/403/Block).";
                            }}

                            // Global Error Handling
                            window.onerror = function(msg, url, lineNo, columnNo, error) {{
                                var errorBox = document.getElementById('error-msg');
                                var debugBox = document.getElementById('debug-info');
                                errorBox.style.display = 'block';
                                debugBox.innerText = "Error: " + msg;
                                return false; // Let default handler run if needed
                            }};

                            // Check immediate availability
                            if (typeof kakao === 'undefined') {{
                                setTimeout(function() {{
                                    if (typeof kakao === 'undefined') {{
                                        handleScriptError();
                                        document.getElementById('debug-info').innerText += " (kakao undefined)";
                                    }}
                                }}, 1000);
                            }}

                            // Only proceed if kakao exists or loads
                            if (typeof kakao !== 'undefined') {{
                                kakao.maps.load(initMap);
                            }} else {{
                                // Wait for it potentially
                                var checkInterval = setInterval(function() {{
                                    if (typeof kakao !== 'undefined') {{
                                        clearInterval(checkInterval);
                                        kakao.maps.load(initMap);
                                    }}
                                }}, 200);
                                // Timeout after 3s
                                setTimeout(function(){{ clearInterval(checkInterval); }}, 3000);
                            }}

                            function initMap() {{
                                try {{
                                    var container = document.getElementById('map');
                                    var options = {{
                                        center: new kakao.maps.LatLng({display_df['lat'].mean()}, {display_df['lon'].mean()}),
                                        level: 9
                                    }};
                                    var map = new kakao.maps.Map(container, options);
                                    
                                    var clusterer = new kakao.maps.MarkerClusterer({{
                                        map: map,
                                        averageCenter: true, 
                                        minLevel: 10 
                                    }});
                                    
                                    var data = {json_data};
                                    var markers = [];
                                    
                                    // Marker Images
                                    var imgSize = new kakao.maps.Size(35, 35); 
                                    var activeImgSrc = "https://maps.google.com/mapfiles/ms/icons/green-dot.png";
                                    var otherImgSrc = "https://maps.google.com/mapfiles/ms/icons/red-dot.png"; // or grey

                                    data.forEach(function(item) {{
                                        // Choose Image
                                        var imgSrc = (item.status === '영업/정상') ? activeImgSrc : otherImgSrc;
                                        var markerImage = new kakao.maps.MarkerImage(imgSrc, imgSize);

                                        var marker = new kakao.maps.Marker({{
                                            position: new kakao.maps.LatLng(item.lat, item.lon),
                                            title: item.title,
                                            image: markerImage
                                        }});
                                        
                                        var closeInfo = '';
                                        if (item.close_date && item.close_date !== 'NaT' && item.close_date.length > 5) {{
                                            closeInfo = '<span style="color:#d32f2f; font-size:11px;">(폐업: ' + item.close_date + ')</span><br>';
                                        }}

                                        
                                        var content = '<div style="padding:12px;font-size:12px;width:240px;line-height:1.6;font-family:sans-serif;">' + 
                                                      '<b style="font-size:14px; color:#333;">' + item.title + '</b>&nbsp;' +
                                                      '<span style="background-color:#e8f5e9; color:#2E7D32; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:11px;">' + item.status + '</span><br>' + 
                                                      closeInfo +
                                                      '<span style="color:#666;">📍 ' + item.addr + '</span><br>' + 
                                                      '<a href="tel:' + item.tel + '" style="text-decoration:none; color:#1976D2; font-weight:bold;">📞 ' + (item.tel ? item.tel : '번호없음') + '</a>' + 
                                                      '</div>';
                                                      
                                        var infowindow = new kakao.maps.InfoWindow({{
                                            content: content,
                                            removable: true
                                        }});
                                        
                                        kakao.maps.event.addListener(marker, 'click', function() {{
                                            infowindow.open(map, marker);
                                        }});
                                        
                                        markers.push(marker);
                                    }});
                                    
                                    clusterer.addMarkers(markers);
                                    
                                    // Controls
                                    var zoomControl = new kakao.maps.ZoomControl();
                                    map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);
                                    var mapTypeControl = new kakao.maps.MapTypeControl();
                                    map.addControl(mapTypeControl, kakao.maps.ControlPosition.TOPRIGHT);
                                    
                                }} catch (err) {{
                                    var errorBox = document.getElementById('error-msg');
                                    var debugBox = document.getElementById('debug-info');
                                    errorBox.style.display = 'block';
                                    debugBox.innerText = "Load Error: " + err.message;
                                }}
                            }}
                        </script>
                    </body>
                    </html>
                    """
                    components.html(html_content, height=520)
                
                else:
                    # Fallback to PyDeck
                    import pydeck as pdk
                    view_state = pdk.ViewState(
                        latitude=map_df['lat'].mean(),
                        longitude=map_df['lon'].mean(),
                        zoom=10,
                        pitch=0,
                    )
                    
                    def get_color(status):
                        if status == "영업/정상": return [46, 125, 50, 160] # Green
                        return [198, 40, 40, 160] # Red
                    
                    map_df['color'] = map_df['영업상태명'].apply(get_color)
                    map_df['display_tel'] = map_df['소재지전화'].fillna('번호없음')
                    map_df['display_addr'] = map_df['소재지전체주소'].fillna('-')
                    
                    def format_date(d):
                        if pd.isna(d): return "-"
                        s = str(d).replace('.0', '').strip()
                        if len(s) == 8: return f"{s[:4]}-{s[4:6]}-{s[6:]}"
                        return s
                    
                    if '인허가일자' in map_df.columns:
                        map_df['display_license_date'] = map_df['인허가일자'].apply(format_date)
                    else: map_df['display_license_date'] = '-'
                    if '폐업일자' in map_df.columns:
                        map_df['display_close_date'] = map_df['폐업일자'].apply(format_date)
                    else: map_df['display_close_date'] = '-'

                    # TileLayer (OSM)
                    tile_layer = pdk.Layer(
                        "TileLayer",
                        data="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                        get_line_color=[0, 0, 0],
                        min_zoom=0,
                        max_zoom=19,
                        picking_method_name="hover",
                    )

                    scatter_layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=map_df,
                        get_position='[lon, lat]',
                        get_color='color',
                        get_radius=100,
                        pickable=True,
                        auto_highlight=True,
                    )
                    
                    tooltip = {
                        "html": "<b>{사업장명}</b><br/>"
                                "<span style='color: white; background-color: grey; padding: 2px; border-radius:3px;'>{영업상태명}</span><br/>"
                                "📅 인허가: {display_license_date}<br/>"
                                "📅 폐업일: {display_close_date}<br/>"
                                "🏠 {display_addr}<br/>"
                                "📞 {display_tel}",
                        "style": {"backgroundColor": "steelblue", "color": "white", "zIndex": "999"}
                    }
                    
                    r = pdk.Deck(
                        map_style=None, 
                        initial_view_state=view_state,
                        layers=[tile_layer, scatter_layer],
                        tooltip=tooltip
                    )
                    st.pydeck_chart(r, use_container_width=True)
                    st.caption("ℹ️ '카카오 API 키'를 입력하시면 카카오 지도로 전환됩니다.")

        with col_chart:
            st.markdown("#### 📊 데이터 분석")
            
            c_tab1, c_tab2 = st.tabs(["지사별 분포", "업태별 분포"])
            
            with c_tab1:
                if not map_df.empty:
                    bar_chart = alt.Chart(map_df).mark_bar(cornerRadius=5).encode(
                        x=alt.X('관리지사', sort='-y', title=None),
                        y=alt.Y('count()', title='업체 수'),
                        color=alt.Color('관리지사', legend=None),
                        tooltip=['관리지사', 'count()']
                    ).properties(height=350)
                    st.altair_chart(bar_chart, use_container_width=True)
                else:
                    st.info("데이터 없음")
            
            with c_tab2:
                if not map_df.empty:
                    top_types = map_df['업태구분명'].value_counts().head(10).index.tolist()
                    pie_df = map_df[map_df['업태구분명'].isin(top_types)]
                    
                    pie_chart = alt.Chart(pie_df).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta("count()"),
                        color=alt.Color("업태구분명", sort="descending"),
                        order=alt.Order("count()", sort="descending"),
                        tooltip=["업태구분명", "count()"]
                    ).properties(height=350)
                    st.altair_chart(pie_chart, use_container_width=True)
                else:
                    st.info("데이터 없음")
            
    # --- Tab 2: Mobile List ---
    with tab2:
        st.subheader("📱 영업 공략 리스트")
        
        # 1. Status Filter (Button Style)
        status_options = ["전체"] + sorted(list(df['영업상태명'].unique()))
        default_status = "영업/정상" if "영업/정상" in status_options else "전체"
        
        st.markdown("##### 영업상태")
        try:
            d_idx = status_options.index(default_status)
        except:
            d_idx = 0
            
        sel_status = st.radio("영업상태 선택", status_options, index=d_idx, horizontal=True, label_visibility="collapsed")
        
        # 2. Local Filters (Keyword)
        keyword = st.text_input("검색", placeholder="업체명 또는 주소...")
            
        # Filtering
        m_df = df.copy()
        if not sel_status: sel_status = "전체"
        
        if sel_status != "전체": m_df = m_df[m_df['영업상태명'] == sel_status]
        if keyword: m_df = m_df[m_df['사업장명'].str.contains(keyword, na=False) | m_df['소재지전체주소'].str.contains(keyword, na=False)]
        
        st.caption(f"조회 결과: {len(m_df):,}건")
        
        # Pagination
        ITEMS_PER_PAGE = 20
        if 'page' not in st.session_state: st.session_state.page = 0
        total_pages = max(1, (len(m_df)-1)//ITEMS_PER_PAGE + 1)
        
        # Display Cards
        start = st.session_state.page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        
        # Navigation
        col_p, col_n = st.columns([1,1])
        with col_p:
            if st.button("Previous Pages") and st.session_state.page > 0:
                st.session_state.page -= 1
                st.rerun()
        with col_n:
            if st.button("Next Pages") and st.session_state.page < total_pages - 1:
                st.session_state.page += 1
                st.rerun()
                
        # Card Loop
        for idx, row in m_df.iloc[start:end].iterrows():
            status_cls = "status-open" if row['영업상태명'] == '영업/정상' else "status-closed"
            tel = row['소재지전화'] if pd.notna(row['소재지전화']) else ""
            
            # HTML Card
            st.markdown(f"""
            <div class="card-container">
                <div class="card-title">
                    {row['사업장명']}
                    <div class="card-badges">
                        <span class="status-badge {status_cls}">{row['영업상태명']}</span>
                    </div>
                </div>
                <div class="card-meta">
                    {row['업태구분명']} | {row['평수']}평 | {row['관리지사']} ({row['SP담당']})
                </div>
                <div class="card-address">
                    📍 {row['소재지전체주소']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Native Streamlit Buttons for actions (simulating staying in card)
            b1, b2, b3 = st.columns([1,1,2])
            with b1:
                if tel:
                    st.link_button("📞 전화", f"tel:{tel}", use_container_width=True)
                else:
                    st.button("📞 번호없음", disabled=True, key=f"no_call_{idx}", use_container_width=True)
            with b2:
                # Use Naver Map search
                st.link_button("🗺️ 지도", f"https://map.naver.com/v5/search/{row['소재지전체주소']}", use_container_width=True)
            with b3:
                # Naver Search
                st.link_button("🔍 네이버 검색", f"https://search.naver.com/search.naver?query={row['사업장명']}", use_container_width=True)
    
    # --- Tab 3: Data Grid ---
    with tab3:
        st.markdown("### 📋 전체 데이터")
        
        # 1. Custom Sort Order for Branch
        # '중앙지사', '강북지사', ... etc (User provided order)
        custom_branch_order = [
            '중앙지사', '강북지사', '서대문지사', '고양지사', '의정부지사', 
            '남양주지사', '강릉지사', '원주지사', '미지정'
        ]
        
        # Create a categorical type for sorting
        df['관리지사'] = pd.Categorical(df['관리지사'], categories=custom_branch_order, ordered=True)
        
        # Sort by Branch (Custom) -> Manager -> Business Type
        df_sorted = df.sort_values(by=['관리지사', 'SP담당', '업태구분명'])
        
        # 2. Select & Reorder Columns
        display_cols = [
            '관리지사', 'SP담당', '업태구분명', '사업장명', 
            '소재지전체주소', '평수', '폐업일자', '인허가일자'
        ]
        
        # Ensure columns exist (handle potential missing ones gracefully)
        final_cols = [c for c in display_cols if c in df_sorted.columns]
        df_display = df_sorted[final_cols]
        
        # Display
        st.dataframe(
            df_display, 
            use_container_width=True, 
            height=600,
            column_config={
                "평수": st.column_config.NumberColumn(format="%.1f평"),
                "인허가일자": st.column_config.DateColumn(format="YYYY-MM-DD"),
                "폐업일자": st.column_config.DateColumn(format="YYYY-MM-DD"),
            }
        )
        
        # CSV Download (cp949 for Excel/Korean compatibility)
        csv = df_display.to_csv(index=False, encoding='cp949').encode('cp949')
        st.download_button("📥 CSV 다운로드", csv, "영업기회_처리결과.csv", "text/csv")

else:
    # Landing Page
    st.info("👈 사이드바에서 데이터를 업로드하거나, '자동 감지' 기능을 확인하세요.")
    st.markdown("""
    ### 🚀 시작하기
    1. **자동 모드**: `data/` 폴더에 파일이 있으면 자동으로 불러옵니다.
    2. **수동 모드**: 언제든지 사이드바에서 파일을 직접 업로드할 수 있습니다.
    
    > **Tip**: 모바일 접속 시 '홈 화면에 추가'하여 앱처럼 사용하세요!
    """)
