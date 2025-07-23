#!/usr/bin/env python3
"""
Arkansas Healthcare Bill Scraper - FIXED GRID EXTRACTION
Properly extracts clean titles and sponsors from search results grid
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
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd
import re

# Healthcare Keywords
KEYWORDS = [
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

class ArkansasFixedGridScraper:
    def __init__(self):
        self.base_url = "https://www.arkleg.state.ar.us"
        self.search_url = "https://www.arkleg.state.ar.us/Bills/Search"
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
    
    def search_arkansas_keyword_fixed(self, keyword):
        """Arkansas search with FIXED grid extraction"""
        driver = None
        results = []
        
        try:
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            wait = WebDriverWait(driver, 20)
            
            # Navigate and search
            driver.get(self.search_url)
            time.sleep(4)
            
            # Select 2025 session
            try:
                checkbox_2025 = wait.until(EC.presence_of_element_located((By.ID, "session2025R")))
                if not checkbox_2025.is_selected():
                    driver.execute_script("arguments[0].click();", checkbox_2025)
            except:
                return []
            
            # Try 2026 session
            try:
                checkbox_2026 = driver.find_element(By.ID, "session2026R")
                if not checkbox_2026.is_selected():
                    driver.execute_script("arguments[0].click();", checkbox_2026)
            except:
                pass
            
            # Enter keyword
            try:
                exact_phrase_input = wait.until(EC.presence_of_element_located((By.ID, "tbExactPhrase")))
                exact_phrase_input.clear()
                exact_phrase_input.send_keys(keyword)
            except:
                return []
            
            # Set exclusivity
            try:
                exclusivity_dropdown = driver.find_element(By.ID, "ddExclusivity")
                select = Select(exclusivity_dropdown)
                select.select_by_value("Only")
            except:
                pass
            
            # Submit search
            try:
                search_button = driver.find_element(By.XPATH, "//button[@onclick='GetAllCheckboxes();']")
                driver.execute_script("arguments[0].click();", search_button)
            except:
                return []
            
            time.sleep(6)
            
            # Extract from search results grid
            results = self.extract_from_arkansas_grid(driver, keyword)
            
            return results
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def extract_from_arkansas_grid(self, driver, keyword):
        """Extract bills from Arkansas search results grid"""
        results = []
        
        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Check if keyword is in results
            if not self.flexible_keyword_match(page_text, keyword):
                return []
            
            print(f"✅ Keyword found in results")
            
            # Find all result rows (based on your HTML structure)
            result_rows = soup.find_all('div', class_=['row', 'tableRowAlt'])
            
            print(f"📊 Total results parsed: {len(result_rows)}")
            
            for row in result_rows:
                try:
                    bill_info = self.extract_bill_from_grid_row(row, keyword)
                    if bill_info:
                        results.append(bill_info)
                        print(f"  ✅ Found: {bill_info['bill_number']} - {bill_info['bill_title'][:50]}...")
                except Exception as e:
                    continue
            
            return results
            
        except Exception as e:
            print(f"❌ Grid extraction error: {e}")
            return []
    
    def extract_bill_from_grid_row(self, row, keyword):
        """Extract bill info from grid row using HTML structure"""
        try:
            # Get all columns in this row
            columns = row.find_all('div', class_='col-md-2') + row.find_all('div', class_='col-md-7')
            
            if len(columns) < 3:
                return None
            
            bill_number = ""
            bill_title = ""
            sponsor_name = ""
            bill_link = ""
            
            # Column 1 (col-md-2): Bill number and link
            col1 = columns[0] if len(columns) > 0 else None
            if col1:
                # Find bill number link
                bill_link_elem = col1.find('a', href=True)
                if bill_link_elem:
                    bill_number = bill_link_elem.get_text(strip=True)
                    href = bill_link_elem.get('href', '')
                    if href.startswith('/'):
                        bill_link = f"{self.base_url}{href}"
                    else:
                        bill_link = href
            
            # Column 2 (col-md-7): Bill title (clean text without bill number)
            col2 = None
            for col in columns:
                if 'col-md-7' in col.get('class', []):
                    col2 = col
                    break
            
            if col2:
                bill_title = col2.get_text(strip=True)
            
            # Column 3 (col-md-2): Sponsor information
            sponsor_cols = [col for col in columns if 'col-md-2' in col.get('class', [])]
            if len(sponsor_cols) > 1:  # Second col-md-2 is sponsor column
                sponsor_col = sponsor_cols[1]
                sponsor_link = sponsor_col.find('a', href=True)
                if sponsor_link:
                    sponsor_name = sponsor_link.get_text(strip=True)
            
            # Verify we have essential data and keyword match
            if not bill_number or not bill_title:
                return None
            
            # Check if this row contains our keyword
            row_text = row.get_text()
            if not self.flexible_keyword_match(row_text, keyword):
                return None
            
            # Get last action from individual bill page
            last_action = self.get_last_action_from_bill_page(bill_link) if bill_link else "Status not available"
            
            return {
                'year': '2025',
                'state': 'Arkansas',
                'bill_number': bill_number,
                'bill_title': bill_title,  # Already clean from grid
                'summary': bill_title,     # Already clean from grid
                'sponsors': sponsor_name or 'Arkansas Legislature',  # Already clean from grid
                'last_action': last_action,
                'bill_link': bill_link,
                'extracted_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return None
    
    def get_last_action_from_bill_page(self, bill_url):
        """Get last action from individual bill page"""
        if not bill_url:
            return "Status not available"
        
        driver = None
        
        try:
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            
            driver.get(bill_url)
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Look for status/action in tables
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        if any(word in label for word in ['status', 'action', 'last']):
                            action_text = cells[1].get_text(strip=True)
                            if len(action_text) > 5:
                                return action_text
            
            # Look for action patterns in page text
            page_text = soup.get_text()
            action_patterns = [
                r'last action[:\s]*([^\n]{10,100})',
                r'status[:\s]*([^\n]{10,100})'
            ]
            
            for pattern in action_patterns:
                match = re.search(pattern, page_text, re.I)
                if match:
                    action_text = match.group(1).strip()
                    if len(action_text) > 5:
                        return action_text
            
            return "Legislative process active"
            
        except Exception as e:
            return "Status not available"
        finally:
            if driver:
                driver.quit()
    
    def flexible_keyword_match(self, text, keyword):
        """Flexible keyword matching"""
        if not text or not keyword:
            return False
        
        clean_text = re.sub(r'[\s\-_]+', ' ', text.lower())
        clean_keyword = re.sub(r'[\s\-_]+', ' ', keyword.lower())
        
        if clean_keyword in clean_text:
            return True
        
        keyword_words = clean_keyword.split()
        if len(keyword_words) > 1:
            return all(word in clean_text for word in keyword_words)
        
        return False
    
    def search_all_keywords_fixed(self, keywords=None):
        """Search all keywords with fixed grid extraction"""
        if keywords is None:
            keywords = KEYWORDS
        
        all_results = []
        
        print(f"🚀 Arkansas Healthcare Bills - FIXED GRID EXTRACTION")
        print("=" * 60)
        print("🔧 Fixed: Clean titles and sponsors from search results grid")
        print("🔧 Fixed: No bill numbers in titles, no extra text in sponsors")
        print()
        
        for idx, keyword in enumerate(keywords, 1):
            print(f"\n[{idx:2d}/{len(keywords)}] Processing: '{keyword}'")
            
            try:
                results = self.search_arkansas_keyword_fixed(keyword)
                
                if results:
                    all_results.extend(results)
                    print(f"✅ Found {len(results)} bills with clean data")
                else:
                    print(f"📄 No results for '{keyword}'")
                
                if idx < len(keywords):
                    time.sleep(3)
                    
            except Exception as e:
                print(f"❌ Error for '{keyword}': {str(e)}")
                continue
        
        # Remove duplicates
        unique_results = []
        seen_bills = set()
        
        for result in all_results:
            bill_key = f"{result['bill_number']}_{result['year']}"
            if bill_key not in seen_bills:
                unique_results.append(result)
                seen_bills.add(bill_key)
        
        print(f"\n📊 FINAL FIXED RESULTS: {len(unique_results)} unique bills")
        return unique_results
    
    def save_to_excel(self, results, filename=None):
        """Save fixed results to Excel"""
        if not results:
            print("❌ No results to save")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"arkansas_healthcare_fixed_grid_{timestamp}.xlsx"
        
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
            
            print(f"✅ Fixed results saved to: {full_path}")
            return full_path
            
        except Exception as e:
            print(f"❌ Save error: {e}")
            return None

def main():
    """Main execution with fixed grid extraction"""
    print("🚀 Arkansas Healthcare Bill Scraper - FIXED GRID EXTRACTION")
    print("=" * 60)
    print("🔧 Fixed: Extracts clean data directly from search results grid")
    print()
    
    scraper = ArkansasFixedGridScraper()
    
    try:
        results = scraper.search_all_keywords_fixed(KEYWORDS)
        
        if results:
            excel_file = scraper.save_to_excel(results)
            
            if excel_file:
                print(f"\n🎉 FIXED GRID EXTRACTION SUCCESS!")
                print(f"📊 Found {len(results)} Arkansas healthcare bills")
                print(f"💾 Clean data saved to: {excel_file}")
                
                # Show sample of fixed data
                print(f"\n📋 SAMPLE FIXED DATA:")
                print("=" * 60)
                for result in results[:2]:
                    print(f"Bill: {result['bill_number']}")
                    print(f"Title: {result['bill_title']}")
                    print(f"Sponsor: {result['sponsors']}")
                    print(f"Last Action: {result['last_action']}")
                    print("-" * 40)
                
        else:
            print("📄 No healthcare bills found")
            
        return 0
        
    except Exception as e:
        print(f"💥 Critical error: {str(e)}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Fixed grid scraper interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)
