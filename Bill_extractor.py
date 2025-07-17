import urllib3
import ssl
import requests
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
from functools import wraps
from config import *
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

def retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Decorator for retrying failed API requests"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logging.error(f"API request failed after {max_retries} attempts: {e}")
                        raise
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    logging.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator

class ProductionCache:
    """Caching system for faster subsequent runs"""
    def __init__(self, cache_dir="cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
    def get_cache_key(self, keyword, year):
        """Generate cache key for search results"""
        return hashlib.md5(f"{keyword}_{year}".encode()).hexdigest()
    
    def is_cache_valid(self, cache_key, max_age_hours=CACHE_DURATION_HOURS):
        """Check if cache is still valid"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return False
        
        try:
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            return datetime.now() - cache_time < timedelta(hours=max_age_hours)
        except (OSError, ValueError) as e:
            logging.warning(f"Cache validation failed for {cache_key}: {e}")
            return False
    
    def save_to_cache(self, cache_key, data):
        """Save data to cache"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except (OSError, json.JSONEncodeError) as e:
            logging.warning(f"Failed to save cache for {cache_key}: {e}")
    
    def load_from_cache(self, cache_key):
        """Load data from cache"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to load cache for {cache_key}: {e}")
        return None

class LegiScanAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.verify= False
        self.cache = ProductionCache() if USE_CACHING else None
        self.request_count = 0
        self.failed_requests = 0
        self.bill_details_cache = {}
    def get_bill_details(self, bill_id):
        """Get detailed bill information with global caching"""
        if not bill_id:
            logging.warning("Empty bill_id provided to get_bill_details")
            return None
        
        # Check global cache first
        if bill_id in self.bill_details_cache:
            return self.bill_details_cache[bill_id]
        
        # Get from API if not cached
        params = {'id': bill_id}
        result = self._make_request('getBill', params)
        
        # Cache the result
        self.bill_details_cache[bill_id] = result
        return result
        
    @retry_on_failure()
    def _make_request(self, operation, params=None):
        """Make API request with error handling and retry logic"""
        if params is None:
            params = {}
        
        params['key'] = self.api_key
        params['op'] = operation
        
        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            self.request_count += 1
            
            # Add delay to respect rate limits
            time.sleep(REQUEST_DELAY)
            
            return response.json()
            
        except requests.RequestException as e:
            self.failed_requests += 1
            logging.error(f"API request failed: {e}")
            raise
    
    def search_bills_optimized(self, query, state='ALL', year=2):
        """Optimized search with caching and filtering"""
        # Check cache first
        if self.cache and USE_CACHING:
            cache_key = self.cache.get_cache_key(query, year)
            if self.cache.is_cache_valid(cache_key):
                cached_data = self.cache.load_from_cache(cache_key)
                if cached_data:
                    logging.info(f"Using cached results for keyword: {query}")
                    return cached_data
        
        # Make API request
        params = {
            'state': state,
            'query': query,
            'year': year
        }
        
        results = self._make_request('getSearchRaw', params)
        
        # Filter and limit results
        if results and results.get('status') == 'OK':
            search_results = results.get('searchresult', {})
            if search_results:  # Check if searchresult exists
                bill_results = search_results.get('results', [])
                
                # Limit results for faster processing
                #limited_results = bill_results
                # Use all results when MAX_RESULTS_PER_KEYWORD is None
                if MAX_RESULTS_PER_KEYWORD is None:
                    limited_results = bill_results  # Use all results
                else:
                    limited_results = bill_results[:MAX_RESULTS_PER_KEYWORD]
                
                # Update results with limited data
                results['searchresult']['results'] = limited_results
                
                # Cache the results
                if self.cache and USE_CACHING:
                    self.cache.save_to_cache(cache_key, results)
        
        return results
    
    def get_bill_details(self, bill_id):
        """Get detailed bill information"""
        if not bill_id:
            logging.warning("Empty bill_id provided to get_bill_details")
            return None
            
        params = {'id': bill_id}
        return self._make_request('getBill', params)
    
   
    
    def get_sessions_by_year(self, year):
        """Get all sessions for a specific year"""
        all_sessions = self._make_request('getSessionList')
        if not all_sessions or all_sessions.get('status') != 'OK':
            return []
        
        year_sessions = []
        sessions_data = all_sessions.get('sessions', [])
        
        for session in sessions_data:
            if session.get('year_start') == year or session.get('year_end') == year:
                year_sessions.append(session)
        
        return year_sessions
    
    def get_performance_stats(self):
        """Get API performance statistics"""
        return {
            'total_requests': self.request_count,
            'failed_requests': self.failed_requests,
            'success_rate': (self.request_count - self.failed_requests) / max(self.request_count, 1) * 100
        }



    def search_temporal_segments(self, query):
        """Search keyword across time segments with parallel processing"""
        all_results = []
        
        def search_time_segment(segment):
            """Search within a specific time segment"""
            params = {
                'state': 'ALL',
                'query': query,
                'year': 2  # Use recent sessions
            }
            
            try:
                results = self._make_request('getSearchRaw', params)
                if results and results.get('status') == 'OK':
                    bills = results.get('searchresult', {}).get('results', [])
                    
                    # Filter by date range (basic filtering by year for now)
                    #filtered_bills = self._filter_by_year(bills, segment['start'][:4])
                    filtered_bills = bills
                    logging.info(f"Segment {segment['label']}: {len(filtered_bills)} bills")
                    return filtered_bills
                else:
                    logging.info(f"Segment {segment['label']}: No results")
                    return []
                    
            except Exception as e:
                logging.error(f"Error searching segment {segment['label']}: {e}")
                return []
        
        # Process time segments in parallel
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SEARCHES) as executor:
            future_to_segment = {
                executor.submit(search_time_segment, segment): segment
                for segment in TIME_SEGMENTS
            }
            
            for future in as_completed(future_to_segment):
                try:
                    segment_results = future.result()
                    all_results.extend(segment_results)
                except Exception as e:
                    logging.error(f"Segment processing failed: {e}")
        
        # Remove duplicates by bill_id
        unique_bills = {bill.get('bill_id'): bill for bill in all_results if bill.get('bill_id')}
        return list(unique_bills.values())

    def _filter_by_year(self, bills, target_year):
        """Filter bills by year"""
        filtered = []
        for bill in bills:
            # Extract year from bill data - check session year
            bill_year = None
            if 'session' in bill:
                bill_year = bill['session'].get('year_start')
            
            # If year matches target year, include the bill
            if bill_year == int(target_year):
                filtered.append(bill)
        
        return filtered

    def search_bills_comprehensive(self, query):
        """Comprehensive search using temporal segmentation"""
        logging.info(f"Starting comprehensive temporal search for: {query}")
        
        # Check cache first
        if self.cache and USE_CACHING:
            cache_key = f"temporal_{self.cache.get_cache_key(query, 'temporal')}"
            if self.cache.is_cache_valid(cache_key):
                cached_data = self.cache.load_from_cache(cache_key)
                if cached_data:
                    logging.info(f"Using cached temporal results for: {query}")
                    return cached_data
        
        # Perform temporal segmentation search
        all_bills = self.search_temporal_segments(query)
        
        # Cache results
        if self.cache and USE_CACHING:
            cache_key = f"temporal_{self.cache.get_cache_key(query, 'temporal')}"
            self.cache.save_to_cache(cache_key, all_bills)
        
        return all_bills
