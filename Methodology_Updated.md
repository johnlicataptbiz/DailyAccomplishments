# DailyAccomplishments: Methodology for Focus, Activity, and Coverage Times

## Executive Summary
This document outlines how DailyAccomplishments currently calculates Focus, Activity (Active Time), and Coverage, and proposes a redesign for more accurate, actionable work-hour tracking. The current system uses hourly buckets and heuristic adjustments (e.g., partial meeting credit) to estimate productive time. The proposed approach leverages detailed timeline data to precisely sum active, focus, and meeting time, and recommends UI changes to make these distinctions clear to users.
### Current Methodology (Phase 1: Backend Overhaul)
- **Data Collection**: Real-time polling via collector.py (5s interval) captures timestamp, app, 
bundle_id, window title, and idle_seconds from macOS screentime APIs.
- **Aggregation**: generate_daily_json.py processes JSONL logs into ActivityReport JSON with 
hourly_focus, by_category, top_apps, and browser_highlights. Focus time is calculated as 
non-idle duration >1s, categorized by app heuristics (e.g., Chrome → Research, Terminal → 
Coding).
- **Output**: Date-specific CSVs (hourly_focus.csv, category_distribution.csv, top_domains.csv) 
and charts (PNG/SVG) via matplotlib.
- **Validation**: Tested with empty/placeholder logs (31 bytes) and full days (~50KB, 457+ 
records, ~525 min activity).
- **Privacy**: No PII logged; apps anonymized to categories.

### Proposed Methodology (Phase 2: UI Integration)
- **Dashboard Updates**: Load ActivityReport JSON dynamically in dashboard.html to render:
  - Pie chart for by_category (Chart.js, colors from #4e79a7 palette).
  - Bar chart for hourly_focus (stacked with pct overlay).
  - List for top_apps and top_domains with visits/time.
- **KPIs**: Display focus_time, coverage_window, projects_count in executive_summary; add idle % 
and deep_work_blocks (consecutive focus >25min).
- **Fallback**: If JSON missing, show "No data—run generate_daily_json.py [date]".
- **Testing**: Validate with large logs (>1K events) for load time <2s; privacy mode excludes 
'Communication' category.

### Phase 3+ Roadmap (From FUTURE_UPDATES.md)
- Ship minimal KPIs (focus/meetings) first; expand to trends/filters.
- QA: Screenshots, empty/large log tests, schema validation.
- Deploy: Auto-build on Railway after push.

This keeps it self-contained while linking to the roadmap. If you want me to expand on a section 
(e.g., code snippet for dashboard pie chart) or rewrite the whole file, just say the word. 
What's your focus now—finishing the UI tweaks, or something else? ---

## Current Methodology

### Metric Definitions & Formulas
- **Focus Time**: Productive screen time, calculated as:
  - `Focus Time = Total App Usage - 0.75 × Meeting Time - 0.3 × Communication Time`
- **Active Time (Activity)**: Total time actively working at the computer, including meetings. Calculated as:
  - `Active Time = sum of (focus minutes + meeting minutes) per hour, capped at 60 per hour`
- **Coverage**: The span from first to last activity of the day.
  - `Coverage = Last Activity Time - First Activity Time`

### Dashboard UI
- **Focus Time**: Shown as a bold duration (e.g., “4h 15m”), labeled “Focus.” If above a threshold (e.g., ≥4h), gets highlight styling. Shows delta vs. baseline if available.
- **Active Time**: Shown as “Active.” Always ≥ Focus Time. Represents total work time.
- **Coverage**: Shown as duration and time range (e.g., “15h 53m”, “07:12–23:05”).
- **Visualizations**:
  - Hourly Focus Chart: Bars for focus, line for meetings, color-coded by intensity.
  - Category Breakdown: Donut chart by app category.
  - Deep Work Blocks: Chips for contiguous focus sessions.

### Limitations
- Focus definition is heuristic and may not reflect true heads-down work.
- Meeting time is not shown explicitly.
- Coverage includes idle/breaks.
- Fixed category weights may not fit all roles.
- Hourly buckets lose timeline detail.

---

## Proposed Redesign

### Comparison Table
| Metric         | Current Logic                                      | Proposed Logic                                      |
|---------------|----------------------------------------------------|-----------------------------------------------------|
| Focus Time    | App usage minus meeting/comm heuristics            | All active time excluding meeting intervals          |
| Meeting Time  | Implied (Active - Focus)                           | Explicit: sum of all time in meeting apps/calls      |
| Active Time   | Hourly sum, capped at 60 min/hr                    | Precise sum of all non-overlapping usage intervals   |
| Coverage      | First to last activity                             | Same, but with context on active vs idle             |
| Communication | Partially subtracted from focus                    | Optionally: separate as Collaboration (non-meeting)  |

### Enhanced Algorithm
1. **Leverage Full Timeline Data**: Use actual app usage intervals, not hourly buckets.
2. **Direct Active Time**: Sum all non-overlapping usage intervals for true active time.
3. **Explicit Meeting and Focus Separation**:
   - **Meeting Time**: Sum of all time in meeting apps/calls.
   - **Focus Time**: All active time excluding meeting intervals.
   - If overlap: attribute to foreground app (if IDE is active during Zoom, count as focus).
4. **(Optional) Deep Focus**: Identify blocks of ≥30 min uninterrupted productive app use.
5. **Refined Categorization**: Optionally, treat all communication as collaboration, not focus.
6. **Idle Time Handling**: Cap single sessions if too long, or use idle signals if available.

### UI Recommendations
- **Show Meeting Time Explicitly**: Add a “Meetings” card/stat to the dashboard.
- **Rename “Active”**: Consider “Total Active Time” or “Screen Time.”
- **Coverage Context**: Add a mini timeline or text to show active vs idle within coverage.
- **Tooltips/Info**: Add hover or info icons for each metric:
  - *Focus*: “Time spent on focused work (non-meeting, screen-active time).”
  - *Meetings*: “Time spent in scheduled meetings or calls.”
  - *Coverage*: “Span from first to last activity, including breaks.”
- **Visualization**: Add donut/bar chart for Focus vs. Meetings vs. Collaboration split.
- **Insights**: Narrative highlights (e.g., “Longest focus stretch: 1h 40m”).

---

## References
- DailyAccomplishments code and dashboard UI ([GitHub](https://github.com/johnlicataptbiz/DailyAccomplishments))
- Microsoft Viva Insights definitions
- RescueTime productivity studies
- [What we learned about productivity from analyzing 225 million hours of working time in 2017](https://medium.com/swlh/what-we-learned-about-productivity-from-analyzing-225-million-hours-of-working-time-in-2017-7c2a1062d41d)
- [Teamwork tab in Viva Insights - Microsoft Support](https://support.microsoft.com/en-us/topic/teamwork-tab-in-viva-insights-cca98877-be3a-47f3-ad4a-acc88111f0cb)

---

*This document reflects the current and proposed methodology for work-hour tracking in DailyAccomplishments. For implementation details, see the referenced code and UI files.*