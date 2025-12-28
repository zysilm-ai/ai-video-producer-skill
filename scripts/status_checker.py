#!/usr/bin/env python3
"""
Check status of async video generation jobs.
"""

import argparse
import sys

try:
    from google import genai
except ImportError:
    print("Error: google-genai package not installed", file=sys.stderr)
    print("Install with: pip install google-genai", file=sys.stderr)
    sys.exit(1)

from utils import get_api_key, print_status


def check_status(operation_name: str) -> dict:
    """
    Check status of an async generation operation.

    Args:
        operation_name: The operation name/ID to check

    Returns:
        Status dictionary with operation details
    """
    client = genai.Client(api_key=get_api_key())

    try:
        operation = client.operations.get(name=operation_name)

        status = {
            "name": operation.name,
            "done": operation.done,
            "state": operation.metadata.get("state", "unknown") if operation.metadata else "unknown",
        }

        if operation.done:
            if operation.error:
                status["error"] = operation.error.message
                print_status(f"Operation failed: {operation.error.message}", "error")
            else:
                status["success"] = True
                print_status("Operation completed successfully", "success")
        else:
            print_status(f"Operation in progress: {status['state']}", "progress")

        return status

    except Exception as e:
        print_status(f"Failed to check status: {e}", "error")
        sys.exit(1)


def list_operations(limit: int = 10) -> list[dict]:
    """
    List recent operations.

    Args:
        limit: Maximum number of operations to list

    Returns:
        List of operation status dictionaries
    """
    client = genai.Client(api_key=get_api_key())

    try:
        operations = client.operations.list(page_size=limit)

        results = []
        for op in operations:
            status = {
                "name": op.name,
                "done": op.done,
                "state": op.metadata.get("state", "unknown") if op.metadata else "unknown",
            }
            results.append(status)

            icon = "✅" if op.done else "⏳"
            print(f"{icon} {op.name}: {status['state']}")

        return results

    except Exception as e:
        print_status(f"Failed to list operations: {e}", "error")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Check status of async video generation jobs"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Check single operation
    check_parser = subparsers.add_parser("check", help="Check single operation status")
    check_parser.add_argument(
        "operation_name",
        help="Operation name/ID to check"
    )

    # List operations
    list_parser = subparsers.add_parser("list", help="List recent operations")
    list_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum number of operations to list"
    )

    args = parser.parse_args()

    if args.command == "check":
        check_status(args.operation_name)
    elif args.command == "list":
        list_operations(args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
