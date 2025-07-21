import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

class LouisianaLegislatureAnalyzer:
    def __init__(self):
        self.base_url = "https://www.legis.la.gov"
        self.search_url = "https://www.legis.la.gov/Legis/BillSearch.aspx"
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome WebDriver with Selenium Manager (automatic driver management)"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Selenium 4.6+ includes Selenium Manager - no need for ChromeDriverManager
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Execute script to remove webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def analyze_search_page(self):
        """Analyze the bill search page structure"""
        print("🔍 Analyzing Louisiana Legislature Search Page...")
        
        try:
            # Navigate to the search page
            self.driver.get(f"{self.search_url}?sid=current")
            time.sleep(3)
            
            # Get page title
            page_title = self.driver.title
            print(f"📄 Page Title: {page_title}")
            
            # Find search form elements
            search_elements = self.find_search_elements()
            
            # Check available sessions
            sessions = self.find_available_sessions()
            
            return {
                'page_title': page_title,
                'search_elements': search_elements,
                'available_sessions': sessions
            }
            
        except Exception as e:
            print(f"❌ Error analyzing search page: {str(e)}")
            return None
    
    def find_search_elements(self):
        """Find and analyze search form elements"""
        elements = {}
        
        try:
            # Look for search input fields
            search_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            print(f"🔎 Found {len(search_inputs)} input elements")
            
            for idx, input_elem in enumerate(search_inputs):
                input_type = input_elem.get_attribute("type")
                input_name = input_elem.get_attribute("name")
                input_id = input_elem.get_attribute("id")
                input_placeholder = input_elem.get_attribute("placeholder")
                
                print(f"  Input {idx}: type='{input_type}', name='{input_name}', id='{input_id}', placeholder='{input_placeholder}'")
                
                if input_type == "text" and ("summary" in str(input_name).lower() or "search" in str(input_name).lower()):
                    elements['summary_search'] = {
                        'name': input_name,
                        'id': input_id,
                        'element': input_elem
                    }
            
            # Look for dropdown/select elements (for session selection)
            dropdowns = self.driver.find_elements(By.TAG_NAME, "select")
            print(f"📋 Found {len(dropdowns)} dropdown elements")
            
            for idx, select_elem in enumerate(dropdowns):
                select_name = select_elem.get_attribute("name")
                select_id = select_elem.get_attribute("id")
                options = select_elem.find_elements(By.TAG_NAME, "option")
                
                print(f"  Dropdown {idx}: name='{select_name}', id='{select_id}', options={len(options)}")
                
                if "session" in str(select_name).lower():
                    elements['session_dropdown'] = {
                        'name': select_name,
                        'id': select_id,
                        'element': select_elem,
                        'options': [opt.text for opt in options]
                    }
            
            # Look for submit buttons
            buttons = self.driver.find_elements(By.TAG_NAME, "input")
            buttons.extend(self.driver.find_elements(By.TAG_NAME, "button"))
            
            for button in buttons:
                button_type = button.get_attribute("type")
                button_value = button.get_attribute("value")
                button_text = button.text
                
                if button_type == "submit" or "search" in str(button_value).lower():
                    elements['search_button'] = {
                        'type': button_type,
                        'value': button_value,
                        'text': button_text,
                        'element': button
                    }
                    print(f"🔘 Search Button: type='{button_type}', value='{button_value}', text='{button_text}'")
            
            return elements
            
        except Exception as e:
            print(f"❌ Error finding search elements: {str(e)}")
            return {}
    
    def find_available_sessions(self):
        """Find available legislative sessions"""
        sessions = []
        
        try:
            # Look for session information in the page
            session_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '2025') or contains(text(), '2026')]")
            
            for elem in session_elements:
                text = elem.text.strip()
                if "2025" in text or "2026" in text:
                    sessions.append(text)
            
            # Remove duplicates
            sessions = list(set(sessions))
            
            print(f"📅 Available Sessions: {sessions}")
            return sessions
            
        except Exception as e:
            print(f"❌ Error finding sessions: {str(e)}")
            return []
    
    def test_search_functionality(self, test_keyword="health"):
        """Test the search functionality with a simple keyword"""
        print(f"🧪 Testing search functionality with keyword: '{test_keyword}'")
        
        try:
            # Navigate to search page
            self.driver.get(f"{self.search_url}?sid=current")
            time.sleep(3)
            
            # Find and fill search input
            search_elements = self.find_search_elements()
            
            if 'summary_search' in search_elements:
                search_input = search_elements['summary_search']['element']
                search_input.clear()
                search_input.send_keys(test_keyword)
                
                # Click search button
                if 'search_button' in search_elements:
                    search_button = search_elements['search_button']['element']
                    search_button.click()
                    
                    # Wait for results
                    time.sleep(5)
                    
                    # Check for results
                    current_url = self.driver.current_url
                    page_source = self.driver.page_source
                    
                    print(f"🌐 Results URL: {current_url}")
                    print(f"📄 Page contains '{test_keyword}': {'yes' if test_keyword.lower() in page_source.lower() else 'no'}")
                    
                    # Try to find result elements
                    result_elements = self.find_search_results()
                    
                    return True
                else:
                    print("❌ Search button not found")
                    return False
            else:
                print("❌ Search input field not found")
                return False
                
        except Exception as e:
            print(f"❌ Error testing search functionality: {str(e)}")
            return False
    
    def find_search_results(self):
        """Find and analyze search result elements"""
        try:
            # Look for common result patterns
            result_patterns = [
                "//table",
                "//div[contains(@class, 'result')]",
                "//div[contains(@class, 'bill')]",
                "//tr",
                "//*[contains(text(), 'HB') or contains(text(), 'SB')]"
            ]
            
            for pattern in result_patterns:
                elements = self.driver.find_elements(By.XPATH, pattern)
                if elements:
                    print(f"📋 Found {len(elements)} elements matching pattern: {pattern}")
                    
                    # Show first few results for analysis
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = elem.text.strip()[:100]  # First 100 characters
                            print(f"  Result {i}: {text}...")
                        except:
                            print(f"  Result {i}: [Unable to extract text]")
            
            return True
            
        except Exception as e:
            print(f"❌ Error finding search results: {str(e)}")
            return False
    
    def get_page_source_sample(self):
        """Get a sample of the current page source for debugging"""
        try:
            source = self.driver.page_source
            print(f"📄 Page source length: {len(source)} characters")
            
            # Look for key indicators
            indicators = ['bill', 'search', 'result', 'HB', 'SB', '2025']
            for indicator in indicators:
                count = source.lower().count(indicator.lower())
                print(f"  '{indicator}' appears {count} times")
            
            return source
            
        except Exception as e:
            print(f"❌ Error getting page source: {str(e)}")
            return None
    
    def close(self):
        """Close the webdriver"""
        if hasattr(self, 'driver'):
            self.driver.quit()

