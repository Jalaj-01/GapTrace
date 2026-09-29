# GapTrace: Lead Product Design & Frontend Implementation Report

**Project Title:** *GapTrace: An Evidence-Grounded NLP Framework for Temporal Research Gap Discovery and Verification*  
**Application Shell:** React 18, Vite, Vanilla CSS Design System, Lucide Icons  
**Design Philosophy:** Clean, intelligent, minimal, academic, calm, modern AI workspace inspired by ChatGPT, Claude, and Gemini usability patterns without copying branding or aesthetics.

---

## 1. Executive Summary

The frontend interface for **GapTrace** has been designed and implemented from the ground up as a modern, minimalist research-AI workspace. The application shell provides a clear 3-part structural paradigm:
- **Left:** Slim, collapsible sidebar (~260px desktop, drawer on mobile) for navigation, research history, theme selection, and scholar profile.
- **Center:** Main research workspace with generous whitespace, minimal academic aesthetics, and fluid view transitions.
- **Bottom Center:** Large rounded **Research Input Composer** featuring multi-PDF drag-and-drop ingestion, evidence querying, and gap analysis triggering.

The frontend is connected directly to the FastAPI backend service layer and includes dedicated views for Paper Ingestion, Research Landscape, Potential Gaps Catalogue, Interactive Knowledge Graph, and Evidence Exploration.

---

## 2. Core Architecture & Component Hierarchy

```
frontend/src/
├── contexts/
│   ├── ThemeContext.jsx          # Dark, Light, System modes with localStorage persistence
│   └── ResearchContext.jsx       # Global workspace views, active session, staged files, multi-stage loader
├── services/
│   ├── api.js                   # API client for /api/v1 (health, upload, papers, Phase 2 NLP endpoints)
│   └── researchData.js          # Grounded academic gap intelligence, timelines, evidence, and graphs
├── components/
│   ├── layout/
│   │   ├── Sidebar.jsx          # GapTrace branding, + New Research CTA, navigation, recent sessions, theme toggle
│   │   ├── Header.jsx           # Sidebar toggle, view breadcrumb, API status badge, quick upload CTA
│   │   └── MainWorkspace.jsx    # Coordinating Welcome, Session, Library, Landscape, Gaps, Graph, Evidence
│   ├── research/
│   │   ├── ResearchComposer.jsx # Bottom-center prompt container, PDF staging pills, action toolbar
│   │   ├── PaperUploaderModal.jsx# Multi-file drag & drop modal with stage progression (uploading->ready)
│   │   ├── ResearchSessionView.jsx# Session banner, focus input, tabs (Overview, Evidence, Timeline, etc.)
│   │   ├── EvidenceCard.jsx     # Structured scientific quotes with page/section provenance & copy action
│   │   ├── GapTimeline.jsx      # Minimalist temporal progression tracking (2021 limitation -> 2026 gap)
│   │   └── ResearchGraphView.jsx# Interactive SVG graph network with entity filters, zoom, and inspector
│   └── ui/
│       ├── SettingsModal.jsx    # Appearance and confidence threshold configuration
│       └── AboutModal.jsx       # Academic citation, architectural pipeline overview, project vision
├── pages/
│   ├── PapersPage.jsx           # Ingested PDF paper library with section drill-down & NLP processing
│   ├── LandscapePage.jsx        # Scientific domain clusters and temporal volume trends
│   ├── PotentialGapsPage.jsx    # Catalogue of persistent, emerging, and addressed gaps
│   └── EvidenceExplorerPage.jsx # Full-text discourse search across sentences with page numbers
├── App.jsx                      # App shell with responsive breakpoint listener & providers
├── App.css                      # Complete academic theme stylesheet
└── index.css                    # Design tokens & color variables for Dark/Light modes
```

---

## 3. Design System & Theme Specifications

### Dark Mode (Primary Theme)
- **Background Base:** Genuine dark charcoal (`#0B0B0C`).
- **Sidebar & Modal:** Deep dark gray (`#101114` / `#131519`).
- **Cards & Surfaces:** Refined dark surfaces (`#15171B` / `#191C22`).
- **Borders:** Subtle restrained gray (`#21242B` / `#2A2F38`).
- **Typography:** Pure off-white (`#F3F4F6`) with muted secondary gray (`#9CA3AF`).
- **Accent:** Restrained academic sapphire/indigo (`#3B82F6` / `rgba(59, 130, 246, 0.12)`).
- **Aesthetic Goal:** Avoid loud gaming glows and neon gradients; maintain a calm, scholarly ambiance for deep reading and verification.

