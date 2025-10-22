# Live Weather Radar Feature

## Overview

wx-cli now includes live weather radar display with animated loops, bringing real-time precipitation and storm tracking directly to your terminal. The radar feature fetches live data from NWS RIDGE (Radar Integrated Display with Geospatial Elements) radar network and displays it using multiple rendering methods.

## Features

### 1. Live Radar Data
- **137 NOAA Radar Stations** across the United States
- Real-time base reflectivity (precipitation intensity)
- Automatic station selection based on location
- Up-to-date radar imagery from NWS

### 2. Multiple Display Methods

#### Terminal Graphics (Automatic Detection)
The radar display automatically detects your terminal's capabilities:

- **Unicode Block Art** (Default): Works in all modern terminals
  - Colored text blocks (░▒▓█) represent precipitation intensity
  - Color-coded: Blue (none) → Cyan (light) → Green (moderate) → Yellow (heavy) → Red (severe) → Magenta (extreme)
  - 40x20 to 120x50 character resolution

- **Kitty Graphics Protocol**: High-quality images in Kitty terminal
  - Full-resolution radar images
  - Native image rendering

- **Sixel Graphics**: For terminals with sixel support
  - xterm with sixel, mlterm, foot, etc.

- **iTerm2 Inline Images**: For iTerm2 on macOS
  - Native inline image display

#### GUI Window Fallback
- Opens a tkinter window if terminal graphics aren't supported
- Full-resolution radar image display
- Useful for saving/sharing radar images

### 3. Animated Radar Loops
- Fetch multiple frames from NWS
- Animate radar progression over time
- Configurable frame count and delay
- Shows storm movement and development
- Ctrl+C to stop animation

### 4. Smart Station Selection
- Auto-detect nearest station based on location
- Manual station selection by ID
- List stations by region
- Find stations near specific places

## Usage

### Basic Commands

#### List Available Stations
```bash
# List major radar stations
wx radar --list

# List stations near a specific place
wx radar --list --place "Denver"
```

#### Display Radar

```bash
# Default station (auto-selected)
wx radar

# Specific station by ID
wx radar KOKX  # New York radar

# Nearest station to a location
wx radar --place "Seattle"
```

#### Animated Radar Loop

```bash
# Basic animation (10 frames, 0.5s delay)
wx radar KOKX --animate

# Custom animation settings
wx radar KDMX --animate --frames 20 --delay 0.3

# With location lookup
wx radar --place "Houston" --animate
```

#### GUI Display

```bash
# Open radar in GUI window
wx radar KFTG --gui

# Animated radar in GUI
wx radar KFTG --gui --animate
```

### Command Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--place` | `-p` | Location to find nearest radar station | - |
| `--animate` | `-a` | Show animated radar loop | false |
| `--frames` | `-f` | Number of frames for animation | 10 |
| `--delay` | `-d` | Delay between frames (seconds) | 0.5 |
| `--gui` | `-g` | Open GUI window for display | false |
| `--list` | `-l` | List available radar stations | false |

## Radar Stations

### Coverage

The NWS RIDGE network provides comprehensive coverage across:
- Continental United States
- Alaska
- Hawaii
- Puerto Rico
- Guam

### Major Stations

| Station ID | Location | Coverage Area |
|------------|----------|---------------|
| KOKX | New York, NY | NYC Metro, Long Island |
| KDMX | Des Moines, IA | Central Iowa |
| KFTG | Denver, CO | Denver Metro, Front Range |
| KFFC | Atlanta, GA | Atlanta Metro, North Georgia |
| KHGX | Houston, TX | Houston Metro, Gulf Coast |
| KLAX | Los Angeles, CA | LA Basin, Southern California |
| KSEA | Seattle, WA | Seattle Metro, Puget Sound |
| KMIA | Miami, FL | South Florida, Keys |
| KORD | Chicago, IL | Chicago Metro, Lake Michigan |
| KDFW | Dallas, TX | Dallas-Fort Worth Metro |

**Find the complete list:** Use `wx radar --list` to see all 137 available stations.

### Finding Your Station

```bash
# Method 1: Auto-detect by city name
wx radar --place "Phoenix"

# Method 2: List nearby stations
wx radar --list --place "Boston"

# Method 3: Use station lookup tools
wx radar --list  # Browse all stations
```

## Technical Details

### Radar Products

Currently supports:
- **N0R**: Base Reflectivity (standard)
- Shows precipitation intensity at the lowest elevation angle
- Updated every 5-10 minutes

Future support planned:
- **N0V**: Base Velocity (storm motion)
- **N0S**: Storm Relative Velocity
- **N0Z**: High-Resolution Base Reflectivity

### Rendering Methods

#### Unicode Block Rendering
```
Intensity Mapping:
  0-32:   ' ' (space)    - No precipitation
  33-64:  '░' (blue)     - Very light
  65-96:  '▒' (cyan)     - Light rain
  97-128: '▓' (green)    - Moderate rain
  129-160: '▓' (yellow)  - Heavy rain
  161-192: '█' (red)     - Very heavy rain
  193-255: '█' (magenta) - Extreme precipitation
```

#### Terminal Detection
The system automatically detects:
1. TERM environment variable
2. Terminal emulator capabilities
3. Graphics protocol support
4. Falls back to Unicode blocks

### Performance

- Image fetch: ~1-2 seconds
- Rendering: <100ms for Unicode blocks
- Animation: Smooth at 0.3-0.5s frame delay
- Memory: ~5-10MB for radar images

