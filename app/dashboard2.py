import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from configparser import ConfigParser
from pg_utils import get_connection
from datetime import datetime, timedelta
import numpy as np

# ---------- CONFIG ----------
config = ConfigParser()
config.read("config.ini")

DB = config["DATABASE"]

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="💰 Expense Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- CUSTOM CSS ----------
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Poppins', sans-serif;
    }
    
    /* Main Background with Financial Theme Gradient */
    .stApp {
        background: linear-gradient(135deg, #1a472a 0%, #2d5a3d 25%, #1e3a2f 75%, #0f2419 100%);
        background-attachment: fixed;
    }
    
    /* Glassmorphism Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.6);
    }
    
    /* Title Styling */
    h1 {
        color: #FFD700;
        font-weight: 700;
        text-align: center;
        font-size: 3rem;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.5);
    }
    
    h2, h3 {
        color: #FFD700;
        font-weight: 600;
        text-shadow: 1px 1px 4px rgba(0,0,0,0.3);
    }
    
    h4 {
        color: #90EE90;
        font-weight: 600;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
    }
    
    /* Metric Values */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #FFD700;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1rem;
        color: rgba(255, 255, 255, 0.95);
        font-weight: 500;
    }
    
    /* Filter Section */
    .stMultiSelect, .stDateInput, .stSlider {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a472a 0%, #0f2419 100%);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
    }
    
    /* Chat Messages */
    .chat-message {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
    }
    
    .user-message {
        background: rgba(144, 238, 144, 0.2);
        border-left: 3px solid #90EE90;
    }
    
    .bot-message {
        background: rgba(255, 215, 0, 0.15);
        border-left: 3px solid #FFD700;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        color: #FFD700;
        font-weight: 600;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(144, 238, 144, 0.25);
        color: #90EE90;
    }
    
    /* Dataframe */
    .dataframe {
        background: rgba(255, 255, 255, 0.98) !important;
        border-radius: 10px;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2d5a3d 0%, #1a472a 100%);
        color: #FFD700;
        border: 1px solid rgba(255, 215, 0, 0.3);
        border-radius: 10px;
        padding: 10px 25px;
        font-weight: 600;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 20px rgba(255, 215, 0, 0.4);
        background: linear-gradient(135deg, #3a6e4d 0%, #2d5a3d 100%);
    }
    
    /* Info boxes */
    .stInfo {
        background: rgba(144, 238, 144, 0.15);
        border-left: 3px solid #90EE90;
    }
</style>
""", unsafe_allow_html=True)

# ---------- DB CONNECTION ----------
@st.cache_data(ttl=300)
def load_data():
    conn = get_connection()
    query = """
        SELECT
            txn_date,
            amount,
            category,
            txn_type,
            paid_to
        FROM expenses
        ORDER BY txn_date DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Add derived columns
    df['txn_date'] = pd.to_datetime(df['txn_date'])
    df['month'] = df['txn_date'].dt.to_period('M').astype(str)
    df['day_of_week'] = df['txn_date'].dt.day_name()
    df['week'] = df['txn_date'].dt.to_period('W').astype(str)
    
    return df

# ---------- HELPER FUNCTIONS ----------
from llm_query import chatbot_ans
def process_chatbot_query(query, df):
    """Process natural language queries about expenses"""
    query_lower = query.lower()
    # Initialize response
    response = ""
    try:
        response = chatbot_ans(query_lower)
    except Exception as e:
        response = f"❌ Sorry, I couldn't process that query. Error: {str(e)}"
    
    return response

# ---------- MAIN UI ----------
st.markdown("<h1>💰 Personal Expense Analytics Dashboard</h1>", unsafe_allow_html=True)

# Load data
df = load_data()

# ---------- SIDEBAR - CHATBOT ----------
with st.sidebar:
    st.markdown("### 🤖 Expense Assistant")
    st.markdown("Ask me anything about your expenses!")
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Chat input
    user_query = st.text_input("Your question:", key="chat_input", placeholder="e.g., How much did I spend on food?")
    
    if st.button("Ask", key="ask_button"):
        if user_query:
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            
            # Get bot response
            bot_response = process_chatbot_query(user_query, df)
            st.session_state.chat_history.append({"role": "bot", "content": bot_response})
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("---")
        st.markdown("### 💬 Conversation")
        for message in reversed(st.session_state.chat_history[-6:]):  # Show last 6 messages
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message">👤 {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message bot-message">🤖 {message["content"]}</div>', unsafe_allow_html=True)
    
    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

# ---------- PDF UPLOAD SECTION ----------
st.markdown("---")
st.markdown("### 📄 Upload Bank Statement PDF")

# Initialize session state for PDF upload
if 'pdf_password_required' not in st.session_state:
    st.session_state.pdf_password_required = False
if 'pdf_file_data' not in st.session_state:
    st.session_state.pdf_file_data = None
if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = None
if 'password_attempts' not in st.session_state:
    st.session_state.password_attempts = 0

col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload your bank statement PDF to automatically extract and categorize transactions"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)  # Spacing
    process_button = st.button("🚀 Process PDF", type="primary", disabled=uploaded_file is None)

# Handle PDF upload and processing
if uploaded_file is not None and process_button:
    st.session_state.pdf_file_data = uploaded_file.read()
    st.session_state.pdf_filename = uploaded_file.name
    st.session_state.pdf_password_required = True
    st.session_state.password_attempts = 0

# Password input if required
if st.session_state.pdf_password_required:
    st.markdown("#### 🔐 PDF Password Required")
    
    if st.session_state.password_attempts > 0:
        st.error(f"❌ Incorrect password. Attempt {st.session_state.password_attempts}/3")
    
    if st.session_state.password_attempts >= 3:
        st.error("🚫 Maximum password attempts reached. Please re-upload the PDF.")
        st.session_state.pdf_password_required = False
        st.session_state.pdf_file_data = None
        st.session_state.password_attempts = 0
    else:
        pdf_password = st.text_input(
            "Enter PDF password:",
            type="password",
            key=f"pdf_password_{st.session_state.password_attempts}"
        )
        
        col1, col2 = st.columns([1, 5])
        with col1:
            submit_password = st.button("Submit Password")
        with col2:
            cancel_upload = st.button("Cancel")
        
        if cancel_upload:
            st.session_state.pdf_password_required = False
            st.session_state.pdf_file_data = None
            st.session_state.password_attempts = 0
            st.rerun()
        
        if submit_password and pdf_password:
            # Save PDF temporarily
            import tempfile
            import os
            from extract_statement import extract_bank_statement
            from categorise_emails import categorize
            from normalize_functions import add_hash
            from pg_utils import insert_expense
            
            temp_pdf_path = None
            try:
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(st.session_state.pdf_file_data)
                    temp_pdf_path = tmp_file.name
                
                # Show loading spinner
                with st.spinner('🔄 Processing PDF... Please wait'):
                    try:
                        # Step 1: Extract transactions from PDF
                        pdf_result = extract_bank_statement(temp_pdf_path, pdf_password)
                        
                        if pdf_result and len(pdf_result) > 0:
                            # Step 2: Categorize transactions
                            categorized_result = categorize(pdf_result)
                            
                            # Step 3: Add hash
                            hashed_results = add_hash(categorized_result)
                            
                            # Step 4: Insert into database
                            insert_expense(hashed_results)
                            
                            # Success!
                            st.success(f"✅ Successfully processed {len(pdf_result)} transactions from {st.session_state.pdf_filename}!")
                            st.balloons()
                            
                            # Reset state
                            st.session_state.pdf_password_required = False
                            st.session_state.pdf_file_data = None
                            st.session_state.password_attempts = 0
                            
                            # Reload dashboard
                            st.info("🔄 Reloading dashboard with new data...")
                            import time
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.warning("⚠️ No transactions found in the PDF.")
                            st.session_state.pdf_password_required = False
                            st.session_state.pdf_file_data = None
                    
                    except Exception as e:
                        error_msg = str(e)
                        
                        # Check if it's a password error
                        if 'password' in error_msg.lower() or 'encrypted' in error_msg.lower():
                            st.session_state.password_attempts += 1
                            st.rerun()
                        else:
                            st.error(f"❌ Error processing PDF: {error_msg}")
                            st.session_state.pdf_password_required = False
                            st.session_state.pdf_file_data = None
            
            finally:
                # Clean up temporary file
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    try:
                        os.unlink(temp_pdf_path)
                    except:
                        pass


# ---------- FILTERS ----------
st.markdown("### 🔍 Filters")
col1, col2, col3, col4 = st.columns(4)

with col1:
    category_filter = st.multiselect(
        "📁 Category",
        options=sorted(df["category"].unique()),
        default=df["category"].unique()
    )

with col2:
    txn_type_filter = st.multiselect(
        "💳 Transaction Type",
        options=df["txn_type"].unique(),
        default=df["txn_type"].unique()
    )

with col3:
    date_range = st.date_input(
        "📅 Date Range",
        [df["txn_date"].min(), df["txn_date"].max()]
    )

with col4:
    amount_range = st.slider(
        "💵 Amount Range",
        min_value=float(df["amount"].min()),
        max_value=float(df["amount"].max()),
        value=(float(df["amount"].min()), float(df["amount"].max()))
    )

# Apply filters with validation
try:
    if len(category_filter) == 0 or len(txn_type_filter) == 0:
        st.warning("⚠️ Please select at least one category and transaction type to view data.")
        filtered_df = pd.DataFrame(columns=df.columns)
    else:
        filtered_df = df[
            (df["category"].isin(category_filter)) &
            (df["txn_type"].isin(txn_type_filter)) &
            (df["txn_date"].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))) &
            (df["amount"].between(amount_range[0], amount_range[1]))
        ]
