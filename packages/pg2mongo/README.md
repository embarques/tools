
# pg2mongo

Small, focused tool to transfer data from **Postgres** to **MongoDB** in a
clean, incremental, and developer-friendly way.

## Supported entities

| Command | Postgres source | Mongo collection |
|---------|----------------|------------------|
| `transfer all` | All entities (see below) | All collections |
| `transfer branch` | `branch` | `branches` |
| `transfer customer` | `vwcustomer_api` | `customers` |
| `transfer container` | `container` | `containers` |
| `transfer delivery` | `vwdelivery_api` | `deliveries` |
| `transfer employee` | `employee` | `employees` |
| `transfer invoice` | `vwinvoice_api` + `vwinvoice_details_api` | `invoices`, `invoice_details` |
| `transfer pickup` | `vwpickup_api` | `pickups` |
| `transfer user` | `auth_user` + `user_profile` | `users` |

## Collection naming

Multi-word MongoDB collection names use **snake_case**. Constants live in `pg2mongo/collections.py`:

| Collection / field | Name |
|------------|------|
| Invoice line items (collection) | `invoice_details` |
| Invoice detail refs (field on invoice doc) | `invoice_details` |
| Activity logs | `activity_logs` |
| Income statements | `income_statements` |

Single-word collections (`invoices`, `customers`, `pickups`, etc.) stay lowercase without underscores.

---

## Features

- Reads config from **`db.toml`** (single config file)
- Supports **MongoDB replica sets** (`mongodb://`) and **MongoDB Atlas** (`mongodb+srv://`)
- Initializes Mongo indexes and counter sequences for a new database
- Transfers data using **date windows** (or year ranges for deliveries)
- Uses `updatedAt` in Mongo to **resume where it left off**
- `test-connection` command to verify Postgres and Mongo connectivity

---

## 1. Setup

```bash
git clone <your-repo-url> pg2mongo
cd pg2mongo

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1

pip install -e .
```

Verify installation:

```bash
pg2mongo --version
```

---

## 2. Configuration

pg2mongo uses **one config file**: `db.toml`. There is no `.env` support.

```bash
cp db.example.toml db.toml
# edit db.toml with your Postgres and Mongo credentials
```

| File | Purpose |
|------|---------|
| `db.example.toml` | Sample config → copy to `db.toml` |
| `db.toml` | Your real credentials (git-ignored) |

### How it is loaded

1. If you pass `-c /path/to/db.toml`, that file is used.
2. Otherwise pg2mongo auto-discovers `db.toml` in the current directory or the pg2mongo project root.

```bash
# Auto-discover db.toml (most common)
pg2mongo test-connection

# Explicit path (useful when running from another directory)
pg2mongo -c packages/pg2mongo/db.toml test-connection
```

---

### Option A — Replica set (default in example file)

Use a base URI **without** credentials. Set `username` and `password` separately — they are injected automatically.

```toml
[postgres]
server = "embserver.embarques.net"
port = 5432
db = "carmencargodb"
username = "your_pg_user"
password = "your_pg_password"
schema_name = "public"

[mongo]
uri = "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/?replicaSet=rs0&connectTimeoutMS=10000&authSource=admin&authMechanism=SCRAM-SHA-256"
db = "emsysdb"
username = "your_mongo_user"
password = "your_mongo_password"

[transfer]
upsert_key = "oldID"
```

---

### Option B — MongoDB Atlas

Put the **full connection string with embedded credentials** in the URI.
Leave `username` and `password` empty.

```toml
[mongo]
uri = "mongodb+srv://your_user:your_password@cluster0.example.mongodb.net/?retryWrites=true&w=majority&authSource=admin"
db = "emsysdb"
username = ""
password = ""
```

> **Tip:** If you copy a URI from Studio 3T, pg2mongo automatically strips unsupported `3t.*` query parameters.

> **Tip:** If the URI already contains `user:password@`, separate `username` / `password` fields are ignored.

---

## 3. Test connections (do this first)

Always verify connectivity before running transfers.

```bash
pg2mongo test-connection
```

Verbose output:

```bash
pg2mongo -v test-connection
```

### Expected output

```
🔌 Testing database connections…

Postgres:
  ✓ Connected successfully
  • Host: embserver.embarques.net:5432
  • Database: carmencargodb
  • Schema: public
  • Ping Result: 1

MongoDB:
  ✓ Connected successfully
  • Database: emsysdb

Done.
```

If either side fails, the error is printed under that section (bad credentials, timeout, unreachable host, etc.).

