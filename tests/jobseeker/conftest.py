import sys
import os
from pathlib import Path

# Add project root to sys.path to allow importing root modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import all fixtures and hooks from the main JobSeeker conftest
# This enables the custom logging and dashboard reporting hooks
from JobSeeker_Conftest import *
