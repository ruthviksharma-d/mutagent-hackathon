"""
Claude CLI adapter implementation.
"""
import sys
import subprocess
from typing import Optional, List
from cli.providers.base import BaseCLIProvider


class ClaudeProvider(BaseCLIProvider):
    @property
    def name(self) -> str:
        return "Claude"

    @property
    def binary_name(self) -> str:
        return "claude"

    def execute(self, prompt: str, extra_args: Optional[List[str]] = None) -> int:
        exe_path = self.get_executable_path()
        if not exe_path:
            print(
                f"\nPromptShield Error: Claude CLI ('{self.binary_name}') is not installed or not found in system PATH.\n",
                file=sys.stderr,
            )
            return 127

        cmd = [exe_path]
        if prompt:
            cmd.extend(["-p", prompt])
        if extra_args:
            cmd.extend(extra_args)

        try:
            stdin_data = (prompt + "\n").encode("utf-8") if prompt else None
            res = subprocess.run(cmd, input=stdin_data)
            return res.returncode
        except Exception as exc:
            print(f"\nPromptShield Error launching Claude CLI: {exc}\n", file=sys.stderr)
            return 1
