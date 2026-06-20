# Quick Start Guide

Get your distributed job queue running in 5 minutes!

## Step 1: Setup Database

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate
```

## Step 2: Start the Django Server

```bash
python manage.py runserver
```

## Step 3: Start Workers (in separate terminals)

```bash
# Terminal 1
python manage.py run_worker --name worker-1

# Terminal 2
python manage.py run_worker --name worker-2

# Terminal 3
python manage.py run_worker --name worker-3
```

## Step 4: Create Jobs

### Option A: Via API
```bash
curl -X POST http://localhost:8000/job/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "send_email",
    "payload": {
      "recipient": "user@example.com",
      "subject": "Hello World"
    }
  }'
```

### Option B: Via Python Script
```bash
python example_usage.py
```

### Option C: Via Django Shell
```bash
python manage.py shell
```

```python
from job.services import create_job
from job.models.job import Job

# Create a job
job, created = create_job(
    type=Job.JobType.SEND_EMAIL,
    payload={"recipient": "test@example.com"}
)

print(f"Job #{job.id} created!")
```

## Step 5: Watch Workers Process Jobs

Workers will automatically pick up and process jobs from the queue. You'll see output like:

```
Worker 'worker-1' started successfully
Polling for jobs every 5 seconds...

[10:30:15] Processed job #1 (send_email) - Status: completed
[10:30:20] No jobs available. Waiting...
[10:30:25] Processed job #2 (generate_report) - Status: completed
```

## Verifying Everything Works

### Check Job Status
```python
from job.models.job import Job

# Count jobs by status
pending = Job.objects.filter(status=Job.Status.PENDING).count()
completed = Job.objects.filter(status=Job.Status.COMPLETED).count()
failed = Job.objects.filter(status=Job.Status.FAILED).count()

print(f"Pending: {pending}, Completed: {completed}, Failed: {failed}")
```

### Check Worker Health
```python
from worker.models.worker import Worker

workers = Worker.objects.filter(status=Worker.Status.ONLINE)
for w in workers:
    print(f"{w.name}: {'alive' if w.is_alive else 'dead'}")
```

## Common Issues

### "No module named 'environ'"
```bash
pip install django-environ
```

### "Table doesn't exist"
```bash
python manage.py migrate
```

### Workers not processing jobs
- Make sure workers are running (`python manage.py run_worker`)
- Check worker status in database
- Verify jobs are in PENDING status

### Jobs stuck in CLAIMED status
- This happens if a worker crashes
- Jobs will auto-recover after 5 minutes
- Or manually reset: `Job.objects.filter(status='claimed').update(status='pending', worker=None)`

## Next Steps

1. Read [README.md](README.md) for detailed usage
2. Read [RACE_CONDITION_HANDLING.md](RACE_CONDITION_HANDLING.md) to understand the implementation
3. Run tests: `python manage.py test job.tests.test_race_conditions`
4. Customize job types in `job/models/job.py` and `job/services/execute_job.py`

## Production Deployment

For production:
1. Use PostgreSQL instead of SQLite
2. Use a process manager (systemd, supervisord, Docker)
3. Add monitoring and alerting
4. Set up proper logging
5. Add authentication to API endpoints

Example systemd service for worker:
```ini
[Unit]
Description=Job Queue Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/python manage.py run_worker --name worker-1
Restart=always

[Install]
WantedBy=multi-user.target
```

Happy job processing! 🚀
