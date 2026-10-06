-- D6-S1 minimal-PII control plane schema (THROWAWAY spike, emulated).
-- By design there is no column for a person's name, email address or device name.
CREATE TABLE invites (
  invite_id   TEXT PRIMARY KEY,          -- opaque, random
  code_hash   TEXT NOT NULL UNIQUE,      -- SHA-256 of the invite code (ADR-0002 section 2)
  expires_at  INTEGER NOT NULL,
  state       TEXT NOT NULL DEFAULT 'unused',
  account_id  TEXT
);
CREATE TABLE accounts (
  account_id   TEXT PRIMARY KEY,         -- opaque, random
  created_hour INTEGER NOT NULL
);
CREATE TABLE devices (
  device_id        TEXT PRIMARY KEY,     -- opaque, random
  account_id       TEXT NOT NULL,
  token_hash       TEXT NOT NULL,
  pubkey           TEXT NOT NULL,        -- device age recipient (public)
  enrolled_hour    INTEGER NOT NULL,
  last_seen_hour   INTEGER,              -- coarse: floored to the hour
  last_commit_hour INTEGER
);
CREATE TABLE commits (
  seq            INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id      TEXT NOT NULL,
  object_id      TEXT NOT NULL,          -- opaque dedup ID (HMAC), never a filename
  committed_hour INTEGER NOT NULL
);
CREATE TABLE meta (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
