#!/usr/bin/env python3
"""
Arizona Healthcare Bill Scraper - All Keywords
Complete extraction for all 13 healthcare keywords with minimal output
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
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd
import re

# All 13 Healthcare Keywords
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

class ArizonaHealthcareScraper:
    def __init__(self):
        self.base_url = "https://www.azleg.gov"
        self.search_url = "https://www.azleg.gov/bills/"
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
    def get_chrome_options(self):
        """Get Chrome options for maximum stability"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        return chrome_options
    
    def search_single_keyword(self, keyword, session_year="2025"):
        """Search for a single keyword with minimal output"""
        driver = None
        results = []
        
        try:
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            wait = WebDriverWait(driver, 20)
            
            # Navigate to search page
            driver.get(self.search_url)
            time.sleep(3)
            
            # Find search input using multiple methods
            try:
                search_input = wait.until(EC.presence_of_element_located((By.NAME, "insearch")))
            except:
                try:
                    search_input = wait.until(EC.presence_of_element_located((By.ID, "searchformdata")))
                except:
                    try:
                        search_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search Bills']")))
                    except:
                        search_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='search']")))
            
            # Clear and enter search term
            search_input.clear()
            search_input.send_keys(keyword)
            
            # Submit using the correct form
            try:
                submit_button = driver.find_element(By.XPATH, "//form[@id='searchForm']//input[@type='submit']")
                submit_button.click()
            except:
                try:
                    submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
                    submit_button.click()
                except:
                    search_input.send_keys(Keys.ENTER)
            
            time.sleep(5)  # Wait for results to load
            
            # Parse results
            basic_results = self.parse_search_results_enhanced(driver, keyword, session_year)
            
            driver.quit()
            driver = None
            
            if not basic_results:
                return []
            
            print(f"📊 Total results parsed: {len(basic_results)}")
            
            # Get detailed information for ALL found bills
            detailed_results = []
            
            for idx, bill in enumerate(basic_results, 1):
                try:
                    sponsors, last_action, clean_title = self.get_bill_details_with_title_fix(bill['bill_link'])
                    
                    # Use clean title if available
                    if clean_title and len(clean_title) > 10:
                        bill['bill_title'] = clean_title
                        bill['summary'] = clean_title
                    
                    bill['sponsors'] = sponsors
                    bill['last_action'] = last_action
                    detailed_results.append(bill)
                    
                except Exception as e:
                    bill['sponsors'] = "Arizona Legislature"
                    bill['last_action'] = "Active" 
                    detailed_results.append(bill)
                
                if idx < len(basic_results):
                    time.sleep(1)  # Shorter delay for speed
            
            return detailed_results
            
        except Exception as e:
            return []
            
        finally:
            if driver:
                driver.quit()
            time.sleep(1)
    
    def parse_search_results_enhanced(self, driver, keyword, session_year):
        """Parse search results with clean title extraction"""
        results = []
        
        try:
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Method 1: Look for bill links
            bill_links = soup.find_all('a', href=True)
            
            for link in bill_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if any(pattern in href.upper() for pattern in ['BILLS/', 'LEGTEXT/', 'HB', 'SB', 'SCR', 'SJR']) and text:
                    
                    bill_match = re.search(r'[HS][BCJ]R?\d+', text, re.I)
                    if bill_match:
                        bill_number = bill_match.group().upper()
                        
                        clean_title = self.extract_super_clean_title(text)
                        
                        if self.is_keyword_match_enhanced(clean_title, keyword):
                            
                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('/'):
                                full_url = f"{self.base_url}{href}"
                            else:
                                full_url = f"{self.base_url}/{href}"
                            
                            bill_data = {
                                'year': session_year,
                                'state': 'Arizona',
                                'bill_number': bill_number,
                                'bill_title': clean_title,
                                'summary': clean_title,
                                'sponsors': 'TBD',
                                'last_action': 'TBD',
                                'bill_link': full_url,
                                'extracted_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'matched_keyword': keyword,
                                'bill_date': datetime.now().strftime('%Y-%m-%d')
                            }
                            
                            results.append(bill_data)
            
            # Method 2: Look for structured tables
            if not results:
                tables = soup.find_all('table')
                
                for table in tables:
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        
                        if len(cells) >= 2:
                            row_text = row.get_text()
                            
                            if self.is_keyword_match_enhanced(row_text, keyword):
                                
                                for cell in cells:
                                    cell_links = cell.find_all('a')
                                    
                                    for link in cell_links:
                                        link_text = link.get_text(strip=True)
                                        link_href = link.get('href', '')
                                        
                                        if re.match(r'[HS][BCJ]R?\d+', link_text, re.I):
                                            
                                            if link_href.startswith('http'):
                                                full_url = link_href
                                            elif link_href.startswith('/'):
                                                full_url = f"{self.base_url}{link_href}"
                                            else:
                                                full_url = f"{self.base_url}/{link_href}"
                                            
                                            clean_title = self.extract_super_clean_title(row_text)
                                            
                                            bill_data = {
                                                'year': session_year,
                                                'state': 'Arizona',
                                                'bill_number': link_text.upper(),
                                                'bill_title': clean_title,
                                                'summary': clean_title,
                                                'sponsors': 'TBD',
                                                'last_action': 'TBD',
                                                'bill_link': full_url,
                                                'extracted_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                'matched_keyword': keyword,
                                                'bill_date': datetime.now().strftime('%Y-%m-%d')
                                            }
                                            
                                            results.append(bill_data)
            
            return results
            
        except Exception as e:
            return []
    
    def extract_super_clean_title(self, raw_text):
        """Clean title extraction removing HTML/version junk"""
        if not raw_text:
            return "Title not available"
        
        clean_text = raw_text.strip()
        
        # Remove junk pattern
        junk_pattern = r'(?:PDF|HTML)\d*[HS][BCJ]R?\d+(?:\s*-\s*\d+[A-Z]*)*(?:\s*-\s*[IV]+\s*Ver[A-Z]*\d*)*'
        
        junk_match = re.search(junk_pattern, clean_text, re.I)
        if junk_match:
            title_start = junk_match.end()
            clean_text = clean_text[title_start:].strip()
        
        # Remove remaining bill references
        clean_text = re.sub(r'\b[HS][BCJ]R?\d+\b', '', clean_text, flags=re.I)
        clean_text = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '', clean_text)
        clean_text = re.sub(r'\b(?:Ver|Version|571R)\b', '', clean_text, flags=re.I)
        clean_text = re.sub(r'\b\d{3,}\b', '', clean_text)
        clean_text = re.sub(r'[-\s]+', ' ', clean_text).strip()
        clean_text = clean_text.strip('- ;,.')
        
        if len(clean_text) < 10:
            semicolon_match = re.search(r'([a-z][^;]*(?:;[^;]*)*)', raw_text, re.I)
            if semicolon_match:
                clean_text = semicolon_match.group(1).strip()
        
        return clean_text if clean_text else "Healthcare related bill"
    
    def is_keyword_match_enhanced(self, text, keyword):
        """Enhanced keyword matching"""
        if not text or not keyword:
            return False
            
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        if keyword_lower in text_lower:
            return True
        
        variations = []
        
        if 'prior authorization' in keyword_lower:
            variations = ['prior auth', 'preauthorization', 'pre-authorization', 'prior approval']
        elif 'artificial intelligence' in keyword_lower:
            variations = ['ai', 'machine learning', 'ml', 'artificial intel']
        elif 'clean claims' in keyword_lower:
            variations = ['clean claim', 'claims processing', 'claims management']
        elif 'utilization review' in keyword_lower:
            variations = ['util review', 'ur', 'utilization mgmt', 'utilization management']
        elif 'medical necessity' in keyword_lower:
            variations = ['medical necessity', 'medically necessary', 'medical need']
        elif 'prompt pay' in keyword_lower:
            variations = ['prompt payment', 'timely payment', 'payment timing']
        elif 'coordination of benefits' in keyword_lower:
            variations = ['cob', 'benefit coordination', 'benefits coordination']
        elif 'clinical decision' in keyword_lower:
            variations = ['clinical support', 'decision support', 'clinical decision support']
        
        for variation in variations:
            if variation in text_lower:
                return True
        
        return False
    
    def get_bill_details_with_title_fix(self, bill_url):
        """Extract sponsors, last action, and clean title from bill page"""
        if not bill_url:
            return "Unknown", "Unknown", ""
        
        driver = None
        
        try:
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            
            driver.get(bill_url)
            time.sleep(3)  # Faster for bulk processing
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract clean title from bill page
            clean_title = self.extract_title_from_bill_page(soup)
            
            # Extract sponsors
            sponsors = self.extract_sponsors_enhanced(driver)
            
            # Extract meaningful last action
            last_action = self.extract_meaningful_last_action(soup)
            
            return sponsors, last_action, clean_title
            
        except Exception as e:
            return "Arizona Legislature", "Committee Review - 2025", ""
            
        finally:
            if driver:
                driver.quit()
    
    def extract_title_from_bill_page(self, soup):
        """Extract clean title from bill page"""
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        for i, cell in enumerate(cells):
                            cell_text = cell.get_text().lower()
                            if 'short title' in cell_text or 'title' in cell_text:
                                if i + 1 < len(cells):
                                    title_text = cells[i + 1].get_text(strip=True)
                                    if len(title_text) > 10:
                                        return title_text
            
            return ""
            
        except Exception as e:
            return ""
    
    def extract_sponsors_enhanced(self, driver):
        """Extract sponsors using working method"""
        try:
            sponsor_select = driver.find_element(By.ID, "slist")
            options = sponsor_select.find_elements(By.TAG_NAME, "option")
            
            if options:
                first_option = options[0]
                title_attr = first_option.get_attribute('title')
                
                if title_attr and len(title_attr) > 2:
                    sponsor_name = title_attr.strip()
                    return f"Sen. {sponsor_name}"
                else:
                    sponsor_text = first_option.text
                    sponsor_name = sponsor_text.replace('(Prime)', '').replace('(Co)', '').strip()
                    return f"Sen. {sponsor_name}" if sponsor_name else "Arizona Legislature"
            
            return "Arizona Legislature"
            
        except Exception as e:
            return "Arizona Legislature"
    
    def extract_meaningful_last_action(self, soup):
        """Extract meaningful last action"""
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                if len(rows) > 1:
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        
                        if len(cells) >= 2:
                            row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                            
                            if any(word in row_text.lower() for word in 
                                   ['committee', 'introduced', 'passed', 'assigned', 'transmitted']):
                                
                                committee_match = re.search(r'committee[:\s]*([A-Z]+)', row_text, re.I)
                                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', row_text)
                                
                                if committee_match:
                                    committee = committee_match.group(1)
                                    date_part = f" on {date_match.group(1)}" if date_match else ""
                                    return f"Assigned to {committee} Committee{date_part}"
                                
                                if 'introduced' in row_text.lower():
                                    date_part = f" on {date_match.group(1)}" if date_match else ""
                                    return f"Introduced{date_part}"
            
            return "Under committee review"
            
        except Exception as e:
            return "Committee review - 2025"
    
    def search_all_keywords(self, keywords=None, session_year="2025"):
        """Search all healthcare keywords with minimal output"""
        if keywords is None:
            keywords = KEYWORDS
        
        all_results = []
        successful_searches = 0
        
        print(f"🚀 Starting Arizona search for {len(keywords)} healthcare keywords in {session_year}")
        print("=" * 70)
        
        for idx, keyword in enumerate(keywords, 1):
            print(f"\n[{idx:2d}/{len(keywords)}] Processing: '{keyword}'")
            
            try:
                results = self.search_single_keyword(keyword, session_year)
                
                if results:
                    all_results.extend(results)
                    successful_searches += 1
                    print(f"✅ Found {len(results)} bills for '{keyword}'")
                else:
                    print(f"📄 No results for '{keyword}'")
                
                # Brief pause between keywords
                if idx < len(keywords):
                    time.sleep(3)
                    
            except Exception as e:
                print(f"❌ Error for '{keyword}': {str(e)}")
                continue
        
        # Remove duplicates across all keywords
        unique_results = []
        seen_bills = set()
        
        for result in all_results:
            bill_key = f"{result['bill_number']}_{result['year']}"
            if bill_key not in seen_bills:
                unique_results.append(result)
                seen_bills.add(bill_key)
        
        print(f"\n📊 FINAL ARIZONA RESULTS:")
        print("=" * 70)
        print(f"Keywords processed: {len(keywords)}")
        print(f"Successful searches: {successful_searches}")
        print(f"Total results found: {len(all_results)}")
        print(f"Unique bills found: {len(unique_results)}")
        
        return unique_results
    
    def save_to_excel(self, results, filename=None):
        """Save results to Excel"""
        if not results:
            print("❌ No results to save")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"arizona_healthcare_all_keywords_{timestamp}.xlsx"
        
        full_path = os.path.join(self.script_dir, filename)
        
        try:
            df = pd.DataFrame(results)
            
            column_order = [
                'year', 'state', 'bill_number', 'bill_title', 'summary',
                'sponsors', 'last_action', 'bill_link', 'extracted_date', 'matched_keyword'
            ]
            
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            df.to_excel(full_path, index=False)
            
            print(f"✅ Results saved to: {full_path}")
            print(f"📊 Saved {len(results)} bills to Excel")
            
            return full_path
            
        except Exception as e:
            print(f"❌ Error saving to Excel: {str(e)}")
            return None

