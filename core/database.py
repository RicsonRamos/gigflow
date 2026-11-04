"""
core/database.py - Persistência Local em SQLite (100% Custo Zero)
Garante que vagas já analisadas não sejam notificadas repetidamente e
rastreia o histórico de propostas aprovadas, orçamentos e status no Notion.
"""

import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        platform TEXT NOT NULL,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        description TEXT,
        proposals_count INTEGER DEFAULT 0,
        match_score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'NEW',
        quote_gross REAL DEFAULT 0.0,
        quote_net REAL DEFAULT 0.0,
        delivery_days INTEGER DEFAULT 0,
        proposal_text TEXT,
        notion_page_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def is_job_seen(job_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_job(job: Dict[str, Any], match_score: int, quote: Dict[str, Any], proposal_text: str, status: str = "NEW"):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT OR REPLACE INTO jobs (
        id, platform, title, url, description, proposals_count,
        match_score, status, quote_gross, quote_net, delivery_days,
        proposal_text, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job["id"],
        job.get("platform", "99freelas"),
        job.get("title", ""),
        job.get("url", ""),
        job.get("description", ""),
        job.get("proposals_count", 0),
        match_score,
        status,
        quote.get("platform_bid_price", 0.0),
        quote.get("net_receivable", 0.0),
        quote.get("delivery_days", 0),
        proposal_text,
        now
    ))
    conn.commit()
    conn.close()

def update_job_status(job_id: str, status: str, notion_page_id: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    if notion_page_id:
        cursor.execute("UPDATE jobs SET status = ?, notion_page_id = ?, updated_at = ? WHERE id = ?", (status, notion_page_id, now, job_id))
    else:
        cursor.execute("UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?", (status, now, job_id))
    conn.commit()
    conn.close()

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def count_today_submitted_proposals() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM jobs 
        WHERE status = 'SENT' AND date(updated_at) = date('now')
    """)
    row = cursor.fetchone()
    count = row[0] if row else 0
    conn.close()
    return count

def get_pending_jobs(limit: int = 5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM jobs 
        WHERE status = 'NEW' 
        ORDER BY match_score DESC, created_at DESC 
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_database_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'NEW'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'SENT'")
    sent = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'SENT' AND date(updated_at) = date('now')")
    today_sent = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'DISCARDED'")
    discarded = cursor.fetchone()[0]

    conn.close()
    return {
        "total": total,
        "pending": pending,
        "sent": sent,
        "today_sent": today_sent,
        "discarded": discarded
    }

# Inicializa ao importar
init_db()
