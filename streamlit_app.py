import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import random
import yfinance as yf
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Stock Analysis Tool", layout="wide")

def get_stock_ratios(tickers):
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    progress_bar = st.progress(0)
    for index, ticker in enumerate(tickers):
        try:
            with st.spinner(f'Fetching data for {ticker}...'):
                analysis_url = f"https://finance.yahoo.com/quote/{ticker}/analysis?p={ticker}"
                stats_url = f"https://finance.yahoo.com/quote/{ticker}/key-statistics?p={ticker}"

                response_analysis = requests.get(analysis_url, headers=headers)
                response_stats = requests.get(stats_url, headers=headers)

                soup_analysis = BeautifulSoup(response_analysis.text, 'html.parser')
                soup_stats = BeautifulSoup(response_stats.text, 'html.parser')

                def extract_value(soup, label, alt_labels=None):
                    try:
                        # Method 1: Direct table cell search with exact match
                        for table in soup.find_all('table'):
                            for row in table.find_all('tr'):
                                cells = row.find_all(['td', 'th'])
                                for i, cell in enumerate(cells):
                                    cell_text = cell.get_text().strip().lower()
                                    if label.lower() in cell_text:
                                        if i + 1 < len(cells):
                                            return cells[i + 1].get_text().strip()
                        
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

                # Extract all values
                forward_pe = extract_value(soup_stats, 'Forward P/E')
                yahoo_peg = extract_value(soup_stats, 'PEG Ratio (5 yr expected)')
                if yahoo_peg == 'N/A':
                    yahoo_peg = extract_value(soup_stats, 'PEG Ratio')
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
                        if isinstance(value, str) and '%' in value:
                            num = float(value.replace('%', '').replace(',', '').strip())
                            return f"{num:.2f}%"
                        num = float(value.replace(',', '').strip())
                        return f"{num:.2f}"
                    except (ValueError, AttributeError):
                        return value

                # Create data row
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

                # Show detailed metrics for this stock
                with st.expander(f"Detailed metrics for {ticker}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("Forward P/E:", forward_pe)
                        st.write("5-Year Growth Rate:", five_year_growth)
                        st.write("Yahoo PEG Ratio:", yahoo_peg)
                    with col2:
                        st.write("Our Calculated PEG:", calculated_peg)
                        if yahoo_peg != 'N/A' and calculated_peg != 'N/A':
                            try:
                                diff = abs(float(yahoo_peg) - float(calculated_peg))
                                st.write("PEG Difference:", f"{diff:.2f}")
                            except:
                                pass

        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {str(e)}")
            stock_data = [ticker, "", "", "", "", "", "", "", ""]

        results.append(stock_data)
        progress_bar.progress((index + 1) / len(tickers))
        time.sleep(random.uniform(1, 2))

    return results

# Streamlit UI
st.title("Stock Analysis Tool")

# Sidebar for input
st.sidebar.header("Input Options")

# Input method selection
input_method = st.sidebar.radio(
    "Choose input method:",
    ["Enter Tickers", "Upload File"]
)

tickers = []
if input_method == "Enter Tickers":
    ticker_input = st.sidebar.text_area("Enter stock tickers (space-separated):", "")
    if ticker_input:
        tickers = [t.strip().upper() for t in ticker_input.split() if t.strip()]
else:
    uploaded_file = st.sidebar.file_uploader("Upload a file with tickers (one per line)", type=["txt"])
    if uploaded_file:
        tickers = [line.decode("utf-8").strip().upper() for line in uploaded_file if line.decode("utf-8").strip()]

if st.sidebar.button("Analyze Stocks") and tickers:
    st.write(f"Analyzing {len(tickers)} stocks...")
    
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
    
    # Download button for CSV
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name="stock_analysis.csv",
        mime="text/csv"
    )
    
    # Download button for Excel
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Stock Analysis')
    
    st.download_button(
        label="Download as Excel",
        data=excel_buffer.getvalue(),
        file_name="stock_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Instructions
if not tickers:
    st.info("""
    ### How to use:
    1. Choose input method in the sidebar
    2. Enter tickers or upload a file
    3. Click 'Analyze Stocks'
    4. View results and download as needed
    
    Example tickers: AAPL MSFT GOOGL
    """)
