import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "doctalk.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT,
            title TEXT,
            pages INTEGER,
            words INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT,
            role TEXT,
            content TEXT,
            sources TEXT,
            top_passage TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES documents(id)
        )
    """)
    conn.commit()
    conn.close()

def save_document(doc_id, meta):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO documents (id, filename, title, pages, words)
        VALUES (?, ?, ?, ?, ?)
    """, (doc_id, meta["filename"], meta["title"], meta["pages"], meta["words"]))
    conn.commit()
    conn.close()

def save_message(doc_id, role, content, sources=None, top_passage=None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO chats (doc_id, role, content, sources, top_passage)
        VALUES (?, ?, ?, ?, ?)
    """, (
        doc_id, role, content,
        json.dumps(sources) if sources else None,
        json.dumps(top_passage) if top_passage else None
    ))
    conn.commit()
    conn.close()

def get_chat_history(doc_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT role, content, sources, top_passage
        FROM chats WHERE doc_id = ? ORDER BY created_at ASC
    """, (doc_id,)).fetchall()
    conn.close()
    history = []
    for row in rows:
        turn = {"role": row["role"], "content": row["content"]}
        if row["sources"]:
            turn["sources"] = json.loads(row["sources"])
        if row["top_passage"]:
            turn["top_passage"] = json.loads(row["top_passage"])
        history.append(turn)
    return history

def get_recent_documents(limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, filename, title, pages, words, uploaded_at
        FROM documents ORDER BY uploaded_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_chat(doc_id):
    conn = get_conn()
    conn.execute("DELETE FROM chats WHERE doc_id = ?", (doc_id,))
    conn.commit()
    conn.close()

def delete_document(doc_id):
    conn = get_conn()
    conn.execute("DELETE FROM chats WHERE doc_id = ?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()