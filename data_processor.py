import pandas as pd
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import *

class BillProcessor:
    def __init__(self):
        self.processed_bills = []
        self.processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'duplicates_removed': 0
        }
        
    def extract_sponsors(self, sponsors_data, api_handler):
        """Extract sponsors using actual LegiScan data structure"""
        if not sponsors_data:
            return "No sponsors listed"
        
        # Sort by sponsor_order to get primary sponsor first
        sorted_sponsors = sorted(sponsors_data, key=lambda x: x.get('sponsor_order', 999))
        
        # Get first sponsor with a name (primary sponsor)
        for sponsor in sorted_sponsors:
            if sponsor.get('name'):
                return sponsor['name']
        
        # If no sponsor has a name available
        return "No sponsors listed"



    
    def extract_last_action(self, history_data):
        """Extract the most recent action from history (without date)"""
        if not history_data:
            return "No action recorded"
        
        try:
            # If it's a list of dictionaries
            if isinstance(history_data, list) and history_data:
                # Sort by date and get the most recent
                sorted_actions = sorted(history_data, 
                                    key=lambda x: x.get('date', '1900-01-01'), 
                                    reverse=True)
                latest_action = sorted_actions[0]
                action_text = latest_action.get('action', 'No action text')
                
                # Truncate long actions for readability
                if len(action_text) > 100:
                    action_text = action_text[:100] + "..."
                
                return action_text  # Return only action text, no date
            
            # If it's already a string
            if isinstance(history_data, str):
                return history_data[:100] + "..." if len(history_data) > 100 else history_data
                
            # If it's a dictionary
            if isinstance(history_data, dict):
                action = history_data.get('action', 'No action recorded')
                return action[:100] + "..." if len(action) > 100 else action
                
        except Exception as e:
            logging.warning(f"Failed to extract last action: {e}")
            
        return "No action recorded"

    
    def process_bill_data(self, bill_data, api_handler):
        """Process individual bill data into required format (optimized)"""
        try:
            bill = bill_data.get('bill', {})
            session = bill.get('session', {})
            
            # Get state abbreviation and convert to full name
            state_abbr = bill.get('state', '')
            state_full_name = STATE_MAPPING.get(state_abbr, state_abbr)  # Fallback to abbreviation if not found
            
            # Extract required fields
            processed_bill = {
                'Year': session.get('year_start', ''),
                'State': state_full_name,  # Use full state name instead of abbreviation
                'Bill Number': bill.get('bill_number', ''),
                'Bill Title/Topic': bill.get('title', ''),
                'Summary': bill.get('description', ''),
                'Sponsors': self.extract_sponsors(bill.get('sponsors', []), api_handler),
                'Last Action': self.extract_last_action(bill.get('history', [])),
                'Bill Link': self.get_state_bill_link(bill),# No date included
                #'Bill Link': bill.get('url', ''),
                'Current Status': STATUS_MAPPING.get(bill.get('status'), 'Unknown'),
                'Extracted Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.processing_stats['successful'] += 1
            return processed_bill
            
        except Exception as e:
            logging.error(f"Failed to process bill data: {e}")
            self.processing_stats['failed'] += 1
            return None

    
    def process_bills_batch(self, bill_ids, api_handler):
        """Process multiple bills concurrently"""
        processed_bills = []
        
        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            # Submit all bill processing tasks
            future_to_bill = {}
            for bill_id in bill_ids:
                future = executor.submit(self._process_single_bill, bill_id, api_handler)
                future_to_bill[future] = bill_id
            
            # Collect results as they complete
            for future in as_completed(future_to_bill):
                bill_id = future_to_bill[future]
                try:
                    result = future.result()
                    if result:
                        processed_bills.append(result)
                except Exception as e:
                    logging.error(f"Error processing bill {bill_id}: {e}")
                    
        return processed_bills
    
    def _process_single_bill(self, bill_id, api_handler):
        """Process a single bill (simplified - trust API search results)"""
        try:
            bill_details = api_handler.get_bill_details(bill_id)
            
            if not bill_details or bill_details.get('status') != 'OK':
                #print(f"    DEBUG: Bill {bill_id} - Failed to get details")
                return None
            
            # Check if bill is from target years
            bill_year = bill_details.get('bill', {}).get('session', {}).get('year_start')
            #print(f"    DEBUG: Bill {bill_id} is from year {bill_year}")
            
            if bill_year not in TARGET_YEARS:
                #print(f"    DEBUG: Filtered out {bill_id} - wrong year ({bill_year})")
                return None
            
            # Skip keyword verification here - trust API search results
            #print(f"    DEBUG: Bill {bill_id} - Processing (trusting API search)")
            return self.process_bill_data(bill_details, api_handler)
            
        except Exception as e:
            logging.error(f"Failed to process bill {bill_id}: {e}")
            #print(f"    DEBUG: Bill {bill_id} - Error: {e}")
            return None

    def check_keyword_match(self, bill_data, target_keyword):
        """Enhanced keyword matching with flexibility"""
        if not bill_data:
            return False, target_keyword
        
        # Get the bill data
        bill = bill_data.get('bill', {}) if 'bill' in bill_data else bill_data
        
        # Fields to search in
        search_fields = [
            bill.get('title', ''),
            bill.get('description', ''),
            bill.get('summary', ''),
            bill.get('text', ''),
        ]
        
        # Search in history/actions
        history = bill.get('history', [])
        if isinstance(history, list):
            for action in history:
                if isinstance(action, dict):
                    search_fields.append(action.get('action', ''))
        
        # Search in sponsors
        sponsors = bill.get('sponsors', [])
        if isinstance(sponsors, list):
            for sponsor in sponsors:
                if isinstance(sponsor, dict):
                    search_fields.append(sponsor.get('name', ''))
        
        # Combine all text and search (case-insensitive)
        combined_text = ' '.join(search_fields).lower()
        
        # Enhanced keyword matching
        keyword_variations = [
            target_keyword.lower(),
            target_keyword.lower().replace(' review', ''),  # "utilization" matches "utilization review"
            target_keyword.lower().replace(' ', ''),        # Handle spacing issues
        ]
        
        # Check for any variation
        for variation in keyword_variations:
            if variation in combined_text:
                return True, target_keyword
        
        # If strict matching fails, trust API results for now
        logging.info(f"Keyword '{target_keyword}' not found in bill {bill.get('bill_number', 'unknown')} - trusting API")
        return True, target_keyword  # Trust API search results
    
    def get_state_bill_link(self, bill):
        """Extract state bill link instead of LegiScan link"""
        # Try state_link first
        state_link = bill.get('state_link', '')
        if state_link:
            return state_link
        
        # Try state_url
        state_url = bill.get('state_url', '')
        if state_url:
            return state_url
        
        # Fallback to LegiScan URL if no state link
        return bill.get('url', 'No link available')

    
    def add_bill(self, processed_bill):
        """Add a processed bill to the collection"""
        if processed_bill:
            self.processed_bills.append(processed_bill)
            self.processing_stats['total_processed'] += 1
            
    def remove_duplicates(self):
        """Remove duplicate bills based on state and bill number"""
        seen = set()
        unique_bills = []
        
        for bill in self.processed_bills:
            identifier = (bill['State'], bill['Bill Number'])
            if identifier not in seen:
                seen.add(identifier)
                unique_bills.append(bill)
            else:
                self.processing_stats['duplicates_removed'] += 1
                #logging.info(f"Removed duplicate: {bill['State']} {bill['Bill Number']}")
        
        self.processed_bills = unique_bills
        
    def save_to_excel(self, output_file=OUTPUT_FILE):
        """Save processed bills to Excel file (optimized)"""
        if not self.processed_bills:
            logging.warning("No bills to save")
            print("No bills found matching your criteria.")
            return
        
        # Remove duplicates before saving
        self.remove_duplicates()
        
        try:
            df = pd.DataFrame(self.processed_bills)
            
            # Ensure output directory exists
            import os
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Save to Excel with formatting
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Bills', index=False)
                
                # Get the workbook and worksheet
                worksheet = writer.sheets['Bills']
                
                # Auto-adjust column widths (optimized)
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logging.info(f"Saved {len(self.processed_bills)} bills to {output_file}")
            print(f"Successfully saved {len(self.processed_bills)} bills to {output_file}")
            
        except Exception as e:
            logging.error(f"Failed to save Excel file: {e}")
            print(f"Error saving Excel file: {e}")
    
    def get_summary(self):
        """Get a summary of processed bills"""
        if not self.processed_bills:
            return "No bills processed"
        
        total_bills = len(self.processed_bills)
        states = set(bill['State'] for bill in self.processed_bills)
        years = set(bill['Year'] for bill in self.processed_bills)
        
        return f"Total Bills: {total_bills} | States: {len(states)} | Years: {sorted(years)}"
    
    def get_processing_stats(self):
        """Get detailed processing statistics"""
        return self.processing_stats
    
    def process_bills_batch_parallel(self, bill_ids, api_handler):
        """Process multiple bills with parallel execution"""
        processed_bills = []
        
        def process_single_bill_wrapper(bill_id):
            """Wrapper for single bill processing"""
            return self._process_single_bill(bill_id, api_handler)
        
        # Process bills in parallel
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BILLS) as executor:
            future_to_bill = {
                executor.submit(process_single_bill_wrapper, bill_id): bill_id
                for bill_id in bill_ids
            }
            
            for future in as_completed(future_to_bill):
                bill_id = future_to_bill[future]
                try:
                    result = future.result()
                    if result:
                        processed_bills.append(result)
                except Exception as e:
                    logging.error(f"Error processing bill {bill_id}: {e}")
        
        return processed_bills

    
