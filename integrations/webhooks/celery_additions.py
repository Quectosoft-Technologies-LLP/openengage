# Add to celery_app.py beat_schedule:
# "sync-to-salesforce"   → every 30 min → pull_from_salesforce
# "sync-to-hubspot"      → every 30 min → pull_from_hubspot
# "push-mqls-to-crm"     → every hour   → push leads with score >= 50

# Also add queue to task_routes:
# "integrations.salesforce.adapter.*" : {"queue": "crm_sync"},
# "integrations.hubspot.adapter.*"    : {"queue": "crm_sync"},
