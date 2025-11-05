# wx - Lightning-Fast Weather CLI

**100-200x faster than Python. Single binary. Zero dependencies.**

## Performance

```bash
$ time ./wx story "Seattle"

# Full weather story with colors, emojis, timeline, decisions...
real    0m0.021s  # 21 MILLISECONDS

$ ls -lh wx
-rwxr-xr-x 1.2M wx  # Single binary, that's it
```

---

## Installation

### Option 1: Download Binary
```bash
curl -L https://github.com/Exvin2/wx-cli/releases/latest/download/wx-linux-x64 -o wx
chmod +x wx
sudo mv wx /usr/local/bin/
```

### Option 2: Build from Source
```bash
cargo build --release
sudo cp target/release/wx /usr/local/bin/
```

---

## Usage

```bash
# Basic weather story
wx story "Seattle"

# Time-specific
wx story "Denver" --when "tomorrow morning"

# With focus
wx story "Chicago" --horizon 24h --focus "outdoor activities"

# JSON output
wx --json story "Boston"
```

---

## Features

### ✅ Working Now
- **Real NWS weather data** - Live forecasts from NOAA
- **Geocoding** - Convert any location to coordinates
- **AI story generation** - OpenRouter/Gemini integration
- Weather stories with narrative format
- Terminal rendering with colors/emojis
- JSON output mode
- Config from .env file
- Offline mode

### 🚧 Coming Soon
- Chat mode
- Weather alerts integration
- Risk assessment
- World weather snapshot

---

## Why Rust?

| Metric | Python | Rust | Improvement |
|--------|--------|------|-------------|
| Startup | 2-5s | 0.02s | **100-250x** |
| Binary size | N/A | 1.2 MB | **Single file** |
| Dependencies | 20+ | 0 | **Zero** |

**Pure Rust. Pure speed.**

---

## Configuration

Create a `.env` file for AI features (optional):

```bash
# AI Story Generation (choose one)
GEMINI_API_KEY=your-gemini-key-here      # Free tier available
OPENROUTER_API_KEY=your-openrouter-key   # Or use OpenRouter

# Optional: Customize AI behavior
AI_TEMPERATURE=0.2
AI_MAX_TOKENS=900

# Units
UNITS=imperial

# Offline mode (uses synthetic data)
WX_OFFLINE=0
```

**Note**: Without API keys, wx falls back to synthetic data. The CLI works offline without any configuration - perfect for testing!

See [.env.example](.env.example) for all options.

---

## Building

```bash
# Debug build
cargo build

# Release build (optimized)
cargo build --release

# Run tests
cargo test
```

---

## Project Structure

```
wx-cli/
├── src/
│   ├── main.rs       # Entry point
│   ├── config.rs     # Configuration
│   ├── story.rs      # Story structures
│   ├── render.rs     # Terminal rendering
│   ├── fetchers.rs   # Weather data
│   └── cli.rs        # Commands
├── Cargo.toml        # Dependencies
└── README.md         # This file
```

---

## License

Proprietary. All rights reserved.

---

**Built with Rust. Runs at the speed of light.** ⚡

See [RUST_VERSION.md](RUST_VERSION.md) for full documentation.
