#!/usr/bin/env python3
"""
Louisiana Legislative Bill Scraper - Main Runner
Searches for healthcare-related keywords in Louisiana legislative bills
"""

import os
import sys
import logging
from datetime import datetime
from src.louisiana_scraper import LouisianaBillScraper, KEYWORDS

def setup_logging():
    """Setup logging configuration"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = f"logs/scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_filename

def main():
    """Main execution function"""
    log_file = setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("🚀 Louisiana Legislative Bill Scraper Started")
    logger.info(f"📅 Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📝 Log File: {log_file}")
    logger.info("=" * 60)
    
    scraper = None
    
    try:
        # Initialize scraper
        logger.info("🔧 Initializing scraper...")
        scraper = LouisianaBillScraper()
        
        # Search for 2025 Regular Session
        logger.info("🔍 Starting search for 2025 Regular Session...")
        results_2025 = scraper.search_all_keywords(KEYWORDS, "2025")
        
        # TODO: Add 2026 when session becomes available
        # results_2026 = scraper.search_all_keywords(KEYWORDS, "2026")
        
        # Combine results
        all_results = results_2025
        
        if all_results:
            # Save to Excel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            excel_file = f"data/output/louisiana_healthcare_bills_{timestamp}.xlsx"
            
            saved_file = scraper.save_to_excel(all_results, excel_file)
            
            if saved_file:
                logger.info("🎉 SUCCESS!")
                logger.info(f"📊 Found {len(all_results)} unique healthcare-related bills")
                logger.info(f"💾 Data saved to: {saved_file}")
                
                # Print summary
                logger.info("\n📋 BILL SUMMARY:")
                for result in all_results:
                    logger.info(f"  • {result['bill_number']} - {result['sponsors']} - '{result['matched_keyword']}'")
            else:
                logger.error("❌ Failed to save results to Excel")
        else:
            logger.info("📄 No healthcare-related bills found")
            
    except Exception as e:
        logger.error(f"💥 Critical error: {str(e)}")
        return 1
        
    finally:
        if scraper:
            logger.info("🔄 Closing browser...")
            scraper.close()
        
        logger.info("✅ Scraper execution completed!")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
