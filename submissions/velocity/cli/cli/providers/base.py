"""
BaseCLIProvider abstract interface.
All provider implementations (Claude, Gemini, OpenAI, etc.) must inherit from this class.
"""
from abc import ABC, abstractmethod
import shutil
import subprocess
from typing import Optional, List


class BaseCLIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name, e.g. 'Claude' or 'Gemini'."""
        pass

    @property
    @abstractmethod
    def binary_name(self) -> str:
        """Name of the target CLI binary on system PATH (e.g. 'claude', 'gemini')."""
        pass

    def get_executable_path(self) -> Optional[str]:
        """Resolves the full system executable path for the target binary (supporting .exe, .cmd, .bat on Windows)."""
        return shutil.which(self.binary_name)

    def is_installed(self) -> bool:
        """Checks whether the target CLI executable is available in system PATH."""
        return self.get_executable_path() is not None

    @abstractmethod
    def execute(self, prompt: str, extra_args: Optional[List[str]] = None) -> int:
        """
        Launches the target AI CLI with the given sanitized prompt and extra arguments.
        Returns the process exit code.
        """
        pass
