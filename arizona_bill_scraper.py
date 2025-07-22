#!/usr/bin/env python3
"""
Arizona Healthcare Bill Scraper - EXACT KEYWORD MATCHING ONLY
Only includes bills that literally contain the exact keywords
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

# EXACT Healthcare Keywords - Must match literally
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

class ArizonaExactKeywordScraper:
    def __init__(self):
        self.base_url = "https://www.azleg.gov"
        self.search_url = "https://www.azleg.gov/bills/"
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
    
    def exact_keyword_match_only(self, text, target_keyword):
        """EXACT MATCH ONLY - No variations, no healthcare context needed"""
        if not text or not target_keyword:
            return False
        
        # Clean text minimally - just remove HTML/PDF artifacts
        clean_text = re.sub(r'(?:PDF|HTML)\d+|\d{1,2}/\d{1,2}/\d{4}|Ver\w*', '', text, flags=re.I)
        clean_text = re.sub(r'\s+', ' ', clean_text).lower()
        target_lower = target_keyword.lower()
        
        # EXACT phrase match ONLY
        return target_lower in clean_text
    
    def search_single_keyword_exact(self, keyword, session_year="2025"):
        """Search with EXACT keyword matching only"""
        driver = None
        results = []
        
        try:
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            wait = WebDriverWait(driver, 20)
            
            # Navigate and search
            driver.get(self.search_url)
            time.sleep(3)
            
            # Find search input
            try:
                search_input = wait.until(EC.presence_of_element_located((By.NAME, "insearch")))
            except:
                try:
                    search_input = wait.until(EC.presence_of_element_located((By.ID, "searchformdata")))
                except:
                    search_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='search']")))
            
            # Execute search
            search_input.clear()
            search_input.send_keys(keyword)
            
            # Submit search
            try:
                submit_button = driver.find_element(By.XPATH, "//form[@id='searchForm']//input[@type='submit']")
                submit_button.click()
            except:
                try:
                    submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
                    submit_button.click()
                except:
                    search_input.send_keys(Keys.ENTER)
            
            time.sleep(5)
            
            # Parse with EXACT matching only
            basic_results = self.parse_results_exact_only(driver, keyword, session_year)
            
            driver.quit()
            driver = None
            
            if not basic_results:
                return []
            
            print(f"📊 Total results parsed: {len(basic_results)}")
            
            # Get detailed information
            detailed_results = []
            
            for idx, bill in enumerate(basic_results, 1):
                try:
                    sponsors, last_action, clean_title = self.get_bill_details(bill['bill_link'])
                    
                    if clean_title and len(clean_title) > 10:
                        bill['bill_title'] = clean_title
                        bill['summary'] = clean_title
                    
                    bill['sponsors'] = sponsors
                    bill['last_action'] = last_action
                    detailed_results.append(bill)
                    
                except Exception as e:
                    bill['sponsors'] = "Arizona Legislature"
                    bill['last_action'] = "Committee Review"
                    detailed_results.append(bill)
                
                if idx < len(basic_results):
                    time.sleep(1)
            
            return detailed_results
            
        except Exception as e:
            return []
        finally:
            if driver:
                driver.quit()
    
    def parse_results_exact_only(self, driver, keyword, session_year):
        """Parse results with EXACT keyword matching ONLY"""
        results = []
        
        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Check bill links
            bill_links = soup.find_all('a', href=True)
            
            for link in bill_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if any(pattern in href.upper() for pattern in ['BILLS/', 'LEGTEXT/', 'HB', 'SB']) and text:
                    
                    bill_match = re.search(r'[HS][BCJ]R?\d+', text, re.I)
                    if bill_match:
                        bill_number = bill_match.group().upper()
                        
                        # EXACT keyword match ONLY
                        if self.exact_keyword_match_only(text, keyword):
                            
                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('/'):
                                full_url = f"{self.base_url}{href}"
                            else:
                                full_url = f"{self.base_url}/{href}"
                            
                            clean_title = self.extract_clean_title(text)
                            
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
                                'bill_date': datetime.now().strftime('%Y-%m-%d')
                            }
                            
                            results.append(bill_data)
            
            # Check tables
            if not results:
                tables = soup.find_all('table')
                
                for table in tables:
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        
                        if len(cells) >= 2:
                            row_text = row.get_text()
                            
                            # EXACT keyword match ONLY
                            if self.exact_keyword_match_only(row_text, keyword):
                                
                                for cell in cells:
                                    cell_links = cell.find_all('a')
                                    
                                    for cell_link in cell_links:
                                        link_text = cell_link.get_text(strip=True)
                                        link_href = cell_link.get('href', '')
                                        
                                        if re.match(r'[HS][BCJ]R?\d+', link_text, re.I):
                                            
                                            if link_href.startswith('http'):
                                                full_url = link_href
                                            elif link_href.startswith('/'):
                                                full_url = f"{self.base_url}{link_href}"
                                            else:
                                                full_url = f"{self.base_url}/{link_href}"
                                            
                                            clean_title = self.extract_clean_title(row_text)
                                            
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
                                                'bill_date': datetime.now().strftime('%Y-%m-%d')
                                            }
                                            
                                            results.append(bill_data)
            
            return results
            
        except Exception as e:
            return []
    
    def extract_clean_title(self, raw_text):
        """Extract clean title"""
        if not raw_text:
            return "Title not available"
        
        clean_text = raw_text.strip()
        
        # Remove junk
        junk_pattern = r'(?:PDF|HTML)\d*[HS][BCJ]R?\d+(?:\s*-\s*\d+[A-Z]*)*(?:\s*-\s*[IV]+\s*Ver[A-Z]*\d*)*'
        
        junk_match = re.search(junk_pattern, clean_text, re.I)
        if junk_match:
            title_start = junk_match.end()
            clean_text = clean_text[title_start:].strip()
        
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
        
        return clean_text if clean_text else "Healthcare bill"
    
    def get_bill_details(self, bill_url):
        """Get bill details"""
        if not bill_url:
            return "Unknown", "Unknown", ""
        
        driver = None
        
        try:
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            
            driver.get(bill_url)
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract details
            clean_title = self.extract_title_from_bill_page(soup)
            sponsors = self.extract_sponsors(driver)
            last_action = self.extract_last_action(soup)
            
            return sponsors, last_action, clean_title
            
        except Exception as e:
            return "Arizona Legislature", "Committee Review", ""
        finally:
            if driver:
                driver.quit()
    
    def extract_title_from_bill_page(self, soup):
        """Extract title from bill page"""
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        for i, cell in enumerate(cells):
                            if 'short title' in cell.get_text().lower() and i + 1 < len(cells):
                                title_text = cells[i + 1].get_text(strip=True)
                                if len(title_text) > 10:
                                    return title_text
            return ""
        except:
            return ""
    
    def extract_sponsors(self, driver):
        """Extract sponsors"""
        try:
            sponsor_select = driver.find_element(By.ID, "slist")
            options = sponsor_select.find_elements(By.TAG_NAME, "option")
            
            if options:
                first_option = options[0]
                title_attr = first_option.get_attribute('title')
                
                if title_attr and len(title_attr) > 2:
                    return f"Sen. {title_attr.strip()}"
                else:
                    sponsor_text = first_option.text
                    sponsor_name = sponsor_text.replace('(Prime)', '').replace('(Co)', '').strip()
                    return f"Sen. {sponsor_name}" if sponsor_name else "Arizona Legislature"
            
            return "Arizona Legislature"
        except:
            return "Arizona Legislature"
    
    def extract_last_action(self, soup):
        """Extract last action"""
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                if len(rows) > 1:
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        
                        if len(cells) >= 2:
                            row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                            
                            if any(word in row_text.lower() for word in ['committee', 'introduced', 'passed']):
                                committee_match = re.search(r'committee[:\s]*([A-Z]+)', row_text, re.I)
                                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', row_text)
                                
                                if committee_match:
                                    committee = committee_match.group(1)
                                    date_part = f" on {date_match.group(1)}" if date_match else ""
                                    return f"Assigned to {committee} Committee{date_part}"
            
            return "Under committee review"
        except:
            return "Committee review"
    
    def search_all_keywords_exact(self, keywords=None, session_year="2025"):
        """Search all keywords with EXACT matching only"""
        if keywords is None:
            keywords = KEYWORDS
        
        all_results = []
        
        print(f"🚀 Starting Arizona EXACT keyword matching")
        print(f"🎯 Only bills with literal keyword matches")
        print("=" * 60)
        
        for idx, keyword in enumerate(keywords, 1):
            print(f"\n[{idx:2d}/{len(keywords)}] Processing: '{keyword}'")
            
            try:
                results = self.search_single_keyword_exact(keyword, session_year)
                
                if results:
                    all_results.extend(results)
                    print(f"✅ Found {len(results)} bills with exact '{keyword}' match")
                else:
                    print(f"📄 No bills contain exact '{keyword}'")
                
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
        
        print(f"\n📊 EXACT MATCHING RESULTS:")
        print("=" * 60)
        print(f"Total bills with exact keyword matches: {len(unique_results)}")
        
        return unique_results
    
    def save_to_excel(self, results, filename=None):
        """Save results to Excel WITHOUT matched_keyword column"""
        if not results:
            print("❌ No results to save")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"arizona_exact_keywords_{timestamp}.xlsx"
        
        full_path = os.path.join(self.script_dir, filename)
        
        try:
            df = pd.DataFrame(results)
            
            # Column order WITHOUT matched_keyword
            column_order = [
                'year', 'state', 'bill_number', 'bill_title', 'summary',
                'sponsors', 'last_action', 'bill_link', 'extracted_date'
            ]
            
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            df.to_excel(full_path, index=False)
            
            print(f"✅ Results saved to: {full_path}")
            print(f"📊 Saved {len(results)} bills with exact keyword matches")
            
            return full_path
            
        except Exception as e:
            print(f"❌ Error saving to Excel: {str(e)}")
            return None

def main():
    """Main execution with EXACT keyword matching only"""
    print("🚀 Arizona EXACT Keyword Healthcare Bill Scraper")
    print("=" * 60)
    print("🎯 EXACT MATCH ONLY - No variations, no context needed")
    print("📋 Must literally contain the exact keywords")
    print("❌ No matched_keyword column in output")
    print()
    
    scraper = ArizonaExactKeywordScraper()
    
    try:
        results = scraper.search_all_keywords_exact(KEYWORDS, "2025")
        
        if results:
            excel_file = scraper.save_to_excel(results)
            
            if excel_file:
                print(f"\n🎉 EXACT MATCHING SUCCESS!")
                print(f"📊 Found {len(results)} bills with exact keyword matches")
                print(f"💾 Data saved to: {excel_file}")
                    
        else:
            print("📄 No bills found with exact keyword matches")
            
        return 0
        
    except Exception as e:
        print(f"💥 Critical error: {str(e)}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Exact keyword scraper interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)
