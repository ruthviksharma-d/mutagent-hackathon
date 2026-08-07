"""
Setup script for PromptShield CLI package (`psh`).
"""
from setuptools import setup, find_packages

setup(
    name="promptshield-cli",
    version="1.0.0",
    description="PromptShield AI CLI Protection Wrapper (Claude CLI + Gemini CLI)",
    author="PromptShield",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "psh = cli.main:main",
        ],
    },
    python_requires=">=3.8",
)
