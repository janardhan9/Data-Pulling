import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import pandas as pd
from datetime import datetime
import re
import os

# Configuration - ALL KEYWORDS MODE
STATE = "Connecticut"
SESSIONS = ["2025"]
OUTPUT_FILE = "Connecticut_Bills_All_Keywords.xlsx"

# ALL KEYWORDS
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

# Chrome Options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Remove to see browser
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

def click_submit_button_safely(driver, button_id="Button1"):
    """Single attempt submit button clicking with overlay removal"""
    
    print(f"    🔘 Attempting to click submit button...")
    
    # Remove any loading overlays first
    try:
        driver.execute_script("""
            // Remove all loading overlays
            var overlays = document.querySelectorAll('div.se-pre-con, .loading-overlay, .loader');
            overlays.forEach(function(overlay) {
                overlay.remove();
            });
            
            // Hide any high z-index elements that might be covering
            var highZElements = document.querySelectorAll('*');
            highZElements.forEach(function(el) {
                var zIndex = window.getComputedStyle(el).zIndex;
                if (zIndex && parseInt(zIndex) > 1000) {
                    el.style.display = 'none';
                }
            });
        """)
        time.sleep(1)
    except:
        pass
    
    # Try JavaScript click (most reliable)
    try:
        driver.execute_script(f"document.getElementById('{button_id}').click();")
        print(f"    ✅ Successfully clicked submit button")
        return True
    except Exception as e:
        print(f"    ❌ Failed to click submit button: {e}")
        return False

def extract_bill_details_selenium(driver, bill_url):
    """Visit individual bill page and extract summary, sponsors, and last action from specific HTML elements"""
    try:
        print(f"      📄 Extracting details from: {bill_url}")
        driver.get(bill_url)
        time.sleep(3)
        
        # Extract Summary from <p class="text-justify"> element
        summary = ""
        try:
            summary_element = driver.find_element(By.CSS_SELECTOR, "p.text-justify")
            summary = summary_element.text.strip()
            print(f"      📋 Summary extracted: {len(summary)} characters")
        except NoSuchElementException:
            print(f"      ⚠️  Summary <p class=\"text-justify\"> element not found")
            summary = "Summary not available"
        except Exception as e:
            print(f"      ❌ Error extracting summary: {e}")
            summary = "Summary extraction error"
        
        # Extract Sponsors from <a> tag after "Introduced by:" <h5>
        sponsors = ""
        try:
            introduced_heading = driver.find_element(By.XPATH, "//h5[contains(text(), 'Introduced by:')]")
            sponsor_link = introduced_heading.find_element(By.XPATH, "following-sibling::a")
            sponsors = sponsor_link.text.strip()
            print(f"      👤 Sponsors extracted: {sponsors}")
        except NoSuchElementException:
            print(f"      ⚠️  Sponsors element not found")
            sponsors = "Sponsor information not available"
        except Exception as e:
            print(f"      ❌ Error extracting sponsors: {e}")
            sponsors = "Sponsor extraction error"
        
        # Extract Last Action from bill history table - CORRECTED VERSION
        last_action = ""
        try:
            # Try multiple selectors for the bill history table
            history_table = None
            
            # Attempt 1: Try the correct class order
            try:
                history_table = driver.find_element(By.CSS_SELECTOR, "table.footable.table.tablet.footable-loaded")
                print("      ✅ Found table with selector 1")
            except NoSuchElementException:
                pass
            
            # Attempt 2: Try with summary attribute
            if not history_table:
                try:
                    history_table = driver.find_element(By.CSS_SELECTOR, "table[summary='Bill history']")
                    print("      ✅ Found table with selector 2")
                except NoSuchElementException:
                    pass
            
            # Attempt 3: Try more general selector
            if not history_table:
                try:
                    history_table = driver.find_element(By.CSS_SELECTOR, "table.footable")
                    print("      ✅ Found table with selector 3")
                except NoSuchElementException:
                    pass
            
            # Attempt 4: Find by text content (Bill History)
            if not history_table:
                try:
                    # Look for h4 with "Bill History" text and find the table after it
                    bill_history_heading = driver.find_element(By.XPATH, "//h4[contains(text(), 'Bill History')]")
                    history_table = bill_history_heading.find_element(By.XPATH, "following-sibling::div//table")
                    print("      ✅ Found table with selector 4")
                except NoSuchElementException:
                    pass
            
            if history_table:
                # Get all rows from tbody
                tbody = history_table.find_element(By.TAG_NAME, "tbody")
                rows = tbody.find_elements(By.TAG_NAME, "tr")
                
                if rows:
                    # Get the first row (most recent action) - tables are usually sorted by date
                    first_row = rows[0]
                    cols = first_row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cols) >= 4:
                        date_text = cols[1].text.strip()  # Date is in 2nd column
                        action_text = cols[3].text.strip()  # Action is in 4th column (last column)
                        
                        if date_text and action_text:
                            last_action = f"{date_text} - {action_text}"
                            print(f"      📅 Last Action extracted: {last_action}")
                        else:
                            last_action = "No action data found"
                    else:
                        last_action = "Insufficient table columns"
                else:
                    last_action = "No action history found"
            else:
                last_action = "Action history not available"
                
        except Exception as e:
            print(f"      ❌ Error extracting last action: {e}")
            last_action = "Last action extraction error"
        
        return summary, sponsors, last_action
        
    except Exception as e:
        print(f"      ❌ Error extracting bill details: {e}")
        return "Error extracting summary", "Error extracting sponsors", "Error extracting action"

