#!/usr/bin/env node
/**
 * HUBEX Roadmap Viewer — Minimaler Server
 * Parsed ROADMAP.md und zeigt den Stand als Dashboard.
 *
 * SETUP: cd cc-system && npm install && node cc-server.js
 * OPEN:  http://localhost:3131
 */

const http = require('http');
const fs   = require('fs');
const path = require('path');

const PORT        = 3131;
const PROJECT_DIR = path.resolve(__dirname, '..');
const ROADMAP     = path.join(PROJECT_DIR, 'ROADMAP.md');

// Parse ROADMAP.md
function parseRoadmap() {
  let md;
  try { md = fs.readFileSync(ROADMAP, 'utf8'); }
  catch(e) { return { milestones: [], error: 'ROADMAP.md nicht gefunden' }; }

  const phases = [];
  let currentPhase = null;
  let current = null;

  // Derive status from line content: ✅, [done], [todo], ← AKTUELL, [in-progress]
  function deriveStatus(line) {
    if (/← ?AKTUELL/i.test(line)) return 'in-progress';
    if (/\[done\]/i.test(line) || /✅/.test(line) || /ABGESCHLOSSEN/i.test(line) || /DONE/i.test(line)) return 'done';
    if (/\[in[- ]?progress\]/i.test(line)) return 'in-progress';
    return 'todo';
  }

  // Extract hours from description: (~2h), (2h), — 2h
  function extractHours(text) {
    const m = text.match(/\(~?(\d+)h\)/);
    if (m) return parseInt(m[1]);
    const m2 = text.match(/— (\d+)h\b/);
    if (m2) return parseInt(m2[1]);
    return 0;
  }

  // Clean name: remove status markers, brackets, ✅, ← AKTUELL etc.
  function cleanName(name) {
    return name
      .replace(/\[(?:done|todo|in[- ]?progress)\]/gi, '')
      .replace(/✅/g, '')
      .replace(/← ?AKTUELL/gi, '')
      .replace(/\bDONE\b/gi, '')
      .replace(/\bABGESCHLOSSEN\b/gi, '')
      .trim()
      .replace(/\s+/g, ' ');
  }

  for (const line of md.split('\n')) {
    // Phase headers: ## Phase N: Name  OR  ## QA: Name
    const phMatch = line.match(/^## (?:Phase (\d+\w*)|QA): (.+)/);
    if (phMatch) {
      const status = deriveStatus(line);
      currentPhase = { name: cleanName(phMatch[2]), status, milestones: [] };
      phases.push(currentPhase);
      continue;
    }

    // Milestone headers: ### Milestone N[.x]: Name  OR  ### Block X: Name
    const msMatch = line.match(/^#{2,3} ((?:Milestone|Block) [\d.a-zA-Z_-]+):\s*(.+)/);
    if (msMatch) {
      const status = deriveStatus(line);
      current = { id: msMatch[1], name: cleanName(msMatch[2]), status, steps: [] };
      if (currentPhase) currentPhase.milestones.push(current);
      continue;
    }

    if (!current) continue;

    // Step lines — multiple formats:
    // - [x] Step N — Desc
    // - [x] V1 — Desc
    // - [x] **Bold** — Desc
    // - [x] A.1 — Desc
    // - [ ] Description without step number
    const stepMatch = line.match(/^- \[([ x])\] ((?:Step|V)\s*\d+)\s*—\s*(.+)/);
    if (stepMatch) {
      const done = stepMatch[1] === 'x';
      const rawDesc = stepMatch[3];
      const isActive = /← ?AKTUELL/i.test(rawDesc);
      const hours = extractHours(rawDesc);
      const name = rawDesc.replace(/\(~?\d+h\)/g, '').replace(/← ?AKTUELL/gi, '').trim();
      current.steps.push({ id: stepMatch[2], name, hours, done, active: isActive });
      continue;
    }

    // Generic checkbox lines: - [x] **Text** or - [x] Text — Desc or - [ ] Text
    const genericMatch = line.match(/^- \[([ x])\] \*{0,2}(.+?)(?:\*{0,2})\s*(?:—\s*(.+))?$/);
    if (genericMatch) {
      const done = genericMatch[1] === 'x';
      const rawName = (genericMatch[2] + (genericMatch[3] ? ' — ' + genericMatch[3] : '')).replace(/\*{1,2}/g, '');
      const isActive = /← ?AKTUELL/i.test(rawName);
      const hours = extractHours(rawName);
      const name = rawName.replace(/\(~?\d+h\)/g, '').replace(/← ?AKTUELL/gi, '').trim().substring(0, 120);
      const id = name.substring(0, 20).replace(/[^a-zA-Z0-9]/g, '_');
      current.steps.push({ id, name, hours, done, active: isActive });
    }
  }

  const milestones = phases.flatMap(p => p.milestones);
  const totalSteps = milestones.reduce((s, m) => s + m.steps.length, 0);
  const doneSteps  = milestones.reduce((s, m) => s + m.steps.filter(x => x.done).length, 0);
  const totalHours = milestones.reduce((s, m) => s + m.steps.reduce((a, x) => a + x.hours, 0), 0);
  const doneHours  = milestones.reduce((s, m) => s + m.steps.filter(x => x.done).reduce((a, x) => a + x.hours, 0), 0);

  return { phases, milestones, totalSteps, doneSteps, totalHours, doneHours, pct: totalSteps ? Math.round(doneSteps / totalSteps * 100) : 0 };
}

// Serve
const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');

  if (req.url === '/api/roadmap') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(parseRoadmap()));
    return;
  }

  if (req.url === '/' || req.url === '/dashboard.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    try { res.end(fs.readFileSync(path.join(__dirname, 'dashboard.html'), 'utf8')); }
    catch(e) { res.end('<h1>dashboard.html nicht gefunden</h1>'); }
    return;
  }

  if (req.url === '/produkt' || req.url === '/produkt.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    try { res.end(fs.readFileSync(path.join(__dirname, 'produkt.html'), 'utf8')); }
    catch(e) { res.end('<h1>produkt.html nicht gefunden</h1>'); }
    return;
  }

  if (req.url === '/product' || req.url === '/product.html') {
    // Redirect English path to produkt.html (same file)
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    try { res.end(fs.readFileSync(path.join(__dirname, 'produkt.html'), 'utf8')); }
    catch(e) { res.end('<h1>produkt.html nicht gefunden</h1>'); }
    return;
  }

  res.writeHead(404);
  res.end('Not found');
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`\n  HUBEX Roadmap Viewer`);
  console.log(`  http://localhost:${PORT}\n`);
});
