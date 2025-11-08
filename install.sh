#!/usr/bin/env bash
# Installation script for wx weather CLI

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect OS and architecture
OS=$(uname -s)
ARCH=$(uname -m)

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  wx - Lightning-fast weather CLI with AI storytelling${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo -e "${RED}✗ Rust is not installed${NC}"
    echo "Please install Rust from https://rustup.rs/"
    exit 1
fi

echo -e "${GREEN}✓ Rust found${NC}"

# Build release binary
echo ""
echo -e "${YELLOW}Building release binary...${NC}"
cargo build --release

if [ ! -f "target/release/wx" ]; then
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Build successful${NC}"

# Determine install location
if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
elif [ -d "$HOME/.local/bin" ]; then
    INSTALL_DIR="$HOME/.local/bin"
else
    mkdir -p "$HOME/.local/bin"
    INSTALL_DIR="$HOME/.local/bin"
fi

# Install binary
echo ""
echo -e "${YELLOW}Installing to $INSTALL_DIR...${NC}"

if [ -w "$INSTALL_DIR" ]; then
    cp target/release/wx "$INSTALL_DIR/wx"
else
    echo "Need sudo to install to $INSTALL_DIR"
    sudo cp target/release/wx "$INSTALL_DIR/wx"
fi

echo -e "${GREEN}✓ Binary installed${NC}"

# Generate and install shell completions
COMPLETION_INSTALLED=false

# Detect shell and install completions
if [ -n "$BASH_VERSION" ]; then
    SHELL_NAME="bash"
    if [ -d "$HOME/.bash_completion.d" ]; then
        COMPLETION_DIR="$HOME/.bash_completion.d"
    elif [ -d "/usr/local/etc/bash_completion.d" ]; then
        COMPLETION_DIR="/usr/local/etc/bash_completion.d"
    else
        mkdir -p "$HOME/.bash_completion.d"
        COMPLETION_DIR="$HOME/.bash_completion.d"
    fi
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_NAME="zsh"
    if [ -d "$HOME/.zsh/completions" ]; then
        COMPLETION_DIR="$HOME/.zsh/completions"
    else
        mkdir -p "$HOME/.zsh/completions"
        COMPLETION_DIR="$HOME/.zsh/completions"
    fi
else
    # Fallback: try to detect from SHELL env var
    case "$SHELL" in
        */bash)
            SHELL_NAME="bash"
            mkdir -p "$HOME/.bash_completion.d"
            COMPLETION_DIR="$HOME/.bash_completion.d"
            ;;
        */zsh)
            SHELL_NAME="zsh"
            mkdir -p "$HOME/.zsh/completions"
            COMPLETION_DIR="$HOME/.zsh/completions"
            ;;
        */fish)
            SHELL_NAME="fish"
            mkdir -p "$HOME/.config/fish/completions"
            COMPLETION_DIR="$HOME/.config/fish/completions"
            ;;
        *)
            SHELL_NAME="bash"
            mkdir -p "$HOME/.bash_completion.d"
            COMPLETION_DIR="$HOME/.bash_completion.d"
            ;;
    esac
fi

echo ""
echo -e "${YELLOW}Installing $SHELL_NAME completions...${NC}"

# Generate completions
if [ "$SHELL_NAME" = "bash" ]; then
    target/release/wx completions bash > "$COMPLETION_DIR/wx"
    echo -e "${GREEN}✓ Bash completions installed to $COMPLETION_DIR/wx${NC}"
    echo ""
    echo "Add this to your ~/.bashrc if not already present:"
    echo -e "${BLUE}source $COMPLETION_DIR/wx${NC}"
elif [ "$SHELL_NAME" = "zsh" ]; then
    target/release/wx completions zsh > "$COMPLETION_DIR/_wx"
    echo -e "${GREEN}✓ Zsh completions installed to $COMPLETION_DIR/_wx${NC}"
    echo ""
    echo "Add this to your ~/.zshrc if not already present:"
    echo -e "${BLUE}fpath=($COMPLETION_DIR \$fpath)${NC}"
    echo -e "${BLUE}autoload -Uz compinit && compinit${NC}"
elif [ "$SHELL_NAME" = "fish" ]; then
    target/release/wx completions fish > "$COMPLETION_DIR/wx.fish"
    echo -e "${GREEN}✓ Fish completions installed to $COMPLETION_DIR/wx.fish${NC}"
fi

# Check if install dir is in PATH
echo ""
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "${YELLOW}⚠ $INSTALL_DIR is not in your PATH${NC}"
    echo ""
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo -e "${BLUE}export PATH=\"\$PATH:$INSTALL_DIR\"${NC}"
    echo ""
fi

# Success message
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Installation complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Try it out:"
echo -e "  ${BLUE}wx story \"your city\"${NC}"
echo -e "  ${BLUE}wx alerts \"your city\"${NC}"
echo -e "  ${BLUE}wx --help${NC}"
echo ""
echo "Configuration (optional):"
echo -e "  Create ${BLUE}~/.env${NC} or ${BLUE}.env${NC} with:"
echo "  GEMINI_API_KEY=your-key-here"
echo ""
echo "Performance:"
echo "  First run:  ~3s (fetches data)"
echo "  Cached:     ~50ms (lightning fast!)"
echo ""
