"""
Logging configuration utilitie.
This module provides centralized logging setup and configuration functions
to reduce redundancy across the application.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_application_logging(
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    max_log_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up comprehensive logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to ./logs)
        enable_file_logging: Whether to enable file logging
        enable_console_logging: Whether to enable console logging
        max_log_file_size: Maximum size of each log file in bytes
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured root logger
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logs directory if needed
    if log_dir is None:
        log_dir = Path.cwd() / "logs"
    else:
        log_dir = Path(log_dir)
    
    if enable_file_logging:
        log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Set up console logging
    if enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Set up file logging
    if enable_file_logging:
        # Main application log
        main_log_file = log_dir / "research_agent.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=max_log_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Error-only log file
        error_log_file = log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_log_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
    
    return root_logger


def setup_agent_activity_logging(agent_name: str, log_dir: Optional[str] = None) -> logging.Logger:
    """
    Set up dedicated logging for individual agent activities.
    
    Args:
        agent_name: Name of the agent (used for log file naming)
        log_dir: Directory for log files (defaults to ./agent_logs)
        
    Returns:
        Configured logger for the specific agent
    """
    if log_dir is None:
        log_dir = Path.cwd() / "agent_logs"
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(exist_ok=True)
    
    # Create agent-specific logger
    logger_name = f"agent.{agent_name}"
    agent_logger = logging.getLogger(logger_name)
    
    # Avoid duplicate handlers
    if agent_logger.handlers:
        return agent_logger
    
    agent_logger.setLevel(logging.DEBUG)
    
    # Agent activity log file
    log_file = log_dir / f"{agent_name}_activity.log"
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    agent_logger.addHandler(handler)
    
    # Prevent propagation to avoid duplicate logs
    agent_logger.propagate = False
    
    return agent_logger


def get_research_executor_logger() -> logging.Logger:
    """
    Get a properly configured logger for ResearchExecutor.
    
    Returns:
        Logger instance for ResearchExecutor
    """
    logger = logging.getLogger("lib.orchestration.research_executor")
    logger.setLevel(logging.INFO)  # Ensure INFO level is set
    return logger


def configure_module_loggers():
    """Configure specific logging levels for different modules to reduce noise."""
    
    # Set semantic-kernel logs to WARNING to reduce noise
    logging.getLogger("semantic_kernel").setLevel(logging.WARNING)
    
    # Set Azure SDK logs to WARNING
    logging.getLogger("azure").setLevel(logging.WARNING)
    
    # Set HTTP client logs to WARNING
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Set our internal module levels
    logging.getLogger("lib.search").setLevel(logging.INFO)
    logging.getLogger("lib.memory").setLevel(logging.INFO)
    logging.getLogger("lib.orchestration").setLevel(logging.INFO)


def log_system_info(logger: logging.Logger):
    """Log system information for debugging purposes."""
    import platform
    import psutil
    
    logger.info("=" * 50)
    logger.info("Research Agent - System Information")
    logger.info("=" * 50)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"CPU count: {psutil.cpu_count()}")
    logger.info(f"Available memory: {psutil.virtual_memory().available / (1024**3):.2f} GB")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Log level: {logger.getEffectiveLevel()}")
    logger.info("=" * 50)


def create_performance_logger() -> logging.Logger:
    """Create a dedicated logger for performance metrics."""
    perf_logger = logging.getLogger("performance")
    
    if perf_logger.handlers:
        return perf_logger
    
    perf_logger.setLevel(logging.INFO)
    
    # Performance log file
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    
    perf_file = log_dir / "performance.log"
    handler = logging.handlers.RotatingFileHandler(
        perf_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - PERF - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    perf_logger.addHandler(handler)
    perf_logger.propagate = False
    
    return perf_logger
