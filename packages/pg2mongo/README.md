
# pg2mongo

Small, focused tool to transfer data from **Postgres** to **MongoDB** in a
clean, incremental, and developer-friendly way.

Current supported entities:

- `customers`  → Mongo `customers` collection  
- `invoices`   → Mongo `invoices` + related collections  
- `pickups`    → Mongo `pickups` collection  

The tool:

- Reads config from a **db.toml** file or environment variables  
- Initializes Mongo indexes + counters for a new database  
- Transfers data using **date windows**  
- Uses `updatedAt` in Mongo to **resume where it left off**  
- Provides a `test-connection` command to verify DB connectivity  


---

## 📦 1. Setup

### Clone & Virtual Environment

```bash
# 1. Clone the repo
git clone <your-repo-url> pg2mongo
cd pg2mongo

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
# macOS / Linux:
source .venv/bin/activate

# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# 4. Install package
pip install -e .
```

Check installation:

```bash
pg2mongo --version
```

---

## ⚙️ 2. Configuration

You can configure pg2mongo using:

1. A **TOML config file** → recommended  
2. Environment variables → fallback  

### Example `db.toml`

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
username = "dbadmin"
password = "your_mongo_password"
```

> 🔒 Add `db.toml` to `.gitignore` — keep credentials out of your repo.

### Optional: Environment Variables

```bash
# Postgres
export POSTGRES_SERVER="embserver.embarques.net"
export POSTGRES_PORT="5432"
export POSTGRES_DB="carmencargodb"
export POSTGRES_USERNAME="your_pg_user"
export POSTGRES_PASSWORD="your_pg_password"
export POSTGRES_SCHEMA_NAME="public"

# Mongo
export MONGO_URI="mongodb://mongo1:27017,..."
export MONGO_DB="emsysdb"
export MONGO_USERNAME="dbadmin"
export MONGO_PASSWORD="your_mongo_password"
```

If `--config` is provided, **env vars are ignored**.

---

## 🧪 3. Test Connections (recommended first step)

```bash
pg2mongo -c db.toml test-connection
```

Using env vars only:

```bash
pg2mongo test-connection
```

Expected output:

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

---

## 🏗️ 4. Initialize a New Mongo Database

Before transferring data into a new Mongo instance:

1. Create required indexes  
2. Seed the `counters` collection  
3. Touch required collections  

Run:

```bash
pg2mongo -c db.toml init-indexes
```

You will see indexes created and counters inserted.

---

## 🔁 5. Transfer Commands

All transfer commands use this pattern:

```bash
pg2mongo transfer <entity> [options]
```

Entities:

- `customer`
- `invoice`
- `pickup`

### Common Options

| Option          | Meaning                                           |
|----------------|---------------------------------------------------|
| `--start-date` | YYYY-MM-DD or MM-DD-YYYY                          |
| `--end-date`   | Optional, defaults to today @ 23:59:59 UTC        |
| `--dry-run`    | No writes; prints actions                         |
| `--limit N`    | Only process N records                            |


---

## 🗓️ 6. Date Window Logic (Very Important)

If you **do not** provide `--start-date`:

1. The tool checks Mongo collection for the **last `updatedAt` value**
2. Uses that as the new start date
3. If the Mongo collection is empty, it starts from:

```
2022-01-01
```

If you do not provide `--end-date`, it uses:

```
today 23:59:59.999999 UTC
```

This makes the transfers **incremental** — perfect for daily automation.

---

## 👤 7. Transfer Customers

### Initial import

```bash
pg2mongo -c db.toml transfer customer --start-date 2022-01-01
```

### Dry-run first

```bash
pg2mongo -c db.toml transfer customer --start-date 2022-01-01 --limit 50 --dry-run
```

### Incremental run

```bash
pg2mongo -c db.toml transfer customer
```

---

## 📦 8. Transfer Invoices

### Full import from 2022

```bash
pg2mongo -c db.toml transfer invoice --start-date 2022-01-01
```

### Dry-run with preview

```bash
pg2mongo -c db.toml transfer invoice --start-date 2022-01-01 --limit 10 --dry-run
```

### Incremental (resume from last updatedAt)

```bash
pg2mongo -c db.toml transfer invoice
```

---

## 🚚 9. Transfer Pickups

Pickups use a Mongo numeric sequence (`pickup_id`).
```bash
### Full import from 2022
pg2mongo -c db.toml transfer pickup --start-date 2022-01-01