def search_bills_by_keyword(driver, keyword, year):
    """Search for bills using single attempt"""
    search_url = "https://www.cga.ct.gov/asp/CGABillInfo/CGABillInfoRequest.asp"
    
    try:
        print(f"  🔍 Navigating to search page for keyword '{keyword}'...")
        driver.get(search_url)
        time.sleep(4)
        
        # Step 1: Set the session year dropdown
        try:
            year_dropdown = driver.find_element(By.NAME, "cboSessYr")
            select = Select(year_dropdown)
            
            options = [option.get_attribute("value") for option in select.options]
            
            if str(year) in options:
                select.select_by_value(str(year))
                print(f"  ✅ Selected year: {year}")
            else:
                print(f"  ⚠️  Year {year} not available. Using default.")
            
            time.sleep(2)
        except Exception as e:
            print(f"    ⚠️  Could not set year dropdown: {e}")
        
        # Step 2: Fill the search field
        try:
            search_input = driver.find_element(By.NAME, "txtTitleWords")
            search_input.clear()
            time.sleep(1)
            search_input.send_keys(keyword)
            print(f"  ✅ Entered keyword: '{keyword}' in txtTitleWords")
            time.sleep(2)
        except Exception as e:
            print(f"    ❌ Could not find txtTitleWords: {e}")
            return []
        
        # Step 3: Single attempt submit button clicking
        if not click_submit_button_safely(driver):
            print(f"    ❌ Failed to submit search for '{keyword}'")
            return []
        
        # Step 4: Wait for results
        print(f"  ⏳ Waiting for results to load...")
        time.sleep(6)
        
        # Step 5: Check results page
        current_url = driver.current_url
        print(f"  📍 Results URL: {current_url}")
        
        # Step 6: Parse results
        bills = []
        try:
            # Wait for tables to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            tables = driver.find_elements(By.TAG_NAME, "table")
            results_table = None
            
            print(f"  📊 Found {len(tables)} tables on page")
            
            for i, table in enumerate(tables):
                table_text = table.text.lower()
                table_rows = table.find_elements(By.TAG_NAME, "tr")
                
                if (('bill' in table_text or 'hb' in table_text or 'sb' in table_text) and 
                    len(table_rows) > 1 and len(table_text) > 50):
                    
                    results_table = table
                    print(f"  ✅ Using table {i+1} as results table ({len(table_rows)} rows)")
                    break
            
            if not results_table:
                print(f"    ❌ No results table found")
                return []
            
            # Process table rows
            rows = results_table.find_elements(By.TAG_NAME, "tr")
            
            if len(rows) <= 1:
                print(f"    ℹ️  No data rows found - no results for '{keyword}'")
                return []
            
            for i, row in enumerate(rows[1:], 1):  # Skip header row
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cols) >= 2:
                        bill_number = cols[0].text.strip()
                        bill_title = cols[1].text.strip()
                        
                        if bill_number and bill_title:
                            print(f"    Row {i}: {bill_number} - {bill_title[:60]}...")
                            
                            # Apply exact phrase filtering
                            has_keyword, matched_keyword = contains_keyword(bill_title, [keyword])
                            
                            if has_keyword:
                                bill_url = f"https://www.cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill&bill_num={bill_number}&which_year={year}"
                                
                                bills.append({
                                    'bill_number': bill_number,
                                    'bill_title': bill_title,
                                    'bill_url': bill_url,
                                    'matched_keyword': matched_keyword,
                                    'year': year
                                })
                                print(f"      ✅ MATCH: {bill_number} - '{matched_keyword}'")
                            else:
                                print(f"      ⏭️  No exact match for '{keyword}'")
                        
                except Exception as e:
                    print(f"    ❌ Error processing row {i}: {e}")
                    continue
                    
        except Exception as e:
            print(f"    ❌ Error processing results table: {e}")
        
        print(f"  🎯 Total matches found for '{keyword}': {len(bills)}")
        return bills
        
    except Exception as e:
        print(f"    ❌ Error searching for keyword '{keyword}': {e}")
        return []

