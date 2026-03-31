import streamlit as st
import re
import json
import streamlit.components.v1 as components
from services.pdf_processor import extract_text_by_page, chunk_pages, get_pdf_metadata
from services.embedder import build_index, retrieve, retrieve_multi
from services.rag import answer_question, answer_cross_doc, answer_diff, summarize_document, suggest_followups
from services.exporter import export_chat_as_text, export_chat_as_pdf
from database.db import init_db, save_document, save_message, get_chat_history, get_recent_documents, clear_chat, delete_document

st.set_page_config(page_title="DocTalk", page_icon="◎", layout="wide",
                   initial_sidebar_state="expanded")
init_db()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Syne:wght@600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer { visibility: hidden; }
header { visibility: hidden; }
[data-testid="collapsedControl"],
[data-testid="collapsedControl"] *,
button[kind="header"],
button[kind="header"] * {
    visibility: visible !important; opacity: 1 !important; pointer-events: auto !important;
}
[data-testid="collapsedControl"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: fixed !important;
    top: 14px !important;
    left: 14px !important;
    z-index: 99999 !important;
    background: rgba(16,185,129,0.12) !important;
    border: 1px solid rgba(16,185,129,0.28) !important;
    border-radius: 8px !important;
    padding: 4px !important;
    backdrop-filter: blur(8px) !important;
    box-shadow: 0 0 16px rgba(16,185,129,0.2) !important;
    transition: all 0.2s !important;
}
[data-testid="collapsedControl"]:hover {
    background: rgba(16,185,129,0.22) !important;
    border-color: rgba(16,185,129,0.5) !important;
    box-shadow: 0 0 24px rgba(16,185,129,0.35) !important;
}
[data-testid="collapsedControl"] svg {
    display: block !important;
    fill: #10b981 !important;
    color: #10b981 !important;
}
.block-container { padding: 0 !important; max-width: 100% !important; }

            
/* ── VARIABLES ── */
:root {
    --bg0:      #0c0e17;
    --bg1:      #161b22;
    --panel:    rgba(14,18,28,0.82);
    --line:     rgba(255,255,255,0.09);
    --t0:       #e2e8f0;
    --t1:       #94a3b8;
    --t2:       #4b5563;
    --accent:   #10b981;
    --acc2:     #059669;
    --acc-glow: rgba(16,185,129,0.22);
    --blue:     #3b82f6;
    --amber:    #f59e0b;
    --red:      #ef4444;
}

/* ═══════════════════════════════════════
   KEYFRAME ANIMATIONS
═══════════════════════════════════════ */
@keyframes fadeInUp    { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeInLeft  { from{opacity:0;transform:translateX(-12px)} to{opacity:1;transform:translateX(0)} }
@keyframes fadeInRight { from{opacity:0;transform:translateX(12px)} to{opacity:1;transform:translateX(0)} }
@keyframes fadeIn      { from{opacity:0} to{opacity:1} }
@keyframes msgInLeft   { from{opacity:0;transform:translateX(-16px) translateY(6px)} to{opacity:1;transform:translateX(0) translateY(0)} }
@keyframes msgInRight  { from{opacity:0;transform:translateX(16px) translateY(6px)} to{opacity:1;transform:translateX(0) translateY(0)} }
@keyframes topbarIn    { from{opacity:0;transform:translateY(-10px)} to{opacity:1;transform:translateY(0)} }
@keyframes chipIn      { from{opacity:0;transform:translateY(10px) scale(0.88)} to{opacity:1;transform:translateY(0) scale(1)} }
@keyframes chipFloat   { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-3px)} }
@keyframes chipPulse   { 0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,0)} 30%{box-shadow:0 0 10px 2px rgba(16,185,129,0.18)} 60%,100%{box-shadow:0 0 0 0 rgba(16,185,129,0)} }
@keyframes floatY      { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)} }
@keyframes pulseGlow   { 0%,100%{box-shadow:0 0 6px 0 rgba(16,185,129,0.15)} 50%{box-shadow:0 0 22px 5px rgba(16,185,129,0.30)} }
@keyframes shimmer     { 0%{background-position:-400px 0} 100%{background-position:400px 0} }
@keyframes pdot        { 0%,60%,100%{transform:translateY(0);opacity:0.3} 30%{transform:translateY(-4px);opacity:1} }
@keyframes scanline    { 0%{transform:translateX(-100%)} 100%{transform:translateX(400%)} }
@keyframes borderPulse { 0%,100%{border-color:rgba(16,185,129,0.14)} 50%{border-color:rgba(16,185,129,0.35)} }
@keyframes dotBlink    { 0%,100%{opacity:0.4;transform:scale(1)} 50%{opacity:1;transform:scale(1.3)} }

/* ═══════════════════════════════════════
   GLOBAL BACKGROUND
═══════════════════════════════════════ */
.stApp {
    background-color: var(--bg0) !important;
    background-image:
        radial-gradient(ellipse at 10% 60%, rgba(16,185,129,0.07) 0%, transparent 45%),
        radial-gradient(ellipse at 88% 15%, rgba(59,130,246,0.06) 0%, transparent 40%),
        radial-gradient(ellipse at 50% 95%, rgba(129,140,248,0.04) 0%, transparent 35%) !important;
    color: var(--t0) !important;
}
.stApp * { color: var(--t0) !important; }

/* ── STICKY TOPBAR ROW ── */
div[data-testid="stHorizontalBlock"]:has(.topbar) {
    position: sticky !important;
    top: 0 !important;
    z-index: 999 !important;
    background: var(--bg0) !important;
    animation: topbarIn 0.4s ease both;
}

/* ── CHAT CONTAINER ── */
div[data-testid="stVerticalBlockBorderWrapper"][style*="overflow-y: auto"],
div[data-testid="stVerticalBlockBorderWrapper"][style*="overflow-y:auto"] {
    height: calc(100vh - 320px) !important;
    min-height: 220px !important;
}

/* ── TAB LABELS — bigger and more polished ── */
div[data-testid="stTabs"] { background: transparent !important; }
div[data-testid="stTabs"] button {
    font-family: 'Inter', sans-serif !important;
    font-size: 15px !important; font-weight: 600 !important;
    letter-spacing: 0.2px !important; color: var(--t2) !important;
    background: transparent !important; border-radius: 0 !important;
    padding: 12px 26px !important;
    transition: color 0.22s, background 0.22s !important;
}
div[data-testid="stTabs"] button:hover {
    color: var(--t1) !important;
    background: rgba(255,255,255,0.03) !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--t0) !important; font-weight: 700 !important; font-size: 15px !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: var(--accent) !important; height: 2px !important; }
div[data-testid="stTabs"] [data-baseweb="tab-border"] { background: rgba(255,255,255,0.06) !important; }

/* ═══════════════════════════════════════
   TOPBAR — premium redesign
═══════════════════════════════════════ */
.topbar {
    background: linear-gradient(135deg, rgba(10,13,22,0.98) 0%, rgba(8,11,18,1.0) 100%);
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border-bottom: 1px solid transparent;
    padding: 0 28px;
    height: 64px;
    display: flex; align-items: center; justify-content: space-between;
    width: 100%;
    position: relative;
    overflow: hidden;
    box-shadow: 0 2px 0 rgba(255,255,255,0.03), 0 8px 40px rgba(0,0,0,0.6);
    animation: topbarIn 0.45s cubic-bezier(0.22,1,0.36,1) both;
    animation: borderPulse 4s ease-in-out infinite;
}
/* animated gradient border bottom */
.topbar::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(16,185,129,0.6) 25%,
        rgba(59,130,246,0.5) 55%,
        rgba(139,92,246,0.4) 75%,
        transparent 100%);
    background-size: 400px 1px;
    animation: shimmer 4s linear infinite;
}
/* scanline highlight */
.topbar::before {
    content: '';
    position: absolute; top: 0; bottom: 0; left: 0;
    width: 80px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.025), transparent);
    animation: scanline 6s ease-in-out infinite;
    pointer-events: none;
}
.topbar-left { display: flex; align-items: center; gap: 20px; }
.topbar-brand {
    display: flex; align-items: center; gap: 10px;
    padding-right: 20px;
    border-right: 1px solid rgba(255,255,255,0.06);
}
.topbar-brand-icon {
    width: 32px; height: 32px; border-radius: 9px;
    background: linear-gradient(135deg, #10b981, #3b82f6);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px;
    box-shadow: 0 0 18px rgba(16,185,129,0.4), 0 2px 8px rgba(0,0,0,0.3);
    animation: pulseGlow 3s ease-in-out infinite;
}
.topbar-brand-name {
    font-family: 'Syne', sans-serif !important;
    font-size: 17px; font-weight: 800;
    color: #10b981 !important; letter-spacing: -0.4px;
}
/* Live indicator dot */
.topbar-live {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 9px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    color: #10b981 !important;
    background: rgba(16,185,129,0.08);
    border: 1px solid rgba(16,185,129,0.18);
    border-radius: 20px; padding: 2px 8px;
}
.topbar-live-dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: #10b981;
    animation: dotBlink 1.8s ease-in-out infinite;
}
.topbar-doc { display: flex; flex-direction: column; justify-content: center; gap: 1px; }
.topbar-title {
    font-family: 'Syne', sans-serif !important;
    font-size: 15px; font-weight: 700; color: var(--t0) !important;
    letter-spacing: -0.2px; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; max-width: 360px;
}
.topbar-file {
    font-size: 11px; color: var(--t2) !important;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 360px;
}
.topbar-chips { display: flex; gap: 5px; flex-wrap: wrap; align-items: center; }
.t-chip {
    font-size: 10px; font-weight: 600; color: var(--t1) !important;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 6px; padding: 4px 10px;
    transition: all 0.2s cubic-bezier(0.4,0,0.2,1); white-space: nowrap;
    position: relative; overflow: hidden;
}
.t-chip::after {
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent, rgba(16,185,129,0.06), transparent);
    transform: translateX(-100%);
    transition: transform 0.3s;
}
.t-chip:hover {
    background: rgba(16,185,129,0.09);
    border-color: rgba(16,185,129,0.28); color: #10b981 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(16,185,129,0.15);
}
.t-chip:hover::after { transform: translateX(100%); }

