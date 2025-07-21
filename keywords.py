"""
Configuration for Louisiana Legislative Bill Scraper
"""

# Healthcare-related keywords to search for
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

# Target legislative sessions
TARGET_SESSIONS = {
    '2025': '2025 Regular Session',
    '2026': '2026 Regular Session'  # Will be available when session starts
}

# Output configuration
OUTPUT_FOLDER = 'data/output'
LOG_FOLDER = 'logs'

# Rate limiting (seconds between requests)
REQUEST_DELAY = 3.0

# Chrome browser options
CHROME_OPTIONS = {
    'headless': True,
    'no_sandbox': True,
    'disable_dev_shm_usage': True,
    'disable_gpu': True,
    'window_size': '1920,1080'
}