def scrape_bills_for_year_selenium(year, keywords):
    """Scrape all bills for a given year from Connecticut legislature using Selenium"""
    print(f"\n🚀 Scraping Connecticut bills for session {year}...")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        all_bills = []
        
        for keyword in keywords:
            print(f"\n  🔍 Searching for keyword: '{keyword}'")
            keyword_bills = search_bills_by_keyword(driver, keyword, year)
            
            for bill_info in keyword_bills:
                print(f"\n    🏛️  Processing {bill_info['bill_number']}...")
                
                summary, sponsors, last_action = extract_bill_details_selenium(driver, bill_info['bill_url'])
                
                bill_data = {
                    "Year": year,
                    "State": STATE,
                    "Bill Number": bill_info['bill_number'],
                    "Bill Title/Topic": bill_info['bill_title'],
                    "Summary": summary,
                    "Sponsors": sponsors,
                    "Last Action": last_action,
                    "Bill Link": bill_info['bill_url'],
                    "Extracted Date": datetime.today().strftime("%Y-%m-%d"),
                }
                
                all_bills.append(bill_data)
                print(f"      ✅ Bill processed successfully")
                time.sleep(2)
        
        # Remove duplicates
        seen_bills = set()
        unique_bills = []
        for bill in all_bills:
            bill_key = (bill['Year'], bill['Bill Number'])
            if bill_key not in seen_bills:
                seen_bills.add(bill_key)
                unique_bills.append(bill)
        
        print(f"\n📊 Year {year}: Found {len(unique_bills)} unique bills matching keywords")
        return unique_bills
        
    except Exception as e:
        print(f"❌ Error scraping bills for year {year}: {e}")
        return []
    finally:
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
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=['Year', 'Bill Number'], keep='last', inplace=True)
    
    combined_df.sort_values(by=['Year', 'Bill Number'], inplace=True)
    combined_df.to_excel(filepath, index=False)
    print(f"✅ Saved {len(combined_df)} total bills to {filepath}")

def main():
    print("🚀 Connecticut Legislative Bill Scraper - ALL KEYWORDS")
    print(f"Processing {len(KEYWORDS)} keywords")
    print("="*70)
    
    all_scraped_bills = []
    
    for year in SESSIONS:
        bills = scrape_bills_for_year_selenium(year, KEYWORDS)
        print(f"\n📈 Session {year}: Found {len(bills)} bills matching keywords")
        all_scraped_bills.extend(bills)
    
    print(f"\n🎯 Total bills scraped across all sessions: {len(all_scraped_bills)}")
    
    existing_df = load_existing_data(OUTPUT_FILE)
    save_data(existing_df, all_scraped_bills, OUTPUT_FILE)
    
    print("\n✅ Connecticut scraper completed with proper data extraction!")

if __name__ == "__main__":
    main()
