// THROWAWAY SPIKE CODE (Reliquary A6, Wave 1). Not production code.
//
// catalog.go: a stand-in SQLite catalog (ADR-0013 is undecided; SQLite is used
// here only because it is embeddable). WAL + synchronous=FULL.
package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"sort"

	_ "modernc.org/sqlite"
)

const schema = `
CREATE TABLE IF NOT EXISTS blobs(
  sha256 TEXT PRIMARY KEY, size INTEGER NOT NULL, stored_sha256 TEXT NOT NULL,
  stored_size INTEGER NOT NULL, epoch INTEGER NOT NULL, committed_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS records(
  record_id TEXT PRIMARY KEY, device_id TEXT NOT NULL, person TEXT NOT NULL, dedup_id TEXT NOT NULL,
  sha256 TEXT NOT NULL REFERENCES blobs(sha256), size INTEGER NOT NULL, header_mac TEXT,
  path TEXT NOT NULL, name TEXT NOT NULL, mtime_ns INTEGER NOT NULL,
  meta_sha256 TEXT NOT NULL, stored_sha256 TEXT NOT NULL, stored_size INTEGER NOT NULL,
  committed_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS records_sha ON records(sha256);
CREATE INDEX IF NOT EXISTS records_name ON records(name);
CREATE TABLE IF NOT EXISTS ingest_events(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL, at INTEGER NOT NULL, outcome TEXT NOT NULL);
`

func OpenCatalog(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", "file:"+path+"?_pragma=journal_mode(WAL)&_pragma=synchronous(FULL)&_pragma=foreign_keys(ON)")
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(schema); err != nil {
		return nil, err
	}
	return db, nil
}

type RecBody struct {
	V             int             `json:"v"`
	Type          string          `json:"type"`
	RecordID      string          `json:"record_id"`
	DeviceID      string          `json:"device_id"`
	Person        string          `json:"person"`
	DedupID       string          `json:"dedup_id"`
	SHA256        string          `json:"sha256"`
	Size          int64           `json:"size"`
	ContentObject *ContentObjRef  `json:"content_object"`
	Path          string          `json:"path"`
	Name          string          `json:"name"`
	MtimeNs       int64           `json:"mtime_ns"`
	Extra         json.RawMessage `json:"extra,omitempty"`
}

type ContentObjRef struct {
	HeaderMAC string `json:"header_mac"`
}

func catalogCommit(db *sql.DB, blob *ManLine, rec ManLine, body RecBody, newBlob bool) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if blob != nil {
		if _, err := tx.Exec(`INSERT OR IGNORE INTO blobs VALUES(?,?,?,?,?,?)`, blob.SHA256, blob.Size,
			blob.StoredSHA256, blob.StoredSize, blob.Epoch, blob.At); err != nil {
			return err
		}
	}
	hm := sql.NullString{}
	if body.ContentObject != nil {
		hm = sql.NullString{String: body.ContentObject.HeaderMAC, Valid: true}
	}
	if _, err := tx.Exec(`INSERT OR IGNORE INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)`, rec.RecordID,
		body.DeviceID, body.Person, body.DedupID, body.SHA256, body.Size, hm, body.Path, body.Name, body.MtimeNs,
		rec.MetaSHA256, rec.StoredSHA256, rec.StoredSize, rec.At); err != nil {
		return err
	}
	if _, err := tx.Exec(`INSERT INTO ingest_events(record_id, at, outcome) VALUES(?,?,?)`, rec.RecordID, rec.At, "committed"); err != nil {
		return err
	}
	return tx.Commit()
}

func catalogHas(db *sql.DB, rid string) bool {
	var n int
	db.QueryRow(`SELECT count(*) FROM records WHERE record_id=?`, rid).Scan(&n)
	return n > 0
}

// Canonical export: JSON lines, fixed key order, sorted; excludes operational
// tables (ingest_events). maskTime zeroes committed_at (for the files-only rebuild).
func exportCanonical(db *sql.DB, w io.Writer, maskTime bool) error {
	rows, err := db.Query(`SELECT sha256,size,stored_sha256,stored_size,epoch,committed_at FROM blobs ORDER BY sha256`)
	if err != nil {
		return err
	}
	for rows.Next() {
		var sha, ss string
		var size, ssz, at int64
		var ep int
		rows.Scan(&sha, &size, &ss, &ssz, &ep, &at)
		if maskTime {
			at = 0
		}
		fmt.Fprintf(w, "{\"t\":\"blob\",\"sha256\":%q,\"size\":%d,\"stored_sha256\":%q,\"stored_size\":%d,\"epoch\":%d,\"committed_at\":%d}\n",
			sha, size, ss, ssz, ep, at)
	}
	rows.Close()
	rows, err = db.Query(`SELECT record_id,device_id,person,dedup_id,sha256,size,coalesce(header_mac,''),path,name,mtime_ns,meta_sha256,stored_sha256,stored_size,committed_at FROM records ORDER BY record_id`)
	if err != nil {
		return err
	}
	var out []string
	for rows.Next() {
		var rid, dev, per, did, sha, hm, p, n, ms, ss string
		var size, mt, ssz, at int64
		rows.Scan(&rid, &dev, &per, &did, &sha, &size, &hm, &p, &n, &mt, &ms, &ss, &ssz, &at)
		if maskTime {
			at = 0
		}
		out = append(out, fmt.Sprintf("{\"t\":\"record\",\"record_id\":%q,\"device_id\":%q,\"person\":%q,\"dedup_id\":%q,\"sha256\":%q,\"size\":%d,\"header_mac\":%q,\"path\":%q,\"name\":%q,\"mtime_ns\":%d,\"meta_sha256\":%q,\"stored_sha256\":%q,\"stored_size\":%d,\"committed_at\":%d}\n",
			rid, dev, per, did, sha, size, hm, p, n, mt, ms, ss, ssz, at))
	}
	rows.Close()
	sort.Strings(out)
	for _, s := range out {
		io.WriteString(w, s)
	}
	return nil
}
