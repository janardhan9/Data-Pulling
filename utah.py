import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import pandas as pd
from datetime import datetime
import os
import re

# Configuration
STATE = "Utah"
SESSIONS = ["2025", "2026"]
OUTPUT_FILE = "Utah_Bills_Filtered_Selenium.xlsx"

# Same keywords as other scrapers - exact phrase match (case-insensitive) in Title
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

# Chrome Options for headless browsing
chrome_options = Options()
chrome_options.add_argument("--headless")  # Remove this line if you want to see the browser
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

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

def safe_click_element(driver, element_locator, wait_time=10):
    """Safely click an element with retry logic for stale element handling"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            wait = WebDriverWait(driver, wait_time)
            element = wait.until(EC.element_to_be_clickable(element_locator))
            element.click()
            return True
        except StaleElementReferenceException:
            if attempt < max_retries - 1:
                print(f"    Stale element on attempt {attempt + 1}, retrying...")
                time.sleep(1)
                continue
            else:
                print(f"    Failed to click element after {max_retries} attempts")
                return False
        except (TimeoutException, NoSuchElementException) as e:
            print(f"    Element not found or not clickable: {e}")
            return False
    return False

def safe_get_text(driver, element_locator, wait_time=5):
    """Safely get text from elements with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            wait = WebDriverWait(driver, wait_time)
            elements = wait.until(EC.presence_of_all_elements_located(element_locator))
            return [elem.text for elem in elements if elem.text.strip()]
        except StaleElementReferenceException:
            if attempt < max_retries - 1:
                print(f"    Stale element while getting text, retrying...")
                time.sleep(1)
                continue
            else:
                print(f"    Failed to get text after {max_retries} attempts")
                return []
        except (TimeoutException, NoSuchElementException):
            return []
    return []

def extract_bill_details_selenium(driver, bill_url):
    """Visit individual bill page using Selenium and extract summary and last action from tabs"""
    try:
        # Build full URL if relative
        if bill_url.startswith('/'):
            bill_url = f"https://le.utah.gov{bill_url}"
        
        print(f"  Extracting details from: {bill_url}")
        driver.get(bill_url)
        
        # Wait for page to load completely
        time.sleep(3)
        
        # Extract Summary from Bill Text tab
        summary = ""
        try:
            # Click on Bill Text tab (should be active by default, but ensure it's clicked)
            if safe_click_element(driver, (By.ID, "activator-billText")):
                time.sleep(2)  # Wait for content to load
                
                # Look for bill text content - try multiple approaches
                summary_parts = []
                
                # Method 1: Look for <gd> elements (General Description)
                gd_texts = safe_get_text(driver, (By.TAG_NAME, "gd"))
                for text in gd_texts:
                    # Clean up line numbers and extra whitespace
                    cleaned = re.sub(r'\b\d+\b', '', text)
                    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                    if len(cleaned) > 50:  # Only substantial content
                        summary_parts.append(cleaned)
                
                # Method 2: Look for <hp> elements (Highlighted Provisions)
                hp_texts = safe_get_text(driver, (By.TAG_NAME, "hp"))
                for text in hp_texts:
                    cleaned = re.sub(r'\d+\s+', '', text)  # Remove line numbers
                    cleaned = re.sub(r'▸', '•', cleaned)  # Replace bullets
                    if len(cleaned) > 50:
                        summary_parts.append("Highlighted Provisions: " + cleaned)
                
                # Combine summary parts
                if summary_parts:
                    summary = ' '.join(summary_parts[:2])  # Take first 2 substantial parts
                    summary = re.sub(r'\s+', ' ', summary).strip()
            
        except Exception as e:
            print(f"    Error extracting summary: {e}")
        
        # Extract Last Action from Status tab
        last_action = ""
        try:
            # Click on Status tab
            if safe_click_element(driver, (By.ID, "activator-billStatus")):
                time.sleep(2)  # Wait for status content to load
                
                # Look for status table with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        tables = driver.find_elements(By.TAG_NAME, "table")
                        for table in tables:
                            # Check if this table contains status information
                            table_text = table.text.lower()
                            if 'action' in table_text or 'status' in table_text or 'date' in table_text:
                                rows = table.find_elements(By.TAG_NAME, "tr")
                                if len(rows) > 1:  # Has header + data
                                    # Get the most recent action (usually the last row with data)
                                    for row in reversed(rows[1:]):  # Skip header, start from last
                                        try:
                                            cols = row.find_elements(By.TAG_NAME, "td")
                                            if len(cols) >= 2:
                                                date_text = cols[0].text.strip()
                                                action_text = cols[1].text.strip()
                                                if date_text and action_text:  # Both have content
                                                    last_action = f"{date_text} {action_text}".strip()
                                                    break
                                        except StaleElementReferenceException:
                                            continue
                                    if last_action:  # Found action, stop looking
                                        break
                        break  # Success, exit retry loop
                    except StaleElementReferenceException:
                        if attempt < max_retries - 1:
                            print(f"    Stale element in status extraction, attempt {attempt + 1}")
                            time.sleep(1)
                            continue
                        else:
                            break
                            
        except Exception as e:
            print(f"    Error extracting last action: {e}")
        
        # Fallback: If no summary found, use page title
        if not summary:
            try:
                title_element = driver.find_element(By.ID, "pagetitle")
                summary = title_element.text.strip()
            except:
                summary = "Summary not available"
        
        return summary, last_action
        
    except Exception as e:
        print(f"    Error extracting bill details: {e}")
        return "", ""

