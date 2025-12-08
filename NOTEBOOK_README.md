# Notebook Execution Guide

This directory contains a Jupyter notebook demonstrating the DailyAccomplishments tracking system.

## Files

- **Untitled-1.ipynb** - Interactive Jupyter notebook with comprehensive examples
- **execute_notebook.py** - Standalone Python script that demonstrates the same functionality

## Quick Start

### Option 1: Run the Python Script (Recommended)

```bash
python3 execute_notebook.py
```

This will:
- Initialize the logging system
- Log sample events (focus changes, browser visits, meetings, etc.)
- Display the logged events
- Show statistics

### Option 2: Use Jupyter Notebook

1. Install Jupyter (if not already installed):
   ```bash
   pip install jupyter nbconvert ipykernel
   ```

2. Open the notebook:
   ```bash
   jupyter notebook Untitled-1.ipynb
   ```

3. Run each cell to see the demonstration

## What It Demonstrates

The notebook/script demonstrates logging these event types:

1. **Focus Changes** - Track time spent in different applications
2. **Browser Visits** - Record website visits with domain and page title
3. **Application Switches** - Log when users switch between apps
4. **Meeting Tracking** - Record meeting starts with duration
5. **Manual Entries** - Log completed deep work sessions

## Output

After execution, you'll find:
- Log file: `logs/daily/YYYY-MM-DD.jsonl`
- Event statistics displayed in console
- Next steps for generating reports and viewing dashboard

## Next Steps

After running the demonstration:

1. **View the logs**:
   ```bash
   cat logs/daily/$(date +%Y-%m-%d).jsonl
   ```

2. **Generate a daily report**:
   ```bash
   python3 tools/auto_report.py --date $(date +%Y-%m-%d)
   ```

3. **View the dashboard**:
   ```bash
   open dashboard.html
   # or
   python3 -m http.server 8000
   # then open http://localhost:8000/dashboard.html
   ```

## Integration

For integrating the tracking system with your own code, see:
- `examples/integration_example.py` - Complete integration examples
- `.github/copilot-instructions.md` - System architecture and conventions
