import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import random
import os
import json
import yfinance as yf
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side

# Initialize session state for lists
if 'saved_lists' not in st.session_state:
    st.session_state.saved_lists = {}
if 'current_tickers' not in st.session_state:
    st.session_state.current_tickers = []

st.set_page_config(page_title="Stock Analysis Tool", layout="wide")

# Your original working get_stock_ratios function
def get_stock_ratios(tickers):
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    progress_text = st.empty()
    for ticker in tickers:
        try:
            progress_text.write(f"Fetching data for {ticker}...")
            analysis_url = f"https://finance.yahoo.com/quote/{ticker}/analysis?p={ticker}"
            stats_url = f"https://finance.yahoo.com/quote/{ticker}/key-statistics?p={ticker}"

            response_analysis = requests.get(analysis_url, headers=headers)
            response_stats = requests.get(stats_url, headers=headers)

            soup_analysis = BeautifulSoup(response_analysis.text, 'html.parser')
            soup_stats = BeautifulSoup(response_stats.text, 'html.parser')

            def extract_value(soup, label, alt_labels=None):
                try:
                    # Debug print for PEG ratio search
                    if 'PEG' in label:
                        st.write(f"\nSearching for PEG ratio in HTML...")
                        for table in soup.find_all('table'):
                            for row in table.find_all('tr'):
                                st.write(f"Row text: {row.get_text()}")

                    # Method 1: Direct table cell search with exact match
                    for table in soup.find_all('table'):
                        for row in table.find_all('tr'):
                            cells = row.find_all(['td', 'th'])
                            for i, cell in enumerate(cells):
                                cell_text = cell.get_text().strip().lower()
                                if label.lower() in cell_text:  # Changed to 'in' instead of exact match
                                    if i + 1 < len(cells):
                                        value = cells[i + 1].get_text().strip()
                                        if 'PEG' in label:
                                            st.write(f"Found PEG value: {value}")
                                        return value

                    # Method 2: Try alternative labels if provided
                    if alt_labels:
                        for alt_label in alt_labels:
                            for table in soup.find_all('table'):
                                for row in table.find_all('tr'):
                                    cells = row.find_all(['td', 'th'])
                                    for i, cell in enumerate(cells):
                                        if alt_label.lower() in cell.get_text().strip().lower():
                                            if i + 1 < len(cells):
                                                return cells[i + 1].get_text().strip()

                    return 'N/A'
                except Exception as e:
                    st.error(f"Error extracting {label} for {ticker}: {str(e)}")
                    return 'N/A'

            # Extract all values with debug output
            st.write(f"\nExtracting data for {ticker}...")

            forward_pe = extract_value(soup_stats, 'Forward P/E')
            st.write(f"Forward P/E: {forward_pe}")

            # Try multiple variations for PEG ratio
            yahoo_peg = extract_value(soup_stats, 'PEG Ratio (5 yr expected)')
            if yahoo_peg == 'N/A':
                yahoo_peg = extract_value(soup_stats, 'PEG Ratio')
            st.write(f"Yahoo PEG: {yahoo_peg}")

            price_to_sales = extract_value(soup_stats, 'Price/Sales')
            qtrly_rev_growth_yoy = extract_value(soup_stats, 'Quarterly Revenue Growth')
            one_year_growth = extract_value(soup_analysis, 'Next Year', ['Growth Estimate Next Year'])
            five_year_growth = extract_value(soup_analysis, 'Next 5 Years (per annum)',
                                             ['Growth Est Next 5Y', '5 Year Growth Est', 'Next Five Years'])

            # Calculate our own PEG ratio
            def calculate_peg(pe, growth):
                try:
                    if pe != 'N/A' and growth != 'N/A':
                        pe_val = float(pe.replace(',', ''))
                        growth_val = float(growth.replace('%', '').replace(',', ''))
                        if growth_val != 0:
                            return f"{(pe_val / growth_val):.2f}"
                except:
                    pass
                return 'N/A'

            calculated_peg = calculate_peg(forward_pe, five_year_growth)

            # Calculate QoQ revenue growth using yfinance
            stock = yf.Ticker(ticker)
            financials = stock.quarterly_financials

            if not financials.empty and 'Total Revenue' in financials.index:
                revenue = financials.loc['Total Revenue']
                if len(revenue) >= 2:
                    latest_revenue = revenue.iloc[0]
                    previous_revenue = revenue.iloc[1]
                    qoq_growth = ((latest_revenue - previous_revenue) / previous_revenue) * 100
                    qoq_growth_str = f"{qoq_growth:.2f}%"
                else:
                    qoq_growth_str = "N/A"
            else:
                qoq_growth_str = "N/A"

            def format_value(value):
                if value == "N/A":
                    return ""
                try:
                    # Handle percentage values
                    if isinstance(value, str) and '%' in value:
                        num = float(value.replace('%', '').replace(',', '').strip())
                        return f"{num:.2f}%"
                    # Handle numeric values
                    num = float(value.replace(',', '').strip())
                    return f"{num:.2f}"
                except (ValueError, AttributeError):
                    return value

            # Print detailed metrics for this stock
            with st.expander(f"Detailed metrics for {ticker}"):
                st.write(f"Forward P/E: {forward_pe}")
                st.write(f"5-Year Growth Rate: {five_year_growth}")
                st.write(f"Yahoo PEG Ratio: {yahoo_peg}")
                st.write(f"Our Calculated PEG: {calculated_peg}")
                if yahoo_peg != 'N/A' and calculated_peg != 'N/A':
                    try:
                        diff = abs(float(yahoo_peg) - float(calculated_peg))
                        st.write(f"PEG Difference: {diff:.2f}")
                    except:
                        pass

            stock_data = [
                ticker,
                format_value(forward_pe),
                format_value(yahoo_peg),
                format_value(calculated_peg),
                format_value(price_to_sales),
                format_value(qtrly_rev_growth_yoy),
                qoq_growth_str if qoq_growth_str != "N/A" else "",
                format_value(one_year_growth),
                format_value(five_year_growth)
            ]

        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {str(e)}")
            stock_data = [ticker, "", "", "", "", "", "", "", ""]

        results.append(stock_data)
        time.sleep(random.uniform(2, 4))

    return results


