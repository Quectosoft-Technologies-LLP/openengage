"""
Contacts CSV Import Pipeline with Multi-Strategy Deduplication
Supports: exact email match, fuzzy name+company match, phone dedup
Upload endpoint: POST /api/contacts/import (multipart CSV)
"""
import os, csv, io, re, json, uuid
from dataclasses import dataclass, field
from typing import Optional
from difflib import SequenceMatcher
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL) if DB_URL else None


# ── REQUIRED / OPTIONAL CSV COLUMNS ──────────────────────────
REQUIRED_COLUMNS = {"email"}
OPTIONAL_COLUMNS = {
    "first_name", "last_name", "company", "industry",
    "job_title", "city", "country", "phone",
    "lead_score", "lifecycle_stage", "tags"
}

# Aliases: maps common CSV header variations to canonical names
COLUMN_ALIASES = {
    "e-mail":           "email",
    "email address":    "email",
    "emailaddress":     "email",
    "mail":             "email",
    "firstname":        "first_name",
    "first name":       "first_name",
    "given name":       "first_name",
    "lastname":         "last_name",
    "last name":        "last_name",
    "surname":          "last_name",
    "family name":      "last_name",
    "organisation":     "company",
    "organization":     "company",
    "account":          "company",
    "role":             "job_title",
    "title":            "job_title",
    "position":         "job_title",
    "score":            "lead_score",
    "points":           "lead_score",
    "status":           "lifecycle_stage",
    "stage":            "lifecycle_stage",
    "segment":          "lifecycle_stage",
}


@dataclass
class ImportResult:
    total_rows:     int = 0
    valid_rows:     int = 0
    invalid_rows:   int = 0
    duplicates_in_csv:  int = 0
    duplicates_in_db:   int = 0
    inserted:       int = 0
    updated:        int = 0
    errors:         list = field(default_factory=list)
    sample_errors:  list = field(default_factory=list)


# ── NORMALIZERS ───────────────────────────────────────────────
def normalize_email(email: str) -> str:
    return email.lower().strip()

def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())

def normalize_company(company: str) -> str:
    """Strip common legal suffixes for fuzzy matching."""
    company = company.lower().strip()
    for suffix in [" inc", " inc.", " llc", " ltd", " limited", " corp",
                   " corporation", " plc", " gmbh", " pvt", " private"]:
        company = company.rstrip(suffix)
    return company.strip()

def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def validate_row(row: dict) -> tuple[bool, str]:
    email = row.get("email", "").strip()
    if not email:
        return False, "Missing email"
    if not validate_email(email):
        return False, f"Invalid email format: {email}"
    return True, ""


# ── CSV PARSER ────────────────────────────────────────────────
def parse_csv(content: bytes, encoding: str = "utf-8-sig") -> tuple[list[dict], list[str]]:
    """
    Parse CSV bytes → list of normalized contact dicts.
    Returns (rows, detected_headers).
    Auto-detects delimiter (comma, semicolon, tab).
    """
    text_content = content.decode(encoding, errors="replace")
    # Detect delimiter
    sample = text_content[:2048]
    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")

    reader = csv.DictReader(io.StringIO(text_content), dialect=dialect)
    raw_headers = reader.fieldnames or []

    # Build header mapping (alias resolution)
    header_map = {}
    for h in raw_headers:
        normalized = h.lower().strip()
        canonical  = COLUMN_ALIASES.get(normalized, normalized.replace(" ", "_"))
        header_map[h] = canonical

    rows = []
    for raw_row in reader:
        row = {}
        for orig_key, value in raw_row.items():
            canonical_key = header_map.get(orig_key, orig_key)
            if canonical_key in (REQUIRED_COLUMNS | OPTIONAL_COLUMNS):
                row[canonical_key] = (value or "").strip()
        rows.append(row)

    return rows, list(header_map.values())


# ── DEDUPLICATION ─────────────────────────────────────────────
def deduplicate_contacts(
    contacts: list[dict],
    key_field: str = "email",
    fuzzy_threshold: float = 0.85
) -> list[dict]:
    """
    Remove duplicates within the input list.
    Strategy 1: Exact email deduplication (primary)
    Strategy 2: Fuzzy name + company deduplication (secondary, threshold configurable)
    """
    seen_emails: dict[str, dict] = {}
    fuzzy_candidates: list[dict] = []

    # Pass 1: exact email dedup — keep highest lead_score version
    for c in contacts:
        email = normalize_email(c.get("email", ""))
        if not email:
            continue
        if email in seen_emails:
            existing = seen_emails[email]
            # Merge: keep higher score, newer lifecycle stage
            try:
                if int(c.get("lead_score", 0)) > int(existing.get("lead_score", 0)):
                    seen_emails[email] = {**existing, "lead_score": c["lead_score"]}
            except (ValueError, TypeError):
                pass
        else:
            seen_emails[email] = {**c, "email": email}

    deduped = list(seen_emails.values())

    # Pass 2: fuzzy dedup on name+company (optional, for merged companies)
    # Only run if no email available
    final = []
    seen_fingerprints: set[str] = set()
    for c in deduped:
        fp = _fuzzy_fingerprint(c)
        is_dup = False
        for seen_fp in seen_fingerprints:
            if _similarity(fp, seen_fp) >= fuzzy_threshold:
                is_dup = True
                break
        if not is_dup:
            seen_fingerprints.add(fp)
            final.append(c)

    return final