/* ═══════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: rgba(9,11,19,0.98) !important;
    border-right: 1px solid var(--line) !important;
    backdrop-filter: blur(16px) !important;
}
section[data-testid="stSidebar"] * { color: var(--t0) !important; }
.sb-brand { padding: 20px 16px 16px; border-bottom: 1px solid var(--line); display: flex; align-items: center; gap: 12px; }
.sb-logo {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, var(--accent), var(--blue));
    display: flex; align-items: center; justify-content: center;
    font-size: 17px; flex-shrink: 0;
    box-shadow: 0 0 16px var(--acc-glow), 0 4px 12px rgba(0,0,0,0.3);
}
.sb-name { font-family: 'Syne', sans-serif !important; font-size: 19px; font-weight: 800; color: var(--t0) !important; letter-spacing: -0.4px; }
.sb-sub { font-size: 10px; color: var(--t2) !important; margin-top: 1px; letter-spacing: 0.3px; }
.sb-label { padding: 14px 14px 5px; font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.8px; color: var(--t2) !important; }
.doc-item { padding: 10px 14px; border-left: 2px solid transparent; cursor: pointer; transition: all 0.18s; margin: 1px 0; border-radius: 0 8px 8px 0; }
.doc-item:hover { background: rgba(255,255,255,0.04); border-left-color: rgba(255,255,255,0.1); }
.doc-item.active { background: rgba(16,185,129,0.08); border-left-color: var(--accent); box-shadow: inset 0 0 0 1px rgba(16,185,129,0.12); }
.doc-item-name { font-size: 13px; font-weight: 500; color: var(--t0) !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-item.active .doc-item-name { color: var(--accent) !important; }
.doc-item-meta { font-size: 11px; color: var(--t2) !important; margin-top: 2px; }

/* ═══════════════════════════════════════
   CHAT
═══════════════════════════════════════ */
.chat-outer { max-width: 760px; margin: 0 auto; padding: 16px 20px 12px; }
.msg-wrap { display: flex; gap: 10px; margin-bottom: 8px; animation: msgInLeft 0.38s cubic-bezier(0.22,1,0.36,1) both; }
.msg-wrap-u { flex-direction: row-reverse; animation: msgInRight 0.38s cubic-bezier(0.22,1,0.36,1) both; }
.av {
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; flex-shrink: 0; margin-top: 2px;
    transition: transform 0.2s;
}
.av:hover { transform: scale(1.1); }
.av-u { background: rgba(51,65,85,0.8); border: 1px solid rgba(255,255,255,0.12); color: var(--t1) !important; }
.av-a {
    background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.28);
    color: var(--accent) !important; font-size: 15px;
    box-shadow: 0 0 10px rgba(16,185,129,0.15);
}
.bub {
    max-width: 78%; padding: 12px 16px; font-size: 14px; line-height: 1.75; border-radius: 18px;
    transition: transform 0.2s, box-shadow 0.2s;
}
.bub:hover { transform: translateY(-1px); }
.bub-u { background: rgba(51,65,85,0.55); border: 1px solid rgba(255,255,255,0.10); color: var(--t0) !important; border-radius: 18px 4px 18px 18px; backdrop-filter: blur(6px); }
.bub-u * { color: var(--t0) !important; }
.bub-a {
    background: rgba(16,185,129,0.07); border: 1px solid rgba(16,185,129,0.20);
    color: var(--t0) !important; border-radius: 4px 18px 18px 18px;
    box-shadow: 0 0 24px rgba(16,185,129,0.07), 0 2px 12px rgba(0,0,0,0.2);
    position: relative; overflow: hidden;
}
.bub-a::before { content:''; position:absolute; inset:0; background:radial-gradient(ellipse at top left,rgba(16,185,129,0.07),transparent 60%); pointer-events:none; }
.bub-a * { color: var(--t0) !important; }

.src-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.07); }
.src-p {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 10px; font-weight: 600; letter-spacing: 0.3px;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12);
    color: var(--t1) !important; border-radius: 6px; padding: 2px 8px;
    transition: all 0.15s; cursor: default;
}
.src-p:hover { background: rgba(16,185,129,0.1); border-color: rgba(16,185,129,0.3); color: #10b981 !important; transform: translateY(-1px); }
.src-p::before { content:''; display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--accent); flex-shrink:0; }

.excerpt {
    max-width: 74%; margin-left: 42px; margin-bottom: 12px;
    background: rgba(245,158,11,0.06); border-left: 2px solid var(--amber);
    border-radius: 0 10px 10px 0; padding: 9px 14px;
    font-size: 13px; font-style: italic; color: var(--t1) !important; line-height: 1.65;
    backdrop-filter: blur(4px);
    transition: background 0.2s, border-color 0.2s;
    animation: fadeIn 0.4s ease both;
}
.excerpt:hover { background: rgba(245,158,11,0.1); border-left-color: #fbbf24; }
.excerpt-lbl { font-size: 9px; font-weight: 700; font-style: normal; text-transform: uppercase; letter-spacing: 1px; color: var(--amber) !important; margin-bottom: 5px; }

/* ── FOLLOW-UP CHIPS — floating glowing cards ── */
.followup-section {
    max-width: 760px; margin: 8px auto 4px; padding: 0 20px 0 52px;
    animation: fadeInUp 0.4s ease both;
}
.followup-label {
    font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;
    color: var(--t2) !important; margin-bottom: 8px; display: block;
}
/* The "Ask Next" strip container */
.fu-strip {
    background: rgba(10,13,22,0.7);
    border: 1px solid rgba(16,185,129,0.14);
    border-radius: 16px;
    padding: 12px 14px 10px;
    backdrop-filter: blur(12px);
    position: relative; overflow: hidden;
    animation: fadeInUp 0.5s ease both;
}
.fu-strip::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(16,185,129,0.4), rgba(59,130,246,0.3), transparent);
}
.fu-label-row {
    display: flex; align-items: center; gap: 7px; margin-bottom: 10px;
}
.fu-label-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #10b981;
    animation: dotBlink 2s ease-in-out infinite;
}
.fu-label-txt {
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.6px; color: #10b981 !important;
}

/* ── PROCESSING CARD ── */
.proc-card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 22px 26px; backdrop-filter: blur(10px); box-shadow: 0 4px 20px rgba(0,0,0,0.3); margin-bottom: 12px; animation: fadeInUp 0.3s ease both; }
.proc-title-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.4px; color: var(--t2) !important; margin-bottom: 4px; }
.proc-doc-name { font-size: 15px; font-weight: 600; color: var(--t0) !important; margin-bottom: 18px; border-bottom: 1px solid var(--line); padding-bottom: 14px; }
.proc-step { display: flex; align-items: center; gap: 12px; padding: 8px 0; font-size: 13px; color: var(--t2) !important; transition: all 0.25s; }
.proc-step.done { color: var(--accent) !important; }
.proc-step.active { color: var(--t0) !important; font-weight: 500; }
.proc-step-icon { font-size: 16px; width: 22px; text-align: center; }
.proc-dots { display: flex; gap: 3px; margin-left: auto; }
.proc-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--accent); opacity: 0.4; animation: pdot 1.2s infinite; }
.proc-dot:nth-child(2) { animation-delay: 0.2s; }
.proc-dot:nth-child(3) { animation-delay: 0.4s; }

