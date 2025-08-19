# Isometric Room Editor

A simple 2D isometric room editor created with Python and Pygame. This tool allows you to visually design room layouts using a tile-based system and export them as JSON files, which can then be easily loaded into a game engine.

![Screenshot of the Isometric Room Editor interface](img/editor_screenshot.png)

## Features

- **Visual Editing**: Create and modify room layouts on an isometric grid.
- **File Operations**: Create new rooms, load existing projects, and save your work.
- **Tile Variations**: Supports full diamond-shaped tiles and four types of corner triangle tiles.
- **Dynamic Anchor Point**: Set a `renderAnchor` to define the room's pivot point for rendering in your game.
- **Live Preview**: A real-time preview panel shows how the room will look, centered on its anchor point.
- **Camera Panning**: Easily navigate large rooms by panning the view with the middle mouse button.
- **Resizable Window**: The editor layout adapts to changes in the window size.
- **JSON Export**: Saves room data in a clean, easy-to-parse JSON format.

## Installation

To get the editor running on your local machine, follow these steps.

1.  **Clone the repository** (or download the files):
    ```bash
    git clone https://your-repository-url.com/isometric-editor.git
    cd isometric-editor
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    The only external dependency is Pygame. You can install it using the provided `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

## How to Use

1.  **Run the application**:
    ```bash
    python room_editor.py
    ```

2.  **Controls**:
    - **New / Load / Save / Save As...**: Use the buttons in the top toolbar for file management.
    - **Paint Tile**: `Left-click` on the grid to place a full tile.
    - **Erase Tile**: `Right-click` on a tile to remove it.
    - **Pan View**: `Click and drag with the middle mouse button` to move the camera.
    - **Place/Cycle Corner Tile**: Hold `Alt` and `Left-click` on a grid cell. This will place a corner tile or cycle through the different corner types if one already exists.
    - **Set Render Anchor**: Hold `Shift` and `Left-click` anywhere in the editor view to set the red anchor crosshair to that exact pixel position.
    - **Nudge Render Anchor**: Use the `Arrow Keys` to move the anchor by 1 pixel. Hold `Shift` with the `Arrow Keys` to move it by 10 pixels.

3.  **Anchor Point**:
    - The red crosshair (`renderAnchor`) represents the (0, 0) point of the room when you render it in your game.
    - The "Preview" window on the right always shows the room centered on this anchor point.
    - You can use the "Offset" input boxes to adjust the anchor's position relative to the geometric center of the tiles. The "Center Anchor" button will reset this offset to zero.

## Output JSON Format

When you save a room, it creates a `.json` file with the following structure:

```json
{
  "name": "My Awesome Room",
  "id": "level_01",
  "dimensions": {
    "width": 10,
    "depth": 8,
    "origin_x": -2,
    "origin_y": -3
  },
  "renderAnchor": {
    "x": 165.0,
    "y": 98.0
  },
  "tiles": [
    "0011100000",
    "0112511000",
    "1134111100",
    "1111111110",
    "0111111110",
    "0011111100",
    "0001111000",
    "0000110000"
  ]
}
```

- **`name`**, **`id`**: Metadata for the room.
- **`dimensions`**:
    - `width`, `depth`: The size of the tile grid bounding box.
    - `origin_x`, `origin_y`: The grid coordinates of the top-left corner of the bounding box. This tells you where the grid starts relative to the (0,0) grid origin.
- **`renderAnchor`**: The pixel coordinates (`x`, `y`) of the room's pivot point relative to the tile layout's own coordinate system.
- **`tiles`**: A list of strings representing the tile grid.
    - `'0'`: Empty space.
    - `'1'`: Full tile.
    - `'2'`-`'5'`: Different corner tile types.