except Exception as e:
    st.error("⚠️ Error applying filters. Please check your selections.")
    filtered_df = pd.DataFrame(columns=df.columns)

st.markdown("---")

# ---------- KPI METRICS ----------
st.markdown("### 📊 Key Metrics")

debit_df = filtered_df[filtered_df["txn_type"] == "Debit"] if len(filtered_df) > 0 else pd.DataFrame()
credit_df = filtered_df[filtered_df["txn_type"] == "Credit"] if len(filtered_df) > 0 else pd.DataFrame()

total_spent = debit_df["amount"].sum() if len(debit_df) > 0 else 0
total_received = credit_df["amount"].sum() if len(credit_df) > 0 else 0
net_balance = total_received - total_spent
txn_count = len(filtered_df)
avg_transaction = filtered_df["amount"].mean() if len(filtered_df) > 0 else 0
top_category = debit_df.groupby("category")["amount"].sum().idxmax() if len(debit_df) > 0 else "N/A"

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

with kpi1:
    # Debit should show red/negative indicator
    st.metric("💸 Total Spent", f"₹{total_spent:,.0f}", delta=f"-₹{total_spent:,.0f}", delta_color="inverse")

with kpi2:
    # Credit should show green/positive indicator
    st.metric("💰 Total Received", f"₹{total_received:,.0f}", delta=f"+₹{total_received:,.0f}", delta_color="normal")

