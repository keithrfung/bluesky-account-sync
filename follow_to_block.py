"""Synchronize follows to blocks between two Bluesky accounts."""

from __future__ import annotations

import os
import sys
from typing import Set

from atproto import Client, models, exceptions

ENV_VARS = [
    "ACCOUNT_A_HANDLE",
    "ACCOUNT_A_APP_PASSWORD",
    "ACCOUNT_B_HANDLE",
    "ACCOUNT_B_APP_PASSWORD",
]


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


def get_follow_dids(client: Client, actor: str) -> Set[str]:
    """Fetch all DIDs that a given actor follows.

    Uses pagination to retrieve all follows, handling cursors automatically.

    Args:
        client: Authenticated Bluesky client.
        actor: The DID or handle of the actor whose follows to retrieve.

    Returns:
        A set of DIDs representing all accounts the actor follows.
    """
    dids: Set[str] = set()
    cursor: str | None = None

    while True:
        response = client.app.bsky.graph.get_follows(
            {"actor": actor, "limit": 100, "cursor": cursor}
        )
        for follow in response.follows:
            did = getattr(follow, "did", None)
            if did:
                dids.add(did)
        cursor = response.cursor
        if not cursor:
            break

    return dids


def get_block_dids(client: Client) -> Set[str]:
    """Fetch all DIDs that the authenticated user has blocked.

    Uses pagination to retrieve all blocks, handling cursors automatically.

    Args:
        client: Authenticated Bluesky client.

    Returns:
        A set of DIDs representing all accounts the authenticated user has blocked.
    """
    dids: Set[str] = set()
    cursor: str | None = None

    while True:
        response = client.app.bsky.graph.get_blocks({"limit": 100, "cursor": cursor})
        for profile in response.blocks:
            did = getattr(profile, "did", None)
            if did:
                dids.add(did)
        cursor = response.cursor
        if not cursor:
            break

    return dids


def unfollow_account(client: Client, did: str) -> None:
    """Unfollow an account by deleting the follow record.

    Searches through the authenticated user's follow records to find and delete
    the follow relationship with the specified DID.

    Args:
        client: Authenticated Bluesky client.
        did: The DID of the account to unfollow.
    """
    cursor: str | None = None

    while True:
        records = client.com.atproto.repo.list_records(
            {
                "repo": client.me.did,
                "collection": "app.bsky.graph.follow",
                "limit": 100,
                "cursor": cursor,
            }
        )

        for record in records.records:
            subject = getattr(record.value, "subject", None)
            if subject == did:
                rkey = record.uri.split("/")[-1]
                client.com.atproto.repo.delete_record(
                    {
                        "repo": client.me.did,
                        "collection": "app.bsky.graph.follow",
                        "rkey": rkey,
                    }
                )
                return

        cursor = records.cursor
        if not cursor:
            break


def unblock_account(client: Client, did: str) -> None:
    """Unblock an account by deleting the block record.

    Searches through the authenticated user's block records to find and delete
    the block relationship with the specified DID.

    Args:
        client: Authenticated Bluesky client.
        did: The DID of the account to unblock.
    """
    cursor: str | None = None

    while True:
        records = client.com.atproto.repo.list_records(
            {
                "repo": client.me.did,
                "collection": "app.bsky.graph.block",
                "limit": 100,
                "cursor": cursor,
            }
        )

        for record in records.records:
            subject = getattr(record.value, "subject", None)
            if subject == did:
                rkey = record.uri.split("/")[-1]
                client.com.atproto.repo.delete_record(
                    {
                        "repo": client.me.did,
                        "collection": "app.bsky.graph.block",
                        "rkey": rkey,
                    }
                )
                return

        cursor = records.cursor
        if not cursor:
            break


