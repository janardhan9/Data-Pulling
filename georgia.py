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
import urllib.parse

# Configuration
STATE = "Georgia"
SESSIONS = ["1033"]  # 2025-2026 regular session
OUTPUT_FILE = "Georgia_Bills_All_Keywords.xlsx"

# All Keywords - Same as Connecticut
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

def extract_bill_details_selenium(driver, bill_url):
    """Visit individual bill page and extract summary, sponsors, and last action"""
    try:
        print(f"      📄 Extracting details from: {bill_url}")
        driver.get(bill_url)
        time.sleep(3)
        
        # Extract Summary from "First Reader Summary" card
        summary = ""
        try:
            # Look for div with "First Reader Summary" h2 and get the card-text-sm content
            summary_card = driver.find_element(By.XPATH, "//h2[@class='card-title' and text()='First Reader Summary']")
            summary_div = summary_card.find_element(By.XPATH, "following-sibling::div[@class='card-text-sm']")
            summary = summary_div.text.strip()
            print(f"      📋 Summary extracted: {len(summary)} characters")
        except NoSuchElementException:
            print(f"      ⚠️  First Reader Summary not found")
            summary = "Summary not available"
        except Exception as e:
            print(f"      ❌ Error extracting summary: {e}")
            summary = "Summary extraction error"
        
        # Extract Sponsors - get the first sponsor from the table
        sponsors = ""
        try:
            # Find the sponsors table and get the first row's name
            sponsors_table = driver.find_element(By.CSS_SELECTOR, "app-sponsor-list table tbody")
            first_row = sponsors_table.find_element(By.TAG_NAME, "tr")
            sponsor_link = first_row.find_element(By.TAG_NAME, "a")
            sponsors = sponsor_link.text.strip()
            print(f"      👤 First Sponsor extracted: {sponsors}")
        except NoSuchElementException:
            print(f"      ⚠️  Sponsors table not found")
            sponsors = "Sponsor information not available"
        except Exception as e:
            print(f"      ❌ Error extracting sponsors: {e}")
            sponsors = "Sponsor extraction error"
        
        # Extract Last Action from Status History - get most recent based on date
        last_action = ""
        try:
            # Find the status history table
            status_table = driver.find_element(By.CSS_SELECTOR, "app-status-history-list table tbody")
            rows = status_table.find_elements(By.TAG_NAME, "tr")
            
            if rows:
                # Parse all rows to find the most recent date
                most_recent_date = None
                most_recent_action = ""
                
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 2:
                        date_text = cols[0].text.strip()  # Date column
                        status_text = cols[1].text.strip()  # Status column
                        
                        if date_text and status_text:
                            try:
                                # Parse date (format: MM/DD/YYYY)
                                parsed_date = datetime.strptime(date_text, '%m/%d/%Y')
                                
                                # Keep the most recent date
                                if most_recent_date is None or parsed_date > most_recent_date:
                                    most_recent_date = parsed_date
                                    most_recent_action = f"{date_text} - {status_text}"
                            except ValueError:
                                # If date parsing fails, just use first valid entry
                                if not most_recent_action:
                                    most_recent_action = f"{date_text} - {status_text}"
                
                last_action = most_recent_action if most_recent_action else "No recent action found"
                print(f"      📅 Last Action extracted: {last_action}")
            else:
                last_action = "No status history found"
                
        except NoSuchElementException:
            print(f"      ⚠️  Status history table not found")
            last_action = "Status history not available"
        except Exception as e:
            print(f"      ❌ Error extracting last action: {e}")
            last_action = "Last action extraction error"
        
        return summary, sponsors, last_action
        
    except Exception as e:
        print(f"      ❌ Error extracting bill details: {e}")
        return "Error extracting summary", "Error extracting sponsors", "Error extracting action"

def get_max_pages(driver, base_url, keyword, session):
    """Get the total number of pages for a keyword search"""
    try:
        # Construct URL for first page
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f"{base_url}?k={encoded_keyword}&s={session}&p=1"
        
        driver.get(search_url)
        time.sleep(3)
        
        # Look for pagination information
        try:
            # Try to find pagination elements
            pagination = driver.find_elements(By.CSS_SELECTOR, ".pagination .page-link")
            if pagination:
                # Get the last page number (excluding "Next" button)
                page_numbers = []
                for link in pagination:
                    text = link.text.strip()
                    if text.isdigit():
                        page_numbers.append(int(text))
                
                max_page = max(page_numbers) if page_numbers else 1
                print(f"    📄 Found {max_page} pages for keyword '{keyword}'")
                return max_page
            else:
                print(f"    📄 No pagination found, assuming 1 page for keyword '{keyword}'")
                return 1
                
        except Exception as e:
            print(f"    ⚠️  Could not determine page count: {e}")
            return 1
            
    except Exception as e:
        print(f"    ❌ Error getting max pages: {e}")
        return 1