with kpi3:
    # Net balance: positive = green, negative = red
    if net_balance >= 0:
        st.metric("📈 Net Balance", f"₹{net_balance:,.0f}", delta=f"+₹{abs(net_balance):,.0f}", delta_color="normal")
    else:
        st.metric("📉 Net Balance", f"₹{net_balance:,.0f}", delta=f"-₹{abs(net_balance):,.0f}", delta_color="inverse")

with kpi4:
    st.metric("🔢 Transactions", f"{txn_count:,}")

with kpi5:
    st.metric("📊 Avg Transaction", f"₹{avg_transaction:,.0f}")

with kpi6:
    st.metric("🏆 Top Category", top_category)

st.markdown("---")

# ---------- CHARTS IN TABS ----------
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Trends", "🔍 Deep Dive", "📋 Transactions"])

with tab1:
    # Row 1: Pie Chart and Bar Chart
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎯 Expenses by Category")
        if len(debit_df) > 0:
            category_totals = debit_df.groupby("category")["amount"].sum().reset_index()
            fig_pie = px.pie(
                category_totals,
                values="amount",
                names="category",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Oranges_r
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FFD700', size=12),
                showlegend=True,
                height=400
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No debit transactions in selected range")
    
    with col2:
        st.markdown("#### 📊 Monthly Comparison")
        monthly_data = filtered_df.groupby(['month', 'txn_type'])['amount'].sum().reset_index()
        fig_bar = px.bar(
            monthly_data,
            x='month',
            y='amount',
            color='txn_type',
            barmode='group',
            color_discrete_map={'Debit': '#FF6B6B', 'Credit': '#4CAF50'}
        )
        fig_bar.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FFD700'),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            height=400
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    
    # Row 2: Budget vs Actual Comparison
    st.markdown("#### 💰 Budget vs Actual Spending Comparison")
    
    # Initialize session state for budget configuration if not exists
    if 'budget_targets' not in st.session_state:
        st.session_state.budget_targets = {
            'Rent': 5000,
            'Food': 8000,
            'Grocery': 1000,
            'Petrol': 4000,
            'Sports': 1000,
            'Others': 1000
        }
    
    if 'category_mapping' not in st.session_state:
        st.session_state.category_mapping = {
            'Rent': ['Rent'],
            'Food': ['Food'],  # Special: Debit from Food - Credit from Person
            'Grocery': ['Grocery'],
            'Petrol': ['Petrol'],
            'Sports': ['Sports'],
            'Others': ['Clothing', 'Salon', 'Hospital']
        }
    
    # Get all available categories from the data
    all_categories = sorted(df['category'].unique().tolist())
    
    # Category Selection Section (Always Visible)
    st.markdown("##### 📁 Select Categories for Each Budget Group")
    
    cat_col1, cat_col2, cat_col3 = st.columns(3)
    
    with cat_col1:
        rent_cats = st.multiselect(
            "🏠 Rent Categories",
            options=all_categories,
            default=st.session_state.category_mapping['Rent'],
            key="rent_categories"
        )
        st.session_state.category_mapping['Rent'] = rent_cats
        
        food_cats = st.multiselect(
            "🍽️ Food Categories",
            options=all_categories,
            default=st.session_state.category_mapping['Food'],
            key="food_categories"
        )
        st.session_state.category_mapping['Food'] = food_cats
    
    with cat_col2:
        grocery_cats = st.multiselect(
            "🛒 Grocery Categories",
            options=all_categories,
            default=st.session_state.category_mapping['Grocery'],
            key="grocery_categories"
        )
        st.session_state.category_mapping['Grocery'] = grocery_cats
        
        petrol_cats = st.multiselect(
            "⛽ Petrol Categories",
            options=all_categories,
            default=st.session_state.category_mapping['Petrol'],
            key="petrol_categories"
        )
        st.session_state.category_mapping['Petrol'] = petrol_cats
    
    with cat_col3:
        sports_cats = st.multiselect(
            "⚽ Sports Categories",
            options=all_categories,
            default=st.session_state.category_mapping['Sports'],
            key="sports_categories"
        )
        st.session_state.category_mapping['Sports'] = sports_cats
        
        others_cats = st.multiselect(
            "📦 Others Categories",
            options=all_categories,
            default=st.session_state.category_mapping['Others'],
            key="others_categories"
        )
        st.session_state.category_mapping['Others'] = others_cats
    
    st.markdown("---")
    
    # Configuration section (collapsible) - for advanced settings
    with st.expander("⚙️ Advanced Settings - Adjust Budget Targets", expanded=False):
        st.markdown("**Customize your budget target amounts**")
        
        config_col1, config_col2, config_col3 = st.columns(3)
        
        with config_col1:
            rent_target = st.number_input(
                "🏠 Rent Target (₹)",
                min_value=0,
                value=st.session_state.budget_targets['Rent'],
                step=500,
                key="target_rent"
            )
            st.session_state.budget_targets['Rent'] = rent_target
            
            food_target = st.number_input(
                "🍽️ Food Target (₹)",
                min_value=0,
                value=st.session_state.budget_targets['Food'],
                step=500,
                key="target_food"
            )
            st.session_state.budget_targets['Food'] = food_target
        
        with config_col2:
            grocery_target = st.number_input(
                "🛒 Grocery Target (₹)",
                min_value=0,
                value=st.session_state.budget_targets['Grocery'],
                step=500,
                key="target_grocery"
            )
            st.session_state.budget_targets['Grocery'] = grocery_target
            
            petrol_target = st.number_input(
                "⛽ Petrol Target (₹)",
                min_value=0,
                value=st.session_state.budget_targets['Petrol'],
                step=500,
                key="target_petrol"
            )
            st.session_state.budget_targets['Petrol'] = petrol_target
        
        with config_col3:
            sports_target = st.number_input(
                "⚽ Sports Target (₹)",
                min_value=0,
                value=st.session_state.budget_targets['Sports'],
                step=500,
                key="target_sports"
            )
            st.session_state.budget_targets['Sports'] = sports_target
            
            others_target = st.number_input(
                "📦 Others Target (₹)",
                min_value=0,
                value=st.session_state.budget_targets['Others'],
                step=500,
                key="target_others"
            )
            st.session_state.budget_targets['Others'] = others_target

        
        # Display current configuration summary
        st.markdown("---")
        st.markdown("##### 📊 Current Configuration")
        total_budget = sum(st.session_state.budget_targets.values())
        st.info(f"**Total Monthly Budget:** ₹{total_budget:,.0f}")
        
        config_summary = []
        for budget_cat, target in st.session_state.budget_targets.items():
            categories = ", ".join(st.session_state.category_mapping[budget_cat]) if st.session_state.category_mapping[budget_cat] else "None"
            config_summary.append(f"- **{budget_cat}** (₹{target:,}): {categories}")
        
        st.markdown("\n".join(config_summary))
    
    
    # Calculate actual spending for each budget category
    # Use date-filtered data to respect the date range filter
    # Filter data by selected date range
    date_filtered_df = df[
        (df["txn_date"] >= pd.Timestamp(date_range[0])) &
        (df["txn_date"] <= pd.Timestamp(date_range[1]))
    ]
    
    debit_df_budget = date_filtered_df[date_filtered_df["txn_type"] == "Debit"]
    credit_df_budget = date_filtered_df[date_filtered_df["txn_type"] == "Credit"]
    
    budget_data = []
    
    for budget_cat, target in st.session_state.budget_targets.items():
        # Get categories that belong to this budget category
        categories = st.session_state.category_mapping[budget_cat]
        
        # Special calculation for Food: Debit from 'Food' - Credit from 'Person'
        if budget_cat == 'Food':
            food_debit = debit_df_budget[debit_df_budget['category'] == 'Food']['amount'].sum()
            #person_credit = int(round((credit_df_budget[credit_df_budget['category'] == 'Person']['amount'].sum())/4))
            actual = food_debit
        else:
            # Standard calculation for other categories
            cat_debit = debit_df_budget[debit_df_budget['category'].isin(categories)]['amount'].sum() if categories else 0
            cat_credit = credit_df_budget[credit_df_budget['category'].isin(categories)]['amount'].sum() if categories else 0
            actual = cat_debit - cat_credit
        
        # Calculate variance
        variance = target - actual
        variance_pct = (variance / target * 100) if target > 0 else 0
        
        budget_data.append({
            'Category': budget_cat,
            'Target': target,
            'Actual': actual,
            'Variance': variance,
            'Variance %': variance_pct,
            'Status': 'Over Budget' if variance < 0 else 'Under Budget'
        })
    
    budget_df = pd.DataFrame(budget_data)
    
    # Create grouped bar chart
    fig_budget = go.Figure()
    
    # Add Target bars
    fig_budget.add_trace(go.Bar(
        name='Target',
        x=budget_df['Category'],
        y=budget_df['Target'],
        marker_color='#4CAF50',
        text=budget_df['Target'].apply(lambda x: f'₹{x:,.0f}'),
        textposition='outside',
        textfont=dict(color='#FFD700', size=11)
    ))
    
    # Add Actual bars with conditional coloring
    colors = ['#FF6B6B' if v > 0 else '#90EE90' for v in budget_df['Variance']]
    
    fig_budget.add_trace(go.Bar(
        name='Actual',
        x=budget_df['Category'],
        y=budget_df['Actual'],
        marker_color=colors,
        text=budget_df['Actual'].apply(lambda x: f'₹{x:,.0f}'),
        textposition='outside',
        textfont=dict(color='#FFD700', size=11)
    ))
    
    fig_budget.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#FFD700'),
        xaxis=dict(showgrid=False, title='Budget Category'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', title='Amount (₹)'),
        barmode='group',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color='#FFD700')
        )
    )
    
    st.plotly_chart(fig_budget, use_container_width=True)
    
    # Display budget summary table
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("##### 📊 Budget Summary")
        summary_df = budget_df[['Category', 'Target', 'Actual', 'Variance', 'Status']].copy()
        summary_df['Target'] = summary_df['Target'].apply(lambda x: f'₹{x:,.0f}')
        summary_df['Actual'] = summary_df['Actual'].apply(lambda x: f'₹{x:,.0f}')
        summary_df['Variance'] = summary_df['Variance'].apply(lambda x: f'₹{x:,.0f}')
        
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Category": "Budget Category",
                "Target": "Target",
                "Actual": "Actual Spent",
                "Variance": "Variance",
                "Status": "Status"
            }
        )
    
    with col2:
        st.markdown("##### 💡 Budget Insights")
        total_target = sum(st.session_state.budget_targets.values())
        total_actual = budget_df['Actual'].sum()
        total_variance = total_actual - total_target
        
        st.metric("Total Budget", f"₹{total_target:,.0f}")
        st.metric("Total Spent", f"₹{total_actual:,.0f}")
        
        if total_variance > 0:
            st.metric("Overall Status", f"₹{abs(total_variance):,.0f}", delta=f"Over by {abs(total_variance):,.0f}", delta_color="inverse")
        else:
            st.metric("Overall Status", f"₹{abs(total_variance):,.0f}", delta=f"Under by {abs(total_variance):,.0f}", delta_color="normal")




