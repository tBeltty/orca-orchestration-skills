# Example: a reviewed contract

A contract for a fictional CSV contact import in app-a, in the shape `worker-brief-builder` asks
for. It is short on purpose: each section answers one question a worker would otherwise guess.

## Components

- **Upload endpoint**: accepts a CSV file and creates an import record.
- **Import job**: a background job that reads the file and writes contacts in batches.
- **Status view**: shows the user the progress and the rows that failed.

## Identity

- Each import gets an id at upload. Two uploads of the same file are two imports, so the file's
  hash does not identify an import.
- A row is identified by `(import_id, row_number)`. A contact is identified by its normalized email
  within an account.

## Ownership

| Field | Written by | Read by |
|---|---|---|
| Import record (`status`, `total_rows`) | Upload endpoint creates it; import job updates it | Status view |
| `processed_rows`, `failed_rows` | Import job only | Status view |
| Contacts | Import job only | The rest of the app |
| Row errors | Import job only | Status view, error download |

## Concurrency

- Two job runners may pick the same import after a retry. A runner starts only after an atomic
  claim: `UPDATE imports SET status = 'running', claimed_by = $1, claimed_at = now() WHERE id = $2
  AND (status = 'queued' OR (status = 'running' AND claimed_at < now() - interval '10 minutes'))`.
  Zero updated rows means another runner owns the import.
- Two imports in one account may write the same contact. Writes are an upsert on
  `(account_id, email)`; a later import overwrites a field only with a non-empty value.

## Failure modes

| Failure | Behavior |
|---|---|
| The runner crashes mid-file | The claim expires after 10 minutes. The next runner resumes from `processed_rows`, which is committed in the same transaction as each batch of 500 rows. |
| A row is malformed | The row goes to the row errors with its number and reason; the import continues. |
| More than 20% of the rows fail | The import stops as `failed`. Contacts already written stay, and the user sees the error list. |
| The file is not valid UTF-8 or not CSV | The upload endpoint answers 422 before creating any record. |

## Interfaces

- `POST /imports` (multipart, field `file`): 201 `{id}`, 413 over 10 MB, 422 for an invalid file.
- `GET /imports/:id`: `{status, total_rows, processed_rows, failed_rows}`, where `status` is
  `queued`, `running`, `done` or `failed`.
- `GET /imports/:id/errors.csv`: columns `row,reason`.

## Out of scope

- Deleting contacts that are missing from the file.
- Formats other than CSV.
