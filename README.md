# Bluesky Account Sync

[![Lint](https://github.com/keithrfung/bluesky-account-sync/actions/workflows/lint.yml/badge.svg)](https://github.com/keithrfung/bluesky-account-sync/actions/workflows/lint.yml)

Automatically keeps two Bluesky accounts mutually exclusive — anyone followed by Account A gets blocked on Account B, and vice versa. Runs once a day for free using GitHub.

## What it does

- Anyone Account A follows → blocked on Account B
- Anyone Account B follows → blocked on Account A
- If both accounts follow the same person → Account B unfollows them
- If both accounts have blocked the same person → Account A unblocks them

## Setup

### 1. Fork this repository

Click **Fork** at the top right of this page to copy it to your own GitHub account.

### 2. Create app passwords for both Bluesky accounts

An app password lets this tool log in on your behalf without using your real password.

1. Log in to your first account at [bsky.app](https://bsky.app)
2. Go to **Settings → App Passwords → Add App Password**
3. Give it a name (e.g. `account-sync`) and save the password somewhere safe
4. Repeat for your second account

### 3. Add your credentials to GitHub

1. In your forked repository, go to **Settings → Secrets and variables → Actions**
2. Add these four secrets:

| Secret name | What to put in it |
|---|---|
| `ACCOUNT_A_HANDLE` | Your first account's handle (e.g. `you.bsky.social`) |
| `ACCOUNT_A_APP_PASSWORD` | The app password you created for the first account |
| `ACCOUNT_B_HANDLE` | Your second account's handle |
| `ACCOUNT_B_APP_PASSWORD` | The app password you created for the second account |

### 4. Enable GitHub Actions

Go to the **Actions** tab in your forked repository and click **Enable workflows**.

That's it. The sync will run automatically every day.

## Schedule

The sync runs once a day at midnight UTC. This is controlled by [this line in the workflow file](.github/workflows/bluesky-block-sync.yml#L5) — you can change the time there if you'd like.

You can also trigger it manually at any time from the **Actions** tab by clicking **Bluesky Account Sync → Run workflow**.

## Disclaimer

This tool modifies your Bluesky account follows and blocks. Use at your own risk.