### Dry-run
pg2mongo -c db.toml transfer pickup --start-date 2022-01-01 --limit 20 --dry-run

### Incremental
pg2mongo -c db.toml transfer pickup
```

## 🚚 9. Transfer Containers

```bash
# Backfill containers from 2022
pg2mongo -c db.toml transfer container --start-date 2022-01-01

# Dry-run with limit
pg2mongo -c db.toml transfer container --start-date 2022-01-01 --limit 20 --dry-run

# Incremental: no dates → uses last updatedAt in Mongo
pg2mongo -c db.toml transfer container
```


---

## 🔧 10. Global Options

```bash
pg2mongo -c db.toml -v transfer customer
```

| Flag            | Description                       |
|----------------|-----------------------------------|
| `-c / --config` | Path to `db.toml`                 |
| `-v / --verbose` | Additional debug output          |
| `--version`    | Show version                      |

Examples:

```bash
pg2mongo version
pg2mongo --version
```

---

## 🔄 11. Typical Daily Workflow

1. Activate virtualenv  
2. Ensure config is correct  
3. Run:

```bash
pg2mongo -c db.toml transfer customer
pg2mongo -c db.toml transfer invoice
pg2mongo -c db.toml transfer pickup
```

The tool resumes exactly where you left off using `updatedAt`.

---

## 📚 12. File Structure Overview

```
pg2mongo/
  __init__.py
  version.py
  config.py
  clients.py
  dates.py
  utils.py

  cli/
    main.py

  transfer/
    common.py
    customer.py
    invoice.py
    pickup.py

  builders/
    customer_build.py
    invoice_build.py
    pickup_build.py

  actions/
    init_indexes.py
    test_connection.py
```

Everything is modular, clean, and predictable.

---

## 🆘 13. Troubleshooting (Common Issues)

### ❌ Mongo authentication failed

- Check username/password in `db.toml`
- Ensure the user has at least `readWrite` on the target DB:

```js
use emsysdb
db.grantRolesToUser(
  "dbadmin",
  [ { role: "readWrite", db: "emsysdb" } ]
)
```

### ❌ Missing counter: "pickup_id"

Run:

```bash
pg2mongo -c db.toml init-indexes
```

### ❌ datetime.date has no tzinfo

Already handled in `utils.to_utc()`  
If you see this error, it means a mis-mapped field needs to be normalized.

---

## ✔️ 14. Version

Use:

```bash
pg2mongo --version
```

Version is stored in:

```
pg2mongo/version.py
```

---

Enjoy a clean, professional Postgres → MongoDB pipeline!













## Generate ssh keys for github

```bash
# open a terminal in your MAC, name your key ~/.ssh/id_mountzion_soft.pub
ssh-keygen -t ed25519 -C "mountzion.soft@gmail.com"
```

- copy ssh keys to ~/.ssh/ folder

- Open your ~/.ssh/config file, then modify the file to contain the following lines

```bash

Host github-mountziontec
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_mountzion_soft.pub
```

```bash
# add ssh key to ssh-agent (must add key to ssh-agent so is use when connecting to github)
ssh-add ~/.ssh/id_mountzion_soft

# ssh ssh key with github repo
ssh -T git@github.com

# copy to clipboard
pbcopy < ~/.ssh/id_mountzion_soft.pub

- Go to github, under the embarques settings, add new ssh keys. Give it a name and paste the content from pbcopy
```


## Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env


# run application
```bash

pip install -e .
pg2mongo  -c db.toml -v transfer customer --dry-run
pg2mongo -c db.toml -v init-db --drop-existing
pg2mongo -c db.toml -v transfer customer --dry-run
pg2mongo -c db.toml -v transfer invoice --start-date 2025-08-01 --end-date 08-31-2025

# insert invoice with date and limit of records
pg2mongo -v transfer invoice --start-date 2025-01-01 --end-date 2025-10-31 --dry-run --limit 10

```

## Configuration files

- **.env.example** – sample environment variables.  
  Copy to **.env** and edit. The real `.env` is **ignored** by git.

- **db.example.toml** – sample TOML config.  
  Copy to **db.toml** and edit. The real `db.toml` is **ignored** by git.

Examples:
```bash
cp .env.example .env
cp db.example.toml db.toml


