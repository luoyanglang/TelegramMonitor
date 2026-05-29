# Changelog

All notable changes to Telegram Monitor will be documented in this file.

## [Unreleased]

### Fixed

- Fixed occasional raw-text forwarding when sender entity enrichment failed.
- Made sender ID fallbacks visible when Telegram cannot resolve a sender username.
- Resolved compact Telegram sender objects through message-context user references before falling back to sender IDs.
- Reused cached sender usernames when Telegram later sends compact user objects without usernames.
- Fixed Telegram release announcements not appearing in linked discussion groups by adding an opt-in discussion mirror.

## [2.2.2] - 2026-05-13

### Added

- Added an inline numeric keypad for Telegram account login verification codes.
- Added regression coverage for login code handling, target chat ID normalization, and sender link enrichment.

### Changed

- Telegram login verification now uses button-based code entry to avoid invalidating codes by sending them as plain Telegram messages.
- Forwarding target selection now stores Bot API-compatible chat IDs for channels, supergroups, and basic groups.
- Telegram release announcements now use a shorter highlights-and-release format.

### Fixed

- Fixed Telegram login failures where plain numeric verification codes were immediately reported as expired.
- Fixed forwarding to basic groups when the stored target ID was incorrectly converted to a `-100...` supergroup ID.
- Fixed legacy positive target IDs by retrying with the basic group Bot API ID when the supergroup ID returns `chat not found`.
- Fixed forwarded sender display by resolving full sender entities when compact message updates do not include usernames.

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
