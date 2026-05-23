"""
Standalone deduplication utility — can be imported by migration tools.
"""
from integrations.csv_import.importer import deduplicate_contacts

__all__ = ["deduplicate_contacts"]
