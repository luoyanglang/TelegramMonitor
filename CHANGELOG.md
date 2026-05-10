# Changelog

All notable changes to Telegram Monitor will be documented in this file.

## [Unreleased]

## [2.2.1] - 2026-05-10

### Changed

- Upgraded Telethon to improve high-volume update catch-up behavior.
- Decoupled Telegram update receiving from keyword processing with a bounded worker queue.
- Reused Bot API HTTP connections during monitoring instead of creating a client per forwarded message.
- Cached keyword and blacklist lookups briefly to reduce SQLite load in high-traffic groups.

### Fixed

- Improved reliability when large groups produce fast message bursts.

## [2.2.0] - 2026-05-09

### Added

- Added multiple administrator support with `AUTHORIZED_USER_IDS`.
- Added pagination for forwarding target selection.
- Added `.dockerignore` to keep local runtime files out of Docker build context.

### Changed

- Forwarded messages now use safe HTML formatting instead of Markdown.
- Forwarding target selection now only shows manageable groups and postable channels.
- Bot-sent group messages are ignored by default to reduce noisy forwarding.
- High-frequency skip logs are now debug-level logs.

### Fixed

- Fixed forwarding loops when the target group is also monitored.
- Fixed invalid message links for basic private groups.
- Fixed malformed forwarded text when source messages contain usernames, links, or Markdown-like content.
- Fixed startup backlog replay causing old matching messages to be forwarded.
