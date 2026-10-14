"""Load the shared PDF contract for every model request and cache identity."""
import hashlib
from .config import ROOT

RULES_PATH = ROOT / 'docs/PDF_AGENT.md'


def rules():
    return RULES_PATH.read_text(encoding='utf-8')


def fingerprint():
    return hashlib.sha256(rules().encode('utf-8')).hexdigest()
