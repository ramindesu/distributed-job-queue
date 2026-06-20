# Race Condition Handling in Distributed Job Queue

This document explains how race conditions are handled in this distributed job queue system.

## Overview

When building a distributed job queue (like Celery), race conditions can occur when:
- Multiple workers try to claim the same job simultaneously
- Concurrent job creation requests with the same idempotency key
- State transitions happening concurrently on the same job
- Jobs being retried while still being processed

## Race Condition Solutions Implemented

### 1. Job Claiming (`claim_job.py`)

**Problem:** Multiple workers could claim the same job.

**Solution:**
```python
with transaction.atomic():
    job = (
        Job.objects.select_for_update(skip_locked=True)
        .filter(status=Job.Status.PENDING)
        .order_by("created_at")
        .first()
    )
```

**Key Mechanisms:**
- `select_for_update(skip_locked=True)`: Acquires a row-level lock but skips locked rows
- `transaction.atomic()`: Ensures atomicity
- Workers that try to lock an already-locked job will skip it and move to the next one
- No worker ever waits; they immediately get the next available job

### 2. Idempotent Job Creation (`create_job.py`)

**Problem:** Two concurrent requests with the same idempotency key could create duplicate jobs.

**Solution:**
```python
try:
    existing_job = Job.objects.get(idempotency_key=idempotency_key)
    return existing_job, False
except Job.DoesNotExist:
    try:
        with transaction.atomic():
            job = Job.objects.create(...)
            return job, True
    except IntegrityError:
        # Another process created it between our check and create
        existing_job = Job.objects.get(idempotency_key=idempotency_key)
        return existing_job, False
```

**Key Mechanisms:**
- Try to get existing job first (fast path)
- If not found, create in atomic transaction
- Handle `IntegrityError` (race condition occurred) by fetching the job that was created
- Requires unique constraint on `idempotency_key` in database
- Pattern: "Optimistic creation with fallback"

### 3. State Transitions (`start_job.py`, `complete_job.py`, `fail_job.py`)

**Problem:** Concurrent state transitions could violate the job state machine.

**Solution:**
```python
with transaction.atomic():
    job = Job.objects.select_for_update().get(pk=job.pk)
    
    if job.status != expected_status:
        raise ValueError(f"Invalid state transition")
    
    job.status = new_status
    job.save(update_fields=[...])
```

**Key Mechanisms:**
- `select_for_update()`: Locks the row for exclusive access
- Re-fetch the job inside the transaction to get latest state
- Validate current state before transition
- Only one thread can hold the lock at a time
- Other threads will wait until the lock is released

### 4. Retry Logic with Concurrency (`fail_job.py`)

**Problem:** Multiple failure detections could incorrectly increment retry count.

**Solution:**
```python
with transaction.atomic():
    job = Job.objects.select_for_update().get(pk=job.pk)
    
    job.retry_count += 1
    
    if job.retry_count < job.max_retries:
        # Reset to PENDING for retry
        job.status = Job.Status.PENDING
        job.worker = None
        # ...
    else:
        # Mark as permanently FAILED
        job.status = Job.Status.FAILED
```

**Key Mechanisms:**
- Lock the row before incrementing retry count
- Atomic read-modify-write operation
- Prevents lost updates

### 5. Expired Job Reclaiming (`process_next_job.py`)

**Problem:** If a worker crashes, its claimed jobs should be released.

**Solution:**
```python
expired_jobs = Job.objects.select_for_update(skip_locked=True).filter(
    status=Job.Status.CLAIMED,
    claimed_at__lt=timezone.now() - timezone.timedelta(minutes=5),
)

for job in expired_jobs:
    job.status = Job.Status.PENDING
    job.worker = None
    job.claimed_at = None
    job.save(update_fields=[...])
```

**Key Mechanisms:**
- Query for jobs claimed more than 5 minutes ago
- Use `skip_locked=True` so multiple workers can reclaim different expired jobs
- Reset job to PENDING status

## Database Requirements

