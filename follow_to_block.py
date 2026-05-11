"""Sync followers to blocks between two Bluesky accounts."""

from __future__ import annotations

import os
import sys
import time
from enum import Enum

from atproto import Client, models, exceptions

# Delay between write operations to stay within Bluesky's rate limits.
# See: https://docs.bsky.app/docs/advanced-guides/rate-limits
_WRITE_DELAY_SECONDS = 1.0

# ANSI Color codes for prettier logging
COLOR_RESET = "\033[0m"
COLOR_GREEN = "\033[92m"  # Success messages
COLOR_YELLOW = "\033[93m"  # Warning/conflict messages
COLOR_RED = "\033[91m"  # Error messages


class LogColor(Enum):
    """Color states for log messages."""

    SUCCESS = COLOR_GREEN
    WARNING = COLOR_YELLOW
    ERROR = COLOR_RED
    NORMAL = ""


def log(message: str, color: LogColor = LogColor.NORMAL, error: bool = False) -> None:
    """Print a colored log message.

    Args:
        message: The message to print.
        color: The color state for the message.
        error: If True, print to stderr instead of stdout.
    """
    colored_message = f"{color.value}{message}{COLOR_RESET}" if color.value else message
    print(colored_message, file=sys.stderr if error else sys.stdout)


def require_env(name: str) -> str:
    """Retrieve a required environment variable.

    Args:
        name: The name of the environment variable to retrieve.

    Returns:
        The value of the environment variable.

    Raises:
        RuntimeError: If the environment variable is not set or is empty.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def get_follower_dids(client: Client, actor: str) -> set[str]:
    """Fetch all DIDs of accounts that follow a given actor.

    Uses pagination to retrieve all followers, handling cursors automatically.

    Args:
        client: Authenticated Bluesky client.
        actor: The DID or handle of the actor whose followers to retrieve.

    Returns:
        A set of DIDs representing all accounts that follow the actor.
    """
    dids: set[str] = set()
    cursor: str | None = None

    while True:
        response = client.app.bsky.graph.get_followers(
            {"actor": actor, "limit": 100, "cursor": cursor}
        )
        for follower in response.followers:
            did = getattr(follower, "did", None)
            if did:
                dids.add(did)
            else:
                log(
                    f"⚠ Skipping follower record with no DID: {follower}",
                    LogColor.WARNING,
                )
        cursor = response.cursor
        if not cursor:
            break

    return dids


def get_block_dids(client: Client) -> set[str]:
    """Fetch all DIDs that the authenticated user has blocked.

    Uses pagination to retrieve all blocks, handling cursors automatically.

    Args:
        client: Authenticated Bluesky client.

    Returns:
        A set of DIDs representing all accounts the authenticated user has blocked.
    """
    dids: set[str] = set()
    cursor: str | None = None

    while True:
        response = client.app.bsky.graph.get_blocks({"limit": 100, "cursor": cursor})
        for profile in response.blocks:
            did = getattr(profile, "did", None)
            if did:
                dids.add(did)
            else:
                log(f"⚠ Skipping block record with no DID: {profile}", LogColor.WARNING)
        cursor = response.cursor
        if not cursor:
            break

    return dids


def _login(handle: str, password: str) -> tuple[Client, str]:
    """Login to a Bluesky account and return the client and DID.

    Args:
        handle: The account handle.
        password: The app password.

    Returns:
        A tuple of (authenticated client, account DID).
    """
    client = Client()
    try:
        profile = client.login(handle, password)
    except exceptions.AtProtocolError as exc:
        log(f"Login failed for {handle}: {exc}", LogColor.ERROR, error=True)
        sys.exit(1)
    assert client.me is not None
    return client, profile.did


def _block_accounts(client: Client, handle: str, dids: list[str]) -> None:
    """Block a list of accounts on the given client.

    Args:
        client: Authenticated Bluesky client.
        handle: The handle of the account performing the blocks (for logging).
        dids: List of DIDs to block.

    Note:
        CREATE operations cost 3 rate-limit points (~1,666 creates/hour, ~11,666/day).
        See: https://docs.bsky.app/docs/advanced-guides/rate-limits
    """
    assert client.me is not None
    for did in dids:
        record = models.AppBskyGraphBlock.Record(
            subject=did,
            created_at=client.get_current_time_iso(),
        )
        try:
            client.app.bsky.graph.block.create(client.me.did, record)
            log(f"  ✓ Blocked {did} on {handle}", LogColor.SUCCESS)
        except exceptions.AtProtocolError as exc:
            log(
                f"  ✗ Failed to block {did} on {handle}: {exc}",
                LogColor.ERROR,
                error=True,
            )
        time.sleep(_WRITE_DELAY_SECONDS)


def main() -> None:
    """Synchronize two Bluesky accounts to maintain mutual exclusivity.

    The script ensures that:
    - Anyone who follows Account B is blocked on Account A
    - Anyone who follows Account A, but not B, is blocked on Account B
    - Anyone who follows both accounts is blocked on A only

    Requires environment variables:
    - ACCOUNT_A_HANDLE: Handle for primary account
    - ACCOUNT_A_APP_PASSWORD: App password for primary account
    - ACCOUNT_B_HANDLE: Handle for secondary account
    - ACCOUNT_B_APP_PASSWORD: App password for secondary account
    """
    try:
        handle_a = require_env("ACCOUNT_A_HANDLE")
        app_password_a = require_env("ACCOUNT_A_APP_PASSWORD")
        handle_b = require_env("ACCOUNT_B_HANDLE")
        app_password_b = require_env("ACCOUNT_B_APP_PASSWORD")
    except RuntimeError as exc:
        log(str(exc), LogColor.ERROR, error=True)
        sys.exit(1)

    log("🔐 Logging into Account A and Account B...")
    client_a, did_a = _login(handle_a, app_password_a)
    client_b, did_b = _login(handle_b, app_password_b)

    log(f"Account A: {handle_a} ({did_a})")
    log(f"Account B: {handle_b} ({did_b})")

    log("📊 Fetching followers for Account A...")
    try:
        followers_a = get_follower_dids(client_a, did_a)
    except exceptions.AtProtocolError as exc:
        log(f"Error fetching followers for A: {exc}", LogColor.ERROR, error=True)
        sys.exit(1)
    log(f"✓ Account A has {len(followers_a)} followers")

    log("📊 Fetching followers for Account B...")
    try:
        followers_b = get_follower_dids(client_b, did_b)
    except exceptions.AtProtocolError as exc:
        log(f"Error fetching followers for B: {exc}", LogColor.ERROR, error=True)
        sys.exit(1)
    log(f"✓ Account B has {len(followers_b)} followers")

    log("🚫 Fetching blocks for Account A...")
    try:
        blocks_a = get_block_dids(client_a)
    except exceptions.AtProtocolError as exc:
        log(f"Error fetching blocks for A: {exc}", LogColor.ERROR, error=True)
        sys.exit(1)
    log(f"✓ Account A blocks {len(blocks_a)} accounts")

    log("🚫 Fetching blocks for Account B...")
    try:
        blocks_b = get_block_dids(client_b)
    except exceptions.AtProtocolError as exc:
        log(f"Error fetching blocks for B: {exc}", LogColor.ERROR, error=True)
        sys.exit(1)
    log(f"✓ Account B blocks {len(blocks_b)} accounts")

    # Everyone who follows B → block on A
    to_block_on_a = sorted((followers_b - blocks_a) - {did_a})
    if to_block_on_a:
        log(f"🚫 Blocking {len(to_block_on_a)} of B's followers on A...")
        _block_accounts(client_a, handle_a, to_block_on_a)

    # Everyone who follows A but not B → block on B
    to_block_on_b = sorted(((followers_a - followers_b) - blocks_b) - {did_b})
    if to_block_on_b:
        log(f"🚫 Blocking {len(to_block_on_b)} of A's exclusive followers on B...")
        _block_accounts(client_b, handle_b, to_block_on_b)

    if not to_block_on_a and not to_block_on_b:
        log("✓ Nothing to do. Accounts are already in sync.", LogColor.SUCCESS)
    else:
        log("✓ Sync complete.", LogColor.SUCCESS)


if __name__ == "__main__":
    main()
