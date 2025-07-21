
import logging
from datetime import datetime
import os
import time
#from concurrent.futures import ThreadPoolExecutor, as_completed
from Bill_extractor import LegiScanAPI
from data_processor import BillProcessor
from config import *

def setup_logging():
    """Setup logging configuration"""
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

'''def process_keyword_batch(api, processor, keywords_batch):
    """Process a batch of keywords"""
    batch_results = []
    
    for keyword in keywords_batch:
        try:
            keyword_result = process_single_keyword(api, processor, keyword)
            batch_results.append(keyword_result)
        except Exception as e:
            logging.error(f"Error processing keyword {keyword}: {e}")
            batch_results.append({'keyword': keyword, 'count': 0, 'error': str(e)})
    
    return batch_results'''


def process_single_keyword(api, processor, keyword):
    """Process a single keyword with STRICT keyword verification"""
    logging.info(f"Searching comprehensively for keyword: {keyword}")
    
    keyword_bills = 0
    
    # Use comprehensive temporal search
    all_bill_results = api.search_bills_comprehensive(keyword)
    
    if not all_bill_results:
        logging.warning(f"No results found for keyword: {keyword}")
        return {'keyword': keyword, 'count': 0, 'error': 'No results found'}
    
    # Extract bill IDs and DEDUPLICATE
    bill_ids_raw = [bill.get('bill_id') for bill in all_bill_results if bill.get('bill_id')]
    bill_ids = list(set(bill_ids_raw))  # Remove duplicates with set()
    
    # Show deduplication impact
    duplicates_removed = len(bill_ids_raw) - len(bill_ids)
    print(f"  📋 Processing {len(bill_ids)} unique bills ({duplicates_removed} duplicates removed)")
    
    # Process unique bills in batches
    total_batches = (len(bill_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(bill_ids), BATCH_SIZE):
        batch = bill_ids[i:i + BATCH_SIZE]
        current_batch = (i // BATCH_SIZE) + 1
        
        print(f"   Batch {current_batch}/{total_batches} - Processing {len(batch)} bills...")
        
        try:
            # Get raw bill details first
            processed_bills = processor.process_bills_batch_parallel(batch, api)
            
            #  CRITICAL FIX: Strict keyword verification before adding
            for bill in processed_bills:
                if bill:
                    # Check keyword match BEFORE processing into final format
                    is_match, matched_keyword = processor.check_keyword_match(bill, keyword)
                    
                    if is_match:  #  Only process bills with verified keyword matches
                        # Process into final format only after keyword verification
                        final_bill = processor.process_bill_data(bill, api)
                        if final_bill:
                            processor.add_bill(final_bill)
                            keyword_bills += 1
                    #  Bills without keyword matches are silently filtered out
                        
        except Exception as e:
            print(f"  ❌ Error processing batch {current_batch}: {e}")
            logging.error(f"Error processing batch {current_batch}: {e}")
    
    print(f"  ✅ Completed processing {keyword_bills} bills with verified keywords")
    return {'keyword': keyword, 'count': keyword_bills, 'error': None}


def main():
    """Main extraction workflow (optimized for production)"""
    start_time = time.time()
    
    print("=" * 60)
    print("PRODUCTION BILL EXTRACTION SYSTEM - STARTING")
    print("=" * 60)
    
    setup_logging()
    logging.info("Starting optimized bill extraction process")
    
    # Initialize API handler and processor
    api = LegiScanAPI(API_KEY)
    processor = BillProcessor()
    
    print(f"Searching for bills containing {len(KEYWORDS)} healthcare-related keywords...")
    print(f"Target years: {TARGET_YEARS}")
    print(f"Max results per keyword: {MAX_RESULTS_PER_KEYWORD}")
    print(f"Concurrent workers: {CONCURRENT_WORKERS}")
    if USE_CACHING:
        print("✅ Caching enabled for faster subsequent runs")
    print("-" * 60)
    
    # Process keywords with progress tracking
    search_results_summary = {}
    
    for i, keyword in enumerate(KEYWORDS, 1):
        print(f"[{i}/{len(KEYWORDS)}] Processing: '{keyword}'")
        
        try:
            result = process_single_keyword(api, processor, keyword)
            search_results_summary[keyword] = result['count']
            
            '''if result['error']:
                print(f"  ⚠️  {result['error']}")
            else:
                print(f"  📊 Added {result['count']} bills")'''
                
        except Exception as e:
            print(f"  ❌ Error processing '{keyword}': {e}")
            logging.error(f"Error processing keyword {keyword}: {e}")
            search_results_summary[keyword] = 0
        
       
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    print("=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    
    # Show comprehensive summary
    total_bills = len(processor.processed_bills)
    print(f"Total bills found: {total_bills}")
    print(f"Processing time: {processing_time:.2f} seconds ({processing_time/60:.1f} minutes)")
    print(f"Processor summary: {processor.get_summary()}")
    
    # Show performance statistics
    api_stats = api.get_performance_stats()
    processing_stats = processor.get_processing_stats()
    
    print(f"\nPerformance Statistics:")
    print(f"  API requests: {api_stats['total_requests']}")
    print(f"  API success rate: {api_stats['success_rate']:.1f}%")
    print(f"  Bills processed: {processing_stats['successful']}")
    print(f"  Processing failures: {processing_stats['failed']}")
    print(f"  Duplicates removed: {processing_stats['duplicates_removed']}")
    
    # Show keyword breakdown
    print("\nKeyword Breakdown:")
    for keyword, count in search_results_summary.items():
        print(f"  • {keyword}: {count} bills")
    
    # Save results to Excel
    print("\nSaving results to Excel...")
    processor.save_to_excel()
    
    # Calculate processing rate
    if processing_time > 0:
        rate = total_bills / processing_time
        print(f"\nProcessing rate: {rate:.2f} bills/second")
    
    print(f"\nExtraction complete! Check your results in: {OUTPUT_FILE}")
    print(f"Logs saved to: {LOG_FILE}")
    
    logging.info(f"Extraction complete. Total bills: {total_bills}, Time: {processing_time:.2f}s")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user.")
        logging.info("Extraction interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        logging.error(f"Unexpected error: {e}")
        raise



