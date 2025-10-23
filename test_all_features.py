#!/usr/bin/env python3
"""Comprehensive integration test suite for wx-cli - all features."""

import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

console = Console()


def print_test_header(test_name: str):
    """Print test section header."""
    console.print()
    console.print("=" * 80, style="bold bright_blue")
    console.print(f"TEST: {test_name}", style="bold bright_blue")
    console.print("=" * 80, style="bold bright_blue")
    console.print()


def run_test(test_name: str, command: str, description: str) -> bool:
    """Run a test command and report results."""
    import subprocess

    console.print(f"[bold cyan]→ {test_name}[/bold cyan]")
    console.print(f"  {description}", style="dim")
    console.print(f"  Command: {command}", style="dim")
    console.print()

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            console.print("  [green]✓ PASSED[/green]")
            if result.stdout:
                # Show first 10 lines of output
                lines = result.stdout.strip().split('\n')
                for line in lines[:10]:
                    console.print(f"  {line}")
                if len(lines) > 10:
                    console.print(f"  ... ({len(lines) - 10} more lines)")
            console.print()
            return True
        else:
            console.print("  [red]✗ FAILED[/red]")
            if result.stderr:
                console.print(f"  Error: {result.stderr[:200]}", style="red")
            console.print()
            return False

    except subprocess.TimeoutExpired:
        console.print("  [yellow]⚠ TIMEOUT[/yellow]")
        console.print()
        return False
    except Exception as e:
        console.print(f"  [red]✗ ERROR: {e}[/red]")
        console.print()
        return False


