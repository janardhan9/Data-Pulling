"""
Scheduler for Louisiana Bill Scraper - Bi-weekly execution
"""

import schedule
import time
import subprocess
import logging
from datetime import datetime
import os

def setup_scheduler_logging():
    """Setup logging for scheduler"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - SCHEDULER - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scheduler.log'),
            logging.StreamHandler()
        ]
    )

def run_scraper():
    """Execute the main scraper script"""
    logger = logging.getLogger(__name__)
    
    logger.info("🕐 Bi-weekly scraper job triggered")
    logger.info(f"📅 Execution time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run the main scraper script
        result = subprocess.run([
            'python', 'main.py'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            logger.info("✅ Scraper executed successfully")
            logger.info(f"📄 Output: {result.stdout[-500:]}")  # Last 500 chars
        else:
            logger.error("❌ Scraper failed")
            logger.error(f"🔴 Error: {result.stderr}")
            
    except Exception as e:
        logger.error(f"💥 Failed to run scraper: {str(e)}")

def start_scheduler():
    """Start the bi-weekly scheduler"""
    setup_scheduler_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Louisiana Bill Scraper Scheduler Started")
    logger.info("⏰ Scheduled to run every 2 weeks on Monday at 9:00 AM")
    
    # Schedule bi-weekly execution (every 2 weeks on Monday at 9:00 AM)
    schedule.every(2).weeks.at("09:00").do(run_scraper)
    
    # For testing: uncomment to run every 5 minutes
    # schedule.every(5).minutes.do(run_scraper)
    
    logger.info("⏳ Scheduler is running... Press Ctrl+C to stop")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        logger.info("⏹️ Scheduler stopped by user")

if __name__ == "__main__":
    start_scheduler()