with tab2:
    # Row 1: Line Chart
    st.markdown("#### 📈 Daily Expense Trend")
    daily_expenses = debit_df.groupby("txn_date")["amount"].sum().reset_index()
    fig_line = px.area(
        daily_expenses,
        x="txn_date",
        y="amount",
        color_discrete_sequence=['#FF6B6B']
    )
    fig_line.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#FFD700'),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        height=400
    )
    st.plotly_chart(fig_line, use_container_width=True)
    
    # Row 2: Two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📅 Spending by Day of Week")
        dow_data = debit_df.groupby("day_of_week")["amount"].sum().reset_index()
        # Order days properly
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_data['day_of_week'] = pd.Categorical(dow_data['day_of_week'], categories=day_order, ordered=True)
        dow_data = dow_data.sort_values('day_of_week')
        
        fig_dow = px.bar(
            dow_data,
            x='day_of_week',
            y='amount',
            color='amount',
            color_continuous_scale='OrRd'
        )
        fig_dow.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FFD700'),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig_dow, use_container_width=True)
    
    with col2:
        st.markdown("#### 💹 Cumulative Spending")
        cumulative = daily_expenses.copy()
        cumulative['cumulative'] = cumulative['amount'].cumsum()
        
        fig_cum = px.line(
            cumulative,
            x='txn_date',
            y='cumulative',
            color_discrete_sequence=['#FFA500']
        )
        fig_cum.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FFD700'),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            height=400
        )
        st.plotly_chart(fig_cum, use_container_width=True)

