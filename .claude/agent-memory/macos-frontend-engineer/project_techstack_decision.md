---
name: Tech Stack Decision - ProxyMakerPro
description: Chosen tech stack and architecture decisions for ProxyMakerPro, an MTG card proxy PDF generator macOS app
type: project
---

Tech stack chosen: Python + PySide6 (not SwiftUI). Decision made on 2026-04-11.

**Why:** The project's mtg-pdf-generator agent explicitly targets Python (httpx/aiohttp + reportlab/fpdf2 + Pillow). Bridging Swift to a Python PDF pipeline would add significant complexity with no gain. PySide6 provides native macOS widgets, dark mode support via Qt::AA_UseHighDpiPixmaps, and system fonts with no extra work. Distribution is via PyInstaller .app bundle.

**How to apply:** All frontend implementation work should use PySide6 (Qt6 for Python). Do not propose SwiftUI or AppKit implementations for this project. PDF generation stays in Python (reportlab). Async network work uses QThread with signals/slots (not asyncio, due to Qt event loop ownership). Minimum target: macOS 13 Ventura.

Key architecture decisions:
- Single-window app, not document-based
- State management: lightweight custom AppState dataclass + Qt signals (no TCA, no heavy framework)
- Card grid: QScrollArea + QGridLayout with lazy QLabel image loading (not QListView/QAbstractItemModel — grid is small enough at 100 cards)
- Network I/O: QThread worker + pyqtSignal for progress updates to main thread
- PDF generation: runs in QThread, reports completion via signal
- Settings panel: right-side collapsible panel or modal QDialog
- macOS menu bar: QMenuBar with File menu (Open, Save PDF, Quit) and standard Edit menu
- Deployment: PyInstaller one-folder bundle → zip as .app for distribution
