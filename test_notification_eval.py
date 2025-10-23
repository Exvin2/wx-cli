#!/usr/bin/env python3
"""Test notification rule evaluation."""

from wx.notifications import NotificationManager
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    nm = NotificationManager(Path(tmpdir))

    # Add rules
    nm.add_rule('wind_alert', 'wind > 50', 'Manchester')
    nm.add_rule('temp_warning', 'temp < 0', 'Birmingham')
    nm.add_rule('aqi_alert', 'aqi > 150', 'London')

    print(f'Created {len(nm.rules)} rules\n')

    print('Testing condition evaluation:')
    test_data = {'wind': 60, 'temp': -5, 'aqi': 180}
    print(f'Test data: {test_data}\n')

    results = nm.check_rules(test_data)
    print(f'Triggered {len(results)} notifications:')
    for n in results:
        print(f'  • {n.rule_name}: {n.severity} - {n.message}')
