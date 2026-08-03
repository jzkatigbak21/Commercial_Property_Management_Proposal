# AI Automation Platform for Commercial Property Management

## Technical Proposal and Application Exercise

This document presents a proposed production architecture for a commercial property management automation platform that integrates Rent Manager, Microsoft 365, Supabase/PostgreSQL, Claude, and supporting automation services.

The proposed system is designed to handle three operational workflows:

1. Triage inbound maintenance emails and recommend tenant or landlord responsibility.
2. Detect month-over-month utility cost anomalies.
3. Generate organized audit invoice packages on demand.

The design prioritizes reliability, human review, auditability, secure data handling, and maintainable production workflows.

---

## Executive Summary

The main challenge is not simply connecting Rent Manager to Microsoft 365. The system must process operational and financial data reliably, explain how it reached each conclusion, recover from failures, and keep property managers in control of decisions that may affect tenants, landlords, and payments.

The proposed event-driven, human-in-the-loop platform would use:

- **Microsoft Graph** for email and document intake
- **Rent Manager** as the property-management system of record
- **Supabase/PostgreSQL** as the normalized operational datastore
- **Claude** for tightly controlled classification and explanation
- **Python or TypeScript workers** for deterministic business logic
- **Vercel and Next.js** for review, approvals, and monitoring
- **n8n** for lightweight notifications, approvals, scheduled reports, and operational workflows

---

## 1. Technical Feasibility and Constraints

### Maintenance Email Triage

The workflow would:

1. Receive an event when a maintenance email arrives.
2. Store the event before processing.
3. Retrieve the full email and attachments.
4. Match the sender, address, unit, tenant, and lease against Rent Manager data.
5. Retrieve relevant lease clauses and property policies.
6. Classify the issue and recommend tenant or landlord responsibility.
7. Route uncertain, urgent, or conflicting cases to human review.
8. Create a draft response or work-order action after approval.

The AI should not make the final responsibility decision independently during the pilot. It should provide a recommendation supported by evidence, confidence, and missing information.

### Utility Anomaly Detection

Utility anomaly detection is feasible when bills can be consistently associated with:

- Properties
- Utility accounts
- Meters
- Billing periods
- Expense categories

Potential data-quality issues include:

- Duplicate invoices
- Estimated readings
- Partial billing periods
- Rate increases
- Vacant units
- Seasonal usage

Deterministic calculations should generate anomaly alerts. The LLM may summarize the anomaly, but it should not perform the core numerical judgment.

### Audit Invoice Packages

The system can generate an audit package for a selected property, vendor, account, or date range.

The workflow would:

1. Retrieve invoices and supporting files.
2. Detect missing, duplicate, or mismatched records.
3. Generate a numbered manifest.
4. Organize files using a consistent naming convention.
5. Produce a ZIP file or combined PDF.
6. Store the output with a checksum and audit log.
7. Display incomplete or excluded items separately.

---

## 2. Proposed Architecture

```text
Rent Manager API ───────┐
                        │
Microsoft Graph ────────┼──> Integration Services
                        │        │
Manual Review Portal ───┘        ▼
                           Supabase/PostgreSQL
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             Email Triage    Utility Analysis   Audit Packaging
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
                        Human Review and Approval
                                   │
                                   ▼
                    Approved Notifications / Write-backs
```

### Integration Layer

A Microsoft Graph webhook would validate incoming notifications, persist or queue the event, and acknowledge it quickly.

A separate worker would retrieve:

- Email content
- Attachments
- Tenant and property information
- Lease details
- Related records

A scheduled delta-sync process would reconcile missed or delayed events.

For Rent Manager, the implementation would begin with controlled synchronization of required entities into Supabase. Incremental updates would use the best method supported by the client environment, such as timestamps, paginated polling, or available event capabilities.

### Application and Processing Layer

Reliability-sensitive logic would be implemented in Python or TypeScript.

This includes:

- Synchronization
- Idempotency
- Validation
- Retry handling
- Failure recovery
- AI-output verification
- Audit logging

n8n may be used for:

- Notifications
- Scheduled reports
- Approval routing
- Operational visibility
- Controlled internal workflows

### Review Interface

A lightweight Next.js application hosted on Vercel would allow authorized users to:

- Review responsibility recommendations
- View supporting lease clauses
- Correct classifications
- Approve or reject actions
- Review utility anomalies
- Request audit packages
- Replay failed workflow items
- View processing history and system health

---

## 3. Data Model Sketch

Each operational table would include an `organization_id` to support multi-tenant separation.

