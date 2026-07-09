import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import re
import requests
from io import BytesIO

# --- 1. CONFIGURATION & STYLING (BLUE THEME) ---
st.set_page_config(page_title="AI Live Reporter", layout="wide", initial_sidebar_state="expanded")

# Inject Custom CSS for Blue Theme, Layout, and Logout Button
st.markdown("""
    <style>
        /* Global Blue Theme Base */
        :root {
            --primary: #1E3A8A;
            --background: #F0F4F8;
        }
        .stApp {
            background-color: #F0F4F8;
        }
        /* Headers and Text */
        h1, h2, h3, p {
            color: #0F172A;
            font-family: 'Segoe UI', Roboto, sans-serif;
        }
        /* Buttons */
        .stButton>button {
            background-color: #2563EB !important;
            color: white !important;
            border-radius: 6px !important;
            border: none !important;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #1D4ED8 !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        }
        /* Top Left Logout Icon Styles */
        .logout-container {
            position: absolute;
            top: -40px;
            left: 0px;
            z-index: 99999;
        }
        .logout-btn {
            background-color: #EF4444 !important;
            color: white !important;
            border-radius: 50% !important;
            width: 40px !important;
            height: 40px !important;
            padding: 0 !important;
            line-height: 40px !important;
            font-size: 18px !important;
            border: none !important;
            cursor: pointer;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize Session States
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'auth_page' not in st.session_state:
    st.session_state.auth_page = 'login'
if 'user_db' not in st.session_state:
    st.session_state.user_db = {"manager@company.com": "Password123"} # Mock Database
if 'last_data_hash' not in st.session_state:
    st.session_state.last_data_hash = None

# --- 2. AUTHENTICATION FUNCTIONS ---
def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True

@st.cache_data(ttl=60)
def load_data_from_url(url):
    try:
        # Handle GitHub raw link conversion automatically
        if "github.com" in url and "/blob/" in url:
            url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        
        response = requests.get(url)
        response.raise_for_status()
        
        if url.endswith('.csv'):
            df = pd.read_csv(BytesIO(response.content))
        else:
            df = pd.read_excel(BytesIO(response.content))
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def generate_ai_summary(df):
    # Configure Gemini API (Ensure GEMINI_API_KEY is set in Render Environment Variables)
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return "• **AI Notice**: Please configure `GEMINI_API_KEY` in secrets or environment variables to generate automated executive insights."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Create a compact summary metadata prompt for the AI
        data_profile = f"Columns: {list(df.columns)}\nShape: {df.shape}\nData Description:\n{df.describe(include='all').to_string()}"
        prompt = f"Provide a professional, executive summary of this dataset in bullet points. Highlight trends, anomalies, and key KPIs:\n\n{data_profile}"
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"• **AI Error**: Unable to generate summary at this moment. ({str(e)})"

# --- 3. UI RENDERING SYSTEM ---

# LOGOUT BUTTON ROUTINE
if st.session_state.logged_in:
    with st.sidebar:
        st.markdown('<div class="logout-container">', unsafe_allow_html=True)
        if st.button("❌", help="Log Out"):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# AUTHENTICATION SCREEN
if not st.session_state.logged_in:
    st.title("Enterprise AI Analytics Portal")
    
    if st.session_state.auth_page == 'login':
        st.subheader("Login to Your Account")
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Log In"):
                if email in st.session_state.user_db and st.session_state.user_db[email] == password:
                    st.session_state.logged_in = True
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
        
        st.markdown("---")
        st.markdown("🌐 **OAuth Fast-Login Options:**")
        col_g, col_a, col_gh = st.columns(3)
        with col_g: st.button("Continue with Google")
        with col_a: st.button("Continue with Apple")
        with col_gh: st.button("Continue with GitHub")
        
        st.markdown("---")
        if st.button("Don't have an account? Sign Up"):
            st.session_state.auth_page = 'signup'
            st.rerun()
        if st.button("Forgot Password?"):
            st.session_state.auth_page = 'forgot'
            st.rerun()

    elif st.session_state.auth_page == 'signup':
        st.subheader("Create a New Account")
        new_email = st.text_input("Enter Email Address")
        new_password = st.text_input("Create Password", type="password")
        st.caption("Password requirements: Min 8 characters, must include uppercase, lowercase, and digits.")
        
        if st.button("Register Account"):
            if new_email in st.session_state.user_db:
                st.error("Email already registered.")
            elif not validate_password(new_password):
                st.error("Password does not meet the complexity requirements.")
            else:
                st.session_state.user_db[new_email] = new_password
                st.success("Registration successful! Please log in.")
                st.session_state.auth_page = 'login'
                st.rerun()
                
        if st.button("Back to Login"):
            st.session_state.auth_page = 'login'
            st.rerun()

    elif st.session_state.auth_page == 'forgot':
        st.subheader("Reset Password")
        reset_email = st.text_input("Enter your registered Email Address")
        if st.button("Send Reset Link"):
            if reset_email in st.session_state.user_db:
                st.success(f"A secure password reset link has been dispatched to {reset_email}.")
            else:
                st.error("Email address not found in our system.")
                
        if st.button("Back to Login"):
            st.session_state.auth_page = 'login'
            st.rerun()

# CORE APPLICATION SCREEN
else:
    st.title("Live Data Engine & AI Analytics Dashboard")
    
    # Live data sync auto-refresh interval configuration
    st.sidebar.header("🔄 Live Synchronization Sync")
    refresh_rate = st.sidebar.slider("Polling interval (seconds)", min_value=5, max_value=60, value=10)
    
    # Input File Configuration
    data_url = st.text_input("Enter Live Excel / CSV Data Link (GitHub Raw or Public URL Direct Link):", 
                             value="https://raw.githubusercontent.com/plotly/datasets/master/2014_usa_states.csv")
    
    if data_url:
        raw_df = load_data_from_url(data_url)
        
        if raw_df is not None:
            # Check for live record hash update detection
            current_hash = hash(raw_df.to_string())
            if st.session_state.last_data_hash != current_hash:
                st.session_state.last_data_hash = current_hash
                st.toast("Data sync updated successfully!", icon="🔄")
            
            # --- 4. CUSTOMIZATION & DATA MANIPULATION CONTROLS ---
            st.markdown("### 🛠️ Workspace Controls (Filter, Row/Column Join & Drops)")
            
            with st.expander("Configure Matrix Transformations", expanded=False):
                # Column Dropping Layout
                all_cols = list(raw_df.columns)
                selected_cols = st.multiselect("Select columns to retain in target workspace view:", default=all_cols, options=all_cols)
                working_df = raw_df[selected_cols]
                
                # Rows Filtering Manipulation
                row_indices = st.slider("Select Row Range Matrix:", 0, len(working_df), (0, len(working_df)))
                working_df = working_df.iloc[row_indices[0]:row_indices[1]]
                
                # Column Merging / Aggregation Operations Simulation
                st.markdown("**Combine Data Columns (Mathematical Aggregation)**")
                join_col1 = st.selectbox("Select Column 1:", options=["None"] + list(working_df.columns), index=0)
                join_col2 = st.selectbox("Select Column 2:", options=["None"] + list(working_df.columns), index=0)
                new_col_name = st.text_input("Merged Column Output Title:", value="Merged_Metric")
                
                if join_col1 != "None" and join_col2 != "None":
                    try:
                        working_df[new_col_name] = working_df[join_col1].astype(str) + " | " + working_df[join_col2].astype(str)
                        st.success(f"Columns successfully joined into '{new_col_name}'!")
                    except Exception as ex:
                        st.error(f"Aggregation failure: {ex}")

            # --- 5. RENDER SYSTEM AND DATA SHOWCASE ---
            st.markdown("### Active Synchronized Datatable Window")
            st.dataframe(working_df, use_container_width=True)
            
            # Layout Setup for AI Summaries and Graphical Displays
            st.markdown("### AI Automated Business Summary Insights")
            ai_summary_box = generate_ai_summary(working_df)
            st.info(ai_summary_box)
            
            st.markdown("### Interactive Business Reporting Visualizations")
            numeric_cols = working_df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = working_df.select_dtypes(include=['object']).columns.tolist()
            
            if len(numeric_cols) >= 1:
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    x_axis = st.selectbox("Select X-Axis Data Plane:", options=working_df.columns.tolist(), index=0)
                    y_axis = st.selectbox("Select Y-Axis Performance Metric:", options=numeric_cols, index=0)
                    
                    fig1 = px.bar(working_df, x=x_axis, y=y_axis, title=f"{y_axis} Distribution Analysis", template="plotly_white")
                    fig1.update_layout(marker_color='#2563EB')
                    st.plotly_chart(fig1, use_container_width=True)
                    
                    # JPEG Export functionality
                    img_bytes1 = fig1.to_image(format="jpeg")
                    st.download_button(label="📥 Save Chart as JPEG", data=img_bytes1, file_name="bar_reporting_chart.jpeg", mime="image/jpeg")
                    
                with chart_col2:
                    if len(numeric_cols) >= 2:
                        y_axis_2 = st.selectbox("Select Comparison Trend Line Metric:", options=numeric_cols, index=min(1, len(numeric_cols)-1))
                        fig2 = px.line(working_df, x=x_axis, y=y_axis_2, title=f"{y_axis_2} Timeline Progression Analysis", template="plotly_white")
                        fig2.update_traces(line_color='#1D4ED8')
                        st.plotly_chart(fig2, use_container_width=True)
                        
                        img_bytes2 = fig2.to_image(format="jpeg")
                        st.download_button(label="📥 Save Chart as JPEG", data=img_bytes2, file_name="line_reporting_chart.jpeg", mime="image/jpeg")
                    else:
                        st.warning("Provide additional numeric columns within the worksheet to unlock comparison analytics layout frames.")
            else:
                st.error("The selected working data model fields do not contain numeric structured elements to chart reports.")
                
            # Setup periodic background trigger for continuous real-time execution polling
            st.empty()
            st.fragment(st.rerun)()