with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📦 Box Plot - Amount Distribution")
        fig_box = px.box(
            debit_df,
            y='amount',
            x='category',
            color='category',
            color_discrete_sequence=px.colors.sequential.Oranges
        )
        fig_box.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FFD700'),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig_box, use_container_width=True)
    
    with col2:
        sunburst_df = debit_df.copy()
        sunburst_df.loc[
            sunburst_df['category'].str.upper() == 'SIP',
            'paid_to'
        ] = 'SIP Investment'
        st.markdown("#### 🌅 Sunburst Chart")

        if len(debit_df) > 0:
            sunburst_df = debit_df.copy()

            sunburst_df['paid_to'] = (
                sunburst_df['paid_to']
                .fillna('Unknown')
                .replace('', 'Unknown')
            )

            sunburst_df.loc[
                sunburst_df['category'].str.upper() == 'SIP',
                'paid_to'
            ] = 'SIP Investment'

            fig_sunburst = px.sunburst(
                sunburst_df,
                path=['category', 'paid_to'],
                values='amount',
                color='amount',
                color_continuous_scale='YlOrRd'
            )

            fig_sunburst.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FFD700'),
                height=400
            )

            st.plotly_chart(fig_sunburst, use_container_width=True)
        else:
            st.info("No data available")

        # st.markdown("#### 🌅 Sunburst Chart")
        # if len(debit_df) > 0:
        #     fig_sunburst = px.sunburst(
        #         debit_df,
        #         path=['category', 'paid_to'],
        #         values='amount',
        #         color='amount',
        #         color_continuous_scale='YlOrRd'
        #     )
        #     fig_sunburst.update_layout(
        #         plot_bgcolor='rgba(0,0,0,0)',
        #         paper_bgcolor='rgba(0,0,0,0)',
        #         font=dict(color='#FFD700'),
        #         height=400
        #     )
        #     st.plotly_chart(fig_sunburst, use_container_width=True)
        # else:
        #     st.info("No data available")
    
    # Waterfall Chart
    st.markdown("#### 💧 Cash Flow Waterfall")
    if len(filtered_df) > 0:
        monthly_flow = filtered_df.groupby(['month', 'txn_type'])['amount'].sum().unstack(fill_value=0)
        
        if 'Credit' in monthly_flow.columns and 'Debit' in monthly_flow.columns:
            monthly_flow['Net'] = monthly_flow['Credit'] - monthly_flow['Debit']
            
            fig_waterfall = go.Figure(go.Waterfall(
                x=monthly_flow.index,
                y=monthly_flow['Net'],
                connector={"line": {"color": "rgba(255,255,255,0.5)"}},
                increasing={"marker": {"color": "#4CAF50"}},
                decreasing={"marker": {"color": "#FF6B6B"}},
                totals={"marker": {"color": "#FFD700"}}
            ))
            
            fig_waterfall.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#FFD700'),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                height=400
            )
            st.plotly_chart(fig_waterfall, use_container_width=True)
        else:
            st.info("Insufficient data for waterfall chart")

