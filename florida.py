import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import re
import time

# Configuration
STATE = "Florida"
SESSIONS = ["2025", "2026"]
OUTPUT_FILE = "Florida_Bills_Filtered.xlsx"

# Keywords for filtering (exact phrase, case-insensitive)
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

def extract_last_action_without_date(raw_text):
    """Remove date from beginning of last action text"""
    if not raw_text:
        return ""
    text = raw_text.strip()
    # Remove "Last Action: " prefix and date pattern
    text = re.sub(r'^Last Action:\s*', '', text)
    text = re.sub(r'^\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?\s*', '', text)
    return text.strip()

def get_bill_summary(bill_url):
    """Visit bill detail page and concatenate all <p class="width80"> elements"""
    try:
        response = requests.get(bill_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all paragraphs with class "width80" and concatenate
        summary_paragraphs = soup.find_all('p', class_='width80')
        summary_parts = []
        
        for p in summary_paragraphs:
            summary_parts.append(p.get_text(separator=' ', strip=True))
        
        return ' '.join(summary_parts)
    except Exception as e:
        print(f"Error fetching summary from {bill_url}: {e}")
        return ""

def scrape_bills_for_year(year, keywords):
    """Scrape all bills for a given year, filtering by keywords"""
    print(f"Scraping Florida bills for session {year}...")
    
    base_url = f"https://www.flsenate.gov/Session/Bills/{year}"
    params = {
        'chamber': 'both',
        'searchOnlyCurrentVersion': 'True',
        'isIncludeAmendments': 'False',
        'isFirstReference': 'True',
        'citationType': 'FL Statutes',
        'pageNumber': 1
    }
    
    all_bills = []
    page_num = 1
    
    while True:
        params['pageNumber'] = page_num
        print(f"Processing page {page_num}...")
        
        try:
            response = requests.get(base_url, params=params, headers=HEADERS)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for total bills found
            h3_tag = soup.find('h3')
            if h3_tag and 'Bills Found' in h3_tag.text:
                print(f"Total bills found: {h3_tag.text.strip()}")
            
            # Find the bills table
            table = soup.find('table', class_='width100 clickableRows tbl')
            if not table:
                print(f"No bill table found on page {page_num}")
                break
            
            # Extract bill numbers from table headers (headers 6+ contain bill numbers)
            all_headers = table.find_all('th')
            bill_numbers = []
            bill_links = {}
            
            for header in all_headers[5:]:  # Skip first 5 headers (Number, Title, etc.)
                header_text = header.text.strip()
                if re.match(r'^[A-Z]{2,3}\s*\d+', header_text):  # Match patterns like SB 2, HB 11
                    bill_numbers.append(header_text)
                    # Look for link in this header
                    link_tag = header.find('a')
                    if link_tag:
                        href = link_tag.get('href', '')
                        full_link = f"https://www.flsenate.gov{href}" if href.startswith('/') else href
                        bill_links[header_text] = full_link
            
            print(f"Found {len(bill_numbers)} bill numbers in headers")
            
            # Get table body rows
            tbody = table.find('tbody')
            if not tbody:
                print(f"No tbody found on page {page_num}")
                break
                
            rows = tbody.find_all('tr')
            if not rows:
                print(f"No bill rows found on page {page_num}")
                break
            
            print(f"Found {len(rows)} data rows")
            
            # Match bill numbers with rows (assuming same order)
            bills_found_on_page = 0
            
            for i, row in enumerate(rows):
                if i >= len(bill_numbers):
                    break
                    
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                
                # Get bill number from headers
                bill_number = bill_numbers[i]
                bill_link = bill_links.get(bill_number, "")
                
                # Extract data from columns: Title, Filed By, Last Action, Track Bill
                bill_title = cols[0].text.strip()  # Title is in first column
                sponsors = cols[1].text.strip()    # Filed By is in second column
                last_action_raw = cols[2].text.strip()  # Last Action is in third column
                last_action = extract_last_action_without_date(last_action_raw)
                
                # Filter by keywords in bill title (exact phrase match)
                has_keyword, matched_keyword = contains_keyword(bill_title, keywords)
                
                if has_keyword:
                    print(f"Found matching bill: {bill_number} - {matched_keyword} - {bill_title[:50]}...")
                    
                    # Get summary from detail page
                    summary = get_bill_summary(bill_link) if bill_link else ""
                    
                    bill_data = {
                        "Year": year,
                        "State": STATE,
                        "Bill Number": bill_number,
                        "Bill Title/Topic": bill_title,
                        "Summary": summary,
                        "Sponsors": sponsors,
                        "Last Action": last_action,
                        "Bill Link": bill_link,
                        "Extracted Date": datetime.today().strftime("%Y-%m-%d"),
                    }
                    
                    all_bills.append(bill_data)
                    bills_found_on_page += 1
                    
                    # Be polite to the server
                    time.sleep(0.5)
            
            print(f"Page {page_num}: Found {bills_found_on_page} bills matching keywords")
            
            # Check for next page
            pagination_div = soup.find('div', class_='ListPagination')
            if pagination_div:
                next_link = pagination_div.find('a', class_='next')
                if next_link and next_link.get('href'):
                    page_num += 1
                    time.sleep(1)  # Be polite between pages
                    continue
            
            # No more pages
            break
            
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            break
    
    return all_bills

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