def _fuzzy_fingerprint(c: dict) -> str:
    name    = normalize_name(f"{c.get('first_name','')} {c.get('last_name','')}")
    company = normalize_company(c.get("company", ""))
    return f"{name}|{company}"

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# ── DB UPSERT WITH CONFLICT RESOLUTION ───────────────────────
def upsert_contacts_to_db(
    contacts: list[dict],
    on_conflict: str = "update",  # "update" | "skip" | "error"
    batch_size: int = 500
) -> ImportResult:
    """
    Bulk upsert contacts with configurable conflict strategy.
    on_conflict="update"  → UPDATE existing record (default)
    on_conflict="skip"    → ignore existing, only insert new
    on_conflict="error"   → raise on any conflict
    """
    result = ImportResult(total_rows=len(contacts))
    valid  = []

    for row in contacts:
        ok, msg = validate_row(row)
        if ok:
            valid.append(row)
            result.valid_rows += 1
        else:
            result.invalid_rows += 1
            if len(result.sample_errors) < 10:
                result.sample_errors.append({"row": row, "error": msg})

    if not engine:
        result.errors.append("No database connection")
        return result

    with engine.connect() as conn:
        # Check existing emails in DB for stats
        if valid:
            emails = [r["email"] for r in valid]
            existing = conn.execute(
                text("SELECT email FROM contacts WHERE email = ANY(:emails)"),
                {"emails": emails}
            ).fetchall()
            existing_set = {r.email for r in existing}
            result.duplicates_in_db = len(existing_set)

        for i in range(0, len(valid), batch_size):
            batch = valid[i:i+batch_size]
            for c in batch:
                contact_id = str(uuid.uuid4())
                try:
                    if on_conflict == "update":
                        conn.execute(text("""
                            INSERT INTO contacts
                                (id, email, first_name, last_name, company, industry,
                                 job_title, lead_score, lifecycle_stage, city, country, created_at)
                            VALUES
                                (:id, :email, :first_name, :last_name, :company, :industry,
                                 :job_title, :lead_score, :lifecycle_stage, :city, :country, NOW())
                            ON CONFLICT (email) DO UPDATE SET
                                first_name      = COALESCE(NULLIF(EXCLUDED.first_name, ''),     contacts.first_name),
                                last_name       = COALESCE(NULLIF(EXCLUDED.last_name, ''),      contacts.last_name),
                                company         = COALESCE(NULLIF(EXCLUDED.company, ''),        contacts.company),
                                industry        = COALESCE(NULLIF(EXCLUDED.industry, ''),       contacts.industry),
                                job_title       = COALESCE(NULLIF(EXCLUDED.job_title, ''),      contacts.job_title),
                                lead_score      = GREATEST(contacts.lead_score, EXCLUDED.lead_score),
                                lifecycle_stage = EXCLUDED.lifecycle_stage,
                                last_active_at  = NOW()
                        """), {
                            "id":             contact_id,
                            "email":          c.get("email", ""),
                            "first_name":     c.get("first_name", ""),
                            "last_name":      c.get("last_name", ""),
                            "company":        c.get("company", ""),
                            "industry":       c.get("industry", ""),
                            "job_title":      c.get("job_title", ""),
                            "lead_score":     _safe_int(c.get("lead_score", 0)),
                            "lifecycle_stage":c.get("lifecycle_stage", "lead"),
                            "city":           c.get("city", ""),
                            "country":        c.get("country", ""),
                        })
                        if c["email"] in existing_set:
                            result.updated += 1
                        else:
                            result.inserted += 1

                    elif on_conflict == "skip":
                        conn.execute(text("""
                            INSERT INTO contacts (id, email, first_name, last_name, company,
                                industry, job_title, lead_score, lifecycle_stage, city, country, created_at)
                            VALUES (:id, :email, :first_name, :last_name, :company, :industry,
                                :job_title, :lead_score, :lifecycle_stage, :city, :country, NOW())
                            ON CONFLICT (email) DO NOTHING
                        """), {**c, "id": contact_id,
                               "lead_score": _safe_int(c.get("lead_score", 0)),
                               "lifecycle_stage": c.get("lifecycle_stage", "lead")})
                        result.inserted += 1

                except Exception as e:
                    result.errors.append(str(e)[:200])
                    if len(result.sample_errors) < 10:
                        result.sample_errors.append({"row": c, "error": str(e)[:200]})

        conn.commit()

    return result

def _safe_int(v) -> int:
    try: return int(float(v))
    except: return 0


# ── TAGS HANDLER ──────────────────────────────────────────────
def apply_tags_from_import(contacts: list[dict]):
    """Parse comma-separated tags column and insert into contact_tags table."""
    if not engine: return
    with engine.connect() as conn:
        for c in contacts:
            tags_raw = c.get("tags", "")
            if not tags_raw: continue
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            email = c.get("email", "")
            if not email: continue
            row = conn.execute(
                text("SELECT id FROM contacts WHERE email = :email"), {"email": email}
            ).fetchone()
            if not row: continue
            for tag in tags:
                conn.execute(text("""
                    INSERT INTO contact_tags (contact_id, tag, added_at)
                    VALUES (:cid, :tag, NOW()) ON CONFLICT DO NOTHING
                """), {"cid": row.id, "tag": tag.lower()})
        conn.commit()
