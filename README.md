## 2D Logistics Game (Desktop)

Basic Pygame-based prototype:
- Press `b` to toggle Build Mode
- In Build Mode: Left-click and drag to draw roads on a grid
- Grid overlay appears only in Build Mode
- A random base spawn point is placed within the current viewport on start

### Run (Windows)
1. Install Python 3.10+ from `https://www.python.org/downloads/` and ensure "Add Python to PATH" is checked
2. Open PowerShell in the project directory
3. Install dependencies:
```
pip install -r requirements.txt
```
4. Run the game:
```
python main.py
```

### Build a standalone .exe
1. Install PyInstaller:
```
pip install pyinstaller
```
2. Build:
```
pyinstaller --onefile --noconsole --name LogisticsGame main.py
```
3. Find the executable in `dist/LogisticsGame.exe`

### Controls
- **B**: Toggle Build Mode
- **Left Mouse (drag)**: Draw roads while in Build Mode
- **Esc**: Quit

### Notes
- Roads snap to grid cells
- Dragging places continuous roads even with fast mouse movement


