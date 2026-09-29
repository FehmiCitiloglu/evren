"""Evren Agent Computer Use - Production Cross-Platform Desktop Automation."""
from __future__ import annotations

from evren_agent.computer_use.backends import (
    ComputerBackend,
    LinuxBackend,
    MacOSBackend,
    MockBackend,
    WindowsBackend,
    get_backend,
)
from evren_agent.computer_use.coordinates import CoordinateManager
from evren_agent.computer_use.models import (
    AccessibilityNode,
    ActionBlockedError,
    CapabilityStatus,
    CapabilityUnavailableError,
    ClickType,
    ComputerUseError,
    ConfirmationRequest,
    DisplayInfo,
    DisplayNotFoundError,
    EnvironmentInfo,
    InvalidCoordinatesError,
    MouseButton,
    PermissionDeniedError,
    Point,
    Region,
    RiskLevel,
    ScreenshotMetadata,
    ScreenshotResult,
    ScrollDirection,
    TimeoutError,
    UserCancelledError,
    WindowInfo,
    WindowNotFoundError,
)
from evren_agent.computer_use.permissions import PermissionChecker
from evren_agent.computer_use.screenshots import ScreenshotProcessor
from evren_agent.computer_use.security import ComputerUseConfig, SecurityManager
from evren_agent.computer_use.service import ComputerUseService
from evren_agent.computer_use.tools import (
    register_computer_use_tools,
    unregister_computer_use_tools,
)

__all__ = [
    "ComputerUseService",
    "ComputerUseConfig",
    "SecurityManager",
    "CoordinateManager",
    "ScreenshotProcessor",
    "PermissionChecker",
    "register_computer_use_tools",
    "unregister_computer_use_tools",
    "ComputerBackend",
    "MacOSBackend",
    "WindowsBackend",
    "LinuxBackend",
    "MockBackend",
    "get_backend",
    "Point",
    "Region",
    "DisplayInfo",
    "WindowInfo",
    "AccessibilityNode",
    "EnvironmentInfo",
    "ScreenshotMetadata",
    "ScreenshotResult",
    "MouseButton",
    "ClickType",
    "ScrollDirection",
    "RiskLevel",
    "CapabilityStatus",
    "ConfirmationRequest",
    "ComputerUseError",
    "PermissionDeniedError",
    "CapabilityUnavailableError",
    "DisplayNotFoundError",
    "WindowNotFoundError",
    "InvalidCoordinatesError",
    "ActionBlockedError",
    "UserCancelledError",
    "TimeoutError",
]
