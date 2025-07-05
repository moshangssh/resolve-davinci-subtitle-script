# Subvigator - Python Port

This project is a Python port of the "Andy's Subvigator" DaVinci Resolve script, originally written in Lua.

## Features

*   Filter and search subtitles in the current timeline.
*   Navigate the timeline by clicking on subtitles.
*   Combine multiple subtitles into a single entry for easier reading.

## Project Structure

```
.
├── Andys Subvigator.lua  (Original Script)
├── memory_bank/
├── README.md
└── subvigator/
    ├── __init__.py
    ├── main.py
    ├── resolve_integration.py
    ├── timecode_utils.py
    └── ui.py