### Required Indexes
```sql
CREATE INDEX idx_job_status ON job (status);
CREATE INDEX idx_job_created_at ON job (created_at);
CREATE INDEX idx_job_type ON job (type);
CREATE UNIQUE INDEX idx_job_idempotency_key ON job (idempotency_key) WHERE idempotency_key IS NOT NULL;
```

### Required Constraints
```sql
ALTER TABLE job ADD CONSTRAINT unique_idempotency_key UNIQUE (idempotency_key);
```

## Locking Strategies

### `select_for_update()` vs `select_for_update(skip_locked=True)`

**Use `select_for_update()` when:**
- State transitions on a specific job
- You MUST process this exact job
- Example: `start_job()`, `complete_job()`

**Use `select_for_update(skip_locked=True)` when:**
- Claiming jobs from a queue
- Any job will do, just skip busy ones
- Example: `claim_job()`, reclaiming expired jobs

## Testing Race Conditions

Run the test suite:
```bash
python manage.py test job.tests.test_race_conditions
```

Key test scenarios:
1. **Concurrent job creation** - 10 threads creating with same idempotency key
2. **Concurrent job claiming** - 10 workers claiming from 5 jobs
3. **Concurrent state transitions** - Starting and completing simultaneously
4. **Concurrent failures** - Multiple failure detections
5. **Expired job reclaiming** - Stale jobs being released

## Common Pitfalls to Avoid

### ❌ DON'T: Check-then-update pattern without locking
```python
# BAD - Race condition!
job = Job.objects.get(pk=job_id)
if job.status == "PENDING":
    job.status = "CLAIMED"  # Another worker could have claimed it!
    job.save()
```

### ✅ DO: Atomic check-and-update with locking
```python
# GOOD - No race condition
with transaction.atomic():
    job = Job.objects.select_for_update().get(pk=job_id)
    if job.status == "PENDING":
        job.status = "CLAIMED"
        job.save()
```

### ❌ DON'T: Use `get_or_create()` for critical idempotency
```python
# RISKY - Can still have issues under high concurrency
job, created = Job.objects.get_or_create(
    idempotency_key=key,
    defaults={...}
)
```

### ✅ DO: Explicit error handling for race conditions
```python
# GOOD - Handles race condition explicitly
try:
    job = Job.objects.create(idempotency_key=key, ...)
    return job, True
except IntegrityError:
    job = Job.objects.get(idempotency_key=key)
    return job, False
```

## Performance Considerations

1. **Lock Duration**: Keep transactions short to minimize lock contention
2. **Skip Locked**: Use when possible to avoid workers waiting
3. **Index Coverage**: Ensure queries use indexes to find jobs quickly
4. **Connection Pooling**: Use database connection pooling for high concurrency

## Database Compatibility

This implementation uses:
- `SELECT FOR UPDATE` (PostgreSQL, MySQL 8.0+, SQLite 3.35+)
- `SKIP LOCKED` (PostgreSQL 9.5+, MySQL 8.0+, SQLite 3.38+)

**SQLite Note:** SQLite's `SKIP LOCKED` support is limited. For production, use PostgreSQL or MySQL.

## Monitoring and Observability

Key metrics to monitor:
- Jobs claimed per second
- Average time to claim a job
- Number of retried jobs
- Number of expired/reclaimed jobs
- Lock wait times (if not using skip_locked)

## Comparison with Celery

| Feature | This Implementation | Celery |
|---------|-------------------|--------|
| Backend | Database (Django ORM) | Redis/RabbitMQ/Database |
| Race Condition Handling | Row-level locking | Atomic operations in broker |
| Idempotency | Database constraint | Task ID deduplication |
| Retry Logic | Database-backed | Broker + result backend |
| Scalability | Good (with proper DB) | Excellent (with Redis/RabbitMQ) |

## Future Improvements

1. **Priority Queues**: Add priority field and order by it
2. **Dead Letter Queue**: Separate table for permanently failed jobs
3. **Job Dependencies**: Support job chains and dependencies
4. **Rate Limiting**: Limit job execution rate per type
5. **Job Cancellation**: Support for cancelling running jobs
6. **Metrics Dashboard**: Web UI for monitoring job queue health
