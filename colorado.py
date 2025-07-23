#!/usr/bin/env python3
"""
Colorado Healthcare Bill Scraper - DIRECT ALL KEYWORDS VERSION
Runs directly with all keywords without menu selection
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
import urllib.parse

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

class ColoradoDirectAllKeywordsScraper:
    def __init__(self):
        self.base_url = "https://leg.colorado.gov"
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Known session values
        self.session_values = {
            '2025': '104236',  # 2025 Regular Session
            '2026': None       # Will be detected when available
        }
        
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
    
    def auto_detect_2026_session(self, driver):
        """Auto-detect 2026 session value if available"""
        try:
            print(f"🔍 Auto-detecting 2026 session...")
            
            driver.get("https://leg.colorado.gov/bill-search")
            time.sleep(5)
            
            session_dropdown = driver.find_element(By.ID, "edit-field-sessions")
            select_session = Select(session_dropdown)
            all_options = select_session.options
            
            for option in all_options:
                option_text = option.text.strip()
                option_value = option.get_attribute('value')
                
                if '2026' in option_text and 'Regular Session' in option_text and option_value != 'All':
                    self.session_values['2026'] = option_value
                    print(f"✅ Detected 2026 session: {option_text} (value: {option_value})")
                    return option_value
            
            print(f"📄 2026 session not yet available")
            return None
            
        except Exception as e:
            print(f"⚠️ Could not auto-detect 2026 session: {e}")
            return None
    
    def construct_search_url(self, keyword, session_year='2025'):
        """Manually construct the complete search URL with all parameters"""
        
        session_value = self.session_values.get(session_year)
        if not session_value:
            return None
        
        encoded_keyword = urllib.parse.quote_plus(keyword)
        
        search_url = (
            f"https://leg.colorado.gov/bill-search?"
            f"field_chamber=All&"
            f"field_bill_type=All&"
            f"field_sessions={session_value}&"
            f"field_subjects=All&"
            f"search_api_views_fulltext={encoded_keyword}&"
            f"sort_bef_combine=search_api_relevance%20DESC"
        )
        
        return search_url
    
    def search_colorado_manual_url(self, keyword):
        """Search Colorado using manually constructed URLs"""
        driver = None
        all_results = []
        
        try:
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            
            # Auto-detect 2026 session if available (only on first keyword)
            if keyword == ALL_KEYWORDS[0]:
                self.auto_detect_2026_session(driver)
            
            # Search available sessions
            available_sessions = [year for year, value in self.session_values.items() if value]
            
            for session_year in available_sessions:
                search_url = self.construct_search_url(keyword, session_year)
                if not search_url:
                    continue
                
                driver.get(search_url)
                time.sleep(6)
                
                session_results = self.extract_manual_url_results(driver, keyword, session_year)
                all_results.extend(session_results)
            
            return all_results
            
        except Exception as e:
            print(f"❌ Error searching '{keyword}': {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def extract_manual_url_results(self, driver, keyword, session_year):
        """Extract results from manual URL search"""
        session_bills = []
        
        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find bill articles
            bill_articles = soup.find_all('article', class_='node-bill')
            if not bill_articles:
                bill_articles = soup.find_all('div', class_='views-row')
            
            # Process articles with pagination
            session_bills = self.process_all_pages(driver, keyword, session_year, bill_articles)
            
            return session_bills
            
        except Exception as e:
            return []
    
    def process_all_pages(self, driver, keyword, session_year, initial_articles):
        """Process all pages of search results"""
        all_session_bills = []
        page_num = 1
        max_pages = 5
        
        # Process first page
        page_bills = self.process_articles(initial_articles, keyword, session_year)
        all_session_bills.extend(page_bills)
        
        # Check for additional pages
        while page_num < max_pages:
            if not self.navigate_to_next_page(driver, page_num):
                break
                
            page_num += 1
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            bill_articles = soup.find_all('article', class_='node-bill')
            if not bill_articles:
                bill_articles = soup.find_all('div', class_='views-row')
            
            if not bill_articles:
                break
            
            page_bills = self.process_articles(bill_articles, keyword, session_year)
            all_session_bills.extend(page_bills)
        
        return all_session_bills
    
    def navigate_to_next_page(self, driver, current_page):
        """Navigate to next page of results"""
        try:
            next_page_num = current_page + 1
            
            next_selectors = [
                f"//a[text()='{next_page_num}']",
                "//a[contains(text(), 'Next') or contains(text(), 'next')]",
                "//a[contains(text(), '›') or contains(text(), '>')]"
            ]
            
            for selector in next_selectors:
                try:
                    next_links = driver.find_elements(By.XPATH, selector)
                    for link in next_links:
                        if link.is_displayed() and link.is_enabled():
                            link.click()
                            return True
                except:
                    continue
            
            return False
            
        except:
            return False
    
    def process_articles(self, bill_articles, keyword, session_year):
        """Process articles from a single page"""
        page_bills = []
        keyword_lower = keyword.lower()
        
        for article in bill_articles:
            try:
                bill_info = self.extract_bill_from_article(article, session_year)
                if bill_info:
                    bill_text = f"{bill_info['bill_title']} {bill_info['summary']}".lower()
                    
                    if keyword_lower in bill_text:
                        page_bills.append(bill_info)
            except:
                continue
        
        return page_bills
    
    def extract_bill_from_article(self, article, session_year):
        """Extract bill information from article"""
        try:
            # Extract bill number
            bill_number = ""
            bill_num_div = article.find('div', class_='field-name-field-bill-number')
            if bill_num_div:
                field_item = bill_num_div.find('div', class_='field-item')
                if field_item:
                    bill_number = field_item.get_text(strip=True)
            
            if not bill_number:
                return None
            
            # Verify bill year matches session year
            extracted_year = self.extract_year_from_bill_number(bill_number)
            if extracted_year != session_year:
                year_diff = abs(int(extracted_year) - int(session_year)) if extracted_year.isdigit() and session_year.isdigit() else 0
                if year_diff > 1:
                    return None
            
            # Extract title
            bill_title = ""
            bill_href = ""
            title_h4 = article.find('h4', class_='node__title') or article.find('h4', class_='node-title')
            if title_h4:
                title_link = title_h4.find('a')
                if title_link:
                    bill_title = title_link.get_text(strip=True)
                    bill_href = title_link.get('href', '')
                else:
                    bill_title = title_h4.get_text(strip=True)
            
            # Extract summary
            summary = ""
            summary_div = article.find('div', class_='field-name-field-bill-long-title')
            if summary_div:
                summary_item = summary_div.find('div', class_='field-item')
                if summary_item:
                    summary = summary_item.get_text(strip=True)
            
            # Extract sponsors
            sponsors = []
            sponsors_div = article.find('div', class_='bill-sponsors')
            if sponsors_div:
                sponsor_links = sponsors_div.find_all('a')
                for link in sponsor_links:
                    sponsor_name = link.get_text(strip=True)
                    if sponsor_name and sponsor_name not in sponsors:
                        sponsors.append(sponsor_name)
            
            sponsors_text = " | ".join(sponsors) if sponsors else "Colorado Legislature"
            
            # Extract last action (only text after "|")
            last_action = "Status not available"
            last_action_div = article.find('div', class_='bill-last-action')
            if last_action_div:
                last_action_span = last_action_div.find('span')
                if last_action_span:
                    action_text = last_action_span.get_text(strip=True)
                    if "|" in action_text:
                        last_action = action_text.split("|", 1)[1].strip()
                    else:
                        last_action = action_text
            
            # Create bill link
            bill_link = ""
            if bill_href:
                if bill_href.startswith('/'):
                    bill_link = f"{self.base_url}{bill_href}"
                else:
                    bill_link = bill_href
            
            return {
                'year': session_year,
                'state': 'Colorado',
                'bill_number': bill_number,
                'bill_title': bill_title or f"Colorado {bill_number}",
                'summary': summary or bill_title or f"Colorado {bill_number}",
                'sponsors': sponsors_text,
                'last_action': last_action,
                'bill_link': bill_link,
                'extracted_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return None
    
    def extract_year_from_bill_number(self, bill_number):
        """Extract year from bill number"""
        try:
            year_match = re.search(r'[HS][BR](\d{2})-', bill_number)
            if year_match:
                year_short = year_match.group(1)
                year_int = int(year_short)
                
                if year_int >= 0 and year_int <= 30:
                    return str(2000 + year_int)
                else:
                    return str(1900 + year_int)
            
            return "Unknown"
            
        except:
            return "Unknown"
    
    def search_all_keywords_direct(self):
        """DIRECT: Search all keywords without menu selection"""
        all_bills = []
        
        print(f"🚀 COLORADO HEALTHCARE BILL SCRAPER")
        print(f"=" * 60)
        print(f"🔧 Strategy: Manual URL construction")
        print(f"🎯 Processing {len(ALL_KEYWORDS)} healthcare keywords")
        print(f"🤖 Auto-detecting available 2025/2026 sessions")
        print(f"⏱️ Estimated time: 3-4 minutes")
        print()
        
        for idx, keyword in enumerate(ALL_KEYWORDS, 1):
            print(f"[{idx:2d}/{len(ALL_KEYWORDS)}] Processing: '{keyword}'")
            
            try:
                keyword_results = self.search_colorado_manual_url(keyword)
                
                if keyword_results:
                    all_bills.extend(keyword_results)
                    print(f"   ✅ Found {len(keyword_results)} bills")
                    
                    # Show sample bills
                    sample_bills = [b['bill_number'] for b in keyword_results[:3]]
                    if sample_bills:
                        print(f"   📋 Sample: {', '.join(sample_bills)}")
                else:
                    print(f"   📄 No results")
                
                # Progress indicator
                progress = (idx / len(ALL_KEYWORDS)) * 100
                print(f"   📊 Progress: {progress:.1f}% complete")
                
                # Pause between keywords
                if idx < len(ALL_KEYWORDS):
                    time.sleep(4)
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                continue
        
        # Remove duplicates
        unique_bills = []
        seen_bills = set()
        
        for bill in all_bills:
            bill_key = f"{bill['bill_number']}_{bill['year']}"
            if bill_key not in seen_bills:
                unique_bills.append(bill)
                seen_bills.add(bill_key)
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"   • Total bills found: {len(all_bills)}")
        print(f"   • Unique bills: {len(unique_bills)}")
        print(f"   • Duplicates removed: {len(all_bills) - len(unique_bills)}")
        
        # Summary by year
        if unique_bills:
            years = [r['year'] for r in unique_bills]
            year_counts = {}
            for year in years:
                year_counts[year] = year_counts.get(year, 0) + 1
            
            print(f"\n📈 BILLS BY YEAR:")
            for year, count in sorted(year_counts.items()):
                print(f"   {year}: {count} bills")
        
        return unique_bills
    
    def save_to_excel(self, results, filename=None):
        """Save results to Excel file"""
        if not results:
            print("❌ No results to save")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"colorado_healthcare_all_keywords_{timestamp}.xlsx"
        
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
    """Main function - runs directly with all keywords"""
    print("🏥 COLORADO HEALTHCARE LEGISLATION SCRAPER")
    print("=" * 60)
    print("🎯 Automatically processing all healthcare keywords")
    print("🔧 Using manual URL construction for reliability")
    print()
    
    scraper = ColoradoDirectAllKeywordsScraper()
    
    try:
        # Run directly with all keywords
        results = scraper.search_all_keywords_direct()
        
        if results:
            excel_file = scraper.save_to_excel(results)
            
            if excel_file:
                print(f"\n🎉 COLORADO SCRAPING COMPLETE!")
                print(f"📊 Successfully extracted {len(results)} healthcare bills")
                print(f"💾 Data saved to: {excel_file}")
                
                # Show top bills by keyword frequency
                print(f"\n📋 SAMPLE RESULTS:")
                for result in results[:5]:
                    print(f"\n📄 {result['bill_number']} ({result['year']})")
                    print(f"   {result['bill_title']}")
                    print(f"   Sponsors: {result['sponsors']}")
                    print(f"   Status: {result['last_action']}")
                    
            else:
                print(f"\n⚠️ Results found but could not save to Excel")
        else:
            print(f"\n📄 No healthcare bills found")
            print(f"💡 This may indicate search syntax needs adjustment")
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Process interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
