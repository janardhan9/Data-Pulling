import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import re
import time

# Configuration
STATE = "West Virginia"
SESSIONS = ["2025", "2026"]
OUTPUT_FILE = "West_Virginia_Bills_Filtered.xlsx"

# Keywords for filtering (exact phrase, case-insensitive) in Title
KEYWORDS = [
    'prior authorization',
    'utilization review',
    'utilization management',
    'medical necessity review',
    'prompt pay',
    'prompt payment',
    'clean claims',
    'clean claim',
    'coordination of benefits',
    'artificial intelligence',
    'clinical decision support',
    'automated decision making',
    'automate decision support',
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}

def normalize_text(text):
    """Normalize text for keyword matching"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip().lower()

def contains_keyword(text, keywords):
    """Check if text contains any of the keywords as exact phrases (case-insensitive)"""
    text_norm = normalize_text(text)
    for keyword in keywords:
        if keyword.lower() in text_norm:
            return True, keyword
    return False, None

def extract_bill_details(bill_url):
    """Visit individual bill page and extract summary, sponsors, and detailed last action"""
    try:
        response = requests.get(bill_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find table with class 'bstat'
        bstat_table = soup.find('table', class_='bstat')
        if not bstat_table:
            return "", "", ""
        
        summary = ""
        sponsors = ""
        last_action = ""
        
        # Extract data from table rows
        rows = bstat_table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                header_cell = cells[0]
                data_cell = cells[1]
                
                header_text = header_cell.get_text(strip=True).upper()
                
                if "SUMMARY:" in header_text:
                    summary = data_cell.get_text(separator=' ', strip=True)
                elif "LEAD SPONSOR:" in header_text:
                    sponsors = data_cell.get_text(separator=' ', strip=True)
                elif "LAST ACTION:" in header_text:
                    last_action = data_cell.get_text(separator=' ', strip=True)
        
        return summary, sponsors, last_action
        
    except Exception as e:
        print(f"Error fetching details from {bill_url}: {e}")
        return "", "", ""

def build_bill_detail_url(bill_number, year):
    """Build the URL for individual bill details"""
    # Extract the numeric part from bill number (e.g., "SB 1" -> "1", "HB 3187" -> "3187")
    bill_num = re.search(r'\d+', bill_number)
    if bill_num:
        input_num = bill_num.group()
        return f"https://www.wvlegislature.gov/Bill_Status/Bills_history.cfm?input={input_num}&year={year}&sessiontype=RS&btype=bill"
    else:
        print(f"Warning: Could not extract number from bill: {bill_number}")
        return ""

def parse_bill_row(row):
    """Parse a bill row handling both 4-column and 6-column structures"""
    cells = row.find_all('td')
    
    if len(cells) < 4:
        return None
    
    # Extract bill number and link from first cell
    bill_number_cell = cells[0]
    bill_link_tag = bill_number_cell.find('a')
    if not bill_link_tag:
        return None
    
    bill_number = bill_link_tag.text.strip()
    
    # Skip header rows
    if not re.match(r'^[SH]B\s+\d+', bill_number):
        return None
    
    # Extract title from second cell
    bill_title = cells[1].text.strip()
    
    # Handle different row structures
    if len(cells) >= 6:
        # Standard 6-column structure: Number, Title, Status, Committee, Step, Last Action
        status = cells[2].text.strip()
        committee = cells[3].text.strip()
        step = cells[4].text.strip()
        last_action_basic = cells[5].text.strip()
    elif len(cells) == 4:
        # Compact 4-column structure: Number, Title, Status, Last Action (with colspan=3)
        status = cells[2].text.strip()
        committee = ""  # Not available in compact structure
        step = ""       # Not available in compact structure
        last_action_basic = cells[3].text.strip()
    else:
        # Handle other structures if needed
        status = cells[2].text.strip() if len(cells) > 2 else ""
        committee = ""
        step = ""
        last_action_basic = cells[3].text.strip() if len(cells) > 3 else ""
    
    return {
        'bill_number': bill_number,
        'bill_title': bill_title,
        'status': status,
        'committee': committee,
        'step': step,
        'last_action_basic': last_action_basic
    }

def scrape_bills_for_year(year, keywords):
    """Scrape all bills for a given year from West Virginia legislature"""
    print(f"Scraping West Virginia bills for session {year}...")
    
    base_url = f"https://www.wvlegislature.gov/Bill_Status/Bills_all_bills.cfm"
    params = {
        'year': year,
        'sessiontype': 'RS',
        'btype': 'bill'
    }
    
    try:
        response = requests.get(base_url, params=params, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find ALL tables on the page
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables on the page")
        
        # Look for the table containing bill data
        bill_table = None
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if cells and len(cells) >= 2:
                    first_cell_text = cells[0].get_text(strip=True)
                    if re.match(r'^[SH]B\s+\d+', first_cell_text):
                        bill_table = table
                        break
            if bill_table:
                break
        
        if not bill_table:
            print(f"No table with bill data found for year {year}")
            return []
        
        print(f"Found bill table with {len(bill_table.find_all('tr'))} rows")
        
        # Process bill rows
        rows = bill_table.find_all('tr')
        all_bills = []
        bills_found_matching_keywords = 0
        
        for i, row in enumerate(rows):
            try:
                # Parse the row using the flexible parser
                bill_info = parse_bill_row(row)
                
                if not bill_info:
                    continue
                
                # Filter by keywords in bill title (exact phrase match, case-insensitive)
                has_keyword, matched_keyword = contains_keyword(bill_info['bill_title'], keywords)
                
                if has_keyword:
                    print(f"Found matching bill: {bill_info['bill_number']} - {matched_keyword} - {bill_info['bill_title'][:50]}...")
                    
                    # Build URL for bill details
                    bill_detail_url = build_bill_detail_url(bill_info['bill_number'], year)
                    
                    if bill_detail_url:  # Only proceed if URL was built successfully
                        # Extract detailed info from bill detail page
                        summary, sponsors, detailed_last_action = extract_bill_details(bill_detail_url)
                        
                        # Use detailed last action if available, otherwise use basic one
                        final_last_action = detailed_last_action if detailed_last_action else bill_info['last_action_basic']
                        
                        bill_data = {
                            "Year": year,
                            "State": STATE,
                            "Bill Number": bill_info['bill_number'],
                            "Bill Title/Topic": bill_info['bill_title'],
                            "Summary": summary,
                            "Sponsors": sponsors,
                            "Last Action": final_last_action,
                            "Bill Link": bill_detail_url,
                            "Extracted Date": datetime.today().strftime("%Y-%m-%d"),
                        }
                        
                        all_bills.append(bill_data)
                        bills_found_matching_keywords += 1
                        
                        # Be polite to the server
                        time.sleep(0.5)
                    else:
                        print(f"Skipping {bill_info['bill_number']} due to URL build failure")
                
                # Progress indicator
                if (i + 1) % 500 == 0:
                    print(f"Processed {i + 1} rows...")
                    
            except Exception as e:
                print(f"Error processing row {i}: {e}")
                continue
        
        print(f"Year {year}: Found {bills_found_matching_keywords} bills matching keywords")
        return all_bills
        
    except Exception as e:
        print(f"Error scraping bills for year {year}: {e}")
        return []

def load_existing_data(filepath):
    """Load existing Excel data if it exists"""
    if os.path.exists(filepath):
        try:
            return pd.read_excel(filepath, engine='openpyxl')
        except Exception as e:
            print(f"Warning: Could not load existing file {filepath}: {e}")
    return pd.DataFrame()

def save_data(existing_df, new_bills, filepath):
    """Save data to Excel, merging with existing data"""
    if not new_bills:
        print("No new bills to save")
        return
        
    new_df = pd.DataFrame(new_bills)
    
    if existing_df.empty:
        combined_df = new_df
    else:
        # Combine and remove duplicates
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=['Year', 'Bill Number'], keep='last', inplace=True)
    
    # Sort by Year and Bill Number
    combined_df.sort_values(by=['Year', 'Bill Number'], inplace=True)
    
    # Save to Excel
    combined_df.to_excel(filepath, index=False)
    print(f"Saved {len(combined_df)} total bills to {filepath}")

def main():
    all_scraped_bills = []
    
    for year in SESSIONS:
        bills = scrape_bills_for_year(year, KEYWORDS)
        print(f"Session {year}: Found {len(bills)} bills matching keywords")
        all_scraped_bills.extend(bills)
    
    print(f"Total bills scraped across all sessions: {len(all_scraped_bills)}")
    
    # Load existing data and save
    existing_df = load_existing_data(OUTPUT_FILE)
    save_data(existing_df, all_scraped_bills, OUTPUT_FILE)

if __name__ == "__main__":
    main()
