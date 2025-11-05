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
- Weather stories with narrative format
- Terminal rendering with colors/emojis
- JSON output mode
- Config from .env file
- Offline mode

### 🚧 Coming Soon
- Real weather data (NWS, Open-Meteo)
- AI story generation
- Chat mode
- Alerts & risk assessment

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

Create a `.env` file (optional):

```bash
# Units
UNITS=imperial

# Offline mode
WX_OFFLINE=0
```

See [.env.example](.env.example) for more options.

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