def main() -> None:
    """Synchronize two Bluesky accounts to maintain mutual exclusivity.

    Account A is the primary account and Account B is the secondary account.
    The script ensures that:
    - Any account followed by A is blocked on B
    - Any account followed by B is blocked on A
    - If both accounts follow the same account, B unfollows it (primary wins)
    - If both accounts block the same account, A unblocks it (secondary wins)

    Requires environment variables:
    - ACCOUNT_A_HANDLE: Handle for primary account
    - ACCOUNT_A_APP_PASSWORD: App password for primary account
    - ACCOUNT_B_HANDLE: Handle for secondary account
    - ACCOUNT_B_APP_PASSWORD: App password for secondary account
    """
    try:
        for name in ENV_VARS:
            require_env(name)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    handle_a = os.environ["ACCOUNT_A_HANDLE"]
    app_password_a = os.environ["ACCOUNT_A_APP_PASSWORD"]
    handle_b = os.environ["ACCOUNT_B_HANDLE"]
    app_password_b = os.environ["ACCOUNT_B_APP_PASSWORD"]

    print("Logging into Account A and Account B...")
    client_a = Client()
    client_b = Client()

    try:
        profile_a = client_a.login(handle_a, app_password_a)
        profile_b = client_b.login(handle_b, app_password_b)
    except exceptions.AtProtocolError as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        sys.exit(1)

    did_a = profile_a.did
    did_b = profile_b.did

    print(f"Account A (Primary): {handle_a} ({did_a})")
    print(f"Account B (Secondary): {handle_b} ({did_b})")

    print("Fetching follows for Account A...")
    try:
        follows_a = get_follow_dids(client_a, did_a)
    except exceptions.AtProtocolError as exc:
        print(f"Error fetching follows for A: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Account A follows {len(follows_a)} accounts")

    print("Fetching follows for Account B...")
    try:
        follows_b = get_follow_dids(client_b, did_b)
    except exceptions.AtProtocolError as exc:
        print(f"Error fetching follows for B: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Account B follows {len(follows_b)} accounts")

    print("Fetching blocks for Account A...")
    try:
        blocks_a = get_block_dids(client_a)
    except exceptions.AtProtocolError as exc:
        print(f"Error fetching blocks for A: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Account A blocks {len(blocks_a)} accounts")

    print("Fetching blocks for Account B...")
    try:
        blocks_b = get_block_dids(client_b)
    except exceptions.AtProtocolError as exc:
        print(f"Error fetching blocks for B: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Account B blocks {len(blocks_b)} accounts")

    conflicting_follows = follows_a & follows_b
    if conflicting_follows:
        print(
            f"\nFound {len(conflicting_follows)} accounts followed by both - unfollowing on B..."
        )
        for did in sorted(conflicting_follows):
            try:
                unfollow_account(client_b, did)
                print(f"  Unfollowed {did} on {handle_b}")
            except exceptions.AtProtocolError as exc:
                print(f"  Failed to unfollow {did} on B: {exc}", file=sys.stderr)
        follows_b -= conflicting_follows

    conflicting_blocks = blocks_a & blocks_b
    if conflicting_blocks:
        print(
            f"\nFound {len(conflicting_blocks)} accounts blocked by both - unblocking on A..."
        )
        for did in sorted(conflicting_blocks):
            try:
                unblock_account(client_a, did)
                print(f"  Unblocked {did} on {handle_a}")
            except exceptions.AtProtocolError as exc:
                print(f"  Failed to unblock {did} on A: {exc}", file=sys.stderr)
        blocks_a -= conflicting_blocks

    to_block_on_b = sorted((follows_a - blocks_b) - {did_b})
    if to_block_on_b:
        print(f"\nBlocking {len(to_block_on_b)} of A's follows on B...")
        for did in to_block_on_b:
            record = models.AppBskyGraphBlock.Record(
                subject=did,
                created_at=client_b.get_current_time_iso(),
            )
            try:
                client_b.app.bsky.graph.block.create(client_b.me.did, record)
                print(f"  Blocked {did} on {handle_b}")
            except exceptions.AtProtocolError as exc:
                print(f"  Failed to block {did} on B: {exc}", file=sys.stderr)

    to_block_on_a = sorted((follows_b - blocks_a) - {did_a})
    if to_block_on_a:
        print(f"\nBlocking {len(to_block_on_a)} of B's follows on A...")
        for did in to_block_on_a:
            record = models.AppBskyGraphBlock.Record(
                subject=did,
                created_at=client_a.get_current_time_iso(),
            )
            try:
                client_a.app.bsky.graph.block.create(client_a.me.did, record)
                print(f"  Blocked {did} on {handle_a}")
            except exceptions.AtProtocolError as exc:
                print(f"  Failed to block {did} on A: {exc}", file=sys.stderr)

    if (
        not conflicting_follows
        and not conflicting_blocks
        and not to_block_on_b
        and not to_block_on_a
    ):
        print("\nNothing to do. Accounts are already mutually exclusive.")
    else:
        print("\nSync complete. Accounts are now mutually exclusive.")


if __name__ == "__main__":
    main()
