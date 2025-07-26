# 'municipal governing',
#    'commission on higher education' 


import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from datetime import datetime
import re
import os

# Configuration
STATE = "Kansas"
SESSION = "2025_26"  # 2025-2026 session
OUTPUT_FILE = "Kansas_Bills_All_Keywords.xlsx"

# All Keywords - Same as Connecticut & Georgia
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
    'municipal governing'
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

def get_max_pages(driver):
    """Get total number of pages from the next-nav element"""
    try:
        # Go to the first page to check pagination
        driver.get("https://kslegislature.gov/li/b2025_26/measures/bills/#1")
        time.sleep(3)
        
        # Look for the next-nav element with page information
        try:
            # Find the div with id="tab-disp" that contains "Page X of Y"
            tab_disp = driver.find_element(By.ID, "tab-disp")
            disp_text = tab_disp.text.strip()  # Should be like "Page 71 of 71"
            
            # Extract the total pages from "Page X of Y"
            if "of" in disp_text:
                total_pages = int(disp_text.split("of")[-1].strip())
                print(f"    📄 Detected {total_pages} total pages from navigation")
                return total_pages
            else:
                print(f"    ⚠️  Could not parse page info: {disp_text}")
                return 71  # Fallback
                
        except NoSuchElementException:
            print(f"    ⚠️  Navigation element not found")
            return 71  # Fallback
        except ValueError as e:
            print(f"    ⚠️  Error parsing page number: {e}")
            return 71  # Fallback
            
    except Exception as e:
        print(f"    ❌ Error getting max pages: {e}")
        return 71  # Fallback

