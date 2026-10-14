"""Keep all source families visible and distinguish models from available data."""
import json
from .config import ROOT


def company_comparisons():
    return json.loads((ROOT/'data/company-comparison-catalog.json').read_text())['sources']
