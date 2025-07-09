"""
Temperature Management for Research Agents.

This module provides configuration and management for temperature-based
analytical approaches in research agents.
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from ..prompts.agents.researcher import get_temperature_researcher_prompt

try:
    from ..config.project_config import get_project_config
except ImportError:
    get_project_config = None


class TemperatureManager:
    """Manages temperature configurations for research agents."""

    @classmethod
    def _get_default_temperature_configs(cls) -> List[Dict[str, Any]]:
        """Get default temperature configurations as fallback."""
        return [
            {"temp": 0.2, "approach": "Conservative detailed analysis", "agent_suffix": "CONSERVATIVE"},
            {"temp": 0.6, "approach": "Balanced analysis", "agent_suffix": "BALANCED"},
            {"temp": 0.9, "approach": "Creative divergent thinking", "agent_suffix": "CREATIVE"}
        ]

    @classmethod
    def _get_project_temperature_configs(cls) -> List[Dict[str, Any]]:
        """Get temperature configurations from project config."""
        if get_project_config is None:
            return cls._get_default_temperature_configs()

        try:
            project_config = get_project_config()
            configs = []

            # Get configurations in order: conservative, balanced, creative
            for agent_type in ['conservative', 'balanced', 'creative']:
                agent_config = project_config.get_agent_config(agent_type)
                if agent_config:
                    configs.append({
                        "temp": agent_config.temp,
                        "approach": agent_config.approach,
                        "agent_suffix": agent_type.upper()
                    })

            return configs if configs else cls._get_default_temperature_configs()
        except Exception:
            return cls._get_default_temperature_configs()

    @classmethod
    def get_temperature_configs(
            cls, use_temperature_variation: bool = False) -> List[Dict[str, Any]]:
        """
        Get temperature configuration for agents.

        Args:
            use_temperature_variation: If True, returns varied temperature configs.
                                     If False, returns standard configs.

        Returns:
            List of temperature configuration dictionaries.
        """
        if use_temperature_variation:
            return cls._get_project_temperature_configs()
        else:
            # Return standard configurations without temperature variation
            return [
                {"temp": None, "approach": "Standard analysis", "agent_suffix": "1"},
                {"temp": None, "approach": "Standard analysis", "agent_suffix": "2"},
                {"temp": None, "approach": "Standard analysis", "agent_suffix": "3"}
            ]

    @classmethod
    def create_model_config_with_temperature(
            cls, base_config: Dict[str, Any], temperature: float) -> Dict[str, Any]:
        """
        Create a model configuration with specified temperature.

        Args:
            base_config: Base model configuration
            temperature: Temperature value to set

        Returns:
            Model configuration with temperature applied
        """
        model_config = deepcopy(base_config)
        model_config["temperature"] = temperature
        return model_config

    @classmethod
    def get_agent_name(cls, suffix: str) -> str:
        """
        Generate agent name with suffix.

        Args:
            suffix: Suffix for the agent name

        Returns:
            Formatted agent name
        """
        return f"RESEARCHER_{suffix}"

    @classmethod
    def get_agent_description(
            cls,
            approach: str,
            temperature: float = None) -> str:
        """
        Generate agent description based on approach and temperature.

        Args:
            approach: Analytical approach description
            temperature: Temperature value (optional)

        Returns:
            Formatted agent description
        """
        if temperature is not None:
            return f"Performs comprehensive INTERNAL DOCUMENT SEARCH ONLY with {
                approach} (temperature={temperature}). NO external source access."
        else:
            return "Performs comprehensive INTERNAL DOCUMENT SEARCH ONLY using Azure AI Search and returns structured JSON results from internal repositories. NO external source access."

    @classmethod
    def get_temperature_instructions(
            cls,
            temperature: float,
            approach: str) -> str:
        """
        Get temperature-specific instructions.

        Args:
            temperature: Temperature value
            approach: Analytical approach

        Returns:
            Temperature-specific instruction prompt
        """
        # Map temperature value to temperature type string
        temperature_type = cls._get_temperature_type_from_value(temperature)
        return get_temperature_researcher_prompt(temperature_type)

    @classmethod
    def _get_temperature_type_from_value(cls, temperature: float) -> str:
        """
        Map temperature value to temperature type string.
        
        Args:
            temperature: Temperature value (0.0-1.0)
            
        Returns:
            Temperature type string for prompt generation
        """
        if temperature <= 0.3:
            return "conservative"
        elif temperature <= 0.7:
            return "balanced"
        else:
            return "creative"