### Light Mode (Academic Theme)
- **Background Base:** Very light gray / off-white (`#F8F9FA`).
- **Cards & Sidebar:** Pure white (`#FFFFFF`).
- **Borders:** Clean neutral gray (`#E5E7EB`).
- **Typography:** Dark charcoal (`#111827`) with secondary slate (`#4B5563`).
- **Accent:** Academic blue (`#2563EB`).

### Theme Switcher
- Fast, instant toggling between **Dark**, **Light**, and **System** (matches OS `prefers-color-scheme`).
- Persists user choice in `localStorage` (`gaptrace_theme`).

---

## 4. Key Functional Features

### 4.1 Research Input Composer
- Positioned near the bottom-center of the workspace for natural ergonomics.
- Native drag-and-drop zone directly on the prompt container.
- Displays staged papers as compact pills showing filename, size, and real-time processing status.
- Action toolbar: `[ + Add Papers ]` `[ 🔎 Search Evidence ]` `[ Analyze → ]`.
- Realistic multi-stage progressive analysis indicator:
  `Preparing papers...` → `Extracting evidence...` → `Building landscape...` → `Detecting gaps...` → `Ready`.

### 4.2 Research Session View
- **Top Banner:** Compact summary (`12 Papers • 2019–2026 [View Papers]`).
- **Research Focus Bar:** Focus query input with toggleable analysis options:
  - ☑ Research limitations
  - ☑ Emerging topics
  - ☑ Research gaps
  - ☑ Counter-evidence
- **7-Tab Result Navigation:**
  1. **Overview:** Gap summary, `PERSISTENT` status badge, 3 metric pillars (Supporting, Addressing, Counter-evidence), and "Why this gap appears" breakdown.
  2. **Evidence:** Stream of subtle evidence cards highlighting exact quotes, paper title, section name, and page number.
  3. **Timeline:** Minimalist temporal progression from 2021 limitation identification to 2026 active gap.
  4. **Genealogy:** Algorithmic ancestry showing inherited limitations from previous architectures.
  5. **Counter-Evidence:** Cross-examination of competing claims and boundary conditions.
  6. **Graph:** Embedded interactive entity network.
  7. **Research Questions:** Formulated open hypotheses ready for grant applications or paper proposals.

### 4.3 Interactive Research Knowledge Graph
- Entity nodes colored by academic ontology:
  - **Paper** (Blue)
  - **Limitation** (Red/Crimson)
  - **Method** (Indigo)
  - **Dataset** (Green/Teal)
  - **Claim** (Amber)
  - **Research Direction** (Cyan)
- Controls: Zoom In, Zoom Out, Reset view, Type Filters (`ALL`, `Paper`, `Limitation`, etc.), and live Search.
- Node selection opens a sliding **Inspector Side Panel** showing entity confidence, source page, associated paper, and grounded evidence snippet.

---

## 5. Verification & Test Results

### 5.1 Frontend Test Suite (`vitest`)
All 6 frontend integration and unit tests passed in 635ms:
- `renders GapTrace branding and navigation elements` — **PASSED**
- `renders welcome view with headline and research composer` — **PASSED**
- `renders recent research sessions and allows navigating to a session` — **PASSED**
- `switches tabs in research session view to inspect evidence and timeline` — **PASSED**
- `supports light and dark theme switching with data-theme attribute` — **PASSED**
- `opens settings modal when settings action is triggered` — **PASSED**

### 5.2 Production Build (`vite build`)
- Transformed 1,490 modules in 3.01s.
- `dist/index.html` (1.26 kB)
- `dist/assets/index.css` (45.10 kB)
- `dist/assets/index.js` (234.52 kB)
- Zero syntax, CSS, or bundle errors.

### 5.3 Backend Regressions (`pytest backend/tests`)
- All 23 backend tests passed in 0.49s with zero regressions.