def extract_bill_details_selenium(driver, bill_url, bill_number, bill_title):
    """Visit individual bill page and extract sponsors and last action using correct HTML selectors"""
    try:
        print(f"      📄 Extracting details from: {bill_url}")
        driver.get(bill_url)
        time.sleep(5)
        
        # Summary is the same as title for Kansas (as specified)
        summary = bill_title
        print(f"      📋 Summary: {summary[:100]}...")
        
        # Extract Original Sponsor - handle hidden dropdown
        sponsors = ""
        try:
            portlets = driver.find_elements(By.CSS_SELECTOR, "div.portlet")
            
            for portlet in portlets:
                try:
                    header = portlet.find_element(By.CSS_SELECTOR, "div.portlet-header")
                    if "original sponsor" in header.text.lower():
                        print(f"      🎯 Found Original Sponsor portlet")
                        
                        content_div = portlet.find_element(By.CSS_SELECTOR, "div.portlet-content")
                        style = content_div.get_attribute("style")
                        
                        if "display: none" in style:
                            print(f"      🔽 Expanding hidden sponsor dropdown")
                            header.click()
                            time.sleep(2)
                        
                        sponsor_link = content_div.find_element(By.CSS_SELECTOR, 
                            "span.tab-group div.module div.infinite-tabs ul.module-list li.module-item a")
                        sponsors = sponsor_link.text.strip()
                        print(f"      👤 Original Sponsor extracted: {sponsors}")
                        break
                        
                except NoSuchElementException:
                    continue
            
            if not sponsors:
                sponsors = "Sponsor information not available"
                
        except Exception as e:
            print(f"      ❌ Error extracting sponsors: {e}")
            sponsors = "Sponsor extraction error"
        
        # Extract Last Action - TARGET CORRECT BILL HISTORY TBODY
        last_action = ""
        try:
            print(f"      🔄 Looking for bill history table...")
            
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Strategy 1: Look specifically for the bill history tbody by ID
            try:
                history_tbody = driver.find_element(By.CSS_SELECTOR, "tbody#history-tab-1")
                print(f"      ✅ Found bill history tbody with id 'history-tab-1'")
                
                rows = history_tbody.find_elements(By.TAG_NAME, "tr")
                print(f"      📊 Found {len(rows)} history entries in bill history tbody")
                
                if rows:
                    most_recent_date = None
                    most_recent_status = ""
                    
                    for i, row in enumerate(rows):
                        cols = row.find_elements(By.TAG_NAME, "td")
                        print(f"        🔍 Row {i+1} has {len(cols)} columns")
                        
                        if len(cols) >= 3:
                            date_text = cols[0].text.strip()
                            chamber_text = cols[1].text.strip()
                            status_text = cols[2].text.strip()
                            
                            print(f"        📅 Row {i+1}: Date='{date_text}' | Chamber='{chamber_text}' | Status='{status_text[:50]}...'")
                            
                            # Check if this is a meaningful entry with actual date
                            if (date_text and status_text and 
                                any(month in date_text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])):
                                
                                try:
                                    # Parse date to find most recent
                                    clean_date = date_text
                                    if ", " in date_text and len(date_text.split(", ")) >= 2:
                                        parts = date_text.split(", ")
                                        clean_date = ", ".join(parts[1:])
                                    
                                    parsed_date = datetime.strptime(clean_date, '%b %d, %Y')
                                    
                                    if most_recent_date is None or parsed_date > most_recent_date:
                                        most_recent_date = parsed_date
                                        most_recent_status = status_text
                                        print(f"        ✅ Updated most recent status: {most_recent_status}")
                                        
                                except ValueError as ve:
                                    print(f"        ⚠️  Date parsing failed for '{date_text}': {ve}")
                                    if not most_recent_status:
                                        most_recent_status = status_text
                            else:
                                print(f"        ⏭️  Skipping row (no proper date or status)")
                    
                    last_action = most_recent_status if most_recent_status else "No meaningful action found"
                    
                else:
                    last_action = "No history entries found"
                    
            except NoSuchElementException:
                print(f"      ⚠️  Bill history tbody with id 'history-tab-1' not found")
                
                # Strategy 2: Look for tbody that contains actual bill history data
                print(f"      🔄 Strategy 2: Looking for bill history data in all tables...")
                
                # Find all tables on the page
                tables = driver.find_elements(By.TAG_NAME, "table")
                print(f"      📊 Found {len(tables)} total tables on page")
                
                found_history = False
                for table_index, table in enumerate(tables):
                    print(f"      🔍 Checking table {table_index + 1}...")
                    
                    # Look for table rows that contain actual dates
                    rows = table.find_elements(By.CSS_SELECTOR, "tr")
                    
                    for row_index, row in enumerate(rows):
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 3:
                            date_text = cols[0].text.strip()
                            chamber_text = cols[1].text.strip()
                            status_text = cols[2].text.strip()
                            
                            # Check if this looks like bill history data
                            if (date_text and chamber_text and status_text and
                                any(month in date_text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']) and
                                chamber_text.lower() in ['senate', 'house']):
                                
                                print(f"        ✅ Found bill history row in table {table_index + 1}: {date_text} | {chamber_text} | {status_text[:50]}...")
                                
                                try:
                                    clean_date = date_text
                                    if ", " in date_text and len(date_text.split(", ")) >= 2:
                                        parts = date_text.split(", ")
                                        clean_date = ", ".join(parts[1:])
                                    
                                    parsed_date = datetime.strptime(clean_date, '%b %d, %Y')
                                    
                                    if not found_history or parsed_date > most_recent_date:
                                        most_recent_date = parsed_date
                                        most_recent_status = status_text
                                        found_history = True
                                        print(f"        🎯 New most recent action: {most_recent_status}")
                                        
                                except ValueError:
                                    if not found_history:
                                        most_recent_status = status_text
                                        found_history = True
                
                if found_history:
                    last_action = most_recent_status
                else:
                    last_action = "No meaningful action found"
            
            print(f"      📅 Final Last Action: {last_action}")
                
        except Exception as e:
            print(f"      ❌ Error extracting last action: {e}")
            last_action = "Last action extraction error"
        
        return summary, sponsors, last_action
        
    except Exception as e:
        print(f"      ❌ Error extracting bill details: {e}")
        return bill_title, "Error extracting sponsors", "Error extracting action"




def scrape_bills_from_page(driver, page_num):
    """Scrape all bills from a single page using correct HTML structure"""
    try:
        # Construct URL for the page
        page_url = f"https://kslegislature.gov/li/b2025_26/measures/bills/#{page_num}"
        
        print(f"    📑 Scraping page {page_num}: {page_url}")
        driver.get(page_url)
        time.sleep(4)  # Wait for page to load
        
        # Wait for the page to actually change and load the correct content
        try:
            # Wait for the page number indicator to update
            WebDriverWait(driver, 10).until(
                EC.text_to_be_present_in_element((By.ID, "tab-disp-num"), str(page_num))
            )
            print(f"    ✅ Page {page_num} loaded successfully")
        except TimeoutException:
            print(f"    ⚠️  Page {page_num} may not have loaded properly")
        
        bills_on_page = []
        
        # Find bills inside infinite-tabs class structure
        try:
            # Wait a bit more for the content to load
            time.sleep(2)
            
            # Look for the infinite-tabs container
            infinite_tabs = driver.find_element(By.CSS_SELECTOR, ".infinite-tabs")
            
            # Find the currently visible tab content for this page
            # The content should be in a div with id like "bill-tab-{page_num}"
            current_tab_content = driver.find_element(By.ID, f"bill-tab-{page_num}")
            
            # Find all bill items within the current tab content only
            bill_items = current_tab_content.find_elements(By.CSS_SELECTOR, ".module-item, li")
            
            print(f"    📊 Found {len(bill_items)} bills on page {page_num}")
            
            # Should be exactly 10 bills per page (or less on the last page)
            if len(bill_items) == 0:
                print(f"    ⚠️  No bills found on page {page_num} - may have reached end")
                return []
            
            if len(bill_items) > 20:  # Something's wrong if we see more than 20 bills
                print(f"    ⚠️  Warning: Found {len(bill_items)} bills, expected ~10. Pagination may not be working.")
            
            for i, item in enumerate(bill_items, 1):
                try:
                    # Find the bill link within each item
                    bill_link = item.find_element(By.TAG_NAME, "a")
                    bill_url = bill_link.get_attribute("href")
                    
                    # Extract bill number and title from the link text or nearby elements
                    link_text = bill_link.text.strip()
                    
                    # Skip empty items
                    if not link_text:
                        continue
                    
                    # Parse bill number and title from the text
                    # Format appears to be: "SB1 - Bill title description"
                    if " - " in link_text:
                        parts = link_text.split(" - ", 1)
                        bill_number = parts[0].strip()
                        bill_title = parts[1].strip()
                    else:
                        # Fallback: use the link text as both number and title
                        bill_number = link_text
                        bill_title = link_text
                    
                    print(f"      📄 Item {i}: {bill_number} - {bill_title[:60]}...")
                    
                    # Apply keyword filtering
                    has_keyword, matched_keyword = contains_keyword(bill_title, KEYWORDS)
                    
                    if has_keyword:
                        bills_on_page.append({
                            'bill_number': bill_number,
                            'bill_title': bill_title,
                            'bill_url': bill_url,
                            'matched_keyword': matched_keyword
                        })
                        print(f"        ✅ MATCH: {bill_number} - '{matched_keyword}'")
                    else:
                        print(f"        ⏭️  No keyword match")
                        
                except Exception as e:
                    print(f"      ❌ Error processing item {i}: {e}")
                    continue
                    
        except NoSuchElementException:
            print(f"    ❌ No content found for page {page_num}")
            # Try alternative method - look for any visible bill items
            try:
                infinite_tabs = driver.find_element(By.CSS_SELECTOR, ".infinite-tabs")
                # Get only visible items (not hidden ones from other pages)
                bill_items = infinite_tabs.find_elements(By.CSS_SELECTOR, ".module-item:not([style*='display: none']), li:not([style*='display: none'])")
                
                # If we still get too many, there might be a different structure
                if len(bill_items) > 50:
                    print(f"    ⚠️  Still finding {len(bill_items)} items. Pagination may not be working correctly.")
                    return []
                
                print(f"    📊 Found {len(bill_items)} visible bills on page {page_num}")
                
                for i, item in enumerate(bill_items, 1):
                    # Same processing logic as above...
                    try:
                        bill_link = item.find_element(By.TAG_NAME, "a")
                        bill_url = bill_link.get_attribute("href")
                        link_text = bill_link.text.strip()
                        
                        if not link_text:
                            continue
                        
                        if " - " in link_text:
                            parts = link_text.split(" - ", 1)
                            bill_number = parts[0].strip()
                            bill_title = parts[1].strip()
                        else:
                            bill_number = link_text
                            bill_title = link_text
                        
                        print(f"      📄 Item {i}: {bill_number} - {bill_title[:60]}...")
                        
                        has_keyword, matched_keyword = contains_keyword(bill_title, KEYWORDS)
                        
                        if has_keyword:
                            bills_on_page.append({
                                'bill_number': bill_number,
                                'bill_title': bill_title,
                                'bill_url': bill_url,
                                'matched_keyword': matched_keyword
                            })
                            print(f"        ✅ MATCH: {bill_number} - '{matched_keyword}'")
                        else:
                            print(f"        ⏭️  No keyword match")
                            
                    except Exception as e:
                        print(f"      ❌ Error processing item {i}: {e}")
                        continue
                
            except Exception as e:
                print(f"    ❌ Error with alternative method: {e}")
                return []
        except Exception as e:
            print(f"    ❌ Error processing page {page_num}: {e}")
            return []
            
        return bills_on_page
        
    except Exception as e:
        print(f"    ❌ Error scraping page {page_num}: {e}")
        return []

def scrape_all_kansas_bills_selenium():
    """Scrape all bills from Kansas legislature with proper page detection"""
    print(f"\n🚀 Scraping Kansas bills for session {SESSION}...")
    print("📄 Using navigation element to detect total pages")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        all_bills = []
        
        # Get total page count from navigation
        max_pages = get_max_pages(driver)
        print(f"Processing {max_pages} pages with keyword filtering")
        
        # Scrape all pages (no early stopping since we know the exact count)
        for page_num in range(1, max_pages + 1):
            print(f"\n  📑 Processing page {page_num}/{max_pages}")
            
            bills_on_page = scrape_bills_from_page(driver, page_num)
            
            if not bills_on_page:
                print(f"    ℹ️  No matching bills found on page {page_num}")
                continue
            
            # Extract detailed information for each matching bill
            for bill_info in bills_on_page:
                print(f"\n    🏛️  Processing {bill_info['bill_number']}...")
                
                summary, sponsors, last_action = extract_bill_details_selenium(
                    driver, 
                    bill_info['bill_url'], 
                    bill_info['bill_number'], 
                    bill_info['bill_title']
                )
                
                bill_data = {
                    "Year": "2025-2026",
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
                print(f"    ✅ Bill processed successfully")
                
                time.sleep(2)
            
            # Add a small delay between pages
            time.sleep(1)
        
        # Remove duplicates
        seen_bills = set()
        unique_bills = []
        for bill in all_bills:
            bill_key = bill['Bill Number']
            if bill_key not in seen_bills:
                seen_bills.add(bill_key)
                unique_bills.append(bill)
            else:
                print(f"    🔄 Duplicate removed: {bill_key}")
        
        print(f"\n📊 Total unique bills found: {len(unique_bills)}")
        return unique_bills
        
    except Exception as e:
        print(f"❌ Error scraping Kansas bills: {e}")
        return []
    finally:
        driver.quit()

def load_existing_data(filepath):
    """Load existing Excel data if it exists"""
    if os.path.exists(filepath):
        try:
            existing_df = pd.read_excel(filepath, engine='openpyxl')
            print(f"📂 Loaded existing data: {len(existing_df)} bills")
            return existing_df
        except Exception as e:
            print(f"Warning: Could not load existing file {filepath}: {e}")
    return pd.DataFrame()

def save_data(existing_df, new_bills, filepath):
    """Save data to Excel, updating existing bills and preventing duplicates"""
    if not new_bills:
        print("No new bills to save")
        return
        
    new_df = pd.DataFrame(new_bills)
    
    if existing_df.empty:
        combined_df = new_df
        print(f"📝 Creating new file with {len(new_df)} bills")
    else:
        # Combine and remove duplicates based on Bill Number (keep latest)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        
        # Remove duplicates, keeping the latest entry (last occurrence)
        combined_df.drop_duplicates(subset=['Bill Number'], keep='last', inplace=True)
        
        print(f"🔄 Updated data: {len(combined_df)} total bills (removed duplicates)")
    
    # Sort by Bill Number for better organization
    combined_df.sort_values(by=['Bill Number'], inplace=True)
    
    # Save to Excel
    combined_df.to_excel(filepath, index=False)
    print(f"✅ Saved {len(combined_df)} total bills to {filepath}")

def main():
    print("🚀 Kansas State Legislature Bill Scraper")
    print(f"Processing {len(KEYWORDS)} keywords with proper page detection")
    print(f"Session: {SESSION}")
    print("="*70)
    
    # Scrape all bills
    all_scraped_bills = scrape_all_kansas_bills_selenium()
    
    print(f"\n🎯 Total bills scraped: {len(all_scraped_bills)}")
    
    if all_scraped_bills:
        # Load existing data and save (with duplicate prevention)
        existing_df = load_existing_data(OUTPUT_FILE)
        save_data(existing_df, all_scraped_bills, OUTPUT_FILE)
        
        print("\n📊 RESULTS SUMMARY:")
        for bill in all_scraped_bills:
            print(f"  • {bill['Bill Number']}: {bill['Bill Title/Topic'][:60]}...")
        
        print(f"\n✅ Kansas scraper completed successfully!")
        print(f"📁 Results saved to: {OUTPUT_FILE}")
        print("📋 Review the Excel file to verify data quality!")
    else:
        print("\n⚠️  No bills found matching the specified keywords")
    
    print("\n🎉 Kansas scraper completed!")

if __name__ == "__main__":
    main()