# Test script
if __name__ == "__main__":
    analyzer = LouisianaLegislatureAnalyzer()
    
    try:
        print("🚀 Starting Louisiana Legislature Website Analysis")
        print("=" * 60)
        
        # Analyze the search page
        analysis_results = analyzer.analyze_search_page()
        
        if analysis_results:
            print("\n" + "="*50)
            print("📊 ANALYSIS SUMMARY")
            print("="*50)
            print(f"Page Title: {analysis_results.get('page_title', 'N/A')}")
            print(f"Available Sessions: {analysis_results.get('available_sessions', [])}")
            print(f"Search Elements Found: {len(analysis_results.get('search_elements', {}))}")
            
            # Show found elements
            search_elements = analysis_results.get('search_elements', {})
            for element_type, element_info in search_elements.items():
                if element_type != 'element':  # Skip the actual selenium element
                    print(f"  - {element_type}: {element_info}")
        
        # Test search functionality
        print("\n" + "="*50)
        print("🧪 TESTING SEARCH FUNCTIONALITY")
        print("="*50)
        test_result = analyzer.test_search_functionality("health")
        
        if test_result:
            print("✅ Search functionality test PASSED")
            
            # Get page source sample for debugging
            print("\n" + "="*50)
            print("🔍 PAGE SOURCE ANALYSIS")
            print("="*50)
            analyzer.get_page_source_sample()
            
        else:
            print("❌ Search functionality test FAILED")
            
    except Exception as e:
        print(f"💥 Critical error: {str(e)}")
        
    finally:
        print("\n🔄 Closing browser...")
        analyzer.close()
        print("✅ Analysis complete!")
