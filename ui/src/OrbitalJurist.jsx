import { useState, useEffect, useRef, useCallback } from "react";

/* ═══════════════════════════════════════════
   GLOBAL STYLES injected once
═══════════════════════════════════════════ */
const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Share+Tech+Mono&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: #060a14;
    color: #e8f4ff;
    overflow-x: hidden;
  }

  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #0b1120; }
  ::-webkit-scrollbar-thumb { background: rgba(0,195,255,0.25); border-radius: 3px; }

  @keyframes spin         { to { transform: rotate(360deg); } }
  @keyframes pulse-dot    { 0%,100%{opacity:1} 50%{opacity:0.3} }
  @keyframes pulse-core   { 0%,100%{transform:translate(-50%,-50%) scale(1);opacity:1} 50%{transform:translate(-50%,-50%) scale(1.7);opacity:0.5} }
  @keyframes slow-rotate  { to { transform: rotate(360deg); } }
  @keyframes danger-pulse { 0%,100%{box-shadow:0 0 14px rgba(255,71,87,0.35)} 50%{box-shadow:0 0 28px rgba(255,71,87,0.6)} }
  @keyframes fade-in      { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
  @keyframes slide-in     { from{opacity:0;transform:translateX(-10px)} to{opacity:1;transform:translateX(0)} }
  @keyframes scan-line    { 0%{top:-10%} 100%{top:110%} }

  .oj-scanline-overlay {
    position: fixed; inset: 0; z-index: 1; pointer-events: none;
    background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.025) 2px, rgba(0,0,0,0.025) 4px);
  }

  .oj-canvas { position: fixed; inset: 0; z-index: 0; pointer-events: none; }

  .oj-root {
    position: relative; z-index: 2;
    max-width: 1320px; margin: 0 auto; padding: 0 24px 80px;
    animation: fade-in 0.5s ease both;
  }

  /* ── System bar ── */
  .oj-sysbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 0; border-bottom: 1px solid rgba(0,195,255,0.1);
    font-family: 'Share Tech Mono', monospace; font-size: 11px;
    color: #4a6585; letter-spacing: 0.08em;
  }
  .oj-sysbar-left { display: flex; gap: 12px; align-items: center; }
  .oj-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
  .oj-dot-g { background: #2ed573; box-shadow: 0 0 6px #2ed573; animation: pulse-dot 2.4s infinite; }
  .oj-dot-c { background: #00c3ff; box-shadow: 0 0 6px #00c3ff; animation: pulse-dot 2.4s 0.8s infinite; }
  .oj-dot-a { background: #f5a623; box-shadow: 0 0 6px #f5a623; animation: pulse-dot 2.4s 1.6s infinite; }
  .oj-clock { font-size: 12px; color: rgba(0,195,255,0.7); }

  /* ── Settings button ── */
  .oj-settings-btn {
    background: transparent; border: 1px solid rgba(0,195,255,0.2); border-radius: 3px;
    color: rgba(0,195,255,0.6); font-family: 'Share Tech Mono', monospace;
    font-size: 10px; letter-spacing: 0.1em; padding: 4px 12px; cursor: pointer;
    transition: all 0.2s; display: flex; align-items: center; gap: 6px;
  }
  .oj-settings-btn:hover { border-color: rgba(0,195,255,0.5); color: #00c3ff; background: rgba(0,195,255,0.06); }

  /* ── Settings drawer ── */
  .oj-settings-drawer {
    background: #0f1929; border: 1px solid rgba(0,195,255,0.2);
    border-top: none; padding: 14px 18px 16px;
    animation: slide-in 0.2s ease both;
  }
  .oj-settings-row {
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  }
  .oj-settings-label {
    font-family: 'Share Tech Mono', monospace; font-size: 10px;
    letter-spacing: 0.14em; text-transform: uppercase; color: #4a6585;
    white-space: nowrap;
  }
  .oj-settings-input {
    flex: 1; min-width: 240px; background: rgba(0,195,255,0.04);
    border: 1px solid rgba(0,195,255,0.2); border-radius: 2px;
    padding: 7px 12px; color: #e8f4ff; font-family: 'Share Tech Mono', monospace;
    font-size: 13px; outline: none; transition: border-color 0.2s, box-shadow 0.2s;
  }
  .oj-settings-input:focus {
    border-color: #00c3ff; box-shadow: 0 0 0 1px rgba(0,195,255,0.15);
  }
  .oj-settings-save {
    background: rgba(0,195,255,0.1); border: 1px solid rgba(0,195,255,0.35);
    border-radius: 2px; color: #00c3ff; font-family: 'Share Tech Mono', monospace;
    font-size: 10px; letter-spacing: 0.12em; padding: 7px 16px; cursor: pointer;
    transition: all 0.2s; text-transform: uppercase; white-space: nowrap;
  }
  .oj-settings-save:hover { background: rgba(0,195,255,0.2); border-color: rgba(0,195,255,0.6); }
  .oj-settings-current {
    font-family: 'Share Tech Mono', monospace; font-size: 10px;
    color: rgba(0,195,255,0.5); letter-spacing: 0.04em;
  }
  .oj-settings-current strong { color: rgba(0,195,255,0.85); }

  /* ── Hero ── */
  .oj-hero {
    padding: 52px 0 36px; position: relative;
    display: flex; justify-content: space-between; align-items: flex-start;
  }
  .oj-hero-eyebrow {
    font-family: 'Share Tech Mono', monospace; font-size: 11px;
    letter-spacing: 0.22em; text-transform: uppercase; color: #00c3ff;
    margin-bottom: 14px; display: flex; align-items: center; gap: 12px;
  }
  .oj-hero-eyebrow::before {
    content: ''; display: inline-block; width: 32px; height: 1px;
    background: #00c3ff; box-shadow: 0 0 12px rgba(0,195,255,0.5);
  }
  .oj-h1 {
    font-family: 'Orbitron', monospace; font-size: clamp(36px, 5.5vw, 68px);
    font-weight: 900; letter-spacing: 0.04em; line-height: 1; text-transform: uppercase;
    background: linear-gradient(135deg, #ffffff 0%, #00c3ff 50%, #00e5c0 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 8px;
  }
  .oj-subtitle {
    font-family: 'Orbitron', monospace; font-size: clamp(10px, 1.4vw, 13px);
    letter-spacing: 0.26em; text-transform: uppercase; color: #8aa8c8;
    margin-bottom: 18px;
  }
  .oj-hero-desc {
    max-width: 580px; font-size: 14px; line-height: 1.7;
    color: #8aa8c8; font-weight: 300;
  }
  .oj-orbit-deco {
    flex-shrink: 0; width: 280px; height: 280px;
    animation: slow-rotate 32s linear infinite;
    opacity: 0.18;
  }
  @media(max-width:780px){ .oj-orbit-deco{ display:none; } }

  /* ── Divider ── */
  .oj-divider {
    height: 1px; margin: 4px 0 32px;
    background: linear-gradient(90deg, transparent, rgba(0,195,255,0.35) 30%, rgba(0,195,255,0.35) 70%, transparent);
  }

  /* ── Layout ── */
  .oj-grid { display: grid; grid-template-columns: 400px 1fr; gap: 22px; align-items: start; }
  @media(max-width:880px){ .oj-grid{ grid-template-columns:1fr; } }
  .oj-results-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
  @media(max-width:680px){ .oj-results-grid{ grid-template-columns:1fr; } }

  /* ── Panel ── */
  .oj-panel {
    background: #111d2e; border: 1px solid rgba(0,195,255,0.1);
    border-radius: 4px; position: relative; overflow: hidden;
  }
  .oj-panel::before {
    content: ''; position: absolute; inset: 0; pointer-events: none;
    background: linear-gradient(135deg, rgba(0,195,255,0.025) 0%, transparent 60%);
  }
  .oj-panel-corner-tl {
    position: absolute; top: 0; left: 0; width: 12px; height: 12px;
    border-top: 2px solid rgba(0,195,255,0.6); border-left: 2px solid rgba(0,195,255,0.6);
    z-index: 1;
  }
  .oj-panel-corner-br {
    position: absolute; bottom: 0; right: 0; width: 12px; height: 12px;
    border-bottom: 2px solid rgba(0,195,255,0.6); border-right: 2px solid rgba(0,195,255,0.6);
    z-index: 1;
  }
  .oj-panel-hdr {
    display: flex; align-items: center; gap: 10px;
    padding: 14px 18px; border-bottom: 1px solid rgba(0,195,255,0.08);
  }
  .oj-panel-hdr-icon { color: #00c3ff; flex-shrink: 0; display: flex; align-items: center; }
  .oj-panel-title {
    font-family: 'Share Tech Mono', monospace; font-size: 11px;
    letter-spacing: 0.16em; text-transform: uppercase; color: #00c3ff;
  }
  .oj-panel-body { padding: 18px; }

  /* ── Form ── */
  .oj-form-group { margin-bottom: 16px; }
  .oj-form-label {
    display: block; font-family: 'Share Tech Mono', monospace; font-size: 10px;
    letter-spacing: 0.14em; text-transform: uppercase; color: #4a6585; margin-bottom: 6px;
  }
  .oj-form-label span { color: #ff4757; margin-left: 3px; }
  .oj-input {
    width: 100%; background: rgba(0,195,255,0.04); border: 1px solid rgba(0,195,255,0.12);
    border-radius: 3px; padding: 10px 13px; color: #e8f4ff;
    font-family: 'Share Tech Mono', monospace; font-size: 13px;
    letter-spacing: 0.05em; outline: none; transition: all 0.2s;
    -webkit-appearance: none;
  }
  .oj-input::placeholder { color: #4a6585; }
  .oj-input:focus {
    border-color: #00c3ff; background: rgba(0,195,255,0.07);
    box-shadow: 0 0 0 1px rgba(0,195,255,0.18);
  }
  .oj-input::-webkit-calendar-picker-indicator {
    filter: invert(0.5) sepia(1) hue-rotate(180deg) saturate(3); opacity: 0.6; cursor: pointer;
  }
  .oj-input-hint {
    font-family: 'Share Tech Mono', monospace; font-size: 10px;
    color: #4a6585; margin-top: 4px; letter-spacing: 0.04em;
  }

  /* Test IDs */
  .oj-testids {
    background: rgba(0,195,255,0.03); border: 1px solid rgba(0,195,255,0.1);
    border-radius: 3px; padding: 11px 13px; margin-bottom: 16px;
  }
  .oj-testids-title {
    font-family: 'Share Tech Mono', monospace; font-size: 9px;
    letter-spacing: 0.18em; text-transform: uppercase; color: #4a6585; margin-bottom: 8px;
  }
  .oj-testid-row {
    display: flex; align-items: center; gap: 8px; margin-bottom: 5px;
    cursor: pointer; border-radius: 2px; padding: 2px 4px; transition: background 0.15s;
  }
  .oj-testid-row:last-child { margin-bottom: 0; }
  .oj-testid-row:hover { background: rgba(0,195,255,0.06); }
  .oj-testid-badge {
    font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #00c3ff;
    background: rgba(0,195,255,0.1); border: 1px solid rgba(0,195,255,0.25);
    border-radius: 2px; padding: 1px 7px; white-space: nowrap; transition: background 0.15s;
  }
  .oj-testid-row:hover .oj-testid-badge { background: rgba(0,195,255,0.2); }
  .oj-testid-name { font-size: 11px; color: #8aa8c8; }

  /* Submit button */
  .oj-btn {
    width: 100%; padding: 13px; background: transparent;
    border: 1px solid #00c3ff; border-radius: 3px; color: #00c3ff;
    font-family: 'Orbitron', monospace; font-size: 11px; font-weight: 700;
    letter-spacing: 0.2em; text-transform: uppercase; cursor: pointer;
    position: relative; overflow: hidden; transition: all 0.3s;
  }
  .oj-btn:hover:not(:disabled) {
    color: #fff; box-shadow: 0 0 20px rgba(0,195,255,0.35), inset 0 0 20px rgba(0,195,255,0.06);
    background: rgba(0,195,255,0.08);
  }
  .oj-btn:disabled { opacity: 0.35; cursor: not-allowed; }

  /* ── Loading ── */
  .oj-loading { padding: 28px 18px; text-align: center; }
  .oj-orbit-spinner { width: 80px; height: 80px; margin: 0 auto 18px; position: relative; }
  .oj-ring {
    position: absolute; inset: 0; border-radius: 50%; border: 2px solid transparent;
  }
  .oj-ring-1 { border-top-color: #00c3ff; border-right-color: rgba(0,195,255,0.25); animation: spin 1.1s linear infinite; box-shadow: 0 0 10px rgba(0,195,255,0.3); }
  .oj-ring-2 { inset: 10px; border-bottom-color: #00e5c0; border-left-color: rgba(0,229,192,0.25); animation: spin 0.85s linear infinite reverse; }
  .oj-ring-3 { inset: 22px; border-top-color: #f5a623; animation: spin 1.5s linear infinite; }
  .oj-ring-core {
    position: absolute; top: 50%; left: 50%;
    width: 8px; height: 8px; border-radius: 50%;
    background: #00c3ff; box-shadow: 0 0 12px #00c3ff;
    animation: pulse-core 1.4s ease-in-out infinite;
  }
  .oj-loading-title {
    font-family: 'Share Tech Mono', monospace; font-size: 11px;
    letter-spacing: 0.14em; color: #00c3ff; margin-bottom: 6px;
  }
  .oj-loading-desc {
    font-family: 'Share Tech Mono', monospace; font-size: 11px;
    color: #4a6585; line-height: 1.55; margin-bottom: 18px;
  }
  .oj-step {
    display: flex; align-items: center; gap: 10px; padding: 8px 11px;
    background: rgba(0,195,255,0.03); border: 1px solid rgba(0,195,255,0.08);
    border-radius: 2px; margin-bottom: 7px; font-family: 'Share Tech Mono', monospace;
    font-size: 10px; color: #4a6585; letter-spacing: 0.04em; transition: all 0.4s;
  }
  .oj-step.active { border-color: rgba(0,195,255,0.28); color: #e8f4ff; background: rgba(0,195,255,0.07); }
  .oj-step.done   { border-color: rgba(46,213,115,0.25); color: #2ed573; background: rgba(46,213,115,0.05); }
  .oj-step-spin   { width: 11px; height: 11px; border: 1.5px solid transparent; border-top-color: #00c3ff; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
  .oj-step-dot    { width: 11px; height: 11px; border-radius: 50%; border: 1.5px solid rgba(255,255,255,0.15); flex-shrink: 0; }
  .oj-step-check  { width: 11px; height: 11px; flex-shrink: 0; color: #2ed573; }

  /* ── Error banner ── */
  .oj-error {
    background: rgba(255,71,87,0.07); border: 1px solid rgba(255,71,87,0.35);
    border-radius: 3px; padding: 14px 16px; margin-bottom: 22px;
    animation: fade-in 0.3s ease both;
  }
  .oj-error-hdr {
    display: flex; align-items: center; gap: 7px; font-family: 'Share Tech Mono', monospace;
    font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: #ff4757;
    margin-bottom: 7px;
  }
  .oj-error-msg { font-size: 13px; color: #8aa8c8; line-height: 1.55; }

  /* ── Info panel (default right col) ── */
  .oj-pipeline-node {
    display: flex; align-items: center; gap: 11px; padding: 9px 12px;
    border: 1px solid rgba(0,195,255,0.08); border-radius: 3px;
    background: rgba(0,195,255,0.02); transition: all 0.2s;
  }
  .oj-pipeline-node:hover { border-color: rgba(0,195,255,0.22); background: rgba(0,195,255,0.05); }
  .oj-pipeline-dot { width: 8px; height: 8px; border-radius: 50%; border: 1.5px solid #00c3ff; flex-shrink: 0; }
  .oj-pipeline-line { width: 2px; height: 14px; background: rgba(0,195,255,0.15); margin-left: 19px; }
  .oj-pipeline-lbl { font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #8aa8c8; letter-spacing: 0.04em; }
  .oj-pipeline-sub { font-family: 'Share Tech Mono', monospace; font-size: 9px; color: #4a6585; margin-top: 1px; }
  .oj-metric { padding: 12px 0; border-bottom: 1px solid rgba(0,195,255,0.06); }
  .oj-metric:last-child { border-bottom: none; }
  .oj-metric-lbl { font-family: 'Share Tech Mono', monospace; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: #4a6585; margin-bottom: 3px; }
  .oj-metric-val { font-family: 'Share Tech Mono', monospace; font-size: 21px; color: #00c3ff; }
  .oj-metric-sub { font-size: 11px; color: #4a6585; margin-top: 2px; }

  /* ── Results ── */
  .oj-results { animation: fade-in 0.45s ease both; }
  .oj-case-row {
    display: flex; align-items: center; gap: 8px; margin-bottom: 18px;
    font-family: 'Share Tech Mono', monospace; font-size: 10px;
    color: #4a6585; letter-spacing: 0.08em;
  }
  .oj-case-id { color: rgba(0,195,255,0.7); font-size: 11px; }

  .oj-verdict {
    background: linear-gradient(135deg, rgba(0,195,255,0.05) 0%, rgba(0,229,192,0.03) 100%);
    border: 1px solid rgba(0,195,255,0.28); border-radius: 4px;
    padding: 22px 26px; margin-bottom: 14px; position: relative; overflow: hidden;
  }
  .oj-verdict::before {
    content: ''; position: absolute; left: 0; top: 0; bottom: 0;
    width: 3px; background: linear-gradient(180deg, #00c3ff, #00e5c0);
    box-shadow: 0 0 18px rgba(0,195,255,0.4);
  }
  .oj-verdict-lbl {
    font-family: 'Share Tech Mono', monospace; font-size: 10px;
    letter-spacing: 0.2em; text-transform: uppercase; color: #00c3ff; margin-bottom: 9px;
  }
  .oj-verdict-text { font-size: 14px; line-height: 1.7; color: #e8f4ff; font-weight: 300; }

  /* Liability */
  .oj-liab { padding: 18px 20px; }
  .oj-liab-objs { display: flex; justify-content: space-between; margin-bottom: 12px; }
  .oj-liab-name { font-family: 'Share Tech Mono', monospace; font-size: 10px; color: #8aa8c8; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .oj-liab-pct  { font-family: 'Orbitron', monospace; font-size: 26px; font-weight: 700; line-height: 1.1; }
  .oj-liab-lbl  { font-family: 'Share Tech Mono', monospace; font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase; color: #4a6585; }
  .oj-pct1 { color: #ff4757; }
  .oj-pct2 { color: #00c3ff; text-align: right; }
  .oj-gauge-track { height: 9px; border-radius: 2px; background: rgba(255,255,255,0.05); overflow: hidden; display: flex; margin-bottom: 5px; }
  .oj-gauge-1 { background: linear-gradient(90deg, #ff4757, rgba(255,71,87,0.7)); box-shadow: 0 0 10px rgba(255,71,87,0.4); height: 100%; transition: width 1s cubic-bezier(0.4,0,0.2,1); }
  .oj-gauge-2 { background: linear-gradient(90deg, rgba(0,195,255,0.7), #00c3ff);   box-shadow: 0 0 10px rgba(0,195,255,0.4); height: 100%; transition: width 1s cubic-bezier(0.4,0,0.2,1); }
  .oj-gauge-lbls { display: flex; justify-content: space-between; font-family: 'Share Tech Mono', monospace; font-size: 9px; color: #4a6585; margin-bottom: 12px; }
  .oj-treaty { padding-top: 11px; border-top: 1px solid rgba(0,195,255,0.07); font-family: 'Share Tech Mono', monospace; font-size: 10px; color: #4a6585; line-height: 1.5; }
  .oj-treaty span { color: rgba(245,166,35,0.75); }

  /* Data card */
  .oj-data-card { padding: 16px 18px; }
  .oj-data-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
  .oj-data-row:last-child { border-bottom: none; }
  .oj-data-key { font-family: 'Share Tech Mono', monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: #4a6585; }
  .oj-data-val { font-family: 'Share Tech Mono', monospace; font-size: 12px; color: #e8f4ff; text-align: right; }
  .oj-miss-val { font-family: 'Orbitron', monospace; font-size: 19px; font-weight: 700; color: #00c3ff; }
  .oj-miss-unit { font-size: 11px; color: #4a6585; margin-left: 3px; }

  .oj-badge { font-family: 'Share Tech Mono', monospace; font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; padding: 2px 7px; border-radius: 2px; font-weight: 600; }
  .oj-badge-active   { color: #2ed573; background: rgba(46,213,115,0.1);  border: 1px solid rgba(46,213,115,0.3); }
  .oj-badge-drifting { color: #f5a623; background: rgba(245,166,35,0.1);  border: 1px solid rgba(245,166,35,0.3); }
  .oj-badge-uncertain{ color: #a855f7; background: rgba(168,85,247,0.1);  border: 1px solid rgba(168,85,247,0.3); }
  .oj-badge-unknown  { color: #4a6585; background: rgba(255,255,255,0.04); border: 1px solid rgba(0,195,255,0.1); }
  .oj-badge-coll     { color: #ff4757; background: rgba(255,71,87,0.1); border: 1px solid rgba(255,71,87,0.3); }
  .oj-badge-nocoll   { color: #2ed573; background: rgba(46,213,115,0.1); border: 1px solid rgba(46,213,115,0.3); }

  /* Damage */
  .oj-damage-card { padding: 16px 18px; }
  .oj-sev-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid rgba(0,195,255,0.07); }
  .oj-sev {
    font-family: 'Orbitron', monospace; font-size: 10px; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase; padding: 4px 13px; border-radius: 2px;
  }
  .oj-sev-minor        { color: #2ed573; background: rgba(46,213,115,0.1); border: 1px solid rgba(46,213,115,0.3); }
  .oj-sev-moderate     { color: #f5a623; background: rgba(245,166,35,0.1); border: 1px solid rgba(245,166,35,0.3); }
  .oj-sev-severe       { color: #ff4757; background: rgba(255,71,87,0.1);  border: 1px solid rgba(255,71,87,0.3); }
  .oj-sev-catastrophic {
    color: #fff; background: rgba(255,71,87,0.18); border: 1px solid #ff4757;
    animation: danger-pulse 1.5s ease-in-out infinite;
  }
  .oj-sev-prob { font-family: 'Share Tech Mono', monospace; font-size: 10px; color: #4a6585; }
  .oj-no-damage { display: flex; align-items: center; gap: 8px; font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #2ed573; padding: 12px 0; }

  /* Legal */
  .oj-legal-card { padding: 16px 18px; }
  .oj-reasoning { font-size: 13px; line-height: 1.7; color: #8aa8c8; font-weight: 300; margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px solid rgba(0,195,255,0.07); }
  .oj-doctrines-lbl { font-family: 'Share Tech Mono', monospace; font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: #4a6585; margin-bottom: 8px; }
  .oj-pills { display: flex; flex-wrap: wrap; gap: 7px; }
  .oj-pill { font-family: 'Share Tech Mono', monospace; font-size: 10px; letter-spacing: 0.05em; padding: 3px 11px; border-radius: 2px; color: #00e5c0; background: rgba(0,229,192,0.07); border: 1px solid rgba(0,229,192,0.22); }
  .oj-no-pills { font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #4a6585; font-style: italic; }

  /* Recs */
  .oj-recs-card { padding: 16px 18px; }
  .oj-rec { display: flex; align-items: flex-start; gap: 11px; font-size: 13px; line-height: 1.55; color: #8aa8c8; font-weight: 300; margin-bottom: 9px; }
  .oj-rec:last-child { margin-bottom: 0; }
  .oj-rec-bullet {
    width: 17px; height: 17px; border: 1px solid rgba(0,195,255,0.3);
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 1px;
  }
  .oj-rec-dot { width: 5px; height: 5px; border-radius: 50%; background: #00c3ff; }

  /* Footer */
  .oj-footer {
    margin-top: 56px; padding-top: 18px; border-top: 1px solid rgba(0,195,255,0.08);
    display: flex; justify-content: space-between; align-items: center;
    font-family: 'Share Tech Mono', monospace; font-size: 10px; color: #4a6585; letter-spacing: 0.07em;
    flex-wrap: wrap; gap: 8px;
  }
  .oj-footer-left { display: flex; gap: 18px; flex-wrap: wrap; }
  .oj-footer-sep { color: rgba(0,195,255,0.15); }
`;

/* ═══════════════════════════════════════════
   CONSTANTS
═══════════════════════════════════════════ */

// Set these in your .env file (local) or Netlify environment variables (prod):
//   VITE_RUNPOD_ENDPOINT_ID=abc1234xyz
//   VITE_RUNPOD_API_KEY=your_runpod_api_key
const RUNPOD_ENDPOINT_ID = import.meta.env.VITE_RUNPOD_ENDPOINT_ID || "";
const RUNPOD_API_KEY     = import.meta.env.VITE_RUNPOD_API_KEY     || "";
const RUNPOD_BASE        = `https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}`;
const RUNPOD_URL         = `${RUNPOD_BASE}/runsync`;
const RUNPOD_HEALTH_URL  = `${RUNPOD_BASE}/health`;

const TEST_IDS = [
  { id: "25544", name: "ISS (ZARYA) — International Space Station" },
  { id: "43013", name: "STARLINK-1007 — SpaceX Starlink (Active)" },
  { id: "37849", name: "COSMOS 2251 DEB — Russian Debris" },
  { id: "28353", name: "FENGYUN 1C DEB — Chinese ASAT Debris" },
  { id: "20580", name: "HST — Hubble Space Telescope" },
];

const STEPS = [
  "PhysicsForensic — Fetching TLE data from CelesTrak",
  "PhysicsForensic — Propagating orbits, computing TCA",
  "MaritimeScholar — Searching legal precedents & treaty articles",
  "LiabilityJudge  — Synthesizing evidence, rendering judgment",
];

const STEP_DELAYS   = [0, 4000, 10000, 18000];
const STEP_DONE_AT  = [4000, 10000, 18000, 99999];

/* ═══════════════════════════════════════════
   STARFIELD (canvas hook)
═══════════════════════════════════════════ */
function Starfield() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx    = canvas.getContext("2d");
    let stars    = [];
    let raf;

    const resize = () => {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    const init = () => {
      stars = Array.from({ length: 260 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.1 + 0.2,
        a: Math.random() * 0.55 + 0.1,
        spd: Math.random() * 0.015 + 0.003,
        off: Math.random() * Math.PI * 2,
      }));
    };

    let t = 0;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      t += 0.008;
      stars.forEach(s => {
        const a = s.a * (0.6 + 0.4 * Math.sin(t + s.off));
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180,220,255,${a})`;
        ctx.fill();
      });
      raf = requestAnimationFrame(draw);
    };

    resize(); init(); draw();
    window.addEventListener("resize", () => { resize(); init(); });
    return () => { cancelAnimationFrame(raf); };
  }, []);
  return <canvas ref={ref} className="oj-canvas" />;
}

/* ═══════════════════════════════════════════
   CLOCK hook
═══════════════════════════════════════════ */
function useClock() {
  const [clock, setClock] = useState("");
  useEffect(() => {
    const tick = () => {
      const n = new Date();
      const pad = v => String(v).padStart(2, "0");
      setClock(`UTC ${pad(n.getUTCHours())}:${pad(n.getUTCMinutes())}:${pad(n.getUTCSeconds())}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return clock;
}

/* ═══════════════════════════════════════════
   LOADING STEPS hook
═══════════════════════════════════════════ */
function useLoadingSteps(active) {
  const [stepState, setStepState] = useState(
    STEPS.map(() => "idle")
  );
  const timers = useRef([]);

  const clear = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  useEffect(() => {
    if (!active) { clear(); setStepState(STEPS.map(() => "idle")); return; }

    STEP_DELAYS.forEach((delay, i) => {
      timers.current.push(setTimeout(() => {
        setStepState(prev => {
          const next = [...prev];
          next[i] = "active";
          if (i > 0) next[i - 1] = "done";
          return next;
        });
      }, delay));
    });

    return clear;
  }, [active, clear]);

  return stepState;
}

/* ═══════════════════════════════════════════
   STATUS BADGE helper
═══════════════════════════════════════════ */
function statusBadgeClass(s) {
  if (!s) return "oj-badge oj-badge-unknown";
  const u = s.toUpperCase();
  if (u === "ACTIVE")    return "oj-badge oj-badge-active";
  if (u === "DRIFTING")  return "oj-badge oj-badge-drifting";
  if (u === "UNCERTAIN") return "oj-badge oj-badge-uncertain";
  return "oj-badge oj-badge-unknown";
}

function sevClass(s) {
  if (!s) return "oj-sev";
  const u = s.toUpperCase();
  if (u === "MINOR")        return "oj-sev oj-sev-minor";
  if (u === "MODERATE")     return "oj-sev oj-sev-moderate";
  if (u === "SEVERE")       return "oj-sev oj-sev-severe";
  if (u === "CATASTROPHIC") return "oj-sev oj-sev-catastrophic";
  return "oj-sev";
}

/* ═══════════════════════════════════════════
   ENDPOINT STATUS BADGE
═══════════════════════════════════════════ */
function EndpointStatus({ ok }) {
  const color  = ok === null ? "#4a6585" : ok ? "#2ed573" : "#ff4757";
  const shadow = ok ? "0 0 7px rgba(46,213,115,0.6)" : "none";
  const label  = ok === null ? "CHECKING" : ok ? "ENDPOINT ONLINE" : "ENDPOINT OFFLINE";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7,
                  fontFamily: "'Share Tech Mono', monospace", fontSize: 10,
                  letterSpacing: "0.1em", color }}>
      <div style={{ width: 6, height: 6, borderRadius: "50%",
                    background: color, boxShadow: shadow,
                    animation: ok === null ? "pulse-dot 1.5s infinite" : "none",
                    transition: "background 0.3s" }} />
      <span>{label}</span>
    </div>
  );
}

/* ═══════════════════════════════════════════
   PANEL wrapper
═══════════════════════════════════════════ */
function Panel({ title, icon, children, style }) {
  return (
    <div className="oj-panel" style={style}>
      <div className="oj-panel-corner-tl" />
      <div className="oj-panel-corner-br" />
      <div className="oj-panel-hdr">
        <div className="oj-panel-hdr-icon">{icon}</div>
        <span className="oj-panel-title">{title}</span>
      </div>
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════════
   DEFAULT RIGHT COL
═══════════════════════════════════════════ */
function DefaultInfoPanel() {
  const pipeline = [
    { label: "PhysicsForensic Agent", sub: "SGP4 propagation · TLE fetch · TCA computation", color: "#00c3ff" },
    { label: "MaritimeScholar Agent", sub: "Precedent search · Treaty analysis · Liability factors", color: "#00e5c0" },
    { label: "LiabilityJudge Agent",  sub: "Evidence synthesis · Fault assignment · Judgment", color: "#f5a623" },
  ];
  const metrics = [
    { lbl: "Tracked Debris Objects", val: "36,000+", sub: "Catalogued by NORAD / Space Force" },
    { lbl: "Legal Framework", val: "1972 Convention", sub: "UN Liability Convention — Article III" },
    { lbl: "Collision Threshold", val: "1.0 km", sub: "Below this distance = collision event" },
    { lbl: "Conjunction Risk Threshold", val: "10.0 km", sub: "CDM issuance level — triggers legal analysis" },
  ];
  return (
    <>
      <Panel
        title="Agent Pipeline"
        icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>}
        style={{ marginBottom: 14 }}
      >
        <div className="oj-panel-body">
          {pipeline.map((p, i) => (
            <div key={i}>
              <div className="oj-pipeline-node">
                <div className="oj-pipeline-dot" style={{ borderColor: p.color }} />
                <div>
                  <div className="oj-pipeline-lbl">{p.label}</div>
                  <div className="oj-pipeline-sub">{p.sub}</div>
                </div>
              </div>
              {i < pipeline.length - 1 && <div className="oj-pipeline-line" />}
            </div>
          ))}
        </div>
      </Panel>

      <Panel
        title="System Metrics"
        icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>}
      >
        <div className="oj-panel-body">
          {metrics.map((m, i) => (
            <div className="oj-metric" key={i}>
              <div className="oj-metric-lbl">{m.lbl}</div>
              <div className="oj-metric-val">{m.val}</div>
              <div className="oj-metric-sub">{m.sub}</div>
            </div>
          ))}
        </div>
      </Panel>
    </>
  );
}

/* ═══════════════════════════════════════════
   RESULTS PANEL
═══════════════════════════════════════════ */
function ResultsPanel({ caseId, judgment }) {
  const j  = judgment;
  const pf = j.physical_findings || {};
  const o1 = pf.object_1 || {};
  const o2 = pf.object_2 || {};
  const f1 = parseFloat(j.fault_percentage_object_1) || 0;
  const f2 = parseFloat(j.fault_percentage_object_2) || 0;
  const dmg = j.damage_estimate;

  const [gaugeReady, setGaugeReady] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setGaugeReady(true), 80);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="oj-results">
      {/* Case ID */}
      <div className="oj-case-row">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>
        CASE ID: <span className="oj-case-id">{caseId || "—"}</span>
      </div>

      {/* Verdict */}
      <div className="oj-verdict">
        <div className="oj-verdict-lbl">⬡ FINAL VERDICT</div>
        <div className="oj-verdict-text">{j.case_summary || "Judgment rendered."}</div>
      </div>

      {/* Liability split */}
      <Panel
        title="Liability Assignment"
        icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>}
        style={{ marginBottom: 14 }}
      >
        <div className="oj-liab">
          <div className="oj-liab-objs">
            <div>
              <div className="oj-liab-name">{o1.sat_name || "Object 1"}</div>
              <div className={`oj-liab-pct oj-pct1`}>{f1.toFixed(1)}%</div>
              <div className="oj-liab-lbl">FAULT</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="oj-liab-name" style={{ textAlign: "right" }}>{o2.sat_name || "Object 2"}</div>
              <div className="oj-liab-pct oj-pct2">{f2.toFixed(1)}%</div>
              <div className="oj-liab-lbl">FAULT</div>
            </div>
          </div>
          <div className="oj-gauge-track">
            <div className="oj-gauge-1" style={{ width: gaugeReady ? f1 + "%" : "0%" }} />
            <div className="oj-gauge-2" style={{ width: gaugeReady ? f2 + "%" : "0%" }} />
          </div>
          <div className="oj-gauge-lbls">
            <span>OBJECT 1 LIABILITY</span>
            <span>OBJECT 2 LIABILITY</span>
          </div>
          {j.treaty_basis && (
            <div className="oj-treaty">TREATY BASIS: <span>{j.treaty_basis}</span></div>
          )}
        </div>
      </Panel>

      {/* Physics + Damage row */}
      <div className="oj-results-grid">
        <Panel
          title="Physics Findings"
          icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>}
        >
          <div className="oj-data-card">
            <div className="oj-data-row">
              <span className="oj-data-key">Miss Distance</span>
              <span className="oj-data-val">
                <span className="oj-miss-val">{pf.miss_distance_km != null ? pf.miss_distance_km.toFixed(3) : "—"}</span>
                <span className="oj-miss-unit">km</span>
              </span>
            </div>
            <div className="oj-data-row">
              <span className="oj-data-key">Object 1 Status</span>
              <span className={statusBadgeClass(o1.status)}>{o1.status || "—"}</span>
            </div>
            <div className="oj-data-row">
              <span className="oj-data-key">Object 2 Status</span>
              <span className={statusBadgeClass(o2.status)}>{o2.status || "—"}</span>
            </div>
            <div className="oj-data-row">
              <span className="oj-data-key">Collision</span>
              {pf.collision_occurred === true  && <span className="oj-badge oj-badge-coll">YES — COLLISION</span>}
              {pf.collision_occurred === false && <span className="oj-badge oj-badge-nocoll">NO COLLISION</span>}
              {pf.collision_occurred == null   && <span className="oj-data-val">—</span>}
            </div>
          </div>
        </Panel>

        <Panel
          title="Damage Assessment"
          icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>}
        >
          <div className="oj-damage-card">
            {dmg && dmg.severity ? (
              <>
                <div className="oj-sev-row">
                  <span className={sevClass(dmg.severity)}>{dmg.severity}</span>
                  <span className="oj-sev-prob">{dmg.damage_probability || ""}</span>
                </div>
                <div className="oj-data-row">
                  <span className="oj-data-key">Kinetic Energy</span>
                  <span className="oj-data-val">{dmg.kinetic_energy_mj != null ? `${dmg.kinetic_energy_mj} MJ` : "—"}</span>
                </div>
                <div className="oj-data-row">
                  <span className="oj-data-key">Relative Speed</span>
                  <span className="oj-data-val">{dmg.collision_speed_m_s != null ? `${dmg.collision_speed_m_s.toFixed(1)} m/s` : "—"}</span>
                </div>
                {dmg.estimated_loss_usd != null && (
                  <div className="oj-data-row">
                    <span className="oj-data-key">Est. Loss</span>
                    <span className="oj-data-val" style={{ color: "#f5a623" }}>
                      ${dmg.estimated_loss_usd.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                )}
              </>
            ) : (
              <div className="oj-no-damage">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                No collision — no damage assessment
              </div>
            )}
          </div>
        </Panel>
      </div>

      {/* Legal Reasoning */}
      <Panel
        title="Legal Reasoning"
        icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>}
        style={{ marginBottom: 14 }}
      >
        <div className="oj-legal-card">
          <div className="oj-reasoning">{j.primary_reasoning || "—"}</div>
          <div className="oj-doctrines-lbl">Applied Doctrines</div>
          <div className="oj-pills">
            {(j.applicable_doctrines || []).length === 0
              ? <span className="oj-no-pills">No specific doctrines — no conjunction risk.</span>
              : (j.applicable_doctrines || []).map((d, i) => (
                  <span key={i} className="oj-pill">{d}</span>
                ))
            }
          </div>
        </div>
      </Panel>

      {/* Recommendations */}
      <Panel
        title="Recommendations"
        icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>}
      >
        <div className="oj-recs-card">
          {(j.recommendations || []).map((r, i) => (
            <div className="oj-rec" key={i}>
              <div className="oj-rec-bullet"><div className="oj-rec-dot" /></div>
              <span>{r}</span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

/* ═══════════════════════════════════════════
   MAIN APP
═══════════════════════════════════════════ */
export default function OrbitalJurist() {
  const clock = useClock();

  // RunPod endpoint health
  const [runpodOk, setRunpodOk] = useState(null);

  const checkHealth = useCallback(async () => {
    if (!RUNPOD_ENDPOINT_ID || !RUNPOD_API_KEY) { setRunpodOk(false); return; }
    try {
      const r = await fetch(RUNPOD_HEALTH_URL, {
        headers: { "Authorization": `Bearer ${RUNPOD_API_KEY}` },
        signal: AbortSignal.timeout(4000),
      });
      setRunpodOk(r.ok);
    } catch { setRunpodOk(false); }
  }, []);

  useEffect(() => {
    checkHealth();
    const id = setInterval(checkHealth, 20000);
    return () => clearInterval(id);
  }, [checkHealth]);

  const [obj1, setObj1] = useState("");
  const [obj2, setObj2] = useState("");
  const [conjTime, setConjTime] = useState("");

  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);
  const [result,   setResult]   = useState(null);

  const stepState = useLoadingSteps(loading);

  const fillId = useCallback((id) => {
    if (!obj1) { setObj1(id); return; }
    if (!obj2 && obj1 !== id) { setObj2(id); return; }
    setObj1(id);
  }, [obj1, obj2]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setError(null);

    const id1 = parseInt(obj1, 10);
    const id2 = parseInt(obj2, 10);

    if (!id1 || !id2) { setError("Both NORAD IDs are required."); return; }
    if (id1 === id2)   { setError("Object 1 and Object 2 must be different NORAD IDs."); return; }

    if (!RUNPOD_ENDPOINT_ID || !RUNPOD_API_KEY) {
      setError("RunPod credentials not configured. Set VITE_RUNPOD_ENDPOINT_ID and VITE_RUNPOD_API_KEY in your .env file.");
      return;
    }

    const conjunctionTime = conjTime ? new Date(conjTime).toISOString() : null;

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch(RUNPOD_URL, {
        method: "POST",
        headers: {
          "Content-Type":  "application/json",
          "Authorization": `Bearer ${RUNPOD_API_KEY}`,
        },
        body: JSON.stringify({
          input: { object_1_id: id1, object_2_id: id2, conjunction_time: conjunctionTime },
        }),
      });

      let data;
      try { data = await response.json(); }
      catch { throw new Error(`RunPod returned non-JSON (HTTP ${response.status}).`); }

      if (!response.ok) {
        throw new Error(data?.detail || data?.error || `HTTP error ${response.status}`);
      }

      // RunPod runsync response: { id, status: "COMPLETED"|"FAILED", output: {...}, error? }
      if (data.status === "FAILED") {
        throw new Error(data.error || "RunPod job failed.");
      }
      if (data.status !== "COMPLETED") {
        throw new Error(`Unexpected job status: ${data.status}`);
      }

      const output = data.output;
      if (!output) throw new Error("RunPod returned no output.");
      if (output.error) throw new Error(output.error);
      if (!output.judgment) throw new Error("Output contained no judgment data.");

      setResult({ case_id: output.metadata?.case_id || data.id, judgment: output.judgment });
    } catch (err) {
      setError(err.message || "Unexpected error contacting RunPod.");
    } finally {
      setLoading(false);
    }
  }, [obj1, obj2, conjTime]);

  return (
    <>
      <style>{GLOBAL_CSS}</style>

      <Starfield />
      <div className="oj-scanline-overlay" />

      <div className="oj-root">

        {/* ── System bar ── */}
        <div className="oj-sysbar">
          <div className="oj-sysbar-left">
            <div className="oj-dot oj-dot-g" />
            <div className="oj-dot oj-dot-c" />
            <div className="oj-dot oj-dot-a" />
            <span>SYS // ORBITAL-JURIST v1.0.0 // ONLINE</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <EndpointStatus ok={runpodOk} />
            <span className="oj-clock">{clock}</span>
          </div>
        </div>

        {/* ── No settings drawer — config via env vars ── */}

        {/* ── Hero ── */}
        <div className="oj-hero">
          <div>
            <div className="oj-hero-eyebrow">⬡ SPACE SITUATIONAL AWARENESS SYSTEM</div>
            <h1 className="oj-h1">Orbital Jurist</h1>
            <div className="oj-subtitle">Autonomous Space Debris Liability Arbiter</div>
            <p className="oj-hero-desc">
              Multi-agent AI system combining orbital mechanics, maritime law precedents,
              and autonomous adjudication to render legally-grounded liability judgments
              for satellite conjunction events and orbital collisions.
            </p>
          </div>
          <svg className="oj-orbit-deco" viewBox="0 0 280 280" fill="none">
            <circle cx="140" cy="140" r="110" stroke="rgba(0,195,255,0.5)" strokeWidth="1" strokeDasharray="4 6"/>
            <circle cx="140" cy="140" r="72"  stroke="rgba(0,229,192,0.4)" strokeWidth="1" strokeDasharray="2 4"/>
            <circle cx="140" cy="140" r="44"  stroke="rgba(245,166,35,0.35)" strokeWidth="1"/>
            <circle cx="140" cy="30"  r="5" fill="rgba(0,195,255,0.8)"/>
            <circle cx="212" cy="140" r="3" fill="rgba(0,229,192,0.7)"/>
            <circle cx="96"  cy="200" r="4" fill="rgba(245,166,35,0.6)"/>
            <circle cx="140" cy="140" r="7" fill="rgba(0,195,255,0.25)" stroke="rgba(0,195,255,0.7)" strokeWidth="1.5"/>
          </svg>
        </div>

        <div className="oj-divider" />

        {/* ── Error banner ── */}
        {error && (
          <div className="oj-error">
            <div className="oj-error-hdr">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              ARBITRATION FAILED
            </div>
            <div className="oj-error-msg">{error}</div>
          </div>
        )}

        {/* ── Main grid ── */}
        <div className="oj-grid">

          {/* LEFT: form */}
          <Panel
            title="Conjunction Analysis Parameters"
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 19.07a10 10 0 0 1 0-14.14"/><path d="M22.54 6.08a16 16 0 0 1 0 11.84M1.46 17.92a16 16 0 0 1 0-11.84"/></svg>}
          >
            <div className="oj-panel-body">
              {!loading ? (
                <form onSubmit={handleSubmit}>
                  <div className="oj-form-group">
                    <label className="oj-form-label">Object 1 NORAD ID<span>*</span></label>
                    <input className="oj-input" type="number" value={obj1}
                      onChange={e => setObj1(e.target.value)}
                      placeholder="e.g. 25544" min="1" max="90000" required />
                    <div className="oj-input-hint">NORAD catalog number of the first orbital object</div>
                  </div>
                  <div className="oj-form-group">
                    <label className="oj-form-label">Object 2 NORAD ID<span>*</span></label>
                    <input className="oj-input" type="number" value={obj2}
                      onChange={e => setObj2(e.target.value)}
                      placeholder="e.g. 43013" min="1" max="90000" required />
                    <div className="oj-input-hint">NORAD catalog number of the second orbital object</div>
                  </div>
                  <div className="oj-form-group">
                    <label className="oj-form-label">
                      Conjunction Time&nbsp;
                      <span style={{ color: "#4a6585", letterSpacing: 0 }}>(optional)</span>
                    </label>
                    <input className="oj-input" type="datetime-local" value={conjTime}
                      onChange={e => setConjTime(e.target.value)} />
                    <div className="oj-input-hint">Leave blank to use current UTC time</div>
                  </div>

                  {/* Test IDs */}
                  <div className="oj-testids">
                    <div className="oj-testids-title">⬡ Valid Test IDs — Click to autofill</div>
                    {TEST_IDS.map(t => (
                      <div key={t.id} className="oj-testid-row" onClick={() => fillId(t.id)}>
                        <span className="oj-testid-badge">{t.id}</span>
                        <span className="oj-testid-name">{t.name}</span>
                      </div>
                    ))}
                  </div>

                  <button className="oj-btn" type="submit" disabled={loading}>
                    ⚖ Render Judgment
                  </button>
                </form>
              ) : (
                <div className="oj-loading">
                  <div className="oj-orbit-spinner">
                    <div className="oj-ring oj-ring-1" />
                    <div className="oj-ring oj-ring-2" />
                    <div className="oj-ring oj-ring-3" />
                    <div className="oj-ring-core" />
                  </div>
                  <div className="oj-loading-title">ORCHESTRATING MULTI-AGENT WORKFLOW</div>
                  <div className="oj-loading-desc">
                    Physics · Maritime Law · Adjudication<br />
                    This may take 10–30 seconds.
                  </div>
                  <div>
                    {STEPS.map((label, i) => {
                      const s = stepState[i];
                      return (
                        <div key={i} className={`oj-step ${s === "active" ? "active" : s === "done" ? "done" : ""}`}>
                          {s === "active" && <div className="oj-step-spin" />}
                          {s === "done"   && (
                            <svg className="oj-step-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                              <polyline points="20 6 9 17 4 12"/>
                            </svg>
                          )}
                          {s === "idle"   && <div className="oj-step-dot" />}
                          <span>{label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </Panel>

          {/* RIGHT: info or results */}
          <div>
            {result
              ? <ResultsPanel caseId={result.case_id} judgment={result.judgment} />
              : <DefaultInfoPanel />
            }
          </div>

        </div>

        {/* ── Footer ── */}
        <div className="oj-footer">
          <div className="oj-footer-left">
            <span>ORBITAL JURIST v1.0.0</span>
            <span className="oj-footer-sep">|</span>
            <span>LANGGRAPH + GROQ</span>
            <span className="oj-footer-sep">|</span>
            <span>SGP4 + CELESTRAK TLE DATA</span>
            <span className="oj-footer-sep">|</span>
            <span style={{ color: "rgba(0,195,255,0.45)" }}>
              RunPod: {RUNPOD_ENDPOINT_ID ? `…${RUNPOD_ENDPOINT_ID.slice(-8)}` : "NOT CONFIGURED"}
            </span>
          </div>
          <span>⬡ IN ORBIT, EVERY COLLISION IS PREVENTABLE</span>
        </div>

      </div>
    </>
  );
}