# Streamlit UI Part
st.title("Stock Analysis Tool")

# Sidebar navigation
st.sidebar.title("Menu Options")
choice = st.sidebar.radio(
    "Choose Operation:",
    ["1. Create new list",
     "2. Choose saved list",
     "3. Edit list",
     "4. Delete list",
     "5. Look up ratios",
     "6. Quit"]
)
# Display current list in sidebar
st.sidebar.write("---")
st.sidebar.write("Current List:",
                 ", ".join(st.session_state.current_tickers) if st.session_state.current_tickers else "No tickers")

# Main area logic based on choice
if choice == "1. Create new list":
    st.header("Create New List")
    new_tickers = st.text_input("Enter tickers for the new list (space-separated):").strip().upper()
    if st.button("Create List"):
        if new_tickers:
            st.session_state.current_tickers = [t.strip() for t in new_tickers.split() if t.strip()]
            st.success("New list created!")
            # Option to save list
            if st.button("Save This List"):
                list_name = st.text_input("Enter a name for this list:")
                if list_name:
                    st.session_state.saved_lists[list_name] = st.session_state.current_tickers
                    st.success(f"List '{list_name}' saved successfully.")

elif choice == "2. Choose saved list":
    st.header("Choose Saved List")
    if st.session_state.saved_lists:
        list_names = list(st.session_state.saved_lists.keys())
        selected_list = st.selectbox("Select a list:", list_names)
        if st.button("Load Selected List"):
            st.session_state.current_tickers = st.session_state.saved_lists[selected_list]
            st.success(f"Loaded list: {selected_list}")
    else:
        st.info("No saved lists found.")

elif choice == "3. Edit list":
    st.header("Edit Current List")
    st.write("Current tickers:", ", ".join(st.session_state.current_tickers))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Remove Tickers")
        remove_tickers = st.text_input("Enter tickers to remove (space-separated) or 'ALL':").strip().upper()
        if st.button("Remove"):
            if remove_tickers == "ALL":
                st.session_state.current_tickers = []
            elif remove_tickers:
                to_remove = remove_tickers.split()
                st.session_state.current_tickers = [t for t in st.session_state.current_tickers if t not in to_remove]
            st.success("Tickers removed!")
            st.experimental_rerun()

    with col2:
        st.subheader("Add Tickers")
        add_tickers = st.text_input("Enter tickers to add (space-separated):").strip().upper()
        if st.button("Add"):
            if add_tickers:
                new_tickers = add_tickers.split()
                st.session_state.current_tickers.extend(
                    [t for t in new_tickers if t not in st.session_state.current_tickers])
            st.success("Tickers added!")
            st.experimental_rerun()

elif choice == "4. Delete list":
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

elif choice == "5. Look up ratios":
    st.header("Look Up Stock Ratios")
    if not st.session_state.current_tickers:
        st.warning("No tickers in current list. Please create or load a list first.")
    else:
        if st.button("Analyze Current List"):
            st.write(f"Analyzing {len(st.session_state.current_tickers)} stocks...")
            results = get_stock_ratios(st.session_state.current_tickers)

            # Create DataFrame
            headers = ["Ticker", "Forward P/E", "Yahoo PEG", "Calc PEG", "Price/Sales",
                       "Qtrly Rev Growth YoY", "Qtrly Rev Growth QoQ", "1Y Rev Growth Est",
                       "5Y Rev Growth Est"]

            df = pd.DataFrame(results, columns=headers)

            # Display results
            st.write("Analysis Results:")
            st.dataframe(df)

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                # CSV Download
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="stock_analysis.csv",
                    mime="text/csv"
                )

            with col2:
                # Excel Download
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Stock Analysis')
                    worksheet = writer.sheets['Stock Analysis']

                    # Apply formatting
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        worksheet.column_dimensions[column_letter].width = max_length + 2

                st.download_button(
                    label="Download Excel",
                    data=buffer.getvalue(),
                    file_name="stock_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

elif choice == "6. Quit":
    st.write("Thank you for using the Stock Analysis Tool!")
    st.stop()

# Instructions
if not st.session_state.current_tickers:
    st.info("""
    ### How to use:
    1. Create a new list or choose a saved list
    2. Edit your list as needed
    3. Use 'Look up ratios' to analyze your stocks
    4. Download results in CSV or Excel format

    Start by creating a new list with some stock symbols!
    """)