with tab4:
    st.markdown("#### 📋 Transaction Details")
    
    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Total Transactions:** {len(filtered_df)}")
    with col2:
        if len(filtered_df) > 0:
            st.markdown(f"**Date Range:** {filtered_df['txn_date'].min().strftime('%Y-%m-%d')} to {filtered_df['txn_date'].max().strftime('%Y-%m-%d')}")
        else:
            st.markdown(f"**Date Range:** N/A")
    with col3:
        st.markdown(f"**Categories:** {filtered_df['category'].nunique()}")
    
    # Display dataframe
    if len(filtered_df) > 0:
        display_df = filtered_df[['txn_date', 'category', 'txn_type', 'amount', 'paid_to']].copy()
        display_df['txn_date'] = display_df['txn_date'].dt.strftime('%Y-%m-%d')
        display_df = display_df.sort_values('txn_date', ascending=False)
    else:
        display_df = pd.DataFrame(columns=['txn_date', 'category', 'txn_type', 'amount', 'paid_to'])
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            "txn_date": "Date",
            "category": "Category",
            "txn_type": "Type",
            "amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
            "paid_to": "Paid To"
        }
    )
    
    # Top Spenders
    st.markdown("#### 🏆 Top 10 Payees")
    top_payees = debit_df.groupby('paid_to')['amount'].sum().sort_values(ascending=False).head(10).reset_index()
    
    fig_top = px.bar(
        top_payees,
        x='amount',
        y='paid_to',
        orientation='h',
        color='amount',
        color_continuous_scale='Reds'
    )
    fig_top.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#FFD700'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=False),
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_top, use_container_width=True)

# ---------- FOOTER ----------
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: rgba(255, 215, 0, 0.7);'>💰 Personal Expense Dashboard | Built with Streamlit & Plotly</p>",
    unsafe_allow_html=True
)