---

## 4. Initialize a new Mongo database

Before the first transfer into a new Mongo database, create indexes and seed counter sequences.

### Standard init (idempotent)

```bash
pg2mongo init-indexes
```

### Full init with drop/recreate indexes

```bash
pg2mongo init-db --drop-existing
pg2mongo init-db --dry-run    # preview only
```

Both commands:

1. Create required unique indexes
2. Seed the `counters` collection (`pickup_id`, `delivery_id`, etc.)
3. Ensure required collections exist

> Pickups require the `pickup_id` counter. Run `init-indexes` or `init-db` before `transfer pickup`.

---

## 5. Transfer commands

All transfers follow this pattern:

```bash
pg2mongo [-c db.toml] [-v] transfer <entity> [options]
```

If `db.toml` is in the current directory (or pg2mongo project root), `-c` is optional.

### Entities

`all` · `branch` · `customer` · `container` · `delivery` · `employee` · `invoice` · `pickup` · `user`

### Transfer all

Run every entity in dependency order:

**branch → employee → user → customer → container → invoice → pickup → delivery**

#### Examples

```bash
# Full backfill from a start date through today
pg2mongo transfer all --start-date 2022-01-01

# Start date only → end defaults to today
pg2mongo transfer all --start-date 2026-01-01

# Explicit date range
pg2mongo transfer all --start-date 2026-01-01 --end-date 2026-05-30

# Incremental (no dates → date-based entities resume from Mongo updatedAt)
pg2mongo transfer all

# Dry-run first (recommended before a large backfill)
pg2mongo transfer all --start-date 2026-01-01 --limit 50 --dry-run

# Verbose output (per-record progress; useful for invoice)
pg2mongo transfer all --start-date 2026-01-01 -v

# Global verbose also works (must appear before subcommands)
pg2mongo -v transfer all --start-date 2026-01-01

# From another directory — pass config explicitly
pg2mongo -c packages/pg2mongo/db.toml transfer all --start-date 2026-01-01
```

#### First-time full import

```bash
source .venv/bin/activate
pg2mongo test-connection
pg2mongo init-indexes
pg2mongo transfer all --start-date 2022-01-01 -v
```

#### Behavior by entity

| Entity type | Behavior in `transfer all` |
|-------------|---------------------------|
| branch, employee, user | Full sync (no date filter) |
| customer, container, invoice, pickup | Uses `--start-date` / `--end-date` (same as individual commands) |
| delivery | Maps date range to `--start-year` / `--end-year` |

If one entity fails, the rest still run. A summary is printed at the end. With `-v`, the command stops on the first error to aid debugging. Each entity header shows step position (e.g. `Transfer: invoice (6/8)`); invoice shows a total count and progress bar.

### Common options

| Option | Applies to | Meaning |
|--------|-----------|---------|
| `--start-date` | customer, invoice, pickup, container, **all** | Start date (`YYYY-MM-DD` or `MM-DD-YYYY`) |
| `--end-date` | customer, invoice, pickup, container, **all** | End date; defaults to today 23:59:59 UTC |
| `--start-year` | delivery | Start year (default: 2022) |
| `--end-year` | delivery | End year (default: current year) |
| `--dry-run` | all | Preview actions without writing to Mongo |
| `--limit N` | all | Limit records **per entity** (`0` = no limit) |
| `-v / --verbose` | **all**, global | Per-record progress and debug output |

---

## 6. Date window logic

For entities that use `--start-date` (customer, invoice, pickup, container):

1. If `--start-date` is provided → use it
2. Else → read the latest `updatedAt` from the Mongo collection
3. Else → default to **2022-01-01**

If `--end-date` is omitted, the window ends at **today 23:59:59 UTC**.

This makes transfers **incremental** — ideal for daily automation.

Deliveries use `--start-year` / `--end-year` instead of date windows.

---

## 7. Transfer examples

### Transfer all