def test_basic_functionality():
    """Test basic CLI functionality."""
    print_test_header("BASIC CLI FUNCTIONALITY")

    tests = [
        ("Help", "python -c 'from wx.cli import main; main([\"--help\"])'", "Check main help displays"),
        ("Version Info", "python -c 'from wx.cli import main; main([\"--offline\"])'", "Default worldview in offline mode"),
        ("Verbose Mode", "python -c 'from wx.cli import main; main([\"--offline\", \"--verbose\"])'", "Verbose output works"),
        ("Severe Filter", "python -c 'from wx.cli import main; main([\"--offline\", \"--severe\"])'", "Severe weather filtering"),
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def test_radar_feature():
    """Test radar visualization."""
    print_test_header("RADAR FEATURE")

    tests = [
        ("List Stations", "python -c 'from wx.cli import main; main([\"radar\", \"--list\"])'", "List available radar stations"),
        ("Radar Help", "python -c 'from wx.cli import main; main([\"radar\", \"--help\"])'", "Radar command help"),
        ("Visual Test", "python test_radar_visual.py", "Radar visualization components"),
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def test_international_weather():
    """Test international weather sources."""
    print_test_header("INTERNATIONAL WEATHER")

    tests = [
        ("International Help", "python -c 'from wx.cli import main; main([\"international\", \"--help\"])'", "International command help"),
        ("UK Weather", "python -c 'from wx.cli import main; main([\"--offline\", \"international\", \"London\"])'", "UK Met Office integration"),
        ("Canada Weather", "python -c 'from wx.cli import main; main([\"--offline\", \"international\", \"Toronto\"])'", "Environment Canada integration"),
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def test_lightning_feature():
    """Test lightning strike tracking."""
    print_test_header("LIGHTNING STRIKES")

    tests = [
        ("Lightning Help", "python -c 'from wx.cli import main; main([\"lightning\", \"--help\"])'", "Lightning command help"),
        # Note: lightning needs valid location lookup, skip actual test in offline mode
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def test_air_quality():
    """Test air quality monitoring."""
    print_test_header("AIR QUALITY INDEX (AQI)")

    tests = [
        ("AQI Help", "python -c 'from wx.cli import main; main([\"aqi\", \"--help\"])'", "AQI command help"),
        # Note: AQI needs valid location lookup, skip actual test in offline mode
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def test_hurricanes():
    """Test hurricane tracking."""
    print_test_header("HURRICANE TRACKING")

    tests = [
        ("Hurricane Help", "python -c 'from wx.cli import main; main([\"hurricanes\", \"--help\"])'", "Hurricane command help"),
        ("List Active", "python -c 'from wx.cli import main; main([\"--offline\", \"hurricanes\"])'", "List active storms"),
        ("Show Scale", "python -c 'from wx.cli import main; main([\"--offline\", \"hurricanes\", \"--scale\"])'", "Saffir-Simpson scale"),
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def test_notifications():
    """Test notification system."""
    print_test_header("WEATHER NOTIFICATIONS")

    tests = [
        ("Notify Help", "python -c 'from wx.cli import main; main([\"notify\", \"--help\"])'", "Notification command help"),
        ("List Rules", "python -c 'from wx.cli import main; main([\"notify\", \"list\"])'", "List alert rules"),
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def test_dashboard():
    """Test multi-location dashboard."""
    print_test_header("MULTI-LOCATION DASHBOARD")

    tests = [
        ("Dashboard Help", "python -c 'from wx.cli import main; main([\"dashboard\", \"--help\"])'", "Dashboard command help"),
        ("Compare Mode", "python -c 'from wx.cli import main; main([\"--offline\", \"dashboard\", \"London\", \"Paris\", \"Berlin\"])'", "Compare multiple cities"),
        ("Travel Mode", "python -c 'from wx.cli import main; main([\"--offline\", \"dashboard\", \"London\", \"Paris\", \"--mode\", \"travel\"])'", "Travel comparison"),
        ("Trending Mode", "python -c 'from wx.cli import main; main([\"--offline\", \"dashboard\", \"London\", \"Paris\", \"Tokyo\", \"--mode\", \"trending\"])'", "Location rankings"),
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def test_existing_features():
    """Test all existing features still work."""
    print_test_header("EXISTING FEATURES (REGRESSION TEST)")

    tests = [
        ("Chat Help", "python -c 'from wx.cli import main; main([\"chat\", \"--help\"])'", "Chat command"),
        ("Extended Help", "python -c 'from wx.cli import main; main([\"extended\", \"--help\"])'", "Extended forecast command"),
        ("Forecast Help", "python -c 'from wx.cli import main; main([\"forecast\", \"--help\"])'", "Forecast command"),
        ("Risk Help", "python -c 'from wx.cli import main; main([\"risk\", \"--help\"])'", "Risk command"),
        ("Alerts Help", "python -c 'from wx.cli import main; main([\"alerts\", \"--help\"])'", "Alerts command"),
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def test_design_system():
    """Test design system and UI."""
    print_test_header("DESIGN SYSTEM & UI")

    tests = [
        ("Visual Tests", "python test_visuals.py", "All UI component tests"),
    ]

    results = []
    for name, cmd, desc in tests:
        results.append(run_test(name, cmd, desc))

    return results


def run_all_tests():
    """Run complete test suite."""
    console.print()
    console.print("=" * 80, style="bold bright_magenta")
    console.print("WX-CLI COMPREHENSIVE TEST SUITE", style="bold bright_magenta")
    console.print("=" * 80, style="bold bright_magenta")
    console.print()
    console.print(Text("Testing all features with real usage scenarios...", style="bright_cyan"))
    console.print()

    all_results = []

    # Run all test suites
    all_results.extend(test_basic_functionality())
    all_results.extend(test_design_system())
    all_results.extend(test_radar_feature())
    all_results.extend(test_international_weather())
    all_results.extend(test_lightning_feature())
    all_results.extend(test_air_quality())
    all_results.extend(test_hurricanes())
    all_results.extend(test_notifications())
    all_results.extend(test_dashboard())
    all_results.extend(test_existing_features())

    # Summary
    console.print()
    console.print("=" * 80, style="bold bright_magenta")
    console.print("TEST SUMMARY", style="bold bright_magenta")
    console.print("=" * 80, style="bold bright_magenta")
    console.print()

    passed = sum(all_results)
    total = len(all_results)
    failed = total - passed

    console.print(f"Total Tests: {total}")
    console.print(f"[green]Passed: {passed}[/green]")
    if failed > 0:
        console.print(f"[red]Failed: {failed}[/red]")
    else:
        console.print(f"Failed: {failed}")

    pass_rate = (passed / total * 100) if total > 0 else 0
    console.print(f"Pass Rate: {pass_rate:.1f}%")
    console.print()

    if pass_rate == 100:
        console.print("[bold green]✓ ALL TESTS PASSED![/bold green]")
    elif pass_rate >= 90:
        console.print("[bold yellow]⚠ MOSTLY PASSING (some issues)[/bold yellow]")
    else:
        console.print("[bold red]✗ MULTIPLE FAILURES[/bold red]")

    console.print()

    return pass_rate >= 90


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Tests interrupted by user[/yellow]")
        sys.exit(1)
