-- state/v3/d1/miniflare-D1DatabaseObject/ebb31a33f27f94efbb056ea4a4982386d6cb7b96ea947c19edbc7cde8ee8c252.sqlite
BEGIN TRANSACTION;
CREATE TABLE _cf_METADATA (
        key INTEGER PRIMARY KEY,
        value BLOB
      );
INSERT INTO "_cf_METADATA" VALUES(2,7518);
CREATE TABLE accounts (
  account_id   TEXT PRIMARY KEY,         -- opaque, random
  created_hour INTEGER NOT NULL
);
INSERT INTO "accounts" VALUES('b229fdf5d562c517c60ca0acaf574c4f',1791194400);
INSERT INTO "accounts" VALUES('a512bbf9dbe24287b72638f7a367aa2a',1791194400);
INSERT INTO "accounts" VALUES('92322d454f639275ca4732046099960e',1791194400);
INSERT INTO "accounts" VALUES('50e5884d5dea3a4e1d8528d7d1979d72',1791194400);
CREATE TABLE commits (
  seq            INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id      TEXT NOT NULL,
  object_id      TEXT NOT NULL,          -- opaque dedup ID (HMAC), never a filename
  committed_hour INTEGER NOT NULL
);
INSERT INTO "commits" VALUES(1,'28e921c2dc242fc1c5d18b37e3eae732','hmac-gamma-phone-0',1791201600);
INSERT INTO "commits" VALUES(2,'671931d5c3ad79ccc3a4daecc70c0a6c','hmac-alpha-phone-0',1791208800);
INSERT INTO "commits" VALUES(3,'07212ce2870b8a26adaa0787e5d26532','hmac-delta-laptop-0',1791219600);
INSERT INTO "commits" VALUES(4,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-0',1791230400);
INSERT INTO "commits" VALUES(5,'790e16d215aecb76a9226c5ade883c4d','hmac-beta-laptop-0',1791234000);
INSERT INTO "commits" VALUES(6,'28e921c2dc242fc1c5d18b37e3eae732','hmac-gamma-phone-1',1791288000);
INSERT INTO "commits" VALUES(7,'671931d5c3ad79ccc3a4daecc70c0a6c','hmac-alpha-phone-1',1791295200);
INSERT INTO "commits" VALUES(8,'07212ce2870b8a26adaa0787e5d26532','hmac-delta-laptop-1',1791306000);
INSERT INTO "commits" VALUES(9,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-1',1791316800);
INSERT INTO "commits" VALUES(10,'790e16d215aecb76a9226c5ade883c4d','hmac-beta-laptop-1',1791320400);
INSERT INTO "commits" VALUES(11,'28e921c2dc242fc1c5d18b37e3eae732','hmac-gamma-phone-2',1791374400);
INSERT INTO "commits" VALUES(12,'671931d5c3ad79ccc3a4daecc70c0a6c','hmac-alpha-phone-2',1791381600);
INSERT INTO "commits" VALUES(13,'07212ce2870b8a26adaa0787e5d26532','hmac-delta-laptop-2',1791392400);
INSERT INTO "commits" VALUES(14,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-2',1791403200);
INSERT INTO "commits" VALUES(15,'790e16d215aecb76a9226c5ade883c4d','hmac-beta-laptop-2',1791406800);
INSERT INTO "commits" VALUES(16,'28e921c2dc242fc1c5d18b37e3eae732','hmac-gamma-phone-3',1791460800);
INSERT INTO "commits" VALUES(17,'671931d5c3ad79ccc3a4daecc70c0a6c','hmac-alpha-phone-3',1791468000);
INSERT INTO "commits" VALUES(18,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-3',1791489600);
INSERT INTO "commits" VALUES(19,'790e16d215aecb76a9226c5ade883c4d','hmac-beta-laptop-3',1791493200);
INSERT INTO "commits" VALUES(20,'28e921c2dc242fc1c5d18b37e3eae732','hmac-gamma-phone-4',1791547200);
INSERT INTO "commits" VALUES(21,'671931d5c3ad79ccc3a4daecc70c0a6c','hmac-alpha-phone-4',1791554400);
INSERT INTO "commits" VALUES(22,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-4',1791576000);
INSERT INTO "commits" VALUES(23,'28e921c2dc242fc1c5d18b37e3eae732','hmac-gamma-phone-5',1791633600);
INSERT INTO "commits" VALUES(24,'671931d5c3ad79ccc3a4daecc70c0a6c','hmac-alpha-phone-5',1791640800);
INSERT INTO "commits" VALUES(25,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-5',1791662400);
INSERT INTO "commits" VALUES(26,'28e921c2dc242fc1c5d18b37e3eae732','hmac-gamma-phone-6',1791720000);
INSERT INTO "commits" VALUES(27,'671931d5c3ad79ccc3a4daecc70c0a6c','hmac-alpha-phone-6',1791727200);
INSERT INTO "commits" VALUES(28,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-6',1791748800);
INSERT INTO "commits" VALUES(29,'28e921c2dc242fc1c5d18b37e3eae732','hmac-gamma-phone-7',1791806400);
INSERT INTO "commits" VALUES(30,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-7',1791835200);
INSERT INTO "commits" VALUES(31,'28e921c2dc242fc1c5d18b37e3eae732','hmac-gamma-phone-8',1791892800);
INSERT INTO "commits" VALUES(32,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-8',1791921600);
INSERT INTO "commits" VALUES(33,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-9',1792008000);
INSERT INTO "commits" VALUES(34,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-10',1792094400);
INSERT INTO "commits" VALUES(35,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-11',1792180800);
INSERT INTO "commits" VALUES(36,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-12',1792267200);
INSERT INTO "commits" VALUES(37,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-13',1792353600);
INSERT INTO "commits" VALUES(38,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-14',1792440000);
INSERT INTO "commits" VALUES(39,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-15',1792526400);
INSERT INTO "commits" VALUES(40,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-16',1792612800);
INSERT INTO "commits" VALUES(41,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-17',1792699200);
INSERT INTO "commits" VALUES(42,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-18',1792785600);
INSERT INTO "commits" VALUES(43,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-19',1792872000);
INSERT INTO "commits" VALUES(44,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-20',1792958400);
INSERT INTO "commits" VALUES(45,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-21',1793044800);
INSERT INTO "commits" VALUES(46,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-22',1793131200);
INSERT INTO "commits" VALUES(47,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-23',1793217600);
INSERT INTO "commits" VALUES(48,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-24',1793304000);
INSERT INTO "commits" VALUES(49,'5614a75ed30cb67ef67cb7bf48d81ead','hmac-alpha-laptop-25',1793390400);
CREATE TABLE "d1_migrations"(
		id         INTEGER PRIMARY KEY AUTOINCREMENT,
		name       TEXT UNIQUE,
		applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
INSERT INTO "d1_migrations" VALUES(1,'0001_init.sql','2026-09-29 10:28:35');
CREATE TABLE devices (
  device_id        TEXT PRIMARY KEY,     -- opaque, random
  account_id       TEXT NOT NULL,
  token_hash       TEXT NOT NULL,
  pubkey           TEXT NOT NULL,        -- device age recipient (public)
  enrolled_hour    INTEGER NOT NULL,
  last_seen_hour   INTEGER,              -- coarse: floored to the hour
  last_commit_hour INTEGER
);
INSERT INTO "devices" VALUES('5614a75ed30cb67ef67cb7bf48d81ead','b229fdf5d562c517c60ca0acaf574c4f','d0d4d40abe326822ac2593f785d71c947e65b8c61f4a32b37ce3806b057fa582','age15cghy97zg46qpl0dtttk6al5gdpgeeeeedfu4gtvu545g0vl5ehsd6v592',1791194400,1793397600,1793390400);
INSERT INTO "devices" VALUES('790e16d215aecb76a9226c5ade883c4d','a512bbf9dbe24287b72638f7a367aa2a','09182c969804edc23685761d13f61a3acde551bf8056ca638ea7b43ea9c422f3','age1r7zutm0x7q5cd9ge7lj046mlv3ptnwvg0jquhkj90gvs50hax5tsnepjxd',1791194400,1793394000,1791493200);
INSERT INTO "devices" VALUES('28e921c2dc242fc1c5d18b37e3eae732','92322d454f639275ca4732046099960e','751642871463687a346f066e0f285b2757771ed734bf770352e533f70e4a8f05','age14wgnyqm2kty3sfmjjdyhj2xuhd0ghf9pl5dadwc3z4z7wsku95fsg5csar',1791194400,1791892800,1791892800);
INSERT INTO "devices" VALUES('07212ce2870b8a26adaa0787e5d26532','50e5884d5dea3a4e1d8528d7d1979d72','3c4b831a39467d6baa809438f0240b9ea84263f552bb13b2a80272c4f073fc8d','age1h8t8h7e6zfqgmpgqye35xnv0hpc2ga2kwsxe2ucqadrz9ujfza4sh8ql6l',1791194400,1791392400,1791392400);
INSERT INTO "devices" VALUES('671931d5c3ad79ccc3a4daecc70c0a6c','b229fdf5d562c517c60ca0acaf574c4f','d067773e75e8d82ea4cfeec1d2800473c4e26ade3362594df3dcc808ca220196','age12te0vjrlwuuyn9zhwct5n97mhq5j24thlcsx2uks7wx5k9ttye6qscqna3',1791198000,1791727200,1791727200);
CREATE TABLE invites (
  invite_id   TEXT PRIMARY KEY,          -- opaque, random
  code_hash   TEXT NOT NULL UNIQUE,      -- SHA-256 of the invite code (ADR-0002 section 2)
  expires_at  INTEGER NOT NULL,
  state       TEXT NOT NULL DEFAULT 'unused',
  account_id  TEXT
);
INSERT INTO "invites" VALUES('b0b01baf70a9ea7fa6a5c87a30e6b8ef','e25d41a7899de36077901c20339df80b8c8daa461bf3cf383df9134341958241',1793782800,'redeemed','b229fdf5d562c517c60ca0acaf574c4f');
INSERT INTO "invites" VALUES('1a47073aab173e808783fe3ec705d986','659662ee1f655801600a18f55c16bf679cc267565e9a5faba936a5ebd1c632da',1793782800,'redeemed','a512bbf9dbe24287b72638f7a367aa2a');
INSERT INTO "invites" VALUES('59db1b0b1461d54a5c81a26c5ca40184','9bba268d95996c511deb5d591ae5dfe0ae5b594622362a9194b3eafcf44a550e',1793782800,'redeemed','92322d454f639275ca4732046099960e');
INSERT INTO "invites" VALUES('970e0cab06531c04443e22f089a36163','c3e5d2d7fbd166988cdb408b1b2d7b37f2ebd5342592cfeb6aaa5cb8e41944d0',1793782800,'redeemed','50e5884d5dea3a4e1d8528d7d1979d72');
CREATE TABLE meta (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
INSERT INTO "meta" VALUES('sim_now','1793401200');
INSERT INTO "meta" VALUES('homelab_last_pull','1793401200');
INSERT INTO "meta" VALUES('dms_alerted_for','1792882800');
INSERT INTO "meta" VALUES('dms_last_fired_at','1792904400');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('d1_migrations',1);
INSERT INTO "sqlite_sequence" VALUES('commits',49);
COMMIT;
-- state/v3/d1/miniflare-D1DatabaseObject/metadata.sqlite
BEGIN TRANSACTION;
CREATE TABLE _cf_ALARM (
      actor_id TEXT PRIMARY KEY,
      scheduled_time INTEGER,
      actor_name TEXT
    ) WITHOUT ROWID;
COMMIT;