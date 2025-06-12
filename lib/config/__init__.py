"""
Configuration package for Deep Research Agent.
Provides unified access to all configuration sources.
"""
from .project_config import ProjectConfig, get_project_config


def _import_config():
    """Lazy import to avoid circular dependencies."""
    import os
    import sys
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(parent_dir, 'config.py')

    import importlib.util
    spec = importlib.util.spec_from_file_location("main_config", config_path)
    main_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_config)

    return main_config.Config

# Create lazy accessor


def get_config_class():
    return _import_config()

# Lazy import to avoid circular dependencies


def get_config():
    """Get a Config instance with lazy loading."""
    ConfigClass = get_config_class()
    return ConfigClass()


# Direct Config class access
Config = get_config_class

__all__ = [
    'get_project_config', 'ProjectConfig',
    'get_config_class', 'get_config', 'Config'
]