def scrape_bills_for_year_selenium(year, keywords):
    """Scrape all bills for a given year from Utah legislature using Selenium"""
    print(f"Scraping Utah bills for session {year}...")
    
    # Initialize WebDriver for this session
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        base_url = f"https://le.utah.gov/asp/passedbills/passedbills.asp"
        params_url = f"{base_url}?session={year}GS"
        
        driver.get(params_url)
        time.sleep(3)  # Wait for page to load
        
        # Find the main table with ID 'passedTbl'
        wait = WebDriverWait(driver, 10)
        try:
            main_table = wait.until(EC.presence_of_element_located((By.ID, "passedTbl")))
        except TimeoutException:
            print(f"No main table found for year {year}")
            return []
        
        # Get all bill data first to avoid stale element issues during iteration
        bill_data_list = []
        
        try:
            rows = main_table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header
            print(f"Found {len(rows)} bills for year {year}")
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 8:
                        # Extract all data immediately to avoid stale references
                        bill_link_element = cells[0].find_element(By.TAG_NAME, "a")
                        bill_data = {
                            'index': i,
                            'bill_number': bill_link_element.text.strip(),
                            'bill_detail_url': bill_link_element.get_attribute("href"),
                            'bill_title': cells[1].text.strip(),
                            'sponsors': cells[2].text.strip(),
                            'date_passed': cells[3].text.strip(),
                            'effective_date': cells[4].text.strip(),
                            'gov_action': cells[5].text.strip(),
                            'gov_action_date': cells[6].text.strip(),
                            'chapter': cells[7].text.strip()
                        }
                        bill_data_list.append(bill_data)
                except Exception as e:
                    print(f"Error extracting data from row {i}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error processing table rows: {e}")
            return []
        
        # Now process each bill for keyword matching
        all_bills = []
        bills_found_matching_keywords = 0
        
        for i, bill_data in enumerate(bill_data_list):
            try:
                # Filter by keywords in bill title (exact phrase match, case-insensitive)
                has_keyword, matched_keyword = contains_keyword(bill_data['bill_title'], keywords)
                
                if has_keyword:
                    print(f"Found matching bill: {bill_data['bill_number']} - {matched_keyword} - {bill_data['bill_title'][:50]}...")
                    
                    # Extract detailed info from bill detail page using tabs
                    summary, detailed_last_action = extract_bill_details_selenium(driver, bill_data['bill_detail_url'])
                    
                    # Use detailed last action if available, otherwise use governor's action
                    final_last_action = detailed_last_action if detailed_last_action else bill_data['gov_action']
                    
                    bill_record = {
                        "Year": year,
                        "State": STATE,
                        "Bill Number": bill_data['bill_number'],
                        "Bill Title/Topic": bill_data['bill_title'],
                        "Summary": summary,
                        "Sponsors": bill_data['sponsors'],
                        "Last Action": final_last_action,
                        "Bill Link": bill_data['bill_detail_url'],
                        "Extracted Date": datetime.today().strftime("%Y-%m-%d"),
                    }
                    
                    all_bills.append(bill_record)
                    bills_found_matching_keywords += 1
                    
                    # Be polite to the server
                    time.sleep(1)
                
                # Progress indicator
                if (i + 1) % 100 == 0:
                    print(f"Processed {i + 1}/{len(bill_data_list)} bills...")
                    
            except Exception as e:
                print(f"Error processing bill {i}: {e}")
                continue
        
        print(f"Year {year}: Found {bills_found_matching_keywords} bills matching keywords")
        return all_bills
        
    except Exception as e:
        print(f"Error scraping bills for year {year}: {e}")
        return []
    finally:
        # Always close the driver for this session
        driver.quit()

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
        bills = scrape_bills_for_year_selenium(year, KEYWORDS)
        print(f"Session {year}: Found {len(bills)} bills matching keywords")
        all_scraped_bills.extend(bills)
    
    print(f"Total bills scraped across all sessions: {len(all_scraped_bills)}")
    
    # Load existing data and save
    existing_df = load_existing_data(OUTPUT_FILE)
    save_data(existing_df, all_scraped_bills, OUTPUT_FILE)

if __name__ == "__main__":
    main()
