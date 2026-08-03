# Property Maintenance AI Triage PoC

This proof of concept uses synthetic data to demonstrate:

- maintenance-email intake
- tenant and lease matching
- structured responsibility assessment
- duplicate prevention using an idempotency key
- manual review for low-confidence or emergency cases
- workflow logging and basic tests

It does not connect to a real Rent Manager account because client-approved API credentials are required.

## Run

```bash
python app.py
```

Open `http://localhost:8000`.

## Test

```bash
python -m unittest discover -s tests -v
```

## Production next steps

Replace the mock connector with Rent Manager and Microsoft Graph APIs, use Anthropic's official SDK for schema-constrained classification, move state to Supabase/PostgreSQL, and add authentication, monitoring, retries, alerts, and a dead-letter queue.