/* ── DIFF BLOCKS ── */
.diff-badge-a { display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;padding:3px 10px;border-radius:7px;background:rgba(96,165,250,0.10);border:1px solid rgba(96,165,250,0.28);color:#60a5fa !important; }
.diff-badge-a::before { content:'';width:6px;height:6px;border-radius:50%;background:#60a5fa;display:inline-block; }
.diff-badge-b { display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;padding:3px 10px;border-radius:7px;background:rgba(251,146,60,0.10);border:1px solid rgba(251,146,60,0.28);color:#fb923c !important; }
.diff-badge-b::before { content:'';width:6px;height:6px;border-radius:50%;background:#fb923c;display:inline-block; }
.diff-added-block   { border-left:3px solid var(--accent);background:rgba(16,185,129,0.07);border-radius:0 10px 10px 0;padding:10px 14px;margin:6px 0; }
.diff-removed-block { border-left:3px solid var(--red);background:rgba(239,68,68,0.07);border-radius:0 10px 10px 0;padding:10px 14px;margin:6px 0; }
.diff-changed-block { border-left:3px solid var(--amber);background:rgba(245,158,11,0.07);border-radius:0 10px 10px 0;padding:10px 14px;margin:6px 0; }

/* ── LANDING ── */
.landing { min-height:93vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:40px 24px;text-align:center;animation:fadeIn 0.6s ease both; }
.stage-header { text-align:center;padding:52px 24px 28px;animation:fadeInUp 0.4s ease both; }
.stage-h2 { font-family:'Syne',sans-serif !important;font-size:30px;font-weight:800;color:var(--t0) !important;letter-spacing:-0.8px;margin-bottom:10px; }
.stage-sub { font-size:15px;color:var(--t1) !important;line-height:1.6; }
.file-card { background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 18px;display:flex;align-items:center;gap:14px;margin-bottom:8px;backdrop-filter:blur(8px);box-shadow:0 2px 8px rgba(0,0,0,0.25);animation:fadeInUp 0.3s ease both;transition:border-color 0.2s,transform 0.2s; }
.file-card:hover { border-color:rgba(16,185,129,0.22);transform:translateX(3px); }
.file-name { font-size:14px;font-weight:500;color:var(--t0) !important; }
.file-size { font-size:12px;color:var(--t2) !important;margin-top:2px; }

/* ── STREAMLIT OVERRIDES ── */
div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important; color: var(--t0) !important;
    font-size: 14px !important; padding: 11px 16px !important;
    font-family: 'Inter', sans-serif !important; transition: all 0.22s !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important; background: rgba(16,185,129,0.04) !important;
    box-shadow: 0 0 0 3px rgba(16,185,129,0.10) !important;
}
div[data-testid="stTextInput"] input::placeholder { color: var(--t2) !important; }
div[data-testid="stButton"] button {
    border-radius: 10px !important; font-weight: 600 !important;
    font-size: 13px !important; font-family: 'Inter', sans-serif !important;
    transition: all 0.18s cubic-bezier(0.4,0,0.2,1) !important;
}
div[data-testid="stButton"] button[kind="primary"] {
    background: var(--accent) !important; color: #052e16 !important; font-weight: 700 !important;
    border: none !important; box-shadow: 0 0 20px rgba(16,185,129,0.28), 0 4px 12px rgba(0,0,0,0.2) !important;
}
div[data-testid="stButton"] button[kind="primary"] p,
div[data-testid="stButton"] button[kind="primary"] * { color: #052e16 !important; }
div[data-testid="stButton"] button[kind="primary"]:hover {
    background: #059669 !important; transform: translateY(-2px) !important;
    box-shadow: 0 0 32px rgba(16,185,129,0.45) !important;
}
div[data-testid="stButton"] button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important; color: var(--t1) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.08) !important; border-color: var(--accent) !important;
    color: var(--t0) !important; transform: translateY(-1px) !important;
}
div[data-testid="stFileUploader"] section {
    background: rgba(255,255,255,0.02) !important; border: 1.5px dashed rgba(255,255,255,0.10) !important;
    border-radius: 14px !important; transition: all 0.22s !important; backdrop-filter: blur(6px) !important;
}
div[data-testid="stFileUploader"] section:hover {
    border-color: var(--accent) !important; background: rgba(16,185,129,0.03) !important;
    box-shadow: 0 0 20px rgba(16,185,129,0.08) !important;
}
div[data-testid="stFileUploader"] * { color: var(--t1) !important; }
div[data-testid="stExpander"] { background: var(--panel) !important; border: 1px solid var(--line) !important; border-radius: 12px !important; backdrop-filter: blur(8px) !important; transition: border-color 0.2s !important; }
div[data-testid="stExpander"]:hover { border-color: rgba(16,185,129,0.15) !important; }
div[data-testid="stExpander"] summary { color: var(--t0) !important; }
div[data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 700 !important; color: var(--t0) !important; }
div[data-testid="stMetricLabel"] { color: var(--t2) !important; font-size: 11px !important; }
div[data-testid="stDownloadButton"] button {
    background: rgba(255,255,255,0.04) !important; color: var(--t1) !important;
    border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 9px !important;
    font-size: 12px !important; transition: all 0.18s !important;
}
div[data-testid="stDownloadButton"] button:hover {
    border-color: var(--accent) !important; color: var(--accent) !important;
    background: rgba(16,185,129,0.07) !important; transform: translateY(-1px) !important;
}
div[data-testid="stAlert"] { background: var(--panel) !important; border-radius: 10px !important; border: 1px solid var(--line) !important; }
div[data-testid="stMarkdownContainer"] * { color: var(--t1) !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
div[class*="stSpinner"] * { color: var(--accent) !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.14); }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def render_md(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    lines = text.split('\n')
    out = []
    for line in lines:
        l = line.strip()
        if l.startswith(('* ', '- ')):
            out.append(f'<li>{l[2:]}</li>')
        elif l.startswith('### '):
            out.append(f'<h4 style="font-size:14px;font-weight:600;margin:14px 0 5px">{l[4:]}</h4>')
        elif l.startswith('## '):
            out.append(f'<h3 style="font-size:16px;font-weight:700;margin:18px 0 6px">{l[3:]}</h3>')
        elif l == '':
            out.append('<br>')
        else:
            out.append(f'<p style="margin:3px 0">{l}</p>')
    result = '\n'.join(out)
    result = re.sub(r'(<li>.*?</li>\n?)+',
        lambda m: f'<ul style="padding-left:18px;margin:8px 0;list-style:disc">{m.group()}</ul>',
        result, flags=re.DOTALL)
    return result

def compute_page_hits(chat):
    hits = {}
    for turn in chat:
        if turn.get("sources"):
            for s in turn["sources"]:
                p = s.get("page")
                if p:
                    hits[p] = hits.get(p, 0) + 1
    return hits

def render_floating_map(hits, total_pages, chat):
    """
    Inject a floating citation-heatmap panel into the parent page purely via JS.
    Zero visible HTML rendered inside the Streamlit iframe — no overlap possible.
    """
    total_hits  = sum(hits.values())
    cited_pages = len(hits)
    hot_page    = max(hits, key=hits.get) if hits else 0
    coverage    = round(cited_pages / total_pages * 100) if total_pages else 0
    hot_label   = f"p.{hot_page}" if hot_page else "-"

    # Build cells as a JS array literal: [{ page, intensity, hits_lbl }, ...]
    cells_js = "["
    for page in range(1, total_pages + 1):
        count     = hits.get(page, 0)
        intensity = min(count, 3)
        hits_lbl  = f"{count}x" if count > 0 else "-"
        cells_js += f'{{"p":{page},"i":{intensity},"h":"{hits_lbl}"}},'
    cells_js += "]"

    empty_msg = "" if chat else "Ask questions to see which pages get cited most"

    js = f"""
(function() {{

  var CELLS      = {cells_js};
  var TOTAL_PGS  = {total_pages};
  var CITED_PGS  = {cited_pages};
  var COVERAGE   = {coverage};
  var TOTAL_HITS = {total_hits};
  var HOT_LABEL  = "{hot_label}";
  var EMPTY_MSG  = "{empty_msg}";

  var pd = window.parent.document;

  /* ── 1. Inject CSS once ─────────────────────────────────────── */
  if (!pd.getElementById('dtm-style')) {{
    var css = pd.createElement('style');
    css.id  = 'dtm-style';
    css.textContent = `
      @keyframes dtpulse {{ 0%,100%{{opacity:.5;transform:scale(1)}} 50%{{opacity:1;transform:scale(1.4)}} }}
      @keyframes dtSlideIn {{ from{{right:-360px}} to{{right:0}} }}

      #dtm-btn {{
        position:fixed; right:0; top:50%; transform:translateY(-50%);
        z-index:9999;
        writing-mode:vertical-rl; text-orientation:mixed;
        background:linear-gradient(180deg,#10b981,#059669);
        color:#052e16 !important;
        font-family:Inter,sans-serif; font-size:11px; font-weight:700;
        letter-spacing:1.8px; text-transform:uppercase;
        padding:22px 9px; border-radius:10px 0 0 10px;
        cursor:pointer; border:none; outline:none;
        box-shadow:-3px 0 24px rgba(16,185,129,0.45);
        transition:padding 0.22s,box-shadow 0.22s;
        display:flex; flex-direction:column; align-items:center; gap:9px;
      }}
      #dtm-btn:hover {{
        padding-left:15px;
        box-shadow:-6px 0 36px rgba(16,185,129,0.65);
      }}
      #dtm-btn .dtm-dot {{
        width:7px; height:7px; border-radius:50%;
        background:rgba(5,46,22,0.55);
        animation:dtpulse 2s ease-in-out infinite;
        flex-shrink:0;
      }}
      #dtm-btn span {{ pointer-events:none; }}

      #dtm-panel {{
        position:fixed; right:-360px; top:64px; bottom:0;
        width:340px; z-index:9998;
        background:rgba(6,9,18,0.98);
        border-left:1px solid rgba(16,185,129,0.22);
        backdrop-filter:blur(32px);
        box-shadow:-10px 0 60px rgba(0,0,0,0.75);
        transition:right 0.32s cubic-bezier(0.4,0,0.2,1);
        overflow-y:auto; overflow-x:hidden;
        padding:18px 15px 32px;
        font-family:Inter,sans-serif;
      }}
      #dtm-panel::-webkit-scrollbar {{ width:3px; }}
      #dtm-panel::-webkit-scrollbar-thumb {{ background:rgba(255,255,255,0.07);border-radius:2px; }}

      #dtm-panel .dtm-head {{
        display:flex; align-items:center; justify-content:space-between;
        margin-bottom:14px; padding-bottom:11px;
        border-bottom:1px solid rgba(255,255,255,0.07);
      }}
      #dtm-panel .dtm-title {{
        font-size:10px; font-weight:700; text-transform:uppercase;
        letter-spacing:1.5px; color:#10b981;
      }}
      #dtm-panel .dtm-legend {{
        display:flex; align-items:center; gap:5px;
        font-size:9px; color:#4b5563;
        background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.06);
        border-radius:5px; padding:3px 7px;
      }}
      #dtm-panel .dtm-lbar {{
        width:38px; height:6px; border-radius:3px;
        background:linear-gradient(to right,#10b981,#3b82f6,#8b5cf6);
      }}
      #dtm-panel .dtm-close {{
        width:24px; height:24px; border-radius:6px;
        background:rgba(255,255,255,0.05);
        border:1px solid rgba(255,255,255,0.09);
        color:#94a3b8; font-size:14px; cursor:pointer;
        display:flex; align-items:center; justify-content:center;
        transition:all 0.15s; line-height:1;
      }}
      #dtm-panel .dtm-close:hover {{ background:rgba(239,68,68,0.18);color:#ef4444;border-color:rgba(239,68,68,0.3); }}

      #dtm-panel .dtm-grid {{
        display:grid;
        grid-template-columns:repeat(auto-fill,minmax(36px,1fr));
        gap:4px; margin-bottom:14px;
      }}
      #dtm-panel .dtm-cell {{
        aspect-ratio:1; border-radius:6px;
        display:flex; flex-direction:column;
        align-items:center; justify-content:center;
        cursor:default; transition:transform 0.13s cubic-bezier(0.34,1.56,0.64,1);
        position:relative;
      }}
      #dtm-panel .dtm-cell:hover {{ transform:scale(1.22); z-index:2; }}
      #dtm-panel .dtm-cell .pn {{ font-size:10px; font-weight:700; line-height:1; }}
      #dtm-panel .dtm-cell .ph {{ font-size:7px; font-weight:500; margin-top:2px; opacity:.75; }}
      #dtm-panel .dtm-i0 {{ background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);color:#374151 !important; }}
      #dtm-panel .dtm-i1 {{ background:rgba(16,185,129,0.18);border:1px solid rgba(16,185,129,0.32);color:#10b981 !important; }}
      #dtm-panel .dtm-i2 {{ background:rgba(59,130,246,0.25);border:1px solid rgba(59,130,246,0.40);color:#93c5fd !important; }}
      #dtm-panel .dtm-i3 {{ background:rgba(139,92,246,0.30);border:1px solid rgba(139,92,246,0.50);color:#c4b5fd !important;box-shadow:0 0 9px rgba(139,92,246,0.3); }}

      #dtm-panel .dtm-stats {{
        display:flex; border-top:1px solid rgba(255,255,255,0.06);
        padding-top:12px; margin-top:4px;
      }}
      #dtm-panel .dtm-stat {{
        flex:1; text-align:center; padding:0 4px;
        border-right:1px solid rgba(255,255,255,0.05);
      }}
      #dtm-panel .dtm-stat:last-child {{ border-right:none; }}
      #dtm-panel .dtm-sv {{ font-size:15px; font-weight:700; color:#e2e8f0 !important; line-height:1; }}
      #dtm-panel .dtm-sl {{ font-size:7px; color:#4b5563 !important; text-transform:uppercase; letter-spacing:1px; margin-top:3px; }}
      #dtm-panel .dtm-empty {{
        text-align:center; padding:36px 12px; color:#374151;
        font-size:12px; line-height:1.6;
      }}
    `;
    pd.head.appendChild(css);
  }}

  /* ── 2. Build / rebuild button ─────────────────────────────── */
  var btn = pd.getElementById('dtm-btn');
  if (!btn) {{
    btn = pd.createElement('button');
    btn.id = 'dtm-btn';
    btn.innerHTML = '<div class="dtm-dot"></div><span>Map</span>';
    btn.addEventListener('click', dtmToggle);
    pd.body.appendChild(btn);
  }}
  btn.style.display = '';

  /* ── 3. Build / rebuild panel ──────────────────────────────── */
  var panel = pd.getElementById('dtm-panel');
  var wasOpen = panel && panel.classList.contains('open');
  if (!panel) {{
    panel = pd.createElement('div');
    panel.id = 'dtm-panel';
    pd.body.appendChild(panel);
  }}

  // Build grid HTML
  var gridHTML = '';
  if (CELLS.length === 0 || EMPTY_MSG) {{
    gridHTML = '<div class="dtm-empty">' + (EMPTY_MSG || 'No pages to display') + '</div>';
  }} else {{
    gridHTML = '<div class="dtm-grid">';
    CELLS.forEach(function(c) {{
      gridHTML += '<div class="dtm-cell dtm-i' + c.i + '" title="Page ' + c.p + ' \u2014 cited ' + c.h + '">'
               +   '<span class="pn">' + c.p + '</span>'
               +   '<span class="ph">' + c.h + '</span>'
               + '</div>';
    }});
    gridHTML += '</div>';
  }}

  panel.innerHTML =
    '<div class="dtm-head">'
  +   '<div class="dtm-title">Citation Heatmap</div>'
  +   '<div class="dtm-legend">High <div class="dtm-lbar"></div> Low</div>'
  +   '<button class="dtm-close" title="Close">\u00d7</button>'
  + '</div>'
  + gridHTML
  + '<div class="dtm-stats">'
  +   '<div class="dtm-stat"><div class="dtm-sv">' + TOTAL_PGS  + '</div><div class="dtm-sl">Pages</div></div>'
  +   '<div class="dtm-stat"><div class="dtm-sv">' + CITED_PGS  + '</div><div class="dtm-sl">Cited</div></div>'
  +   '<div class="dtm-stat"><div class="dtm-sv">' + COVERAGE   + '%</div><div class="dtm-sl">Cover</div></div>'
  +   '<div class="dtm-stat"><div class="dtm-sv">' + TOTAL_HITS + '</div><div class="dtm-sl">Hits</div></div>'
  +   '<div class="dtm-stat"><div class="dtm-sv">' + HOT_LABEL  + '</div><div class="dtm-sl">Hot</div></div>'
  + '</div>';

  // Re-wire close button
  panel.querySelector('.dtm-close').addEventListener('click', dtmClose);

  // Restore open state across Streamlit reruns
  if (wasOpen) {{
    panel.classList.add('open');
    panel.style.right = '0';
    btn.style.right = '340px';
  }}

  /* ── 4. Toggle logic ───────────────────────────────────────── */
  function dtmToggle() {{
    if (panel.classList.contains('open')) {{ dtmClose(); }}
    else {{ dtmOpen(); }}
  }}
  function dtmOpen() {{
    panel.classList.add('open');
    panel.style.right  = '0';
    btn.style.right = '340px';
  }}
  function dtmClose() {{
    panel.classList.remove('open');
    panel.style.right  = '-360px';
    btn.style.right = '0';
  }}

  // Expose on parent for cross-iframe calls
  pd.dtmClose = dtmClose;

}})();
"""

    components.html(f"<script>{js}</script>", height=0, scrolling=False)



# ── Session init ──────────────────────────────────────────────────────────────
for k, v in {
    "documents": {}, "active_doc": None, "staged": [],
    "show_about_landing": False,
    "cross_doc_mode": False, "cross_doc_chat": [],
    "diff_mode": False, "diff_chat": [],
    "diff_doc_a": None, "diff_doc_b": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
      <div class="sb-logo">◎</div>
      <div><div class="sb-name">DocTalk</div><div class="sb-sub">Multi-Vector Retrieval Engine</div></div>
    </div>""", unsafe_allow_html=True)
    st.markdown('<div style="padding:14px 14px 8px"><span style="font-size:13px;font-weight:600;color:#e2e8f0">Neural Document Index</span></div>', unsafe_allow_html=True)

    sb_up = st.file_uploader("PDF", type=["pdf"], accept_multiple_files=True,
                              label_visibility="collapsed", key="sb_up")
    if sb_up:
        st.session_state.staged = sb_up
        st.session_state.active_doc = None
        st.rerun()

    if st.session_state.documents:
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        for did, d in list(st.session_state.documents.items()):
            is_a = st.session_state.active_doc == did
            cls  = "doc-item active" if is_a else "doc-item"
            st.markdown(f"""
            <div class="{cls}" style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
              <div style="display:flex;align-items:flex-start;gap:8px;min-width:0">
                <span style="font-size:14px;flex-shrink:0;margin-top:1px">📄</span>
                <div style="min-width:0">
                  <div class="doc-item-name">{d['meta']['title'][:24]}</div>
                  <div class="doc-item-meta" style="color:{'#10b981' if is_a else '#4b5563'}">Indexed · {d['meta']['pages']}p</div>
                </div>
              </div>
              <span style="color:{'#10b981' if is_a else '#6b7280'};font-size:14px">&#10003;</span>
            </div>""", unsafe_allow_html=True)
            if not is_a:
                c1, c2 = st.columns([3, 1])
                with c1:
                    if st.button("Open", key=f"op_{did}", use_container_width=True):
                        st.session_state.active_doc = did; st.rerun()
                with c2:
                    if st.button("✕", key=f"rm_{did}", use_container_width=True):
                        delete_document(did); del st.session_state.documents[did]
                        rem = list(st.session_state.documents.keys())
                        st.session_state.active_doc = rem[0] if rem else None; st.rerun()
        if st.button("＋ Upload new document", use_container_width=True, key="new_doc"):
            st.session_state.active_doc = None; st.session_state.staged = []; st.rerun()

    recent   = get_recent_documents(5)
    unloaded = [r for r in recent if r["id"] not in st.session_state.documents]
    if unloaded:
        st.markdown('<div class="sb-label" style="margin-top:8px">Recent</div>', unsafe_allow_html=True)
        for r in unloaded:
            st.markdown(f"""
            <div class="doc-item" style="display:flex;align-items:center;gap:8px">
              <span style="font-size:13px">📎</span>
              <div><div class="doc-item-name">{r['title'][:26]}</div><div class="doc-item-meta">{r['uploaded_at'][:10]}</div></div>
            </div>""", unsafe_allow_html=True)

    if st.session_state.active_doc and st.session_state.active_doc in st.session_state.documents:
        d = st.session_state.documents[st.session_state.active_doc]
        if d["chat"]:
            st.markdown('<div class="sb-label" style="margin-top:8px">Export</div>', unsafe_allow_html=True)
            e1, e2 = st.columns(2)
            with e1:
                st.download_button("TXT", data=export_chat_as_text(d["meta"]["title"], d["chat"]).encode(),
                    file_name=f"doctalk_{d['meta']['title'][:16]}.txt", mime="text/plain", use_container_width=True)
            with e2:
                st.download_button("PDF", data=export_chat_as_pdf(d["meta"]["title"], d["chat"]),
                    file_name=f"doctalk_{d['meta']['title'][:16]}.pdf", mime="application/pdf", use_container_width=True)

    if len(st.session_state.documents) >= 2:
        st.markdown("""<div style="margin:12px 8px 0;padding:10px 12px;background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.14);border-radius:10px"><div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#10b981;margin-bottom:8px">Multi-document</div></div>""", unsafe_allow_html=True)
        if st.session_state.cross_doc_mode:
            if st.button("← Back to single doc", key="exit_cross", use_container_width=True):
                st.session_state.cross_doc_mode = False; st.rerun()
        elif st.session_state.diff_mode:
            if st.button("← Back to single doc", key="exit_diff", use_container_width=True):
                st.session_state.diff_mode = False; st.rerun()
        else:
            if st.button("🔗 Cross-doc Q&A", key="enter_cross", use_container_width=True, type="primary"):
                st.session_state.cross_doc_mode = True; st.rerun()
            if st.button("🔀 Compare / Diff", key="enter_diff", use_container_width=True):
                st.session_state.diff_mode = True; st.session_state.diff_chat = []
                doc_ids = list(st.session_state.documents.keys())
                st.session_state.diff_doc_a = doc_ids[0]; st.session_state.diff_doc_b = doc_ids[1]; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
staged = st.session_state.staged
active = st.session_state.active_doc

# ── CROSS-DOC VIEW ────────────────────────────────────────────────────────────
if st.session_state.cross_doc_mode and len(st.session_state.documents) >= 2:
    # Remove floating map from parent DOM when in cross-doc mode
    components.html("""<script>
    (function(){try{
      var pd=window.parent.document;
      var b=pd.getElementById('dtm-btn');
      var p=pd.getElementById('dtm-panel');
      if(b) b.style.display='none';
      if(p){ p.classList.remove('open'); p.style.right='-360px'; }
    }catch(e){}}());
    </script>""", height=0)
    DOC_COLORS = [
        ("#60a5fa","rgba(96,165,250,0.12)","rgba(96,165,250,0.3)"),
        ("#a78bfa","rgba(167,139,250,0.12)","rgba(167,139,250,0.3)"),
        ("#fb923c","rgba(251,146,60,0.12)","rgba(251,146,60,0.3)"),
        ("#f472b6","rgba(244,114,182,0.12)","rgba(244,114,182,0.3)"),
        ("#facc15","rgba(250,204,21,0.12)","rgba(250,204,21,0.3)"),
    ]
    doc_ids    = list(st.session_state.documents.keys())
    color_map  = {did: DOC_COLORS[i % len(DOC_COLORS)] for i, did in enumerate(doc_ids)}
    titles_map = {did: st.session_state.documents[did]["meta"]["title"] for did in doc_ids}

    tb1, tb2 = st.columns([1, 10])
    with tb1:
        if st.button("← Home", key="cross_home_btn", use_container_width=True):
            st.session_state.cross_doc_mode = False; st.rerun()
    with tb2:
        doc_chips = "".join(f'<span class="t-chip" style="border-color:{color_map[did][2]};color:{color_map[did][0]}">&#9679; {titles_map[did][:22]}</span>' for did in doc_ids)
        st.markdown(f"""
        <div class="topbar">
          <div class="topbar-left">
            <div class="topbar-brand"><div class="topbar-brand-icon">&#9711;</div><span class="topbar-brand-name">DocTalk</span></div>
            <div class="topbar-doc">
              <div class="topbar-title">Cross-document Q&amp;A</div>
              <div class="topbar-file">Querying {len(doc_ids)} documents simultaneously</div>
            </div>
          </div>
          <div class="topbar-chips">{doc_chips}</div>
        </div>""", unsafe_allow_html=True)

    legend_pills = "".join(f'<span style="font-size:11px;font-weight:600;padding:3px 11px;border-radius:20px;background:{color_map[did][1]};border:1px solid {color_map[did][2]};color:{color_map[did][0]}">&#9679; {titles_map[did][:30]}</span>' for did in doc_ids)
    st.markdown(f"""
    <div style="max-width:740px;margin:10px auto 4px;padding:0 20px">
      <div style="background:rgba(10,12,22,0.8);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:10px 18px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <span style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#475569;margin-right:4px">Sources</span>
        {legend_pills}
      </div>
    </div>""", unsafe_allow_html=True)

    cross_chat = st.session_state.cross_doc_chat
    if not cross_chat:
        st.markdown("""<div style="max-width:740px;margin:8px auto;padding:0 20px"><div style="background:#0d1117;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:12px 18px"><div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#475569;margin-bottom:10px">Try asking across all documents</div>""", unsafe_allow_html=True)
        cq1, cq2 = st.columns(2)
        for i, sq in enumerate(["What do these documents have in common?","How do these documents differ?","What are the key conclusions across all?","Which covers this topic most thoroughly?"]):
            col = cq1 if i % 2 == 0 else cq2
            if col.button(sq, key=f"csq{i}", use_container_width=True):
                st.session_state["pf_cross"] = sq; st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)

    cross_container = st.container(height=520, border=False)
    with cross_container:
        st.markdown('<div class="chat-outer">', unsafe_allow_html=True)
        for turn in cross_chat:
            is_u     = turn["role"] == "user"
            av_cls   = "av av-u" if is_u else "av av-a"
            bub_cls  = "bub bub-u" if is_u else "bub bub-a"
            wrap_cls = "msg-wrap msg-wrap-u" if is_u else "msg-wrap"
            body     = turn["content"].replace("\n","<br>") if is_u else render_md(turn["content"])
            srcs_html = ""
            if not is_u and turn.get("sources"):
                pills = ""
                for s in turn["sources"]:
                    ct,cb,cbd = color_map.get(s["doc_id"],("#94a3b8","rgba(148,163,184,0.1)","rgba(148,163,184,0.25)"))
                    st_t = titles_map.get(s["doc_id"],s["doc_id"])[:18]
                    pills += f'<span style="font-size:10px;font-weight:600;background:{cb};border:1px solid {cbd};color:{ct};border-radius:20px;padding:2px 9px">&#9679; {st_t} p.{s["page"]}</span>'
                srcs_html = f'<div class="src-row">{pills}</div>'
            st.markdown(f'<div class="chat-outer" style="padding:2px 20px"><div class="{wrap_cls}"><div class="{av_cls}">{"U" if is_u else "&#9711;"}</div><div class="{bub_cls}">{body}{srcs_html}</div></div></div>', unsafe_allow_html=True)
            if not is_u and turn.get("top_passage"):
                p = turn["top_passage"]
                ct,cb,cbd = color_map.get(p["doc_id"],("#fbbf24","rgba(251,191,36,0.08)","rgba(251,191,36,0.3)"))
                st_t = titles_map.get(p["doc_id"],p["doc_id"])[:24]
                st.markdown(f'<div style="max-width:740px;margin:0 auto;padding:0 20px"><div class="excerpt" style="border-left-color:{ct}"><div class="excerpt-lbl" style="color:{ct}">{st_t} &middot; Page {p["page"]}</div>&ldquo;{p["text"][:220]}...&rdquo;</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Input — form so Enter submits and field clears ─────────────────────────
    prefill_cross = st.session_state.pop("pf_cross", "")
    with st.form(key="cross_form", clear_on_submit=True):
        ci1, ci2, ci3 = st.columns([7, 1, 1])
        with ci1:
            cross_input = st.text_input("cq", value=prefill_cross, placeholder="Ask anything across all your documents...", label_visibility="collapsed", key="cross_qi")
        with ci2:
            cross_send = st.form_submit_button("Ask &#8594;", type="primary", use_container_width=True)
        with ci3:
            cross_clear_btn = st.form_submit_button("&#128465; Clear", use_container_width=True)

    if cross_clear_btn:
        st.session_state.cross_doc_chat = []; st.rerun()

    if cross_send and cross_input.strip():
        q = cross_input.strip()
        cross_chat.append({"role":"user","content":q})
        with st.spinner("Searching..."):
            retrieved = retrieve_multi(q, st.session_state.documents, top_k_per_doc=3, global_top_k=8)
        if not retrieved:
            cross_chat.append({"role":"assistant","content":"I couldn't find relevant content across your documents.","sources":[],"top_passage":None})
        else:
            with st.spinner("Synthesising..."):
                ans = answer_cross_doc(q, retrieved, chat_history=cross_chat[:-1])
            sources = [{"doc_id":r["doc_id"],"page":r["page"],"score":r["score"]} for r in retrieved]
            cross_chat.append({"role":"assistant","content":ans,"sources":sources,"top_passage":retrieved[0]})
        st.session_state.cross_doc_chat = cross_chat; st.rerun()

    # handle prefill from starter chips (runs after form clears)
    if prefill_cross and not cross_send:
        q = prefill_cross.strip()
        cross_chat.append({"role":"user","content":q})
        with st.spinner("Searching..."):
            retrieved = retrieve_multi(q, st.session_state.documents, top_k_per_doc=3, global_top_k=8)
        if not retrieved:
            cross_chat.append({"role":"assistant","content":"I couldn't find relevant content across your documents.","sources":[],"top_passage":None})
        else:
            with st.spinner("Synthesising..."):
                ans = answer_cross_doc(q, retrieved, chat_history=cross_chat[:-1])
            sources = [{"doc_id":r["doc_id"],"page":r["page"],"score":r["score"]} for r in retrieved]
            cross_chat.append({"role":"assistant","content":ans,"sources":sources,"top_passage":retrieved[0]})
        st.session_state.cross_doc_chat = cross_chat; st.rerun()

# ── DIFF VIEW ─────────────────────────────────────────────────────────────────
elif st.session_state.diff_mode and len(st.session_state.documents) >= 2:
    # Remove floating map from parent DOM when in diff mode
    components.html("""<script>
    (function(){try{
      var pd=window.parent.document;
      var b=pd.getElementById('dtm-btn');
      var p=pd.getElementById('dtm-panel');
      if(b) b.style.display='none';
      if(p){ p.classList.remove('open'); p.style.right='-360px'; }
    }catch(e){}}());
    </script>""", height=0)
    doc_ids = list(st.session_state.documents.keys())
    titles  = {did: st.session_state.documents[did]["meta"]["title"] for did in doc_ids}
    if len(doc_ids) >= 3:
        sel1, sel2, sel3 = st.columns([1, 4, 4])
        with sel1:
            if st.button("&#8592; Back", key="diff_back", use_container_width=True): st.session_state.diff_mode = False; st.rerun()
        with sel2:
            opt_a = st.selectbox("Document A", doc_ids, index=doc_ids.index(st.session_state.diff_doc_a) if st.session_state.diff_doc_a in doc_ids else 0, format_func=lambda x: titles[x], key="sel_doc_a"); st.session_state.diff_doc_a = opt_a
        with sel3:
            remaining = [d for d in doc_ids if d != st.session_state.diff_doc_a]
            opt_b = st.selectbox("Document B", remaining, index=0 if st.session_state.diff_doc_b not in remaining else remaining.index(st.session_state.diff_doc_b), format_func=lambda x: titles[x], key="sel_doc_b"); st.session_state.diff_doc_b = opt_b
    else:
        tb1, tb2 = st.columns([1, 10])
        with tb1:
            if st.button("&#8592; Back", key="diff_back", use_container_width=True): st.session_state.diff_mode = False; st.rerun()

    diff_a_id = st.session_state.diff_doc_a; diff_b_id = st.session_state.diff_doc_b
    if not diff_a_id or not diff_b_id or diff_a_id == diff_b_id:
        st.warning("Please select two different documents to compare.")
    else:
        doc_a = st.session_state.documents[diff_a_id]; doc_b = st.session_state.documents[diff_b_id]
        title_a, title_b = doc_a["meta"]["title"], doc_b["meta"]["title"]
        st.markdown(f"""
        <div class="topbar">
          <div class="topbar-left">
            <div class="topbar-brand"><div class="topbar-brand-icon">&#9711;</div><span class="topbar-brand-name">DocTalk</span></div>
            <div class="topbar-doc">
              <div class="topbar-title">Document Comparison</div>
              <div class="topbar-file" style="display:flex;align-items:center;gap:8px;margin-top:2px">
                <span class="diff-badge-a">A: {title_a[:26]}</span>
                <span style="color:#475569;font-size:11px">vs</span>
                <span class="diff-badge-b">B: {title_b[:26]}</span>
              </div>
            </div>
          </div>
          <div class="topbar-chips">
            <span class="t-chip">&#128196; A: {doc_a['meta']['pages']}p</span>
            <span class="t-chip">&#128196; B: {doc_b['meta']['pages']}p</span>
          </div>
        </div>""", unsafe_allow_html=True)

        diff_chat = st.session_state.diff_chat
        if not diff_chat:
            st.markdown(f"""<div style="max-width:740px;margin:10px auto;padding:0 20px"><div style="background:#0d1117;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:12px 20px"><div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#475569;margin-bottom:10px">Diff starter questions</div>""", unsafe_allow_html=True)
            dq1, dq2 = st.columns(2)
            for i, sq in enumerate(["What changed between these two documents?",f"What's new in {title_b[:22]}?",f"What was removed from {title_a[:22]}?","How do the conclusions differ?"]):
                col = dq1 if i % 2 == 0 else dq2
                if col.button(sq, key=f"dq{i}", use_container_width=True): st.session_state["pf_diff"] = sq; st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

        diff_container = st.container(height=520, border=False)
        with diff_container:
            st.markdown('<div class="chat-outer">', unsafe_allow_html=True)
            for turn in diff_chat:
                is_u     = turn["role"] == "user"
                av_cls   = "av av-u" if is_u else "av av-a"
                bub_cls  = "bub bub-u" if is_u else "bub bub-a"
                wrap_cls = "msg-wrap msg-wrap-u" if is_u else "msg-wrap"
                if is_u: body = turn["content"].replace("\n","<br>")
                else:
                    raw = turn["content"]
                    raw = re.sub(r'(###\s*&#10133;.*?)(?=###|\Z)', lambda m: f'<div class="diff-added-block">{render_md(m.group(1))}</div>', raw, flags=re.DOTALL)
                    raw = re.sub(r'(###\s*&#10134;.*?)(?=###|\Z)', lambda m: f'<div class="diff-removed-block">{render_md(m.group(1))}</div>', raw, flags=re.DOTALL)
                    raw = re.sub(r'(###\s*&#128260;.*?)(?=###|\Z)', lambda m: f'<div class="diff-changed-block">{render_md(m.group(1))}</div>', raw, flags=re.DOTALL)
                    raw = re.sub(r'(###\s*➕.*?)(?=###|\Z)', lambda m: f'<div class="diff-added-block">{render_md(m.group(1))}</div>', raw, flags=re.DOTALL)
                    raw = re.sub(r'(###\s*➖.*?)(?=###|\Z)', lambda m: f'<div class="diff-removed-block">{render_md(m.group(1))}</div>', raw, flags=re.DOTALL)
                    raw = re.sub(r'(###\s*🔄.*?)(?=###|\Z)', lambda m: f'<div class="diff-changed-block">{render_md(m.group(1))}</div>', raw, flags=re.DOTALL)
                    body = render_md(raw)
                srcs_html = ""
                if not is_u and turn.get("sources"):
                    pills = "".join(f'<span class="{"diff-badge-a" if s.get("doc_id")==diff_a_id else "diff-badge-b"}" style="margin-right:4px">{"A" if s.get("doc_id")==diff_a_id else "B"} p.{s["page"]}</span>' for s in turn["sources"])
                    srcs_html = f'<div class="src-row">{pills}</div>'
                st.markdown(f'<div class="chat-outer" style="padding:2px 20px"><div class="{wrap_cls}"><div class="{av_cls}">{"U" if is_u else "&#9711;"}</div><div class="{bub_cls}">{body}{srcs_html}</div></div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Input — form so Enter submits and field clears ─────────────────────
        prefill_diff = st.session_state.pop("pf_diff", "")
        with st.form(key="diff_form", clear_on_submit=True):
            di1, di2, di3 = st.columns([7, 1, 1])
            with di1:
                diff_input = st.text_input("dq", value=prefill_diff, placeholder="Ask what changed, what's new, how they differ...", label_visibility="collapsed", key="diff_qi")
            with di2:
                diff_send = st.form_submit_button("Ask &#8594;", type="primary", use_container_width=True)
            with di3:
                diff_clear_btn = st.form_submit_button("&#128465; Clear", use_container_width=True)

        if diff_clear_btn:
            st.session_state.diff_chat = []; st.rerun()

        if diff_send and diff_input.strip():
            q = diff_input.strip(); diff_chat.append({"role":"user","content":q})
            with st.spinner("Retrieving..."):
                chunks_a = retrieve(q, doc_a["index"], doc_a["chunks"], top_k=5)
                chunks_b = retrieve(q, doc_b["index"], doc_b["chunks"], top_k=5)
            if not chunks_a and not chunks_b:
                diff_chat.append({"role":"assistant","content":"I couldn't find relevant content in either document.","sources":[]})
            else:
                with st.spinner("Comparing..."): ans = answer_diff(q, chunks_a, chunks_b, title_a, title_b, chat_history=diff_chat[:-1])
                sources = ([{"doc_id":diff_a_id,"page":c["page"]} for c in chunks_a]+[{"doc_id":diff_b_id,"page":c["page"]} for c in chunks_b])
                diff_chat.append({"role":"assistant","content":ans,"sources":sources})
            st.session_state.diff_chat = diff_chat; st.rerun()

        # handle prefill from starter chips
        if prefill_diff and not diff_send:
            q = prefill_diff.strip(); diff_chat.append({"role":"user","content":q})
            with st.spinner("Retrieving..."):
                chunks_a = retrieve(q, doc_a["index"], doc_a["chunks"], top_k=5)
                chunks_b = retrieve(q, doc_b["index"], doc_b["chunks"], top_k=5)
            if not chunks_a and not chunks_b:
                diff_chat.append({"role":"assistant","content":"I couldn't find relevant content in either document.","sources":[]})
            else:
                with st.spinner("Comparing..."): ans = answer_diff(q, chunks_a, chunks_b, title_a, title_b, chat_history=diff_chat[:-1])
                sources = ([{"doc_id":diff_a_id,"page":c["page"]} for c in chunks_a]+[{"doc_id":diff_b_id,"page":c["page"]} for c in chunks_b])
                diff_chat.append({"role":"assistant","content":ans,"sources":sources})
            st.session_state.diff_chat = diff_chat; st.rerun()

# ── LANDING ───────────────────────────────────────────────────────────────────
elif not st.session_state.documents and not staged:
    if st.session_state.show_about_landing:
        _b1, _b2, _b3 = st.columns([0.7, 8.6, 1])
        with _b1:
            if st.button("&#8592; Back", key="about_back_btn"): st.session_state.show_about_landing = False; st.rerun()
        st.markdown("""
        <style>
        @keyframes afu{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
        .af1{animation:afu 0.5s ease both}.af2{animation:afu 0.5s 0.1s ease both}.af3{animation:afu 0.5s 0.2s ease both}
        .fg{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.05);border-radius:18px;overflow:hidden;margin-bottom:18px}
        .fc{background:#0d1117;padding:24px;transition:background 0.2s}.fc:hover{background:#111827}
        .fn{font-size:9px;font-weight:700;font-family:monospace;color:rgba(110,231,183,0.5);letter-spacing:1px;margin-bottom:12px}
        .fi{width:34px;height:34px;border-radius:9px;background:rgba(110,231,183,0.06);border:1px solid rgba(110,231,183,0.12);display:flex;align-items:center;justify-content:center;font-size:15px;margin-bottom:12px}
        .ft{font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:6px}.fd{font-size:12px;color:#475569;line-height:1.65}
        .hw{background:#0d1117;border:1px solid rgba(255,255,255,0.05);border-radius:18px;padding:28px 32px;margin-bottom:18px}
        .hs{display:grid;grid-template-columns:repeat(5,1fr);position:relative}
        .hs::before{content:'';position:absolute;top:19px;left:10%;right:10%;height:1px;background:linear-gradient(90deg,transparent,rgba(110,231,183,0.3),rgba(59,130,246,0.3),transparent)}
        .hst{text-align:center;padding:0 8px}.hc{width:38px;height:38px;border-radius:50%;background:#0d1117;border:1px solid rgba(110,231,183,0.32);display:flex;align-items:center;justify-content:center;font-size:14px;margin:0 auto 10px;position:relative;z-index:1}
        .hl{font-size:10px;font-weight:600;color:#64748b;line-height:1.4}
        </style>
        <div style="max-width:880px;margin:0 auto;padding:20px 20px 56px">
          <div class="af1" style="text-align:center;padding:36px 0 44px">
            <div style="display:inline-flex;align-items:center;gap:7px;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#6ee7b7;background:rgba(110,231,183,0.07);border:1px solid rgba(110,231,183,0.14);border-radius:20px;padding:4px 12px;margin-bottom:20px"><div style="width:5px;height:5px;border-radius:50%;background:#6ee7b7"></div>About DocTalk</div>
            <div style="font-family:'Syne',sans-serif;font-size:clamp(32px,5vw,52px);font-weight:800;color:#f1f5f9;letter-spacing:-1.5px;line-height:1.06;margin-bottom:16px">Your documents,<br>finally <span style="background:linear-gradient(135deg,#6ee7b7,#3b82f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">answering back</span></div>
            <p style="font-size:15px;color:#64748b;max-width:480px;margin:0 auto;line-height:1.8">Upload any PDF and ask it anything in plain English. Get grounded answers with exact page citations.</p>
          </div>
          <div class="fg af2">
            <div class="fc"><div class="fn">01</div><div class="fi">&#128269;</div><div class="ft">RAG Pipeline</div><div class="fd">Chunks &#8594; embeddings &#8594; FAISS retrieval &#8594; grounded generation. Zero hallucinations.</div></div>
            <div class="fc"><div class="fn">02</div><div class="fi">&#128204;</div><div class="ft">Exact Citations</div><div class="fd">Every answer cites the precise page numbers it was drawn from.</div></div>
            <div class="fc"><div class="fn">03</div><div class="fi">&#128203;</div><div class="ft">Auto Summary</div><div class="fd">Executive summary, key topics, and suggested questions generated on upload.</div></div>
            <div class="fc"><div class="fn">04</div><div class="fi">&#128193;</div><div class="ft">Multi-document</div><div class="fd">Up to 5 PDFs simultaneously. Each with its own independent chat history.</div></div>
            <div class="fc"><div class="fn">05</div><div class="fi">&#127897;</div><div class="ft">Voice Input</div><div class="fd">Click the mic icon and ask out loud &#8212; Web Speech API captures it instantly.</div></div>
            <div class="fc"><div class="fn">06</div><div class="fi">&#8595;</div><div class="ft">Chat Export</div><div class="fd">Download your Q&amp;A session as a styled PDF or plain text file.</div></div>
          </div>
          <div class="hw af3">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:#475569;margin-bottom:22px">How it works</div>
            <div class="hs">
              <div class="hst"><div class="hc">&#128196;</div><div class="hl"><span style="color:#94a3b8">Upload</span><br>PDF</div></div>
              <div class="hst"><div class="hc">&#9986;</div><div class="hl"><span style="color:#94a3b8">Chunk</span><br>text</div></div>
              <div class="hst"><div class="hc">&#129504;</div><div class="hl"><span style="color:#94a3b8">Embed</span><br>vectors</div></div>
              <div class="hst"><div class="hc">&#128270;</div><div class="hl"><span style="color:#94a3b8">Retrieve</span><br>chunks</div></div>
              <div class="hst"><div class="hc">&#10024;</div><div class="hl"><span style="color:#94a3b8">Generate</span><br>answer</div></div>
            </div>
          </div>
          <div style="background:#0d1117;border:1px solid rgba(255,255,255,0.05);border-radius:18px;padding:22px 28px;display:flex;align-items:center;gap:24px;flex-wrap:wrap">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:#475569;flex-shrink:0">Built with</div>
            <div style="display:flex;flex-wrap:wrap;gap:7px">
              <span style="font-size:12px;font-weight:600;padding:4px 12px;border-radius:20px;border:1px solid rgba(110,231,183,0.18);background:rgba(110,231,183,0.06);color:#6ee7b7">Streamlit</span>
              <span style="font-size:12px;font-weight:600;padding:4px 12px;border-radius:20px;border:1px solid rgba(110,231,183,0.18);background:rgba(110,231,183,0.06);color:#6ee7b7">Llama 3-70B</span>
              <span style="font-size:12px;font-weight:600;padding:4px 12px;border-radius:20px;border:1px solid rgba(110,231,183,0.18);background:rgba(110,231,183,0.06);color:#6ee7b7">FAISS</span>
              <span style="font-size:12px;font-weight:600;padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,0.07);background:rgba(255,255,255,0.02);color:#94a3b8">sentence-transformers</span>
              <span style="font-size:12px;font-weight:600;padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,0.07);background:rgba(255,255,255,0.02);color:#94a3b8">Groq API</span>
              <span style="font-size:12px;font-weight:600;padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,0.07);background:rgba(255,255,255,0.02);color:#94a3b8">PyMuPDF</span>
              <span style="font-size:12px;font-weight:600;padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,0.07);background:rgba(255,255,255,0.02);color:#94a3b8">SQLite</span>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        _g1, _g2, _g3 = st.columns([8.5, 1, 0.7])
        with _g3:
            if st.button("&#8505; About", key="land_about_btn"): st.session_state.show_about_landing = True; st.rerun()
        st.markdown("""
        <div style="text-align:center;padding:36px 24px 0;animation:fadeInUp 0.6s ease both">
          <div style="width:78px;height:78px;border-radius:22px;background:linear-gradient(135deg,#6ee7b7,#3b82f6);display:flex;align-items:center;justify-content:center;font-size:34px;margin:0 auto 26px;box-shadow:0 0 60px rgba(110,231,183,0.25),0 8px 32px rgba(110,231,183,0.15);animation:pulseGlow 3s ease-in-out infinite">&#9711;</div>
          <h1 style="font-family:'Syne',sans-serif;font-size:50px;font-weight:800;color:#f1f5f9;letter-spacing:-2px;line-height:1.08;margin-bottom:16px">Ask anything about<br>your <span style="color:#6ee7b7">documents</span></h1>
          <p style="font-size:17px;color:#94a3b8;line-height:1.7;max-width:460px;margin:0 auto 40px">Upload any PDF and start a conversation with it. Get precise answers with exact page citations.</p>
        </div>""", unsafe_allow_html=True)
        st.markdown("""<style>
        div[data-testid="stFileUploader"]{max-width:580px !important;margin:0 auto 40px !important}
        div[data-testid="stFileUploader"] section{background:#0d1117 !important;border:2px dashed rgba(59,130,246,0.22) !important;border-radius:22px !important;padding:60px !important;cursor:pointer !important;transition:all 0.28s !important;text-align:center !important;min-height:230px !important;display:flex !important;align-items:center !important;justify-content:center !important}
        div[data-testid="stFileUploader"] section:hover{border-color:#6ee7b7 !important;box-shadow:0 8px 40px rgba(110,231,183,0.14) !important;transform:translateY(-3px) !important}
        div[data-testid="stFileUploaderDropzoneInstructions"]>div>span{font-size:17px !important;font-weight:600 !important;color:#f1f5f9 !important;display:block !important;margin-bottom:6px !important}
        div[data-testid="stFileUploaderDropzoneInstructions"]>div>small{font-size:13px !important;color:#475569 !important}
        div[data-testid="stFileUploader"] section svg{width:50px !important;height:50px !important;color:#6ee7b7 !important;margin-bottom:14px !important}
        div[data-testid="stFileUploader"] button{background:linear-gradient(135deg,#6ee7b7,#3b82f6) !important;color:#052e16 !important;font-weight:700 !important;border:none !important;border-radius:10px !important;margin-top:12px !important}
        </style>""", unsafe_allow_html=True)
        lup = st.file_uploader("Drop your PDF here", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed", key="land_up")
        if lup: st.session_state.staged = lup; st.rerun()

# ── BACK TO HOME ──────────────────────────────────────────────────────────────
elif st.session_state.documents and not active and not staged:
    st.markdown("""<div class="landing"><div style="font-size:48px;margin-bottom:20px;animation:floatY 3s ease-in-out infinite">&#128194;</div><h2 style="font-family:'Syne',sans-serif;font-size:30px;font-weight:800;color:#f1f5f9;letter-spacing:-0.5px;margin-bottom:12px">Upload another document</h2><p style="font-size:15px;color:#94a3b8;margin-bottom:28px">Or select an existing document from the sidebar.</p></div>""", unsafe_allow_html=True)
    _, uc, _ = st.columns([1, 2, 1])
    with uc:
        more = st.file_uploader("u2", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed", key="home_up")
        if more: st.session_state.staged = more; st.rerun()

# ── STAGING ───────────────────────────────────────────────────────────────────
elif staged and not active:
    st.markdown("""<div class="stage-header"><div style="font-size:42px;margin-bottom:14px">&#128203;</div><h2 class="stage-h2">Ready to process</h2><p class="stage-sub">Review your files, then click Process.<br>DocTalk will chunk, embed, and summarize each document.</p></div>""", unsafe_allow_html=True)
    _, fc, _ = st.columns([1, 2, 1])
    with fc:
        for f in staged:
            kb = round(len(f.getvalue()) / 1024)
            sz = (str(kb)+"KB") if kb < 1024 else (str(round(kb/1024,1))+"MB")
            st.markdown(f'<div class="file-card"><div style="font-size:24px;flex-shrink:0">&#128196;</div><div><div class="file-name">{f.name}</div><div class="file-size">{sz}</div></div></div>', unsafe_allow_html=True)
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        proc_area = st.empty()
        if st.button("&#9881;  Process documents", type="primary", use_container_width=True, key="proc"):
            for uf in staged[:5]:
                did = uf.name
                if did not in st.session_state.documents:
                    def show_proc(name, step):
                        steps_def = [("&#128214;","Reading PDF"),("&#9986;","Chunking text"),("&#129504;","Building embeddings"),("&#10024;","Generating summary")]
                        rows = ""
                        for i,(ic,lb) in enumerate(steps_def):
                            if i < step:   rows += f'<div class="proc-step done"><span class="proc-step-icon">&#10003;</span><span style="text-decoration:line-through;opacity:0.5">{lb}</span></div>'
                            elif i == step: rows += f'<div class="proc-step active"><span class="proc-step-icon">{ic}</span>{lb}<div class="proc-dots"><div class="proc-dot"></div><div class="proc-dot"></div><div class="proc-dot"></div></div></div>'
                            else:           rows += f'<div class="proc-step"><span class="proc-step-icon" style="opacity:0.3">{ic}</span><span style="opacity:0.3">{lb}</span></div>'
                        proc_area.markdown(f'<div class="proc-card"><div class="proc-title-label">Processing</div><div class="proc-doc-name">{name[:42]}</div>{rows}</div>', unsafe_allow_html=True)
                    show_proc(uf.name, 0)
                    pdf_bytes = uf.read(); meta = get_pdf_metadata(pdf_bytes, uf.name); pages = extract_text_by_page(pdf_bytes)
                    show_proc(uf.name, 1); chunks = chunk_pages(pages)
                    show_proc(uf.name, 2); index, _, chunks = build_index(chunks)
                    show_proc(uf.name, 3); summary = summarize_document(pages, meta["title"]) if pages else "Image-based PDF — no text extracted."
                    sc = get_chat_history(did)
                    st.session_state.documents[did] = {"meta":meta,"pages":pages,"chunks":chunks,"index":index,"summary":summary,"chat":sc,"pdf_bytes":pdf_bytes}
                    save_document(did, meta); proc_area.empty()
                if st.session_state.active_doc is None: st.session_state.active_doc = uf.name
            st.session_state.staged = []; st.rerun()
        if st.button("&#8592; Cancel", use_container_width=True, key="cancel"): st.session_state.staged = []; st.rerun()

# ── DOCUMENT VIEW ─────────────────────────────────────────────────────────────
elif st.session_state.documents and active and not staged and not st.session_state.cross_doc_mode and not st.session_state.diff_mode:
    if active not in st.session_state.documents:
        active = list(st.session_state.documents.keys())[0]; st.session_state.active_doc = active

    doc  = st.session_state.documents[active]
    meta = doc["meta"]
    chat = doc["chat"]
    hits = compute_page_hits(chat)

    # ── JS: sticky topbar ─────────────────────────────────────────────────────
    components.html("""
    <script>
    (function() {
      function stickyTopbar() {
        try {
          var pd = window.parent.document;
          // Find the row that contains our .topbar div
          var topbarDiv = pd.querySelector('.topbar');
          if (!topbarDiv) return;
          var row = topbarDiv.closest('[data-testid="stHorizontalBlock"]');
          if (!row) return;
          // Walk up to find the scrolling container
          var scrollParent = row.parentElement;
          while (scrollParent && scrollParent !== pd.body) {
            var overflow = window.parent.getComputedStyle(scrollParent).overflow;
            if (overflow === 'auto' || overflow === 'scroll' || overflow === 'overlay') break;
            scrollParent = scrollParent.parentElement;
          }
          // Apply sticky to the row itself
          row.style.position   = 'sticky';
          row.style.top        = '0';
          row.style.zIndex     = '999';
          row.style.background = '#0c0e17';
          row.style.boxShadow  = '0 2px 24px rgba(0,0,0,0.55)';
        } catch(e) {}
      }
      // Run immediately and after DOM settles
      stickyTopbar();
      setTimeout(stickyTopbar, 300);
      setTimeout(stickyTopbar, 800);
      // Re-run on Streamlit reruns (MutationObserver)
      try {
        var obs = new MutationObserver(function() { stickyTopbar(); });
        obs.observe(window.parent.document.body, { childList: true, subtree: true });
        setTimeout(function() { obs.disconnect(); }, 8000);
      } catch(e) {}
    })();
    </script>""", height=0)

    # ── Topbar ────────────────────────────────────────────────────────────────
    tb1, tb2 = st.columns([1, 10])
    with tb1:
        if st.button("&#8592; Back", key="home_btn", use_container_width=True):
            st.session_state.active_doc = None; st.session_state.staged = []; st.rerun()
    with tb2:
        st.markdown(f"""
        <div class="topbar">
          <div class="topbar-left">
            <div class="topbar-brand">
              <div class="topbar-brand-icon">&#9711;</div>
              <span class="topbar-brand-name">DocTalk</span>
            </div>
            <div class="topbar-doc">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:2px">
                <div class="topbar-title">{meta['title']}</div>
                <div class="topbar-live"><div class="topbar-live-dot"></div>Live</div>
              </div>
              <div class="topbar-file">{meta['filename']}</div>
            </div>
          </div>
          <div class="topbar-chips">
            <span class="t-chip">&#9889; ~400ms</span>
            <span class="t-chip">&#129504; Llama-3-70B</span>
            <span class="t-chip">&#128196; {meta['pages']}p</span>
            <span class="t-chip">&#128221; {meta['words']:,}w</span>
            <span class="t-chip">&#128172; {len(chat)//2} Q&amp;As</span>
          </div>
        </div>""", unsafe_allow_html=True)

    # ── Multi-doc banner ──────────────────────────────────────────────────────
    if len(st.session_state.documents) >= 2:
        b1, b2, b3 = st.columns([5, 2, 2])
        with b2:
            if st.button(f"&#128279; Cross-doc Q&A ({len(st.session_state.documents)} docs)", key="cross_banner_btn", use_container_width=True, type="primary"):
                st.session_state.cross_doc_mode = True; st.rerun()
        with b3:
            if st.button("&#128256; Compare / Diff", key="diff_banner_btn", use_container_width=True):
                st.session_state.diff_mode = True; st.session_state.diff_chat = []
                doc_ids = list(st.session_state.documents.keys()); st.session_state.diff_doc_a = doc_ids[0]; st.session_state.diff_doc_b = doc_ids[1]; st.rerun()

    # ── Tabs — Map is now a floating panel, so only 3 tabs ────────────────────
    tab_chat, tab_sum, tab_docs = st.tabs(["  &#128172;  Chat  ", "  &#128203;  Summary  ", "  &#128193;  Documents  "])

    # ════════════════════════════════════════════════════════════════════════
    # CHAT TAB
    # ════════════════════════════════════════════════════════════════════════
    with tab_chat:
        # ── Floating map — only rendered inside Chat tab ──────────────────────
        render_floating_map(hits, meta["pages"], chat)
        # JS: watch for tab clicks → hide map button on non-Chat tabs
        components.html("""
        <script>
        (function() {
          function watchTabs() {
            try {
              var pd = window.parent.document;
              var tabs = pd.querySelectorAll('[data-testid="stTabs"] button[role="tab"]');
              if (!tabs.length) return;
              function updateMap() {
                var activeTab = pd.querySelector('[data-testid="stTabs"] button[role="tab"][aria-selected="true"]');
                var mapBtn   = pd.getElementById('dtm-btn');
                var mapPanel = pd.getElementById('dtm-panel');
                if (!mapBtn) return;
                var isChat = activeTab && activeTab.textContent.toLowerCase().includes('chat');
                mapBtn.style.display = isChat ? '' : 'none';
                if (!isChat && mapPanel) {
                  mapPanel.classList.remove('open');
                  mapPanel.style.right = '-360px';
                  mapBtn.style.right = '0';
                }
              }
              tabs.forEach(function(t) { t.addEventListener('click', function() { setTimeout(updateMap, 80); }); });
              updateMap();
            } catch(e) {}
          }
          setTimeout(watchTabs, 400);
          setTimeout(watchTabs, 900);
        })();
        </script>""", height=0)

        if not doc.get("chunks"):
            st.markdown("""<div style="max-width:600px;margin:40px auto;background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.22);border-radius:14px;padding:24px 28px"><div style="font-size:15px;font-weight:600;color:#f59e0b;margin-bottom:8px">&#9888; Image-based PDF detected</div><div style="font-size:13px;color:#6b7280;line-height:1.65">No text could be extracted. DocTalk requires text-based PDFs.</div></div>""", unsafe_allow_html=True)
        else:
            if not chat:
                st.markdown("""
                <div style="max-width:740px;margin:12px auto 8px;padding:0 20px">
                  <div style="background:rgba(14,18,28,0.85);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:14px 18px;animation:fadeInUp 0.4s ease both">
                    <div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.3px;color:#4b5563;margin-bottom:10px">Try asking</div>""", unsafe_allow_html=True)
                q1, q2 = st.columns(2)
                for i, sq in enumerate(["What is this document about?","What are the key findings?","List the most important points.","What conclusions does this draw?"]):
                    col = q1 if i % 2 == 0 else q2
                    if col.button(sq, key=f"sq{i}", use_container_width=True): st.session_state[f"pf_{active}"] = sq; st.rerun()
                st.markdown('</div></div>', unsafe_allow_html=True)

            chat_container = st.container(height=420, border=False)
            with chat_container:
                st.markdown('<div class="chat-outer">', unsafe_allow_html=True)
                for idx, turn in enumerate(chat):
                    is_u     = turn["role"] == "user"
                    av_lbl   = "U" if is_u else "&#9711;"
                    av_cls   = "av av-u" if is_u else "av av-a"
                    bub_cls  = "bub bub-u" if is_u else "bub bub-a"
                    wrap_cls = "msg-wrap msg-wrap-u" if is_u else "msg-wrap"
                    body     = turn["content"].replace("\n","<br>") if is_u else render_md(turn["content"])
                    delay    = min(idx * 0.04, 0.28)
                    srcs = ""
                    if not is_u and turn.get("sources"):
                        pills = "".join(f'<span class="src-p">p.{s["page"]}</span>' for s in turn["sources"])
                        srcs  = f'<div class="src-row">{pills}</div>'
                    st.markdown(f'<div class="chat-outer" style="padding:2px 20px"><div class="{wrap_cls}" style="animation-delay:{delay}s"><div class="{av_cls}">{av_lbl}</div><div class="{bub_cls}">{body}{srcs}</div></div></div>', unsafe_allow_html=True)
                    if not is_u and turn.get("top_passage"):
                        p = turn["top_passage"]
                        st.markdown(f'<div style="max-width:740px;margin:0 auto;padding:0 20px"><div class="excerpt"><div class="excerpt-lbl">Source &middot; Page {p["page"]}</div>&ldquo;{p["text"][:220]}...&rdquo;</div></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            components.html("""<script>
            window.parent.document.querySelectorAll('div[style*="overflow-y: auto"],div[style*="overflow-y:auto"]').forEach(function(el){
                if(el.scrollHeight>el.clientHeight+10) el.scrollTop=el.scrollHeight;
            });
            </script>""", height=0)

            # ── Follow-up chips — animated glowing strip ──────────────────────
            if chat and chat[-1]["role"] == "assistant":
                followups = chat[-1].get("followups", [])
                if followups:
                    # Strip wrapper with accent border + label
                    st.markdown("""
                    <div style="max-width:760px;margin:8px auto 2px;padding:0 20px 0 52px">
                      <div class="fu-strip">
                        <div class="fu-label-row">
                          <div class="fu-label-dot"></div>
                          <span class="fu-label-txt">Ask Next</span>
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)

                    # Per-chip: staggered chipIn + chipFloat + chipPulse
                    anim_css = ""
                    for i in range(len(followups)):
                        delay_in    = f"{i * 0.1:.2f}s"
                        delay_float = f"{i * 0.35:.2f}s"
                        delay_pulse = f"{i * 0.45:.2f}s"
                        anim_css += f"""
                        <style>
                        div[data-testid="stHorizontalBlock"] > div:nth-child({i+1}) button {{
                            animation:
                                chipIn   0.45s {delay_in} cubic-bezier(0.22,1,0.36,1) both,
                                chipFloat 3.4s {delay_float} ease-in-out infinite,
                                chipPulse 3.8s {delay_pulse} ease-in-out infinite !important;
                            border-radius: 22px !important;
                            background: rgba(16,185,129,0.06) !important;
                            border: 1px solid rgba(16,185,129,0.18) !important;
                            color: #94a3b8 !important;
                            font-size: 13px !important;
                            font-weight: 500 !important;
                            padding: 8px 18px !important;
                            white-space: nowrap !important;
                            text-overflow: ellipsis !important;
                            overflow: hidden !important;
                        }}
                        div[data-testid="stHorizontalBlock"] > div:nth-child({i+1}) button:hover {{
                            background: rgba(16,185,129,0.14) !important;
                            border-color: rgba(16,185,129,0.42) !important;
                            color: #e2e8f0 !important;
                            transform: translateY(-3px) scale(1.03) !important;
                            box-shadow: 0 6px 20px rgba(16,185,129,0.25) !important;
                            animation-play-state: paused !important;
                        }}
                        </style>"""
                    st.markdown(anim_css, unsafe_allow_html=True)

                    fu_cols = st.columns(len(followups))
                    for i, fq in enumerate(followups):
                        with fu_cols[i]:
                            if st.button(fq, key=f"fu_{active}_{i}", use_container_width=True):
                                st.session_state[f"pf_{active}"] = fq; st.rerun()

            # ── Input row ──────────────────────────────────────────────────────
            prefill = st.session_state.pop(f"pf_{active}", "")
            inp_col, voice_col = st.columns([11, 1])
            with voice_col:
                components.html("""
                <style>
                #vb{width:100%;height:41px;border-radius:10px;border:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.04);font-size:18px;cursor:pointer;color:#6b7280;transition:all 0.18s;display:block}
                #vb:hover{border-color:#10b981;color:#10b981;background:rgba(16,185,129,0.08);transform:scale(1.05)}
                #vb.on{background:rgba(239,68,68,0.1);border-color:#ef4444;color:#ef4444}
                </style>
                <button id="vb" title="Voice input">&#127897;</button>
                <script>
                let rec=null;
                document.getElementById("vb").onclick=function(){
                  if(!("webkitSpeechRecognition"in window)){alert("Use Chrome for voice");return;}
                  if(rec){rec.stop();return;}
                  rec=new webkitSpeechRecognition();rec.lang="en-US";rec.maxAlternatives=1;
                  this.classList.add("on");this.textContent="&#128308;";
                  rec.onresult=e=>{
                    const t=e.results[0][0].transcript;
                    const inp=[...window.parent.document.querySelectorAll("input")].find(i=>i.placeholder?.includes("anything"));
                    if(inp){Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(inp,t);inp.dispatchEvent(new Event("input",{bubbles:true}));}
                  };
                  rec.onend=()=>{this.classList.remove("on");this.textContent="&#127897;";rec=null;};
                  rec.onerror=()=>{this.classList.remove("on");this.textContent="&#127897;";rec=null;};
                  rec.start();
                };
                </script>""", height=44)

            with st.form(key=f"chat_form_{active}", clear_on_submit=True):
                fc1, fc2, fc3 = st.columns([7, 1, 1])
                with fc1:
                    user_input = st.text_input("q", value=prefill, placeholder="Ask anything about your documents...", label_visibility="collapsed", key=f"qi_{active}")
                with fc2:
                    send = st.form_submit_button("Ask &#8594;", type="primary", use_container_width=True)
                with fc3:
                    clear_btn = st.form_submit_button("&#128465; Clear", use_container_width=True)

            if clear_btn: clear_chat(active); st.session_state.documents[active]["chat"] = []; st.rerun()

            if (send or prefill) and user_input.strip():
                q = user_input.strip(); chat.append({"role":"user","content":q}); save_message(active,"user",q)
                with st.spinner("Searching document..."): retrieved = retrieve(q, doc["index"], doc["chunks"])
                if not retrieved:
                    ans = "I couldn't find relevant content in this document for that question."
                    chat.append({"role":"assistant","content":ans,"sources":[],"top_passage":None}); save_message(active,"assistant",ans,[],None)
                else:
                    with st.spinner("Generating answer..."): ans = answer_question(q, retrieved, chat_history=chat[:-1])
                    sources = [{"page":r["page"],"score":r["score"]} for r in retrieved]; top = retrieved[0]
                    with st.spinner("Generating follow-ups..."): followups = suggest_followups(q, ans, retrieved)
                    chat.append({"role":"assistant","content":ans,"sources":sources,"top_passage":top,"followups":followups}); save_message(active,"assistant",ans,sources,top)
                st.session_state.documents[active]["chat"] = chat; st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # SUMMARY TAB
    # ════════════════════════════════════════════════════════════════════════
    with tab_sum:
        summary_html = render_md(doc["summary"])
        st.markdown(f"""
        <div style="max-width:740px;margin:24px auto;padding:0 20px;animation:fadeInUp 0.4s ease both">
          <div style="background:rgba(12,15,24,0.88);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,0.07);border-radius:18px;padding:34px;box-shadow:0 0 32px rgba(16,185,129,0.04),0 4px 24px rgba(0,0,0,0.35)">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:22px;padding-bottom:16px;border-bottom:1px solid rgba(255,255,255,0.06)">
              <div style="width:3px;height:18px;background:linear-gradient(180deg,#10b981,#3b82f6);border-radius:2px;flex-shrink:0"></div>
              <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.4px;color:#10b981">AI-generated summary</div>
              <div style="margin-left:auto;font-size:10px;color:#374151;background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.12);border-radius:6px;padding:2px 9px">{meta['pages']} pages &middot; {meta['words']:,} words</div>
            </div>
            <div style="font-size:15px;color:#94a3b8;line-height:1.9">{summary_html}</div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # DOCUMENTS TAB
    # ════════════════════════════════════════════════════════════════════════
    with tab_docs:
        st.markdown('<div style="max-width:740px;margin:20px auto;padding:0 20px">', unsafe_allow_html=True)
        for did, d in st.session_state.documents.items():
            is_a = did == active
            with st.expander(f"{'&#9658; ' if is_a else ''}&#128196; {d['meta']['title']} — {d['meta']['pages']}p", expanded=is_a):
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Pages", d['meta']['pages'])
                c2.metric("Words", f"{d['meta']['words']:,}")
                c3.metric("Chunks", len(d['chunks']))
                c4.metric("Q&As", len(d['chat'])//2)
                if not is_a:
                    dc1,dc2 = st.columns([3,1])
                    with dc1:
                        if st.button("Switch to this document", key=f"sw_{did}"): st.session_state.active_doc = did; st.rerun()
                    with dc2:
                        if st.button("Delete", key=f"dl_{did}", type="secondary"):
                            delete_document(did); del st.session_state.documents[did]
                            rem = list(st.session_state.documents.keys()); st.session_state.active_doc = rem[0] if rem else None; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)