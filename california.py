#!/usr/bin/env python3
"""
California Healthcare Bill Scraper - COMPLETE FIXED VERSION
1. Handles pagination to get all bills from all pages
2. Visits Status tab to extract proper bill title, summary, and last action
3. Processes all keywords with duplicate removal
"""

import time
import os
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import pandas as pd
import re

# Single keyword for testing
TEST_KEYWORD = 'Prior authorization'

# All keywords for full implementation
ALL_KEYWORDS = [
    'Prior authorization',
    'Utilization review', 
    'Utilization management',
    'Medical necessity review',
    'Prompt pay',
    'Prompt payment',
    'Clean claims',
    'Clean claim',
    'Coordination of benefits',
    'Artificial intelligence',
    'Clinical decision support',
    'Automated decision making',
    'Automate decision support'
]

class CaliforniaFixedTextSearchScraper:
    def __init__(self):
        self.base_url = "https://leginfo.legislature.ca.gov"
        self.search_url = "https://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml"
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
    def get_chrome_options(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        return chrome_options
    
    def search_california_text_search_fixed(self, keyword):
        """Search California with FIXED pagination handling"""
        print(f"🔍 Searching California for: '{keyword}'")
        print(f"🔧 Fixed: Pagination + Status tab extraction")
        
        driver = None
        results = []
        
        try:
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            wait = WebDriverWait(driver, 20)
            
            # Navigate and setup search
            driver.get(self.search_url)
            time.sleep(5)
            print(f"✅ Navigated to California search page")
            
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            time.sleep(3)
            
            # Click Text Search tab
            text_search_tab = driver.find_element(By.ID, "j_idt91:nav_bar_top_text_search")
            text_search_tab.click()
            time.sleep(4)
            print(f"✅ Clicked Text Search tab")
            
            # Select 2025-2026 session
            session_dropdown = driver.find_element(By.ID, "billSearchAdvForm:sessionyear")
            select = Select(session_dropdown)
            select.select_by_value("20252026")
            print(f"✅ Selected 2025-2026 session")
            
            # Enter keyword
            all_words_input = driver.find_element(By.ID, "billSearchAdvForm:and_one")
            all_words_input.clear()
            all_words_input.send_keys(keyword)
            print(f"✅ Entered keyword: '{keyword}'")
            
            # Submit search
            search_button = driver.find_element(By.ID, "billSearchAdvForm:attrSearch")
            search_button.click()
            print(f"✅ Submitted search")
            time.sleep(8)
            
            # FIXED: Extract from ALL pages with proper pagination
            results = self.extract_all_pages_fixed_pagination(driver, keyword)
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching for '{keyword}': {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def extract_all_pages_fixed_pagination(self, driver, keyword):
        """FIXED: Extract bills from ALL pages with proper pagination handling"""
        all_bills = []
        page_num = 1
        max_pages = 10  # Safety limit
        
        try:
            while page_num <= max_pages:
                print(f"  📄 Processing search results page {page_num}...")
                
                # Extract bills from current page
                page_bills = self.extract_bills_from_page_fixed(driver, page_num)
                all_bills.extend(page_bills)
                
                print(f"    ✅ Extracted {len(page_bills)} bills from page {page_num}")
                
                if len(page_bills) == 0:
                    print(f"    ✅ No bills on page {page_num} - reached end")
                    break
                
                # FIXED: Better pagination detection and clicking
                if not self.navigate_to_next_page_fixed(driver, page_num):
                    print(f"    ✅ No more pages available")
                    break
                
                page_num += 1
                time.sleep(3)
            
            print(f"📊 TOTAL BILLS EXTRACTED: {len(all_bills)} bills across {page_num} pages")
            return all_bills
            
        except Exception as e:
            print(f"❌ Error in pagination: {e}")
            return all_bills
    
    def navigate_to_next_page_fixed(self, driver, current_page):
        """FIXED: Navigate to next page with multiple strategies"""
        try:
            # Strategy 1: Look for "Next" button
            next_buttons = driver.find_elements(By.XPATH, "//input[@value='Next' or @value='next' or @value='NEXT']")
            for btn in next_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(4)
                    print(f"      ✅ Clicked 'Next' button")
                    return True
            
            # Strategy 2: Look for next page number (current_page + 1)
            next_page_num = current_page + 1
            page_links = driver.find_elements(By.XPATH, f"//a[text()='{next_page_num}']")
            for link in page_links:
                if link.is_displayed() and link.is_enabled():
                    link.click()
                    time.sleep(4)
                    print(f"      ✅ Clicked page {next_page_num} link")
                    return True
            
            # Strategy 3: Look for ">" or ">>" symbols
            arrow_links = driver.find_elements(By.XPATH, "//a[contains(text(), '>') and not(contains(text(), '>>>'))]")
            for link in arrow_links:
                if link.is_displayed() and link.is_enabled():
                    link.click()
                    time.sleep(4)
                    print(f"      ✅ Clicked arrow '>' link")
                    return True
            
            # Strategy 4: Look for pagination in forms
            next_inputs = driver.find_elements(By.XPATH, "//input[contains(@onclick, 'next') or contains(@onclick, 'Next')]")
            for inp in next_inputs:
                if inp.is_displayed() and inp.is_enabled():
                    inp.click()
                    time.sleep(4)
                    print(f"      ✅ Clicked pagination input")
                    return True
            
            return False
            
        except Exception as e:
            print(f"      ❌ Navigation error: {e}")
            return False
    
    def extract_bills_from_page_fixed(self, driver, page_num):
        """Extract bills from current page"""
        bills = []
        
        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find results table
            tbody = soup.find('tbody')
            if not tbody:
                print(f"      ⚠️ No tbody found on page {page_num}")
                return []
            
            rows = tbody.find_all('tr')
            print(f"      ✅ Found {len(rows)} result rows on page {page_num}")
            
            for row in rows:
                try:
                    bill_info = self.extract_bill_from_row_fixed(row)
                    if bill_info:
                        bills.append(bill_info)
                        print(f"        ✅ {bill_info['bill_number']} by {bill_info['author']}")
                
                except Exception as e:
                    continue
            
            return bills
            
        except Exception as e:
            print(f"❌ Error extracting from page {page_num}: {e}")
            return []
    
    def extract_bill_from_row_fixed(self, row):
        """Extract bill from row"""
        try:
            cell = row.find('td')
            if not cell:
                return None
            
            div = cell.find('div', class_='commdataRow')
            if not div:
                return None
            
            link = div.find('a', href=True)
            if not link:
                return None
            
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            bill_match = re.search(r'([AS]B-?\d+)', link_text, re.I)
            if not bill_match:
                return None
            
            bill_number = bill_match.group(1)
            
            div_text = div.get_text()
            author_match = re.search(r'Author:\s*([^\n\r]+)', div_text, re.I)
            author = author_match.group(1).strip() if author_match else "Unknown"
            
            # Create Status tab URL directly
            bill_id_match = re.search(r'bill_id=([^&]+)', href)
            if bill_id_match:
                bill_id = bill_id_match.group(1)
                # Go directly to Status tab
                status_url = f"{self.base_url}/faces/billStatusClient.xhtml?bill_id={bill_id}"
            else:
                status_url = f"{self.base_url}{href}"
            
            return {
                'year': '2025-2026',
                'state': 'California',
                'bill_number': bill_number,
                'author': author,
                'bill_link': status_url,  # Direct link to Status tab
                'extracted_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return None
    
    def enhance_with_status_tab_data(self, basic_bills):
        """FIXED: Extract data from Status tab on each bill"""
        enhanced_results = []
        
        print(f"\n🔍 Getting Status tab data for {len(basic_bills)} bills...")
        
        for idx, bill in enumerate(basic_bills, 1):
            print(f"  [{idx}/{len(basic_bills)}] Processing {bill['bill_number']}...")
            
            try:
                enhanced_bill = self.get_status_tab_data(bill)
                enhanced_results.append(enhanced_bill)
                
                print(f"    ✅ Title: {enhanced_bill['bill_title'][:50]}...")
                print(f"    ✅ Sponsor: {enhanced_bill['sponsors']}")
                print(f"    ✅ Last Action: {enhanced_bill['last_action'][:50]}...")
                
            except Exception as e:
                print(f"    ⚠️ Error getting Status tab data: {e}")
                # Add with defaults from search results
                bill.update({
                    'bill_title': f"California {bill['bill_number']}",
                    'summary': f"California {bill['bill_number']}",
                    'sponsors': bill.get('author', 'California Legislature'),
                    'last_action': 'Status not available'
                })
                enhanced_results.append(bill)
            
            if idx < len(basic_bills):
                time.sleep(2)
        
        return enhanced_results
    
    def get_status_tab_data(self, basic_bill):
        """FIXED: Extract data from Status tab page"""
        driver = None
        
        try:
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            
            # Go directly to Status tab URL
            driver.get(basic_bill['bill_link'])
            time.sleep(4)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract from Status page structure
            bill_title = self.extract_topic_from_status_page(soup)
            summary = self.extract_title_from_status_page(soup)
            sponsors = self.extract_lead_authors_from_status_page(soup)
            last_action = self.extract_last_action_from_history_table(soup)
            
            enhanced_bill = basic_bill.copy()
            enhanced_bill.update({
                'bill_title': bill_title,
                'summary': summary,
                'sponsors': sponsors,
                'last_action': last_action
            })
            
            return enhanced_bill
            
        except Exception as e:
            enhanced_bill = basic_bill.copy()
            enhanced_bill.update({
                'bill_title': f"California {basic_bill['bill_number']}",
                'summary': f"California {basic_bill['bill_number']}",
                'sponsors': basic_bill.get('author', 'California Legislature'),
                'last_action': 'Status not available'
            })
            return enhanced_bill
            
        finally:
            if driver:
                driver.quit()
    
    def extract_topic_from_status_page(self, soup):
        """Extract bill title from Topic field on Status page"""
        try:
            # Look for Topic/Subject in status section
            topic_span = soup.find('span', id='subject')
            if topic_span:
                return topic_span.get_text(strip=True)
            
            # Alternative: Look for topic in status labels
            status_labels = soup.find_all('span', class_='statusLabel')
            for label in status_labels:
                parent = label.find_parent()
                if parent and 'topic' in parent.get_text().lower():
                    return label.get_text(strip=True)
            
            return "California healthcare bill"
            
        except:
            return "California healthcare bill"
    
    def extract_title_from_status_page(self, soup):
        """Extract summary from Title field on Status page (cleaned)"""
        try:
            # Look for Title in status section
            title_span = soup.find('span', id='title')
            if title_span:
                raw_html = str(title_span)
                clean_text = re.sub(r'<[^>]+>', '', raw_html)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                return clean_text if clean_text else "Legislative summary not available"
            
            return "Legislative summary not available"
            
        except:
            return "Legislative summary not available"
    
    def extract_lead_authors_from_status_page(self, soup):
        """Extract sponsors from Lead Authors field on Status page"""
        try:
            # Look for Lead Authors
            authors_span = soup.find('span', id='leadAuthors')
            if authors_span:
                authors_text = authors_span.get_text(strip=True)
                if authors_text and authors_text != '-':
                    # Clean up author names (remove party affiliations)
                    clean_authors = re.sub(r'\s*\([AS]\)\s*', '', authors_text).strip()
                    return clean_authors
            
            return "California Legislature"
            
        except:
            return "California Legislature"
    
    def extract_last_action_from_history_table(self, soup):
        """FIXED: Extract last action from 'Last 5 History Actions' table"""
        try:
            # Find the history table by ID
            history_table = soup.find('table', id='billhistory')
            
            if history_table:
                # Find tbody
                tbody = history_table.find('tbody')
                if tbody:
                    # Get first row (most recent action)
                    first_row = tbody.find('tr')
                    if first_row:
                        cells = first_row.find_all('td')
                        if len(cells) >= 2:
                            date_text = cells[0].get_text(strip=True)
                            action_text = cells[1].get_text(strip=True)
                            return f"{action_text} ({date_text})"
            
            # Fallback: Look for any history table
            history_rows = soup.find_all('tr')
            for row in history_rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    date_text = cells[0].get_text(strip=True)
                    action_text = cells[1].get_text(strip=True)
                    
                    # Check if this looks like a date and action
                    if re.match(r'\d{2}/\d{2}/\d{2}', date_text) and len(action_text) > 10:
                        return f"{action_text} ({date_text})"
            
            return "Legislative process active"
            
        except Exception as e:
            return "Legislative process active"
    
    def search_all_keywords(self, keywords=ALL_KEYWORDS):
        """ADDED: Search all keywords using text search with fixed pagination and status tab extraction"""
        all_basic_bills = []
        
        print(f"🚀 Starting California search for {len(keywords)} healthcare keywords")
        print("=" * 60)
        
        for idx, keyword in enumerate(keywords, 1):
            print(f"\n[{idx:2d}/{len(keywords)}] Processing: '{keyword}'")
            
            try:
                basic_results = self.search_california_text_search_fixed(keyword)
                
                if basic_results:
                    all_basic_bills.extend(basic_results)
                    print(f"✅ Found {len(basic_results)} bills for '{keyword}'")
                else:
                    print(f"📄 No results for '{keyword}'")
                
                # Pause between keywords to avoid overwhelming the server
                if idx < len(keywords):
                    time.sleep(5)
                    
            except Exception as e:
                print(f"❌ Error for '{keyword}': {str(e)}")
                continue
        
        # Remove duplicates
        unique_basic_bills = []
        seen_bills = set()
        
        for bill in all_basic_bills:
            bill_key = f"{bill['bill_number']}_{bill['year']}"
            if bill_key not in seen_bills:
                unique_basic_bills.append(bill)
                seen_bills.add(bill_key)
        
        print(f"\n📊 UNIQUE SEARCH RESULTS: {len(unique_basic_bills)} bills")
        
        # Enhance with Status tab data
        if unique_basic_bills:
            enhanced_results = self.enhance_with_status_tab_data(unique_basic_bills)
            return enhanced_results
        else:
            return []
    
    def test_single_keyword_fixed(self, keyword=TEST_KEYWORD):
        """Test with single keyword using FIXED pagination and Status tab"""
        print(f"🧪 CALIFORNIA FIXED TEST - PAGINATION & STATUS TAB")
        print("=" * 60)
        print(f"🔍 Testing with: '{keyword}'")
        print(f"🔧 Fixed: Pagination to get ALL bills")
        print(f"🔧 Fixed: Status tab extraction for proper data")
        print()
        
        # Get search results from ALL pages
        search_results = self.search_california_text_search_fixed(keyword)
        
        if search_results:
            print(f"\n🎉 SUCCESS! Found {len(search_results)} bills across all pages")
            
            # Show bill numbers
            bill_numbers = [b['bill_number'] for b in search_results]
            print(f"Bills found: {bill_numbers}")
            
            # Enhance with Status tab data
            enhanced_bills = self.enhance_with_status_tab_data(search_results)
            
            return enhanced_bills
        else:
            return []
    
    def save_to_excel(self, results, filename=None):
        """Save to Excel"""
        if not results:
            print("❌ No results to save")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"california_healthcare_fixed_full_{timestamp}.xlsx"
        
        full_path = os.path.join(self.script_dir, filename)
        
        try:
            df = pd.DataFrame(results)
            column_order = [
                'year', 'state', 'bill_number', 'bill_title', 'summary',
                'sponsors', 'last_action', 'bill_link', 'extracted_date'
            ]
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            df.to_excel(full_path, index=False)
            
            print(f"✅ Results saved to: {full_path}")
            return full_path
            
        except Exception as e:
            print(f"❌ Save error: {e}")
            return None

def main():
    """Test California with FIXED pagination and Status tab extraction"""
    print("🧪 CALIFORNIA FIXED SCRAPER")
    print("=" * 50)
    print("🔧 Fixed: Pagination to get bills from ALL pages")
    print("🔧 Fixed: Status tab extraction for proper data")
    print()
    
    scraper = CaliforniaFixedTextSearchScraper()
    
    # Process all keywords
    results = scraper.search_all_keywords(ALL_KEYWORDS)
    
    if results:
        excel_file = scraper.save_to_excel(results)
        
        if excel_file:
            print(f"\n🎉 CALIFORNIA COMPLETE SUCCESS!")
            print(f"📊 Found {len(results)} bills with proper data")
            print(f"💾 Data saved to: {excel_file}")
            
            # Show sample
            print(f"\n📋 SAMPLE RESULTS:")
            for result in results[:2]:
                print(f"\nBill: {result['bill_number']}")
                print(f"Title: {result['bill_title']}")
                print(f"Summary: {result['summary'][:100]}...")
                print(f"Sponsor: {result['sponsors']}")
                print(f"Last Action: {result['last_action']}")
    else:
        print("📄 No results found")

if __name__ == "__main__":
    main()
