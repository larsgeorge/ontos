"""
Unit tests for logging module

Tests logging setup and configuration including:
- Logger creation
- Logger configuration
- Logger naming
"""
import pytest
import logging

from src.common.logging import setup_logging, get_logger


class TestLogging:
    """Test suite for logging module"""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logger instance."""
        # Act
        logger = get_logger("test_module")

        # Assert
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_module_name(self):
        """Test get_logger creates logger with correct name."""
        # Arrange
        module_name = "test.module.name"

        # Act
        logger = get_logger(module_name)

        # Assert
        assert logger.name == module_name

    def test_get_logger_different_names_different_loggers(self):
        """Test get_logger returns different instances for different names."""
        # Act
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Assert
        assert logger1 is not logger2
        assert logger1.name != logger2.name

    def test_get_logger_same_name_same_logger(self):
        """Test get_logger returns same instance for same name."""
        # Act
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        # Assert
        assert logger1 is logger2

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        # Act - Should not raise
        setup_logging()

        # Assert - Check root logger is configured
        root_logger = logging.getLogger()
        assert root_logger.level <= logging.INFO

    def test_setup_logging_with_handlers(self):
        """Test setup_logging configures handlers."""
        # Act
        setup_logging()

        # Assert
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

