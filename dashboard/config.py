"""
Dashboard configuration handler.

Manages loading and saving of dashboard configuration to JSON file.
"""

import json
import os
from datetime import datetime
from typing import Optional


DEFAULT_CONFIG = {
    "version": 2,
    "lastModified": None,
    "settings": {
        "autoRefresh": True,
        "refreshInterval": 60,
        "timeRange": 24
    },
    "charts": []
}


class DashboardConfig:
    """Handler for dashboard configuration file."""

    def __init__(self, config_path: str = "dashboard_config.json"):
        self.config_path = config_path

    def _migrate_v1_to_v2(self, config: dict) -> dict:
        """
        Migrate config from version 1 to version 2.

        Version 2 changes:
        - Move per-chart 'hours' to global 'settings.timeRange'
        - Remove 'hours' from individual chart configs
        """
        # Get the most common hours value from charts, default to 24
        hours_values = [c.get('hours', 24) for c in config.get('charts', [])]
        if hours_values:
            # Use the most common value
            time_range = max(set(hours_values), key=hours_values.count)
        else:
            time_range = 24

        # Ensure settings exists
        if 'settings' not in config:
            config['settings'] = {}

        # Add timeRange to settings
        config['settings']['timeRange'] = time_range

        # Remove hours from individual charts
        for chart in config.get('charts', []):
            chart.pop('hours', None)

        # Update version
        config['version'] = 2

        return config

    def load(self) -> dict:
        """Load configuration from file, creating default if not exists."""
        if not os.path.exists(self.config_path):
            return DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

                # Ensure all required keys exist
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]

                # Handle version migration
                version = config.get('version', 1)
                if version < 2:
                    config = self._migrate_v1_to_v2(config)
                    # Save migrated config
                    self.save(config)

                # Ensure settings has timeRange
                if 'timeRange' not in config.get('settings', {}):
                    config['settings']['timeRange'] = 24

                return config
        except (json.JSONDecodeError, IOError):
            return DEFAULT_CONFIG.copy()

    def save(self, config: dict) -> bool:
        """
        Save configuration to file.

        Uses atomic write (write to temp file, then rename) to prevent corruption.
        """
        config['lastModified'] = datetime.now().isoformat()

        temp_path = self.config_path + '.tmp'
        try:
            with open(temp_path, 'w') as f:
                json.dump(config, f, indent=2)
            os.replace(temp_path, self.config_path)
            return True
        except IOError:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    def add_chart(self, chart: dict) -> dict:
        """Add a chart to configuration."""
        config = self.load()
        config['charts'].append(chart)
        self.save(config)
        return config

    def remove_chart(self, chart_id: str) -> dict:
        """Remove a chart from configuration."""
        config = self.load()
        config['charts'] = [c for c in config['charts'] if c.get('id') != chart_id]
        self.save(config)
        return config

    def update_chart(self, chart_id: str, updates: dict) -> Optional[dict]:
        """Update a chart in configuration."""
        config = self.load()
        for chart in config['charts']:
            if chart.get('id') == chart_id:
                chart.update(updates)
                self.save(config)
                return config
        return None