def search_bills_by_keyword(driver, keyword, session):
    """Search for bills using Georgia's search URL pattern with pagination"""
    base_url = "https://www.legis.ga.gov/search"
    
    try:
        print(f"  🔍 Searching for keyword: '{keyword}'")
        
        # Get total number of pages for this keyword
        max_pages = get_max_pages(driver, base_url, keyword, session)
        
        all_bills = []
        
        # Search through all pages
        for page in range(1, max_pages + 1):
            print(f"    📑 Processing page {page}/{max_pages}")
            
            # Construct search URL
            encoded_keyword = urllib.parse.quote(keyword)
            search_url = f"{base_url}?k={encoded_keyword}&s={session}&p={page}"
            
            print(f"    🔍 Navigating to: {search_url}")
            driver.get(search_url)
            time.sleep(3)
            
            # Extract bill information from search results table
            try:
                # Find the results table
                table = driver.find_element(By.CSS_SELECTOR, "table")
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                
                print(f"    📊 Found {len(rows)} bills on page {page}")
                
                for i, row in enumerate(rows, 1):
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 2:
                            # Extract bill number and link from first column
                            bill_link_element = cols[0].find_element(By.TAG_NAME, "a")
                            bill_number = bill_link_element.text.strip()
                            bill_url = bill_link_element.get_attribute("href")
                            
                            # Extract bill title from second column
                            title_link = cols[1].find_element(By.TAG_NAME, "a")
                            bill_title = title_link.text.strip()
                            
                            print(f"      📄 Row {i}: {bill_number} - {bill_title[:60]}...")
                            
                            # Apply keyword filtering - only include bills that actually contain the keyword
                            has_keyword, matched_keyword = contains_keyword(bill_title, [keyword])
                            
                            if has_keyword:
                                all_bills.append({
                                    'bill_number': bill_number,
                                    'bill_title': bill_title,
                                    'bill_url': bill_url,
                                    'matched_keyword': matched_keyword,
                                    'session': session
                                })
                                print(f"        ✅ MATCH: {bill_number} - '{matched_keyword}'")
                            else:
                                print(f"        ⏭️  No exact match for '{keyword}'")
                                
                    except Exception as e:
                        print(f"      ❌ Error processing row {i}: {e}")
                        continue
                        
            except NoSuchElementException:
                print(f"    ❌ No results table found on page {page}")
                continue
            except Exception as e:
                print(f"    ❌ Error processing page {page}: {e}")
                continue
                
        print(f"  🎯 Total matches found for '{keyword}': {len(all_bills)}")
        return all_bills
        
    except Exception as e:
        print(f"    ❌ Error searching for keyword '{keyword}': {e}")
        return []

def scrape_bills_for_session_selenium(session, keywords):
    """Scrape all bills for a given session from Georgia legislature using Selenium"""
    print(f"\n🚀 Scraping Georgia bills for session {session}...")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        all_bills = []
        
        for keyword in keywords:
            print(f"\n  🔍 Processing keyword: '{keyword}'")
            keyword_bills = search_bills_by_keyword(driver, keyword, session)
            
            # Extract detailed information for each matching bill
            for bill_info in keyword_bills:
                print(f"\n    🏛️  Processing {bill_info['bill_number']}...")
                
                summary, sponsors, last_action = extract_bill_details_selenium(driver, bill_info['bill_url'])
                
                bill_data = {
                    "Year": "2025-2026",  # Since session 1033 covers both years
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
                
                time.sleep(2)  # Be polite to the server
        
        # Remove duplicates (same bill might match multiple keywords)
        seen_bills = set()
        unique_bills = []
        for bill in all_bills:
            bill_key = (bill['Year'], bill['Bill Number'])
            if bill_key not in seen_bills:
                seen_bills.add(bill_key)
                unique_bills.append(bill)
        
        print(f"\n📊 Session {session}: Found {len(unique_bills)} unique bills matching keywords")
        return unique_bills
        
    except Exception as e:
        print(f"❌ Error scraping bills for session {session}: {e}")
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
    print("🚀 Georgia State Legislature Bill Scraper")
    print(f"Processing {len(KEYWORDS)} keywords across {len(SESSIONS)} session(s)")
    print("="*70)
    
    all_scraped_bills = []
    
    for session in SESSIONS:
        bills = scrape_bills_for_session_selenium(session, KEYWORDS)
        print(f"\n📈 Session {session}: Found {len(bills)} bills matching keywords")
        all_scraped_bills.extend(bills)
    
    print(f"\n🎯 Total bills scraped across all sessions: {len(all_scraped_bills)}")
    
    if all_scraped_bills:
        existing_df = load_existing_data(OUTPUT_FILE)
        save_data(existing_df, all_scraped_bills, OUTPUT_FILE)
        
        print("\n📊 RESULTS SUMMARY:")
        for bill in all_scraped_bills:
            print(f"  • {bill['Bill Number']}: {bill['Bill Title/Topic'][:60]}...")
        
        print(f"\n✅ Saved {len(all_scraped_bills)} bills to {OUTPUT_FILE}")
        print("📁 Review the Excel file to verify data quality!")
    
    print("\n🎉 Georgia scraper completed!")

if __name__ == "__main__":
    main()
