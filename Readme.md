# IT Ticket System - Integration Documentation

## What Happens When You Connect Jira, ServiceNow, and Azure Boards

---

## Part 1: Jira Integration (Developer Side)

### When Python Detects a Bug

The user submits an issue. Python scans the text for keywords like "bug", "crash", "error", "broken", or "exception". If any of these words are found, Python marks the ticket as a bug and prepares to create a task in Jira.

### The API Call to Jira

Python sends an HTTP POST request to Jira's REST API at:
`https://yourcompany.atlassian.net/rest/api/3/issue`

The request includes:
- Project key (like DEV)
- Issue summary from the user
- Full description with user name
- Issue type set to "Bug"
- Priority level (Low, Medium, High, Critical)
- Developer's email address for assignment

An API token is attached in the header for authentication.

### What Jira Does Internally

**Validation** - Jira checks if the API token is valid, if the project exists, if the developer account is active, and if the "Bug" issue type is allowed in that project.

**Database Insert** - Jira inserts a new row into its issues table. This stores the summary, description, status, priority, creation time, and assignee.

**Key Generation** - Jira creates a human-readable key like DEV-1234. The "DEV" comes from the project name. The number is the next available sequential number.

**Change Log** - Jira adds an entry to the change log table. This records every status change for audit purposes.

**Search Index** - Jira updates its Elasticsearch index so the new issue can be found immediately when someone searches.

**Notifications** - Jira queues an email to the assigned developer. It also checks for any automation rules.

**Webhook Trigger** - Jira sends a POST request to any registered webhook URLs (like our Python backend).

**Response** - Jira returns the issue ID and key to Python. Python stores the Jira key in its local database, linking the local ticket to the Jira task.

### When the Developer Starts Working

The developer opens Jira and clicks the "Start Progress" button. Jira checks if this status change is allowed. It then updates the status column in the issues table from "To Do" to "In Progress". Jira adds another entry to the change log. It also triggers a webhook to Python. Python receives this webhook and updates the local ticket status to "In Progress". The user can see this change when they refresh the page.

### When the Developer Fixes the Bug

The developer writes code, tests it, and confirms the issue is fixed. They return to Jira and click the "Resolve" or "Done" button. They may add a resolution note like "Fixed in version 2.1.3". Jira updates the database again, setting status to "Done" and resolution to "Fixed". It records the resolution date. It triggers another webhook to Python. Python updates the local ticket status to "Resolved". The user now sees a green badge indicating the ticket is resolved.

### Error Handling for Jira

If the API token expires, Python receives a 401 error. It logs the error, writes the failed request to a retry queue, and sends an alert to the system administrator. A background job runs every hour to retry failed requests.

If Jira is down for maintenance, the HTTP request times out after 30 seconds. Python catches the timeout, logs it, and queues the request for later retry. No data is lost.

---

## Part 2: ServiceNow Integration (IT Support Side)

### Creating an Incident

For every ticket submitted by the user, Python also creates an incident in ServiceNow. The API endpoint is:
`https://yourcompany.service-now.com/api/now/table/incident`

Python sends a JSON payload containing:
- Short description from the issue
- Long description with user name and full details
- Category like Software, Hardware, or Access
- Urgency level (1=High, 2=Medium, 3=Low)
- Impact level (how many users are affected)

Python uses basic authentication with a service account username and password.

### What ServiceNow Does Internally

**Validation** - ServiceNow checks if the API account has the "incident_creator" role. Without this role, the request is rejected.

**Number Generation** - ServiceNow creates a unique incident number like INC0012345. This follows a pattern defined in the system properties.

**Database Insert** - ServiceNow inserts a record into the incident table. This table has many columns including short_description, caller_id, opened_at, category, urgency, and impact. The state field is set to 1, which means "New".

**Assignment Rules** - ServiceNow runs its assignment engine. Company rules determine which support group receives the incident. For example, a password reset request goes to Level 1 support. A server outage pages the on-call engineer.

**SLA Timer** - ServiceNow starts SLA tracking. If the company promises to respond within 30 minutes, ServiceNow calculates the target response time based on business hours. It stores this target in the SLA table.

**Notifications** - ServiceNow sends email alerts. The assigned support person gets an email. The user who reported the issue gets a confirmation email with the incident number.

**Audit Log** - ServiceNow records the entire transaction in the sys_audit table. Every field set during creation is logged for compliance purposes.

### When IT Support Works on the Incident

When IT support investigates the issue, they may change the incident state to "In Progress". They may add comments or reassign to another group. Each change triggers ServiceNow's webhook system. ServiceNow sends a POST request to our Python endpoint containing the incident number, the changed fields, the new values, the old values, who made the change, and when it happened. Python receives this webhook and updates the local ticket status.

### When the Incident is Resolved

