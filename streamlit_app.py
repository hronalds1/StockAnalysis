import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import random
import yfinance as yf
import pandas as pd
from io import BytesIO
import json

# Initialize session state for lists
if 'saved_lists' not in st.session_state:
    st.session_state.saved_lists = {}
if 'current_tickers' not in st.session_state:
    st.session_state.current_tickers = []

st.set_page_config(page_title="Stock Analysis Tool", layout="wide")

# Functions from original program
def get_stock_ratios(tickers):
    # [Previous get_stock_ratios code remains the same]
    [... Your existing get_stock_ratios function ...]

# Sidebar navigation
st.sidebar.title("Stock Analysis Tool")
page = st.sidebar.radio("Choose Operation:", 
    ["Quick Analysis",
     "Manage Lists",
     "Load Saved List",
     "Edit Current List",
     "Save Current List",
     "Delete Lists"])

# Main area
if page == "Quick Analysis":
    st.header("Quick Stock Analysis")
    
    # Input method selection
    input_method = st.radio("Choose input method:", ["Enter Tickers", "Upload File"])
    
    tickers = []
    if input_method == "Enter Tickers":
        ticker_input = st.text_area("Enter stock tickers (space-separated):", "")
        if ticker_input:
            tickers = [t.strip().upper() for t in ticker_input.split() if t.strip()]
    else:
        uploaded_file = st.file_uploader("Upload a file with tickers (one per line)", type=["txt"])
        if uploaded_file:
            tickers = [line.decode("utf-8").strip().upper() for line in uploaded_file if line.decode("utf-8").strip()]

    if st.button("Analyze Stocks") and tickers:
        st.session_state.current_tickers = tickers  # Save to current list
        results = get_stock_ratios(tickers)
        
        # Create DataFrame
        df = pd.DataFrame(results, columns=[
            "Ticker", "Forward P/E", "Yahoo PEG", "Calc PEG", "Price/Sales",
            "Qtrly Rev Growth YoY", "Qtrly Rev Growth QoQ", "1Y Rev Growth Est",
            "5Y Rev Growth Est"
        ])
        
        # Display results
        st.write("Analysis Results:")
        st.dataframe(df)
        
        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name="stock_analysis.csv",
                mime="text/csv"
            )
        
        with col2:
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Stock Analysis')
            
            st.download_button(
                label="Download as Excel",
                data=excel_buffer.getvalue(),
                file_name="stock_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

elif page == "Manage Lists":
    st.header("Manage Stock Lists")
    st.write("Current List:", ", ".join(st.session_state.current_tickers) if st.session_state.current_tickers else "No tickers in current list")
    
    new_tickers = st.text_area("Enter new tickers (space-separated):")
    if st.button("Create New List"):
        if new_tickers:
            st.session_state.current_tickers = [t.strip().upper() for t in new_tickers.split() if t.strip()]
            st.success("New list created!")
            st.experimental_rerun()

elif page == "Load Saved List":
    st.header("Load Saved List")
    if st.session_state.saved_lists:
        list_names = list(st.session_state.saved_lists.keys())
        selected_list = st.selectbox("Choose a list to load:", list_names)
        if st.button("Load List"):
            st.session_state.current_tickers = st.session_state.saved_lists[selected_list]
            st.success(f"Loaded list: {selected_list}")
            st.write("Loaded tickers:", ", ".join(st.session_state.current_tickers))
    else:
        st.info("No saved lists available.")

elif page == "Edit Current List":
    st.header("Edit Current List")
    st.write("Current List:", ", ".join(st.session_state.current_tickers) if st.session_state.current_tickers else "No tickers in current list")
    
    col1, col2 = st.columns(2)
    with col1:
        remove_tickers = st.text_area("Remove tickers (space-separated):")
        if st.button("Remove Tickers"):
            if remove_tickers.upper() == "ALL":
                st.session_state.current_tickers = []
            else:
                to_remove = [t.strip().upper() for t in remove_tickers.split()]
                st.session_state.current_tickers = [t for t in st.session_state.current_tickers if t not in to_remove]
            st.experimental_rerun()
    
    with col2:
        add_tickers = st.text_area("Add tickers (space-separated):")
        if st.button("Add Tickers"):
            new_tickers = [t.strip().upper() for t in add_tickers.split()]
            st.session_state.current_tickers.extend([t for t in new_tickers if t not in st.session_state.current_tickers])
            st.experimental_rerun()

elif page == "Save Current List":
    st.header("Save Current List")
    if st.session_state.current_tickers:
        list_name = st.text_input("Enter a name for this list:")
        if st.button("Save List") and list_name:
            st.session_state.saved_lists[list_name] = st.session_state.current_tickers
            st.success(f"List '{list_name}' saved successfully!")
    else:
        st.warning("No tickers in current list to save.")

elif page == "Delete Lists":
    st.header("Delete Saved Lists")
    if st.session_state.saved_lists:
        lists_to_delete = st.multiselect(
            "Select lists to delete:",
            options=list(st.session_state.saved_lists.keys())
        )
        if st.button("Delete Selected Lists"):
            for list_name in lists_to_delete:
                del st.session_state.saved_lists[list_name]
            st.success("Selected lists deleted!")
            st.experimental_rerun()
    else:
        st.info("No saved lists to delete.")

# Show current list status in sidebar
st.sidebar.write("---")
st.sidebar.write("Current List:")
st.sidebar.write(", ".join(st.session_state.current_tickers) if st.session_state.current_tickers else "No tickers selected")

# Instructions
if not st.session_state.current_tickers and page == "Quick Analysis":
    st.info("""
    ### How to use:
    1. Choose operation from the sidebar
    2. For quick analysis:
       - Enter tickers directly or upload a file
       - Click 'Analyze Stocks'
    3. For list management:
       - Create, save, and load lists
       - Edit existing lists
       - Delete unwanted lists
    
    Example tickers: AAPL MSFT GOOGL
    """)
