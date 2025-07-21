import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import re

# Keywords directly in the file
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

TARGET_SESSIONS = {
    '2025': '2025 Regular Session',
    '2026': '2026 Regular Session'
}

class LouisianaBillScraper:
    def __init__(self):
        self.base_url = "https://www.legis.la.gov"
        self.search_url = "https://www.legis.la.gov/Legis/BillSearch.aspx"
        self.scraped_data = []
        
    def get_chrome_options(self):
        """Get Chrome options for maximum stability"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        return chrome_options
    
    def search_single_keyword_isolated(self, keyword, session_year="2025"):
        """Search for a single keyword with isolated browser session"""
        print(f"🔍 Searching for keyword: '{keyword}' in {session_year}")
        
        driver = None
        results = []
        
        try:
            # Create fresh browser instance for this keyword only
            chrome_options = self.get_chrome_options()
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            wait = WebDriverWait(driver, 20)
            
            # Navigate to search page
            search_url_with_session = f"{self.search_url}?sid=current"
            driver.get(search_url_with_session)
            time.sleep(3)
            
            print("✅ Navigated to search page")
            
            # Check if page loaded properly
            if "Bill Search" not in driver.title:
                raise Exception("Search page did not load properly")
            
            # Step 1: Click "Search by Summary" button
            summary_button = wait.until(
                EC.element_to_be_clickable((By.ID, "ctl00_ctl00_PageBody_PageContent_btnHeadSummary"))
            )
            driver.execute_script("arguments[0].click();", summary_button)
            time.sleep(3)
            
            print("✅ Clicked 'Search by Summary' button")
            
            # Step 2: Find and fill the summary input field
            summary_input = wait.until(
                EC.presence_of_element_located((By.ID, "ctl00_ctl00_PageBody_PageContent_tbSummary"))
            )
            
            driver.execute_script("arguments[0].value = '';", summary_input)
            summary_input.send_keys(keyword)
            time.sleep(1)
            
            print(f"✅ Entered keyword: '{keyword}'")
            
            # Step 3: Click search button
            search_button = wait.until(
                EC.element_to_be_clickable((By.ID, "ctl00_ctl00_PageBody_PageContent_btnSearchBySummary"))
            )
            driver.execute_script("arguments[0].click();", search_button)
            
            print("✅ Clicked search button")
            
            # Wait for results
            time.sleep(5)
            
            # Parse results using the same driver instance
            results = self.parse_search_results_isolated(driver, keyword, session_year)
            
            print(f"📊 Found {len(results)} results for '{keyword}'")
            
        except Exception as e:
            print(f"❌ Error searching for keyword '{keyword}': {str(e)}")
            results = []
            
        finally:
            # Always close the browser for this keyword
            if driver:
                try:
                    driver.quit()
                    print("🔄 Browser closed for this keyword")
                except:
                    pass
            
            # Wait between keywords
            time.sleep(2)
        
        return results
    
    def parse_search_results_isolated(self, driver, keyword, session_year):
        """Parse search results using the provided driver instance"""
        results = []
        
        try:
            current_url = driver.current_url
            print(f"🌐 Parsing results from: {current_url}")
            
            # Get page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Check if we have results or "no results" message
            page_text = soup.get_text().lower()
            
            if "no bills found" in page_text or "no results" in page_text or "no bills were found" in page_text:
                print(f"📄 No bills found for keyword: '{keyword}'")
                return []
            
            # Look specifically for the ResultsListTable
            results_table = soup.find('table', class_='ResultsListTable')
            
            if not results_table:
                print(f"❌ Could not find ResultsListTable for '{keyword}'")
                return []
            
            print("✅ Found ResultsListTable")
            
            # Find all rows in the tbody
            tbody = results_table.find('tbody')
            if not tbody:
                print("❌ Could not find tbody in ResultsListTable")
                return []
            
            rows = tbody.find_all('tr')
            print(f"📋 Found {len(rows)} rows in ResultsListTable")
            
            # Process rows in pairs (bill info + summary)
            i = 0
            while i < len(rows):
                bill_row = rows[i]
                summary_row = rows[i + 1] if i + 1 < len(rows) else None
                
                # Check if this is a bill info row (has bill number link)
                bill_link_elem = bill_row.find('a', href=lambda href: href and 'BillInfo.aspx' in href)
                
                if bill_link_elem:
                    bill_data = self.extract_bill_data_from_result_rows(bill_row, summary_row, keyword, session_year)
                    if bill_data:
                        results.append(bill_data)
                        print(f"✅ Extracted: {bill_data['bill_number']} by {bill_data['sponsors']}")
                    
                    i += 2  # Skip summary row
                else:
                    i += 1  # Move to next row
            
            # Remove duplicates for this keyword
            unique_results = []
            seen_bills = set()
            
            for result in results:
                bill_id = result['bill_number']
                if bill_id not in seen_bills:
                    unique_results.append(result)
                    seen_bills.add(bill_id)
            
            return unique_results
            
        except Exception as e:
            print(f"❌ Error parsing results: {str(e)}")
            return []
    
    def extract_bill_data_from_result_rows(self, bill_row, summary_row, keyword, session_year):
        """Extract bill data from the structured ResultsListTable rows with enhanced sponsor extraction"""
        try:
            # Extract bill number and link
            bill_link_elem = bill_row.find('a', href=lambda href: href and 'BillInfo.aspx' in href)
            if not bill_link_elem:
                return None
            
            bill_number = bill_link_elem.get_text(strip=True)
            bill_href = bill_link_elem.get('href', '')
            
            # Create full bill link
            if bill_href.startswith('/'):
                bill_link = f"{self.base_url}{bill_href}"
            elif bill_href.startswith('http'):
                bill_link = bill_href
            else:
                bill_link = f"{self.base_url}/Legis/{bill_href}"
            
            # Enhanced sponsor extraction with multiple fallback methods
            sponsors = self.extract_sponsors_enhanced(bill_row)
            
            # Extract current status
            status_elem = bill_row.find('span', id=lambda x: x and 'LabelStatus' in x)
            last_action = status_elem.get_text(strip=True) if status_elem else 'Unknown'
            
            # Extract title and summary from summary row
            title = ""
            summary = ""
            
            if summary_row:
                summary_elem = summary_row.find('span', id=lambda x: x and 'LabelKWordAndSTitle' in x)
                if summary_elem:
                    full_summary = summary_elem.get_text(strip=True)
                    
                    if ':' in full_summary:
                        parts = full_summary.split(':', 1)
                        category = parts[0].strip()
                        title_summary = parts[1].strip()
                        title = f"{category}: {title_summary}"
                        summary = full_summary
                    else:
                        title = full_summary
                        summary = full_summary
            
            if not title:
                title = f"{bill_number} - {keyword} Related Bill"
            
            if not summary:
                summary = title
            
            bill_data = {
                'year': session_year,
                'state': 'Louisiana',
                'bill_number': bill_number,
                'bill_title': title,
                'summary': summary,
                'sponsors': sponsors,
                'last_action': last_action,
                'bill_link': bill_link,
                'extracted_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'matched_keyword': keyword
            }
            
            return bill_data
            
        except Exception as e:
            print(f"❌ Error extracting bill data from rows: {str(e)}")
            return None
    
    def extract_sponsors_enhanced(self, bill_row):
        """Enhanced sponsor extraction with multiple fallback methods"""
        try:
            # Method 1: Look for standard senate/house.la.gov links
            author_elem = bill_row.find('a', href=lambda href: href and ('senate.la.gov' in href or 'house.la.gov' in href))
            if author_elem:
                sponsor_name = author_elem.get_text(strip=True)
                if sponsor_name and sponsor_name.upper() not in ['', 'UNKNOWN']:
                    print(f"  ✅ Found sponsor via method 1: {sponsor_name}")
                    return sponsor_name
            
            # Method 2: Look for any links that might be author links (broader search)
            all_links = bill_row.find_all('a')
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Skip bill info links
                if 'BillInfo.aspx' in href:
                    continue
                    
                # Look for links with author-like text (all caps, reasonable length)
                if text and len(text) > 2 and len(text) < 50 and text.isupper():
                    print(f"  ✅ Found sponsor via method 2: {text}")
                    return text
            
            # Method 3: Look in specific table cells (second column typically has author)
            cells = bill_row.find_all(['td', 'th'])
            if len(cells) >= 2:
                # Check second cell for author name
                author_cell = cells[1]
                
                # First try to find a link in the author cell
                author_link = author_cell.find('a')
                if author_link:
                    author_text = author_link.get_text(strip=True)
                    if author_text and len(author_text) > 2 and author_text.upper() not in ['UNKNOWN', '']:
                        print(f"  ✅ Found sponsor via method 3a: {author_text}")
                        return author_text
                
                # If no link, try to extract text directly from the cell
                cell_text = author_cell.get_text(strip=True)
                # Clean up the text (remove extra whitespace, newlines)
                cell_text = ' '.join(cell_text.split())
                
                if cell_text and len(cell_text) > 2 and len(cell_text) < 50:
                    # Filter out common non-author text
                    exclude_patterns = ['more...', 'billinfo', 'considered', 'status', 'current']
                    if not any(pattern.lower() in cell_text.lower() for pattern in exclude_patterns):
                        print(f"  ✅ Found sponsor via method 3b: {cell_text}")
                        return cell_text
            
            # Method 4: Look for text patterns that match author names (all caps words)
            row_text = bill_row.get_text()
            
            # Look for patterns like "SMITH", "JONES", "MARTIN", etc.
            author_pattern = r'\b[A-Z]{3,15}\b'
            matches = re.findall(author_pattern, row_text)
            
            for match in matches:
                # Filter out common non-author words
                exclude_words = ['BILL', 'ACT', 'HOUSE', 'SENATE', 'MORE', 'CURRENT', 'STATUS', 'SIGNED', 'PASSED', 'GOVERNOR', 'PRESIDENT']
                if match not in exclude_words and len(match) >= 4:
                    print(f"  ✅ Found sponsor via method 4: {match}")
                    return match
            
            # Method 5: Look for LinkAuthor control ID pattern
            author_link_by_id = bill_row.find('a', id=lambda x: x and 'LinkAuthor' in x)
            if author_link_by_id:
                author_text = author_link_by_id.get_text(strip=True)
                if author_text and len(author_text) > 2:
                    print(f"  ✅ Found sponsor via method 5: {author_text}")
                    return author_text
            
            # Method 6: Debug - show what we have in this row for troubleshooting
            print(f"  🔍 Debug - Row content for sponsor extraction:")
            for i, cell in enumerate(cells[:4]):  # Only show first 4 cells
                cell_text = cell.get_text(strip=True)[:80]  # Truncate long text
                links_in_cell = len(cell.find_all('a'))
                print(f"    Cell {i}: '{cell_text}' (links: {links_in_cell})")
            
            print(f"  ❌ No sponsor found using any method")
            return 'Unknown'
            
        except Exception as e:
            print(f"  ❌ Error in enhanced sponsor extraction: {str(e)}")
            return 'Unknown'
    
    def search_all_keywords(self, keywords=None, session_year="2025"):
        """Search for all keywords using isolated browser sessions"""
        if keywords is None:
            keywords = KEYWORDS
        
        all_results = []
        successful_searches = 0
        
        print(f"🚀 Starting ISOLATED search for {len(keywords)} keywords in {session_year}")
        print("🔧 Each keyword will use a fresh browser session")
        print("=" * 70)
        
        for idx, keyword in enumerate(keywords, 1):
            print(f"\n[{idx}/{len(keywords)}] Processing: '{keyword}'")
            print("-" * 50)
            
            try:
                # Each keyword gets its own isolated browser session
                results = self.search_single_keyword_isolated(keyword, session_year)
                
                if results:
                    all_results.extend(results)
                    successful_searches += 1
                    print(f"✅ Found {len(results)} bills for '{keyword}'")
                else:
                    print(f"📄 No results for '{keyword}'")
                
                # Brief pause between keywords
                if idx < len(keywords):
                    print("⏳ Waiting 3 seconds before next keyword...")
                    time.sleep(3)
                    
            except Exception as e:
                print(f"❌ Critical error for '{keyword}': {str(e)}")
                continue
        
        # Remove duplicates across all keywords
        unique_results = []
        seen_bills = set()
        
        for result in all_results:
            bill_key = f"{result['bill_number']}_{result['year']}"
            if bill_key not in seen_bills:
                unique_results.append(result)
                seen_bills.add(bill_key)
        
        print(f"\n📊 FINAL RESULTS:")
        print("=" * 70)
        print(f"Keywords processed: {len(keywords)}")
        print(f"Successful searches: {successful_searches}")
        print(f"Total results found: {len(all_results)}")
        print(f"Unique bills found: {len(unique_results)}")
        
        # Show summary of found bills grouped by keyword
        if unique_results:
            print(f"\n📋 BILLS FOUND BY KEYWORD:")
            keyword_groups = {}
            for result in unique_results:
                kw = result['matched_keyword']
                if kw not in keyword_groups:
                    keyword_groups[kw] = []
                keyword_groups[kw].append(result)
            
            for keyword, bills in keyword_groups.items():
                print(f"\n  🔍 '{keyword}': {len(bills)} bills")
                for bill in bills:
                    print(f"    • {bill['bill_number']} - {bill['sponsors']}")
        
        return unique_results
    
    def save_to_excel(self, results, filename=None):
        """Save results to Excel file"""
        if not results:
            print("❌ No results to save")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/output/louisiana_bills_{timestamp}.xlsx"
        
        try:
            # Create DataFrame
            df = pd.DataFrame(results)
            
            # Ensure output directory exists
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Save to Excel
            df.to_excel(filename, index=False)
            
            print(f"✅ Results saved to: {filename}")
            print(f"📊 Saved {len(results)} bills to Excel")
            
            return filename
            
        except Exception as e:
            print(f"❌ Error saving to Excel: {str(e)}")
            return None
    
    def test_search_functionality(self):
        """Test with a single keyword using isolated session"""
        print("🧪 Testing isolated search functionality...")
        
        test_results = self.search_single_keyword_isolated("prior authorization", "2025")
        
        if test_results:
            print(f"✅ Test passed! Found {len(test_results)} results")
            for result in test_results:
                print(f"  - {result.get('bill_number', 'Unknown')}: {result.get('sponsors', 'Unknown')}")
                print(f"    Status: {result.get('last_action', 'Unknown')}")
            return True
        else:
            print("❌ Test failed - no results found")
            return False
    
    def close(self):
        """Cleanup method (not needed for isolated sessions)"""
        pass

# Test the scraper
if __name__ == "__main__":
    scraper = LouisianaBillScraper()
    
    try:
        print("🚀 Testing Louisiana Bill Scraper with Enhanced Sponsor Extraction")
        print("=" * 70)
        
        # Test search functionality
        success = scraper.test_search_functionality()
        
        if success:
            print("\n✅ Enhanced scraper is working correctly!")
            
            print("\n" + "=" * 70)
            print("🎯 Ready to search all keywords with enhanced sponsor extraction?")
            print("   - Better sponsor name detection")
            print("   - Multiple fallback methods")
            print("   - Debug output for troubleshooting")
            
            user_input = input("\nRun full search with enhanced features? (y/n): ").lower().strip()
            
            if user_input == 'y':
                print("\n🚀 Starting full enhanced keyword search...")
                
                # Run search for all keywords
                all_results = scraper.search_all_keywords(KEYWORDS, "2025")
                
                if all_results:
                    # Save to Excel
                    excel_file = scraper.save_to_excel(all_results)
                    
                    if excel_file:
                        print(f"\n🎉 SUCCESS! Enhanced data saved to: {excel_file}")
                        
                        # Show sponsor extraction summary
                        sponsors_found = [r['sponsors'] for r in all_results if r['sponsors'] != 'Unknown']
                        unknown_count = len([r for r in all_results if r['sponsors'] == 'Unknown'])
                        
                        print(f"\n📊 SPONSOR EXTRACTION SUMMARY:")
                        print(f"   - Found sponsors: {len(sponsors_found)}")
                        print(f"   - Unknown sponsors: {unknown_count}")
                        print(f"   - Success rate: {len(sponsors_found)/(len(sponsors_found)+unknown_count)*100:.1f}%")
                        
                    else:
                        print("\n❌ Failed to save Excel file")
                else:
                    print("\n📄 No bills found for any keywords")
            else:
                print("\n👍 Test completed successfully!")
        else:
            print("\n❌ Scraper needs debugging")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Search interrupted by user")
    except Exception as e:
        print(f"\n💥 Critical error: {str(e)}")
    finally:
        scraper.close()
        print("✅ Analysis complete!")
