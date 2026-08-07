"""
Main CLI entry point for `psh`.
Supports `psh claude` and `psh gemini`.
Handles argument parsing, prompt/file reading, backend scanning, decision logic, and launching target AI CLI.
Includes multi-turn interactive chat mode (`> ` loop) and global traceback suppression.
"""
import argparse
import sys
from typing import Dict, Type, List, Optional

from cli.backend import BackendClient
from cli.config import load_config
from cli.providers.base import BaseCLIProvider
from cli.providers.claude import ClaudeProvider
from cli.providers.gemini import GeminiProvider
from cli.utils import (
    load_and_encode_file,
    print_banner,
    print_block_details,
    print_error,
    print_scan_result,
    print_warning_details,
)

PROVIDERS: Dict[str, Type[BaseCLIProvider]] = {
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="psh",
        description="PromptShield AI CLI Protection Wrapper",
    )
    subparsers = parser.add_subparsers(dest="provider", help="Target AI CLI provider")

    for name in PROVIDERS.keys():
        sub = subparsers.add_parser(name, help=f"Protect and run {name.capitalize()} CLI")
        sub.add_argument(
            "prompt_args",
            nargs="*",
            help="Prompt text (optional, if omitted will enter interactive mode)",
        )
        sub.add_argument(
            "-p",
            "--prompt",
            type=str,
            default="",
            help="Prompt string",
        )
        sub.add_argument(
            "-f",
            "--file",
            action="append",
            dest="files",
            default=[],
            help="Attach file for security scanning (e.g. -f file.txt -f data.csv)",
        )
        sub.add_argument(
            "-i",
            "--interactive",
            action="store_true",
            help="Force multi-turn interactive session mode",
        )
        sub.add_argument(
            "--backend-url",
            type=str,
            default="",
            help="Override PromptShield backend URL",
        )

    return parser


def parse_prompt(args) -> str:
    prompt_parts = []
    if args.prompt:
        prompt_parts.append(args.prompt)
    if args.prompt_args:
        prompt_parts.extend(args.prompt_args)

    prompt = " ".join(prompt_parts).strip()

    # If stdin has piped data, read it
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()

    return prompt


def process_and_execute_prompt(
    prompt: str,
    provider: BaseCLIProvider,
    client: BackendClient,
    file_inputs: List[dict],
    extra_args: Optional[List[str]] = None,
    show_banner: bool = True,
) -> int:
    """
    Core security pipeline for a single prompt:
    1. Scan prompt + files via backend.
    2. Enforce decision (ALLOW / WARN / REDACT / BLOCK).
    3. Forward to target AI CLI if permitted.
    """
    if show_banner:
        print_banner(provider.name)
    else:
        print(f"\n[PromptShield Scanning...]")

    try:
        scan_response = client.scan(
            prompt=prompt,
            provider_name=provider.name,
            files=file_inputs,
        )
    except Exception as exc:
        print_error(str(exc))
        return 1

    print_scan_result(scan_response)

    decision = scan_response.get("decision", "ALLOW")
    sanitized_prompt = scan_response.get("sanitized_prompt", prompt)

    if decision == "ALLOW":
        return provider.execute(prompt=prompt, extra_args=extra_args)

    elif decision == "WARN":
        print_warning_details(scan_response)
        try:
            confirm = input("Continue? (y/N) ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return 1

        if confirm in ("y", "yes"):
            return provider.execute(prompt=prompt, extra_args=extra_args)
        else:
            print("\nExecution cancelled by user.")
            return 0

    elif decision == "REDACT":
        print("Sensitive data detected and redacted by PromptShield policy.\n")
        print(f"Sanitized Prompt:\n{sanitized_prompt}\n")
        return provider.execute(prompt=sanitized_prompt, extra_args=extra_args)

    elif decision == "BLOCK":
        print_block_details(scan_response)
        print("Action blocked by PromptShield policy. Execution aborted.")
        return 1

    else:
        print_error(f"Unknown decision returned by backend: {decision}")
        return 1


def run_interactive_mode(
    provider: BaseCLIProvider,
    client: BackendClient,
    file_inputs: List[dict],
    extra_args: Optional[List[str]] = None,
) -> int:
    """
    Multi-turn interactive session mode.
    Continually intercepts every prompt typed at the `> ` prompt.
    """
    print(f"\nPromptShield Ready (Intercepting all prompts for {provider.name})")
    print("Type 'exit' or 'quit' to end session.\n")

    while True:
        try:
            user_input = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSession ended by user.")
            return 0

        if user_input.lower() in ("exit", "quit", ":q"):
            print("Exiting PromptShield session.")
            return 0

        if not user_input:
            continue

        process_and_execute_prompt(
            prompt=user_input,
            provider=provider,
            client=client,
            file_inputs=file_inputs,
            extra_args=extra_args,
            show_banner=False,
        )
        print()


def _run_cli() -> int:
    parser = build_parser()
    args, extra_args = parser.parse_known_args()

    if not args.provider or args.provider not in PROVIDERS:
        parser.print_help()
        return 1

    provider_class = PROVIDERS[args.provider]
    provider = provider_class()

    config = load_config()
    backend_url = args.backend_url or config["backend_url"]
    timeout = config["timeout"]
    api_token = config.get("api_token", "")

    client = BackendClient(backend_url=backend_url, timeout=timeout, api_token=api_token)

    prompt = parse_prompt(args)
    file_paths = args.files or []

    # Load and encode attached files if provided
    file_inputs = []
    for fp in file_paths:
        try:
            file_data = load_and_encode_file(fp)
            file_inputs.append(file_data)
        except Exception as exc:
            print_error(str(exc))
            return 1

    # Decide between one-shot mode vs interactive multi-turn mode
    if args.interactive or (not prompt and sys.stdin.isatty()):
        return run_interactive_mode(
            provider=provider,
            client=client,
            file_inputs=file_inputs,
            extra_args=extra_args,
        )

    if not prompt and not file_inputs:
        print_error("Scan failed: Prompt or attached file is required.")
        return 1

    return process_and_execute_prompt(
        prompt=prompt,
        provider=provider,
        client=client,
        file_inputs=file_inputs,
        extra_args=extra_args,
        show_banner=True,
    )


def main() -> int:
    try:
        return _run_cli()
    except (KeyboardInterrupt, EOFError):
        print("\n\nSession terminated by user.")
        return 0
    except ConnectionError as exc:
        print_error(str(exc))
        return 1
    except TimeoutError as exc:
        print_error(str(exc))
        return 1
    except Exception as exc:
        print_error(f"Execution error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