| Table | Purpose |
|---|---|
| `organizations` | Client account, configuration, retention policy |
| `integration_connections` | Provider, scopes, connection status, last sync |
| `properties` | Property details and Rent Manager ID |
| `units` | Property units and status |
| `contacts` | Tenants, owners, vendors, and identifiers |
| `leases` | Lease dates, unit, tenant, document location |
| `lease_clauses` | Extracted clauses and source references |
| `email_messages` | Message IDs, sender, timestamps, processing status |
| `attachments` | File metadata, checksum, extraction status |
| `maintenance_cases` | Issue type, severity, property, unit, status |
| `responsibility_assessments` | Recommendation, confidence, evidence, reviewer decision |
| `utility_accounts` | Provider, property, account, or meter |
| `utility_bills` | Billing period, amount, usage, normalized values |
| `anomaly_events` | Rule, baseline, variance, severity, review status |
| `invoices` | Vendor, property, invoice number, amount, date |
| `audit_packages` | Request parameters, manifest, output location |
| `review_tasks` | Reviewer, reason, decision, timestamps |
| `workflow_runs` | Workflow status, attempts, duration, correlation ID |
| `dead_letter_events` | Failed payload, stage, error, replay status |
| `audit_log` | Actor, action, entity, before/after values |

Unique constraints and upserts would prevent duplicate processing.

Supabase Row Level Security should be enabled to provide additional protection between organizations and users.

---

## 4. Workflow Details

### Maintenance Responsibility Workflow

The system would first apply deterministic logic to:

- Match the sender to a known tenant or contact
- Resolve the property and unit
- Detect emergency terms
- Retrieve the applicable lease and policies
- Check whether required information is missing

Claude would then return a structured result such as:

```json
{
  "issue_type": "plumbing_leak",
  "severity": "urgent",
  "recommended_responsibility": "landlord",
  "confidence": 0.86,
  "evidence": [
    {
      "clause_id": "clause_123",
      "reason": "Owner is responsible for building plumbing systems."
    }
  ],
  "missing_information": [],
  "recommended_action": "Create urgent maintenance review task."
}
```

The result would be rejected or routed to review when:

- Required fields are missing
- The model cites an unsupported clause
- Lease language conflicts with company policy
- Confidence is below the threshold
- The case involves an emergency, injury, legal threat, or unclear responsibility
- No reliable tenant, unit, or lease match exists

### Utility Anomaly Workflow

The system would normalize:

- Billing-period length
- Total amount
- Usage
- Cost per unit
- Credits and adjustments
- Occupancy context
- Duplicate records

Possible detection rules include:

- Month-over-month percentage change
- Rolling-median deviation
- Same-month prior-year comparison
- Cost-per-unit changes
- Missing or duplicate bills
- Unusual billing-period length

### Audit Package Workflow

The system would:

1. Query relevant invoices.
2. Retrieve attachments.
3. Detect missing or mismatched records.
4. Generate a numbered manifest.
5. Organize documents.
6. Produce a ZIP file or combined PDF.
7. Store the package with a checksum and audit log.
8. Display incomplete records separately.

Original source files would remain unchanged.

---

## 5. AI Reliability and Trust

The LLM would be treated as one controlled component, not the final decision-maker.

Safeguards would include:

- Strict structured-output schemas
- Retrieval limited to approved company data
- Evidence IDs linked to source records
- Deterministic validation before and after each model call
- Confidence thresholds
- Exception rules
- Human approval
- Versioned prompts and models
- Complete audit history
- Evaluation against labeled historical cases

Testing should include:

- Standard maintenance requests
- Emergencies
- Missing information
- Conflicting lease clauses
- Duplicate emails
- Prompt-injection attempts
- Unsupported conclusions

Suggested metrics:

- Agreement with human reviewers
- Manual-review rate
- False-confidence rate
- Processing time
- Unmatched tenant or property rate
- Reviewer correction rate
- Failure and replay rate

---

## 6. Reliability Strategy

### Idempotency

Every event would receive an idempotency key based on:

- Source system
- Organization
- Record ID
- Relevant version

Database uniqueness constraints and upserts would prevent duplicate processing.

### Retry and Failure Recovery

Transient errors would use bounded retries with exponential backoff and jitter.

Permanent failures and exhausted retries would move to a dead-letter table with enough context to diagnose and safely replay the event.

### Silent Failure Detection

Monitoring would track:

- Last successful synchronization
- Oldest unprocessed event
- Queue depth
- Error rate
- Dead-letter count
- Emails received versus processed
- Expiring Microsoft Graph subscriptions
- Missing utility imports
- Incomplete audit packages
- Unexpected drops or spikes in processing volume

### Testing and Deployment

The implementation would include:

- Unit tests
- Contract tests
- Integration tests
- LLM evaluation fixtures
- Duplicate-event tests
- Retry tests
- Missing-data tests
- Development, staging, and production environments
- Feature flags
- Version-controlled database migrations
- Rollback procedures

---

## 7. Project Phases

### Phase 1: Discovery and Access

- Map the current process
- Review Rent Manager and Microsoft 365
- Define responsibility rules
- Review sample leases, emails, invoices, and utility records
- Confirm security and retention requirements
- Establish baseline metrics

### Phase 2: Integration Foundation

- Configure Microsoft Graph
- Validate Rent Manager connectivity
- Create the Supabase schema
- Implement initial synchronization
- Add logging, idempotency, and dead-letter handling

### Phase 3: Maintenance Email Pilot

- Build email and attachment ingestion
- Match tenants, properties, units, and leases
- Implement responsibility assessment
- Add human review
- Evaluate against historical cases

### Phase 4: Utility Anomaly Detection

- Normalize utility records
- Establish baselines
- Implement rules
- Add review feedback

### Phase 5: Audit Package Generation

- Retrieve invoices and attachments
- Add completeness checks
- Generate manifests
- Produce downloadable packages
- Test incomplete and large requests

### Phase 6: Hardening and Security Review

- Test retries and duplicates
- Review access controls
- Test recovery
- Validate logs and alerts
- Run user acceptance testing

### Phase 7: Controlled Pilot and Handoff

- Release to a limited scope
- Monitor reviewer corrections
- Tune thresholds
- Complete documentation
- Train internal users
- Recommend the next phase

---

## 8. Estimated Implementation Effort

- **Functional pilot:** approximately 140 to 180 hours
- **Production-hardened pilot:** approximately 180 to 220 hours

The final estimate depends on:

- Rent Manager API access
- Lease-document condition
- Utility-data quality
- Email and attachment volume
- Dashboard complexity
- Whether production write-back is included

A useful vertical slice of the maintenance email workflow should be demonstrable within 7 to 10 working days after access and sample data are provided.

---

## 9. Required Client Access and Dependencies

The project would require:

- Rent Manager sandbox or restricted API account
- Rent Manager API documentation
- Microsoft Entra application registration
- Approved Graph permissions
- Test mailbox
- Representative email samples
- Supabase environment
- Vercel environment
- GitHub access
- Approved Claude API account
- Sample property, tenant, lease, invoice, and utility data
- Historical maintenance cases
- Responsibility and escalation rules
- Security and data-retention requirements
- A designated property-management reviewer

Production credentials should be stored only in approved company environments.

Sensitive data should never be placed in personal AI accounts, personal automation services, repositories, or logs.

---

## 10. Proof of Concept

A small proof of concept was built using synthetic data.

It demonstrates:

- Microsoft Graph-style maintenance-email intake
- Duplicate prevention through idempotency
- Tenant and lease matching
- Synthetic lease-clause retrieval
- Structured responsibility assessment
- Manual-review routing
- Workflow-run logging
- Automated tests for duplicates, emergencies, unknown senders, and low-confidence cases

The proof of concept does not connect to a live Rent Manager account because client-approved credentials are required.

### Repository Structure

```text
property_maintenance_poc/
├── app.py
├── README.md
├── sample_email.json
├── data/
│   └── records.json
├── state/
└── tests/
    └── test_app.py
```

### Run the Proof of Concept

Requires Python 3.11 or later.

```bash
python app.py
```

Open:

```text
http://localhost:8000
```

### Run Tests

```bash
python -m unittest discover -s tests -v
```

### Production Next Steps

1. Replace the synthetic connector with Rent Manager and Microsoft Graph APIs.
2. Use Anthropic's official SDK for schema-constrained classification.
3. Move workflow state to Supabase/PostgreSQL.
4. Add secure authentication and role-based access.
5. Add production monitoring, retries, alerts, and dead-letter handling.
6. Build a Next.js review dashboard.
7. Add write-back only after controlled testing and approval.

---

## Author

**Jerome Isaac Katigbak**  
AI Automation and Operations Specialist

**GitHub Portfolio:**  
https://github.com/jzkatigbak21/Jerome-Isaac-Katigbak---Ai-Business-Automation-Portfolio