def main():
    """Main execution function for all keywords"""
    print("🚀 Arizona Healthcare Bill Scraper - All 13 Keywords")
    print("=" * 60)
    print("💊 Complete healthcare keyword extraction")
    print("🏛️ Target: 2025 Arizona Legislative Session")
    print()
    
    scraper = ArizonaHealthcareScraper()
    
    try:
        # Search for 2025 session with all keywords
        results_2025 = scraper.search_all_keywords(KEYWORDS, "2025")
        
        if results_2025:
            excel_file = scraper.save_to_excel(results_2025)
            
            if excel_file:
                print(f"\n🎉 SUCCESS!")
                print(f"📊 Found {len(results_2025)} unique healthcare bills")
                print(f"💾 Data saved to: {excel_file}")
                
                # Summary by keyword
                keyword_summary = {}
                for result in results_2025:
                    kw = result['matched_keyword']
                    keyword_summary[kw] = keyword_summary.get(kw, 0) + 1
                
                print("\n📋 KEYWORD SUMMARY:")
                for keyword, count in keyword_summary.items():
                    print(f"  • {keyword}: {count} bills")
                    
            else:
                print("❌ Failed to save results to Excel")
        else:
            print("📄 No healthcare bills found in Arizona")
            
        return 0
        
    except Exception as e:
        print(f"💥 Critical error: {str(e)}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Arizona scraper interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

