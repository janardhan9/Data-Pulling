import os
from datetime import datetime

# API Configuration
API_KEY = "ee677b253411d702f9b39f2731dff7b7"  # Keep your actual API key
BASE_URL = "https://api.legiscan.com/"

# Search Keywords
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

# Target Years
TARGET_YEARS = [2025, 2026]

# Status Code Mapping
STATUS_MAPPING = {
    1: "Introduced",
    2: "Engrossed", 
    3: "Enrolled",
    4: "Passed"
}

# Output Configuration
OUTPUT_FILE = "data/bills_output.xlsx"
LOG_FILE = "logs/extraction.log"

# Production Performance Settings
REQUEST_DELAY = 0.25  # Reduced from 0.5 seconds
MAX_RESULTS_PER_KEYWORD = None  # Limit results per keyword for faster processing
CONCURRENT_WORKERS = 3  # Number of parallel workers
BATCH_SIZE = 20  # Process bills in batches
USE_CACHING = True  # Enable caching for faster subsequent runs
CACHE_DURATION_HOURS = 12  # Cache validity period

# Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # Initial retry delay in seconds

# Logging Configuration
LOG_LEVEL = "INFO"
ENABLE_PROGRESS_BAR = True

# Add this to your existing config.py file

# Temporal segmentation for complete coverage
TIME_SEGMENTS = [
    {'start': '2025-01-01', 'end': '2025-03-31', 'label': 'Q1 2025'},
    {'start': '2025-04-01', 'end': '2025-06-30', 'label': 'Q2 2025'},
    {'start': '2025-07-01', 'end': '2025-09-30', 'label': 'Q3 2025'},
    {'start': '2025-10-01', 'end': '2025-12-31', 'label': 'Q4 2025'},
    {'start': '2026-01-01', 'end': '2026-06-30', 'label': 'H1 2026'},
    {'start': '2026-07-01', 'end': '2026-12-31', 'label': 'H2 2026'}
]

# Parallel processing settings
MAX_CONCURRENT_SEARCHES = 3  # Time segments processed simultaneously
MAX_CONCURRENT_BILLS = 5     # Bill details processed simultaneously

# State abbreviation to full name mapping
STATE_MAPPING = {
    'AL': 'Alabama',
    'AK': 'Alaska',
    'AZ': 'Arizona',
    'AR': 'Arkansas',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'HI': 'Hawaii',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'IA': 'Iowa',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'ME': 'Maine',
    'MD': 'Maryland',
    'MA': 'Massachusetts',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MS': 'Mississippi',
    'MO': 'Missouri',
    'MT': 'Montana',
    'NE': 'Nebraska',
    'NV': 'Nevada',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NY': 'New York',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VT': 'Vermont',
    'VA': 'Virginia',
    'WA': 'Washington',
    'WV': 'West Virginia',
    'WI': 'Wisconsin',
    'WY': 'Wyoming',
    'DC': 'District of Columbia',
    'US': 'United States'
}

