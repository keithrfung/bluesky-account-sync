# Bluesky Account Sync

A toolkit for synchronizing and managing multiple Bluesky accounts. Keep your accounts organized with automated synchronization rules and policies.

## Features

### Follow-to-Block Sync (Current)

Maintain mutual exclusivity between two accounts by automatically blocking accounts that are followed by the other. This ensures your accounts remain completely separate with no overlap in their social graphs.

**Accounts:**
- **Account A (Primary)**: The main account
- **Account B (Secondary)**: The secondary account

**Synchronization Rules:**

1. **Mutual Blocking**: Any account followed by A is blocked on B, and vice versa
2. **Conflict Resolution**:
   - If both accounts follow the same account → B unfollows (primary wins)
   - If both accounts block the same account → A unblocks (secondary wins)
3. **Self-Protection**: Neither account will block itself

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Bluesky account credentials (handles and app passwords)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/keithrfung/bluesky-account-sync.git
   cd bluesky-account-sync
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

## Configuration

Set the following environment variables:

- `ACCOUNT_A_HANDLE`: Handle for the primary account (e.g., `user.bsky.social`)
- `ACCOUNT_A_APP_PASSWORD`: App password for the primary account
- `ACCOUNT_B_HANDLE`: Handle for the secondary account
- `ACCOUNT_B_APP_PASSWORD`: App password for the secondary account

### Creating App Passwords

1. Go to [Bluesky Settings → App Passwords](https://bsky.app/settings/app-passwords)
2. Create a new app password for each account
3. Store them securely (they won't be shown again)

## Usage

### Follow-to-Block Sync

Run the follow-to-block sync:

```bash
uv run follow-to-block
```

Or directly with Python:

```bash
uv run python follow_to_block.py
```

### GitHub Actions (Automated)

The repository includes a GitHub Actions workflow that runs automatically at midnight UTC daily. 

To set it up:

1. Go to your repository's Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `ACCOUNT_A_HANDLE`
   - `ACCOUNT_A_APP_PASSWORD`
   - `ACCOUNT_B_HANDLE`
   - `ACCOUNT_B_APP_PASSWORD`
3. Enable GitHub Actions in your repository

You can also manually trigger the workflow from the Actions tab.

## Development

### Code Quality Tools

The project uses:

- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checker

Run checks:

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type check
uv run mypy .
```

### Project Structure

```
.
├── follow_to_block.py          # Follow-to-block sync script
├── pyproject.toml              # Project configuration and dependencies
├── .python-version             # Python version specification
├── .github/
│   └── workflows/
│       └── bluesky-block-sync.yml  # GitHub Actions workflow
└── README.md                   # This file
```

## How It Works

### Follow-to-Block Sync

1. **Authentication**: Logs into both accounts using app passwords
2. **Data Collection**: Fetches follows and blocks for both accounts
3. **Conflict Resolution**: Resolves any conflicting follows/blocks
4. **Synchronization**: Applies blocks to maintain mutual exclusivity
5. **Reporting**: Outputs detailed logs of all actions taken

## License

MIT

## Disclaimer

This tool modifies your Bluesky account follows and blocks. Use at your own risk. Always test with non-critical accounts first.