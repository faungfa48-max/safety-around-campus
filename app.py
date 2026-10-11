import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# ตั้งค่าหน้าเว็บเป็นแบบ Wide Screen
st.set_page_config(page_title="Campus Safety Dashboard", layout="wide", initial_sidebar_state="expanded")

# 1. โหลดข้อมูลจากไฟล์ Excel ทุก Sheet (Zone A - E)
@st.cache_data
def load_data():
    file_path = "3-compressed.xlsx"
    xls = pd.ExcelFile(file_path, engine='openpyxl')
    all_dfs = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet, header=1)
        df['Zone'] = sheet
        all_dfs.append(df)
    combined_df = pd.concat(all_dfs, ignore_index=True)
    # คัดกรองข้อมูลที่มีพิกัดครบถ้วน
    combined_df = combined_df.dropna(subset=['Latitude', 'Longitude'])
    return combined_df

df = load_data()

# 2. Sidebar สำหรับ Filter
st.sidebar.title("🔍 Filters")
selected_zone = st.sidebar.multiselect("เลือก Zone", options=df['Zone'].unique(), default=df['Zone'].unique())
selected_category = st.sidebar.multiselect("เลือก Category", options=df['Category'].dropna().unique(), default=df['Category'].dropna().unique())
selected_condition = st.sidebar.multiselect("เลือก Condition", options=['Good', 'Poor'], default=['Good', 'Poor'])

# กรองข้อมูลตามที่เลือก
filtered_df = df[
    (df['Zone'].isin(selected_zone)) &
    (df['Category'].isin(selected_category)) &
    (df['Condition'].isin(selected_condition))
]

# 3. Header & KPI Metrics
st.title("🛡️ CAMPUS SAFETY DASHBOARD")
st.subheader("Safety Around Campus - Senior Project")

col1, col2, col3, col4 = st.columns(4)
total_assets = len(filtered_df)
poor_count = len(filtered_df[filtered_df['Condition'] == 'Poor'])
safety_score = round((1 - (poor_count / total_assets if total_assets > 0 else 0)) * 100, 1)
top_category = filtered_df[filtered_df['Condition'] == 'Poor']['Category'].mode()[0] if poor_count > 0 else "None"

col1.metric("Total Assets Surveyed", f"{total_assets} จุด")
col2.metric("Campus Safety Score", f"{safety_score}%")
col3.metric("Active Risk Points (Poor)", f"{poor_count} จุด")
col4.metric("Highest Risk Category", top_category)

st.markdown("---")

# 4. แผนที่ Interactive (Folium Map)
map_col, chart_col = st.columns([2, 1])

with map_col:
    st.subheader("📍 Interactive Safety Map")
    avg_lat = filtered_df['Latitude'].mean() if len(filtered_df) > 0 else 20.045
    avg_lon = filtered_df['Longitude'].mean() if len(filtered_df) > 0 else 99.875
    
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=15, tiles="cartodb dark_matter")
    
    for idx, row in filtered_df.iterrows():
        color = "red" if row['Condition'] == 'Poor' else "green"
        problem_desc = row['Problem (อย่างละเอียด)'] if pd.notna(row['Problem (อย่างละเอียด)']) else 'ปกติ'
        popup_html = f"""
        <b>ID:</b> {row['Name ID']}<br>
        <b>Zone:</b> {row['Zone']}<br>
        <b>Category:</b> {row['Category']}<br>
        <b>Condition:</b> {row['Condition']}<br>
        <b>Problem:</b> {problem_desc}
        """
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=250)
        ).add_to(m)
        
    st_folium(m, width="100%", height=500)

with chart_col:
    st.subheader("📊 Risk Analytics")
    
    # Chart 1: Risk Points by Zone
    poor_df = filtered_df[filtered_df['Condition'] == 'Poor']
    if not poor_df.empty:
        fig_zone = px.bar(
            poor_df.groupby('Zone').size().reset_index(name='Count'),
            x='Zone', y='Count',
            title='จุดเสี่ยง (Poor) แยกตาม Zone',
            color_discrete_sequence=['#ff4d4d']
        )
        st.plotly_chart(fig_zone, use_container_width=True)
        
        # Chart 2: Risk by Category
        fig_cat = px.pie(
            poor_df, names='Category',
            title='สัดส่วนปัญหาตาม Category',
            hole=0.4
        )
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("ไม่พบจุดเสี่ยงในเงื่อนไขที่เลือก")

# 5. ตารางแสดงรายการปัญหา
st.subheader("📋 Active Campus Issues List")
st.dataframe(
    filtered_df[['Zone', 'Road ID', 'Name ID', 'Category', 'Condition', 'Problem (อย่างละเอียด)']],
    use_container_width=True
)
