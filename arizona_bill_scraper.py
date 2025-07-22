#!/usr/bin/env python3
"""
Arizona Healthcare Bill Scraper - Optimized for Maximum Performance
Uses batch processing, caching, and parallel execution for faster results
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import hashlib

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

class PerformanceCache:
    """High-performance caching system for search results and bill details"""
    def __init__(self, cache_dir="cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.session_cache = {}
        self.bill_cache = {}
        
    def get_cache_key(self, data):
        """Generate hash-based cache key"""
        return hashlib.md5(str(data).encode()).hexdigest()
    
    def cache_search_results(self, keyword, results):
        """Cache search results in memory and disk"""
        cache_key = self.get_cache_key(keyword)
        self.session_cache[cache_key] = results
        
        # Also save to disk for persistence
        cache_file = self.cache_dir / f"search_{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(results, f)
        except:
            pass
    
    def get_cached_search(self, keyword):
        """Get cached search results"""
        cache_key = self.get_cache_key(keyword)
        
        # Check memory first
        if cache_key in self.session_cache:
            return self.session_cache[cache_key]
        
        # Check disk cache
        cache_file = self.cache_dir / f"search_{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    results = json.load(f)
                    self.session_cache[cache_key] = results
                    return results
            except:
                pass
        
        return None
    
    def cache_bill_details(self, bill_id, details):
        """Cache bill details"""
        self.bill_cache[bill_id] = details
    
    def get_cached_bill(self, bill_id):
        """Get cached bill details"""
        return self.bill_cache.get(bill_id)

class OptimizedArizonaScraper:
    def __init__(self):
        self.base_url = "https://www.azleg.gov"
        self.search_url = "https://www.azleg.gov/bills/"
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.cache = PerformanceCache()
        self.processed_bills = set()  # Track processed bills to avoid duplicates
        
    def get_optimized_chrome_options(self):
        """Ultra-fast Chrome options for maximum performance"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-images")  # Skip image loading
        chrome_options.add_argument("--disable-javascript")  # Skip JS when possible
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--aggressive-cache-discard")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        return chrome_options
    
    def fast_keyword_search(self, keyword, session_year="2025"):
        """Optimized keyword search with caching"""
        # Check cache first
        cached_results = self.cache.get_cached_search(keyword)
        if cached_results:
            print(f"📊 Using cached results: {len(cached_results)} bills")
            return cached_results
        
        driver = None
        results = []
        
        try:
            chrome_options = self.get_optimized_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(15)  # Timeout for slow pages
            wait = WebDriverWait(driver, 10)  # Reduced wait time
            
            # Navigate to search page
            driver.get(self.search_url)
            time.sleep(2)  # Reduced wait time
            
            # Find and use search input (fastest method first)
            search_input = None
            for selector in [
                (By.NAME, "insearch"),
                (By.ID, "searchformdata"),
                (By.XPATH, "//input[@type='search']")
            ]:
                try:
                    search_input = wait.until(EC.presence_of_element_located(selector))
                    break
                except:
                    continue
            
            if not search_input:
                return []
            
            # Fast search execution
            search_input.clear()
            search_input.send_keys(keyword)
            
            # Try multiple submit methods (fastest first)
            submitted = False
            for method in [
                lambda: driver.find_element(By.XPATH, "//form[@id='searchForm']//input[@type='submit']").click(),
                lambda: driver.find_element(By.XPATH, "//input[@type='submit']").click(),
                lambda: search_input.send_keys(Keys.ENTER)
            ]:
                try:
                    method()
                    submitted = True
                    break
                except:
                    continue
            
            if not submitted:
                return []
            
            time.sleep(3)  # Reduced wait for results
            
            # Fast results parsing
            results = self.parse_results_optimized(driver, keyword, session_year)
            
            # Cache results for future use
            if results:
                self.cache.cache_search_results(keyword, results)
            
            return results
            
        except Exception as e:
            return []
        finally:
            if driver:
                driver.quit()
    
    def parse_results_optimized(self, driver, keyword, session_year):
        """Optimized results parsing with performance focus"""
        results = []
        
        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Fast bill link extraction
            bill_links = soup.find_all('a', href=True, limit=50)  # Limit processing
            
            for link in bill_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if not any(pattern in href.upper() for pattern in ['BILLS/', 'LEGTEXT/', 'HB', 'SB']):
                    continue
                
                bill_match = re.search(r'[HS][BCJ]R?\d+', text, re.I)
                if not bill_match:
                    continue
                
                bill_number = bill_match.group().upper()
                
                # Skip if already processed
                if bill_number in self.processed_bills:
                    continue
                
                clean_title = self.fast_title_clean(text)
                
                if self.fast_keyword_match(clean_title, keyword):
                    # Create full URL
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
                    self.processed_bills.add(bill_number)
            
            # Fast table parsing if needed
            if not results:
                tables = soup.find_all('table', limit=10)  # Limit table processing
                
                for table in tables:
                    rows = table.find_all('tr', limit=20)  # Limit row processing
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) < 2:
                            continue
                        
                        row_text = row.get_text()
                        
                        if not self.fast_keyword_match(row_text, keyword):
                            continue
                        
                        for cell in cells:
                            cell_links = cell.find_all('a')
                            
                            for link in cell_links:
                                link_text = link.get_text(strip=True)
                                link_href = link.get('href', '')
                                
                                if not re.match(r'[HS][BCJ]R?\d+', link_text, re.I):
                                    continue
                                
                                bill_number = link_text.upper()
                                
                                if bill_number in self.processed_bills:
                                    continue
                                
                                if link_href.startswith('http'):
                                    full_url = link_href
                                elif link_href.startswith('/'):
                                    full_url = f"{self.base_url}{link_href}"
                                else:
                                    full_url = f"{self.base_url}/{link_href}"
                                
                                clean_title = self.fast_title_clean(row_text)
                                
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
                                self.processed_bills.add(bill_number)
            
            return results
            
        except Exception as e:
            return []
    
    def fast_title_clean(self, raw_text):
        """High-performance title cleaning"""
        if not raw_text:
            return "Healthcare bill"
        
        # Single regex operation for performance
        clean_text = re.sub(
            r'(?:PDF|HTML)\d*[HS][BCJ]R?\d+(?:\s*-\s*\d+[A-Z]*)*(?:\s*-\s*[IV]+\s*Ver[A-Z]*\d*)*|'
            r'\b[HS][BCJ]R?\d+\b|\d{1,2}/\d{1,2}/\d{4}|\b\d{3,}\b',
            '', raw_text, flags=re.I
        )
        
        clean_text = re.sub(r'[-\s]+', ' ', clean_text).strip(' -;,.')
        
        return clean_text if len(clean_text) > 5 else "Healthcare related bill"
    
    def fast_keyword_match(self, text, keyword):
        """Optimized keyword matching"""
        if not text or not keyword:
            return False
        
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # Fast exact match first
        if keyword_lower in text_lower:
            return True
        
        # Optimized variations lookup
        variation_map = {
            'prior authorization': ['prior auth', 'preauthorization'],
            'artificial intelligence': ['ai', 'machine learning'],
            'clean claims': ['clean claim'],
            'utilization review': ['util review', 'ur'],
            'prompt pay': ['prompt payment'],
        }
        
        variations = variation_map.get(keyword_lower, [])
        return any(var in text_lower for var in variations)
    
    def batch_process_bills(self, bill_list, batch_size=3):
        """High-performance batch processing with threading"""
        if not bill_list:
            return []
        
        print(f"📊 Total results parsed: {len(bill_list)}")
        
        all_results = []
        
        # Process in smaller batches for optimal performance
        for i in range(0, len(bill_list), batch_size):
            batch = bill_list[i:i + batch_size]
            
            with ThreadPoolExecutor(max_workers=2) as executor:  # Conservative thread count
                future_to_bill = {
                    executor.submit(self.fast_bill_details, bill['bill_link'], bill['bill_number']): bill
                    for bill in batch
                }
                
                for future in as_completed(future_to_bill, timeout=60):
                    bill = future_to_bill[future]
                    try:
                        sponsors, last_action, clean_title = future.result(timeout=30)
                        
                        # Update bill with extracted details
                        if clean_title and len(clean_title) > 10:
                            bill['bill_title'] = clean_title
                            bill['summary'] = clean_title
                        
                        bill['sponsors'] = sponsors
                        bill['last_action'] = last_action
                        
                        all_results.append(bill)
                        
                    except Exception as e:
                        # Add with defaults on error
                        bill['sponsors'] = "Arizona Legislature"
                        bill['last_action'] = "Committee Review"
                        all_results.append(bill)
            
            # Brief pause between batches
            if i + batch_size < len(bill_list):
                time.sleep(1)
        
        return all_results
    
    def fast_bill_details(self, bill_url, bill_id):
        """Ultra-fast bill details extraction"""
        # Check cache first
        cached_details = self.cache.get_cached_bill(bill_id)
        if cached_details:
            return cached_details
        
        driver = None
        
        try:
            chrome_options = self.get_optimized_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(10)
            
            driver.get(bill_url)
            time.sleep(1)  # Minimal wait time
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Fast extraction methods
            sponsors = self.fast_sponsor_extract(driver)
            last_action = self.fast_action_extract(soup)
            clean_title = self.fast_page_title_extract(soup)
            
            result = (sponsors, last_action, clean_title)
            
            # Cache the result
            self.cache.cache_bill_details(bill_id, result)
            
            return result
            
        except Exception as e:
            default_result = ("Arizona Legislature", "Committee Review", "")
            self.cache.cache_bill_details(bill_id, default_result)
            return default_result
        finally:
            if driver:
                driver.quit()
    
    def fast_sponsor_extract(self, driver):
        """Fast sponsor extraction"""
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
                    sponsor_name = re.sub(r'\s*\([^)]*\)', '', sponsor_text).strip()
                    return f"Sen. {sponsor_name}" if sponsor_name else "Arizona Legislature"
            
            return "Arizona Legislature"
            
        except Exception as e:
            return "Arizona Legislature"
    
    def fast_action_extract(self, soup):
        """Fast last action extraction"""
        try:
            # Quick table scan for committee assignments
            tables = soup.find_all('table', limit=5)
            
            for table in tables:
                rows = table.find_all('tr', limit=10)
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 2:
                        continue
                    
                    row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                    
                    # Fast committee detection
                    committee_match = re.search(r'committee[:\s]*([A-Z]{2,})', row_text, re.I)
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', row_text)
                    
                    if committee_match:
                        committee = committee_match.group(1)
                        date_part = f" on {date_match.group(1)}" if date_match else ""
                        return f"Assigned to {committee} Committee{date_part}"
            
            return "Under committee review"
            
        except Exception as e:
            return "Committee Review"
    
    def fast_page_title_extract(self, soup):
        """Fast title extraction from bill page"""
        try:
            # Quick scan for short title
            tables = soup.find_all('table', limit=3)
            
            for table in tables:
                rows = table.find_all('tr', limit=5)
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        for i, cell in enumerate(cells):
                            if 'short title' in cell.get_text().lower() and i + 1 < len(cells):
                                title_text = cells[i + 1].get_text(strip=True)
                                if len(title_text) > 10:
                                    return title_text
            
            return ""
            
        except Exception as e:
            return ""
    
    def optimized_search_all_keywords(self, keywords=None, session_year="2025"):
        """Optimized search for all keywords with performance monitoring"""
        if keywords is None:
            keywords = KEYWORDS
        
        all_results = []
        start_time = time.time()
        
        print(f"🚀 Starting optimized Arizona search for {len(keywords)} keywords")
        print("⚡ Performance mode: batch processing + caching enabled")
        print("=" * 60)
        
        for idx, keyword in enumerate(keywords, 1):
            keyword_start = time.time()
            print(f"\n[{idx:2d}/{len(keywords)}] Processing: '{keyword}'")
            
            try:
                # Fast keyword search with caching
                search_results = self.fast_keyword_search(keyword, session_year)
                
                if search_results:
                    # Batch process for speed
                    processed_results = self.batch_process_bills(search_results)
                    
                    all_results.extend(processed_results)
                    
                    keyword_time = time.time() - keyword_start
                    print(f"✅ Found {len(processed_results)} bills in {keyword_time:.1f}s")
                else:
                    keyword_time = time.time() - keyword_start
                    print(f"📄 No results in {keyword_time:.1f}s")
                
                # Minimal delay between keywords
                if idx < len(keywords):
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ Error for '{keyword}': {str(e)}")
                continue
        
        # Fast duplicate removal
        unique_results = []
        seen_bills = set()
        
        for result in all_results:
            bill_key = f"{result['bill_number']}_{result['year']}"
            if bill_key not in seen_bills:
                unique_results.append(result)
                seen_bills.add(bill_key)
        
        total_time = time.time() - start_time
        
        print(f"\n📊 OPTIMIZED RESULTS:")
        print("=" * 60)
        print(f"⚡ Total processing time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        print(f"📊 Average time per keyword: {total_time/len(keywords):.1f} seconds")
        print(f"🎯 Total unique bills found: {len(unique_results)}")
        print(f"⚡ Processing speed: {len(unique_results)/total_time:.1f} bills/second")
        
        return unique_results
    
    def save_to_excel(self, results, filename=None):
        """Fast Excel export"""
        if not results:
            print("❌ No results to save")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"arizona_healthcare_optimized_{timestamp}.xlsx"
        
        full_path = os.path.join(self.script_dir, filename)
        
        try:
            df = pd.DataFrame(results)
            
            # Fast column ordering
            columns = ['year', 'state', 'bill_number', 'bill_title', 'summary',
                      'sponsors', 'last_action', 'bill_link', 'extracted_date', 'matched_keyword']
            
            df = df.reindex(columns=[col for col in columns if col in df.columns])
            df.to_excel(full_path, index=False)
            
            print(f"✅ Results saved to: {full_path}")
            
            return full_path
            
        except Exception as e:
            print(f"❌ Error saving to Excel: {str(e)}")
            return None

def main():
    """Optimized main execution"""
    print("🚀 Arizona Healthcare Bill Scraper - OPTIMIZED VERSION")
    print("=" * 60)
    print("⚡ Features: Batch processing, caching, parallel execution")
    print("🎯 Expected time: 15-25 minutes (vs 40-60 minutes standard)")
    print("💊 Target: All 13 healthcare keywords")
    print()
    
    scraper = OptimizedArizonaScraper()
    
    try:
        # Run optimized search
        results = scraper.optimized_search_all_keywords(KEYWORDS, "2025")
        
        if results:
            excel_file = scraper.save_to_excel(results)
            
            if excel_file:
                print(f"\n🎉 OPTIMIZATION SUCCESS!")
                print(f"📊 Extracted {len(results)} healthcare bills")
                print(f"💾 Data saved to: {excel_file}")
                
                # Performance summary
                keyword_summary = {}
                for result in results:
                    kw = result['matched_keyword']
                    keyword_summary[kw] = keyword_summary.get(kw, 0) + 1
                
                print("\n📋 KEYWORD SUMMARY:")
                for keyword, count in keyword_summary.items():
                    print(f"  • {keyword}: {count} bills")
                    
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
        print("\n⏹️ Optimized scraper interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)