See [section 5](#transfer-all) for the full reference. Quick examples:

```bash
# Backfill everything from 2022
pg2mongo transfer all --start-date 2022-01-01

# Daily incremental sync
pg2mongo transfer all

# Safe preview before a large run
pg2mongo transfer all --start-date 2026-01-01 --limit 50 --dry-run -v
```

### Customers

```bash
# Initial backfill
pg2mongo -c db.toml transfer customer --start-date 2022-01-01

# Dry-run first
pg2mongo -c db.toml transfer customer --start-date 2022-01-01 --limit 50 --dry-run

# Incremental (resume from last updatedAt)
pg2mongo -c db.toml transfer customer
```

### Invoices

Invoices are synced inside a **MongoDB transaction** per invoice (header + line items + barcodes).

Before processing, a `COUNT` query reports how many invoices match the date window (e.g. `Invoices: 150 of 7,280 record(s) to process`). During the run you get a progress bar with position, percent, and ETA; with `-v`, each line is prefixed with `[current/total] (pct%)`.

```bash
pg2mongo -c db.toml transfer invoice --start-date 2022-01-01
pg2mongo -c db.toml transfer invoice --start-date 2022-01-01 --limit 10 --dry-run
pg2mongo -c db.toml transfer invoice --start-date 2026-01-01 -v
```

### Pickups

Pickups assign a numeric `_id` from the `pickup_id` counter.

```bash
pg2mongo -c db.toml transfer pickup --start-date 2022-01-01
pg2mongo -c db.toml transfer pickup --start-date 2022-01-01 --limit 20 --dry-run
pg2mongo -c db.toml transfer pickup
```

### Containers

```bash
pg2mongo -c db.toml transfer container --start-date 2022-01-01
pg2mongo -c db.toml transfer container --start-date 2022-01-01 --limit 20 --dry-run
pg2mongo -c db.toml transfer container
```

### Employees, users, branches (full sync)

```bash
pg2mongo -c db.toml transfer employee
pg2mongo -c db.toml transfer employee --limit 50 --dry-run

pg2mongo -c db.toml transfer user
pg2mongo -c db.toml transfer user --limit 25 --dry-run

pg2mongo -c db.toml transfer branch
pg2mongo -c db.toml transfer branch --limit 5 --dry-run
```

### Deliveries (year range)

```bash
pg2mongo transfer delivery
pg2mongo transfer delivery --start-year 2023 --end-year 2024
pg2mongo transfer delivery --start-year 2023 --end-year 2024 --limit 50 --dry-run
```

---

## 8. Global CLI options

| Flag | Description |
|------|-------------|
| `-c / --config` | Path to `db.toml` (optional if auto-discovered) |
| `-v / --verbose` | Additional debug output |
| `--version` | Show version |
| `-h / --help` | Show help |

```bash
pg2mongo --help
pg2mongo transfer --help
pg2mongo transfer all --help
pg2mongo transfer invoice --help
pg2mongo --version
```

---

## 9. Typical daily workflow

```bash
source .venv/bin/activate

# 1. Verify connections
pg2mongo test-connection

# 2. One-shot incremental sync of everything
pg2mongo transfer all

# Or with verbose output
pg2mongo transfer all -v

# Or run entities individually:
pg2mongo transfer branch
pg2mongo transfer employee
pg2mongo transfer user
pg2mongo transfer customer
pg2mongo transfer container
pg2mongo transfer invoice
pg2mongo transfer pickup
pg2mongo transfer delivery
```

For a scheduled backfill of a specific date range:

```bash
pg2mongo transfer all --start-date 2026-01-01 --end-date 2026-05-30
```

---

## 10. Project structure

```
pg2mongo/
  pyproject.toml
  README.md
  db.example.toml

  pg2mongo/
    cli/main.py           # CLI entry point
    config.py             # Settings (TOML + env)
    mongo_uri.py          # URI builder (replica set + Atlas)
    clients.py            # Postgres / Mongo connections
    transfer/all.py         # transfer all command
    transfer/               # One module per entity
    builders/             # Row → Mongo document mappers
    actions/              # init-indexes, test-connection
    init_db.py            # init-db command
    admin.py              # Index + counter helpers
    utils.py              # Shared helpers (dates, sequences)
```

---

## 11. Troubleshooting

### Mongo authentication failed

- **Replica set:** check `username` / `password` in config match your Mongo user
- **Atlas:** ensure credentials are correct in the URI (or in separate fields if URI has no creds)
- Ensure the user has `readWrite` on the target database

### Mongo connection timeout / host not found

- **Replica set:** verify hostnames resolve from your machine (e.g. `mongo1`, `mongo2`)
- **Atlas:** use a `mongodb+srv://` URI; check IP allowlist in Atlas Network Access

### Missing counter: `pickup_id`

```bash
pg2mongo init-indexes
```

### `datetime.date has no tzinfo`

Handled by `utils.to_utc()`. If you see this, a field mapping likely needs normalization.

---

## 12. Version

```bash
pg2mongo --version
```

Version is defined in `pg2mongo/version.py`.