When the issue is fixed, IT support changes the incident state to "Resolved" or "Closed". ServiceNow requires a resolution code such as "Fixed", "Workaround Provided", or "Duplicate". It also requires a resolution note explaining what was done. ServiceNow stops the SLA timer, records the resolution time, and updates its analytics dashboards. It sends a final webhook to Python, and Python marks the local ticket as resolved.

---

## Part 3: Azure Boards Integration (Management Side)

### Creating a Work Item

When Python detects a bug, it also creates a work item in Azure Boards. The API endpoint is:
`https://dev.azure.com/organization/project/_apis/wit/workitems/$Bug?api-version=6.0`

Python sends a JSON payload with fields including:
- System.Title - the issue summary
- System.Description - full issue details
- Microsoft.VSTS.Common.Priority - 1 for Critical, 2 for High, 3 for Medium, 4 for Low
- System.AssignedTo - developer's email address
- System.IterationPath - which sprint this should go into

Python attaches a Personal Access Token (PAT) in the authorization header.

### What Azure Boards Does Internally

**Token Validation** - Azure checks that the PAT has the "work_items_write" scope. Without this scope, the request fails.

**Project Validation** - Azure verifies that the project exists. If the project name in the URL is wrong, it returns a 404 error.

**Work Item Type Validation** - Azure checks if "Bug" is a valid work item type in this project. Some projects rename or remove certain types.

**ID Generation** - Azure creates a unique work item ID. This is a sequential integer like 12345.

**Database Insert** - Azure stores the work item in its cloud database. Every change creates a new version rather than overwriting the old one. This provides complete history.

**Backlog Addition** - Azure adds the work item to the product backlog. The product owner can later prioritize it against other items.

**Analytics Update** - Azure refreshes its analytics engine. Dashboard widgets that show work item counts, burndown charts, and velocity metrics eventually update.

### Sprint Assignment and Status Tracking

The product owner can drag the work item from the backlog into a specific sprint. This changes the IterationPath field. Azure creates a new version of the work item and updates sprint capacity calculations.

During the sprint, the developer updates the work item status. The typical workflow is:
- New - Created but not yet reviewed
- Active - Someone is working on it
- Resolved - Work is done, waiting for verification
- Closed - Verified and complete

Each status change creates a new version with a timestamp and the person who made the change.

---

## Part 4: Complete Flow Example

A user submits this issue: "The payroll system crashes when I try to generate reports. This is a critical bug because payroll is due tomorrow."

### First 5 seconds:
- Python saves the ticket locally with status "Open"
- Python detects the word "crashes" and sets the bug flag to true
- Python calls ServiceNow API and creates incident INC0012345
- Python calls Jira API and creates bug DEV-5678
- Python calls Azure API and creates work item 12345
- Python returns a success message to the user

### After 5 minutes:
- IT support sees the incident in ServiceNow
- They confirm it is a software bug
- They add a comment "Escalating to development team"
- They change the assignment group to Development
- ServiceNow sends a webhook to Python
- Python updates the local ticket status to "In Progress"

### After 1 hour:
- The developer sees the Jira task
- They click "Start Progress"
- Jira sends a webhook to Python
- Python updates the local ticket status again
- Python also calls ServiceNow API to add a note: "Developer is investigating"

### After 3 hours:
- The developer finds the bug and writes a fix
- They test the fix and deploy it
- They change the Jira status to "Done" and add a resolution note
- Jira sends a webhook to Python
- Python updates the local ticket to "Resolved"
- Python calls ServiceNow to close the incident
- Python calls Azure to close the work item

### After 4 hours:
- The user refreshes the ticket system
- They see the ticket status is now "Resolved"
- They see the developer's resolution note
- The issue is completely closed

---

## Error Handling Summary

| Problem | What Happens |
|---------|--------------|
| API token expired | Python gets 401 error, logs it, queues retry, alerts admin |
| ServiceNow is down | Request times out after 30 seconds, Python queues retry |
| Rate limited by Azure | Azure returns 429 with Retry-After header, Python waits and retries |
| Missing ticket mapping | Python logs webhook to dead letter file, admin reconciles manually |

A background retry job runs every hour to process any failed requests.

---

## Security Summary

| System | Authentication Method | Token Lifespan |
|--------|----------------------|----------------|
| Jira | Personal Access Token | 1 year |
| ServiceNow | Basic Authentication over HTTPS | Service account password |
| Azure Boards | Personal Access Token | 1 year |
| Webhooks | Secret token validation | Permanent |

All communication between systems happens over TLS encrypted connections.

---

## Benefits of Integration

### Jira Benefits:
- Developers track all bugs in one place
- Status is visible to the entire team
- Priority reflects business impact
- Complete change history is maintained

### ServiceNow Benefits:
- IT support follows a defined workflow
- SLA tracking ensures response times are met
- Audit trail helps with compliance
- Knowledge base grows from resolved incidents

### Azure Boards Benefits:
- Agile sprint management is centralized
- Burndown charts show progress
- Team velocity is tracked over time
- Backlog prioritization is systematic

---

*Documentation Version 1.0*