### Dependencies

**Required:**
- `requests` - HTTP requests for radar data
- `Pillow (PIL)` - Image processing and rendering
- `rich` - Terminal output and colors

**Optional:**
- `tkinter` - GUI window display (usually pre-installed with Python)

## Examples

### Example 1: Quick Local Radar
```bash
# Show radar for your area
wx radar --place "$(curl -s ifconfig.me/city)"
```

### Example 2: Storm Tracking
```bash
# Watch storm development over time
wx radar KOKX --animate --frames 20 --delay 0.5
```

### Example 3: Multiple Locations
```bash
# Compare radar across different cities
wx radar --place "Miami" && wx radar --place "New York"
```

### Example 4: Save Radar Image
```bash
# Open in GUI to save/screenshot
wx radar KHGX --gui
```

## Troubleshooting

### Radar Not Displaying

**Problem**: "Failed to fetch radar image"

**Solutions**:
1. Check internet connection
2. Verify station ID is valid: `wx radar --list`
3. Try a different station
4. Check if NWS radar is operational

### Animation Issues

**Problem**: Animation is choppy or slow

**Solutions**:
1. Reduce frame count: `--frames 5`
2. Increase delay: `--delay 1.0`
3. Check network speed
4. Use single frame mode (remove `--animate`)

### Display Quality

**Problem**: Radar looks blocky or unclear

**Solutions**:
1. Use GUI mode for full resolution: `--gui`
2. Increase terminal size for more pixels
3. Try a terminal with graphics support (Kitty, iTerm2)
4. Use higher resolution Unicode rendering (120x50)

### PIL/Pillow Not Found

**Problem**: "ModuleNotFoundError: No module named 'PIL'"

**Solution**:
```bash
pip install Pillow
# or
pip install --user Pillow
```

### GUI Window Won't Open

**Problem**: "Error opening GUI window"

**Solutions**:
1. Ensure tkinter is installed:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install python3-tk

   # macOS (included with Python)
   # Windows (included with Python)
   ```
2. Use terminal display instead (remove `--gui`)

## Integration with Chat Mode

Radar commands are also available in interactive chat mode:

```bash
wx chat
```

Then use natural language:
```
You: Show me the radar for Chicago
You: Animate the radar
You: What stations are near Seattle?
```

The bot will interpret radar-related requests and display radar data inline.

## Limitations

### Current Limitations

1. **US Coverage Only**: NWS RIDGE radars are US-based
2. **Static Images**: Not true real-time streaming (5-10 min delay)
3. **Single Product**: Currently only base reflectivity (N0R)
4. **Frame Extraction**: Animated GIFs need frame parsing (future enhancement)

### Future Enhancements

Planned features:
- [ ] Additional radar products (velocity, composite)
- [ ] International radar support (EU, Canada)
- [ ] Overlay maps and city markers
- [ ] Save radar images to file
- [ ] Radar alerts and notifications
- [ ] Composite multi-radar views
- [ ] 3D volumetric radar data

## Technical Architecture

### Components

1. **RadarFetcher**: Fetches data from NWS RIDGE
   - Station database (137 stations)
   - HTTP client with proper headers
   - Nearest station algorithm
   - Frame sequencing for animation

2. **RadarRenderer**: Converts images to terminal display
   - Terminal capability detection
   - Unicode block color mapping
   - Sixel/Kitty protocol encoding
   - GUI window creation

3. **CLI Integration**: Command-line interface
   - Typer-based command structure
   - Option parsing and validation
   - Console output formatting

### Data Flow

```
User Command → CLI Parser → RadarFetcher → NWS RIDGE API
                                               ↓
                                          Radar Image
                                               ↓
                                        RadarRenderer
                                               ↓
                        Terminal Display / GUI Window / Animation Loop
```

## API and Data Sources

### NWS RIDGE Radar
- **Base URL**: `https://radar.weather.gov/ridge/`
- **Product**: Standard radar loops (GIF format)
- **Update Frequency**: Every 5-10 minutes
- **Coverage**: 137 stations across US territories

### No API Key Required
- NWS radar data is publicly available
- No rate limits or authentication needed
- Free for personal and commercial use

## Performance Tips

### For Best Performance

1. **Terminal Size**: Larger terminals show more detail
   - Recommended: 120x50 characters minimum
   - Full screen provides best visualization

2. **Network**: Fast internet improves fetch speed
   - Radar images are 100-500KB each
   - Animation fetches multiple frames

3. **Graphics**: Use terminals with native graphics support
   - Kitty terminal: Best image quality
   - iTerm2: Excellent on macOS
   - Standard terminals: Good Unicode rendering

4. **Animation**: Adjust for your system
   - Fast systems: `--delay 0.3`
   - Standard systems: `--delay 0.5`
   - Slow systems: `--delay 1.0` or use single frame

## Contributing

Want to improve the radar feature? Areas for contribution:

1. **International Radar**: Add support for non-US radars
2. **Additional Products**: Implement velocity, composite products
3. **Frame Parsing**: Extract individual frames from GIF loops
4. **Map Overlays**: Add city names, state borders
5. **Performance**: Optimize rendering and caching

See the main repository for contribution guidelines.

## License

The radar feature is part of wx-cli and follows the same license. NWS radar data is in the public domain.

---

**Questions or Issues?**
- Check the main README for general wx-cli help
- Report bugs in the GitHub issue tracker
- Consult NWS documentation for radar data specifics
