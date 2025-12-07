# Dashboard Navigation Guide

## Overview
The GoodTrade2 dashboard uses a **tabbed navigation system** (Notebook widget) instead of a traditional navigation bar. The navigation is implemented at the top of the dashboard panel.

## Navigation Bar Location

The navigation bar for the dashboard is located at **line 49-50** in `UI/ui_dashboard.py`:

```python
self.tab = tb.Notebook(self.ui.dashboard_panel)
self.tab.place(relx=0, rely=0.01, relheight=0.98, relwidth=1)
```

This creates a Notebook widget (tabbed interface) that spans the full width of the dashboard panel, starting at 1% from the top.

## Dashboard Tabs (Navigation Items)

The dashboard contains **5 main tabs** that serve as the navigation mechanism (defined at line 53-56):

1. **Risk** - Risk management panel showing risk metrics and monitoring
2. **Gateways** - Market panel for gateway connections and market data
3. **Symbol** - Symbol dashboard showing symbol-specific information and positions
4. **Algos** - Algorithms dashboard for managing trading algorithms
5. **PitchPit** - Chart/candle panel for market visualization

### Tab Implementation

Each tab is created and added to the navigation bar in this loop:

```python
for name in ('Risk','Gateways','Symbol','Algos','PitchPit'):
    frame = tb.Frame(self.tab)
    self.frames[name] = frame
    self.tab.add(frame, text=name)
```

## Tab Content

Each tab contains specific panels:

- **Risk Tab**: Contains `RiskPanel` (line 70-71)
- **Gateways Tab**: Contains `MarketPanel` (line 60-64)
- **Symbol Tab**: Contains `Symbol_Dashboard_Panel` (line 67-68)
- **Algos Tab**: Contains `Algo_Dashboard_Panel` (line 74-75)
- **PitchPit Tab**: Contains `CandlePanel` (line 77-78)

## How to Navigate

Users navigate the dashboard by **clicking on the tab labels** at the top of the dashboard panel. The ttkbootstrap Notebook widget provides:
- Visual indication of the active tab
- Click-to-switch navigation
- Professional themed appearance

## Main Application Layout

In the main application (`ui_main.py`), the dashboard panel is positioned at:
```python
self.dashboard_panel = tb.LabelFrame(self.root, text="Dashboard", bootstyle="success")
self.dashboard_panel.place(x=360, y=10, height=270, width=1200)
```

This means the dashboard (with its tab-based navigation bar) appears:
- **X position**: 360 pixels from the left
- **Y position**: 10 pixels from the top  
- **Width**: 1200 pixels
- **Height**: 270 pixels

## Visual Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Dashboard                                                    │
├─────────────────────────────────────────────────────────────┤
│ [Risk] [Gateways] [Symbol] [Algos] [PitchPit]  ← Navigation│
├─────────────────────────────────────────────────────────────┤
│                                                              │
│              Active Tab Content                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Summary

**The navigation bar IS the tab bar** created by the `tb.Notebook` widget. It appears as a horizontal row of clickable tab labels at the top of the dashboard panel. This is the standard ttkbootstrap/tkinter approach to creating multi-section interfaces with navigation.
