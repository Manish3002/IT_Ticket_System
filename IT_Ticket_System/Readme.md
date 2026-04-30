# IT Ticket Support System - Integration Documentation

## Jira, ServiceNow & Azure Boards - Internal Working

---

## JIRA INTEGRATION

### When Python Detects a Bug

The user submits an issue. Python scans the text for keywords: bug, crash, error, broken. If found, Python marks the ticket as a bug and prepares to talk to Jira.

### The API Call

Python opens a connection to Jira's REST API:
`https://company.atlassian.net/rest/api/3/issue`

Python sends a JSON message containing:
- Project key (like DEV)
- Issue summary from the user
- Full description with user name and details
- Issue type set to "Bug"
- Priority from the form
- Developer's email for assignment

Python attaches an API token in the header for authentication.

### Jira's Internal Process

**Validation** - Jira checks if the API token is valid, project exists, developer account is active, and "Bug" issue type is allowed.

**Database Insert** - Jira inserts a new row into its issues table with summary, description, status, priority, creation time, and assignee.

**Key Generation** - Jira creates a human-readable key like DEV-1234 using the project prefix and next sequential number.

**Change Log** - Jira adds an entry to the change log table recording every status change and field update.

**Search Index** - Jira updates its Elasticsearch index making the issue searchable immediately.

**Notifications** - Jira queues an email to the assigned developer and checks automation rules.

**Webhook Trigger** - Jira sends a POST request to registered webhook URLs.

**Response** - Jira returns the issue ID and key to Python. Python stores the Jira key in its local database.

### When Developer Works

Developer clicks "Start Progress" in Jira. Jira validates the transition, updates status from "To Do" to "In Progress", adds entry to change log, and triggers webhook. Python receives webhook and updates local ticket status.

### When Developer Fixes Bug

Developer clicks "Resolve" or "Done", adds resolution note. Jira updates status to "Done", resolution to "Fixed", records resolution date, triggers webhook. Python updates local ticket to "Resolved".

### Error Handling

- API token expired - 401 error, log, queue retry, alert admin
- Jira down - timeout, queue retry
- Background job retries failed requests every hour

---

## SERVICENOW INTEGRATION

### Creating an Incident

For every ticket, Python creates an incident in ServiceNow at:
`https://company.service-now.com/api/now/table/incident`

Python sends JSON payload with:
- Short description from issue
- Long description with user name
- Category (Software, Hardware, Access)
- Urgency level (1=High, 2=Medium, 3=Low)
- Impact level

Python uses basic authentication with service account credentials.

### ServiceNow Internal Process

**Validation** - Checks API account has "incident_creator" role.

**Number Generation** - Creates incident number like INC0012345.

**Database Insert** - Inserts record into incident table with state = "New".

**Assignment Rules** - Runs assignment engine to determine which support group gets the incident.

**SLA Timer** - Starts SLA tracking for response time targets.

**Notifications** - Sends email alerts to assigned support person and user.

**Audit Log** - Records transaction in sys_audit table for compliance.

### Updating Incident

IT support changes state to "In Progress" or adds comments. Each change triggers webhook to Python. Python updates local ticket status.

### Resolving Incident

IT support changes state to "Resolved" or "Closed". Requires resolution code (Fixed, Workaround, Duplicate) and resolution note. SLA timer stops, resolution time recorded, webhook sent to Python.

---

## AZURE BOARDS INTEGRATION

### Creating a Work Item

When bug detected, Python creates work item at:
`https://dev.azure.com/organization/project/_apis/wit/workitems/$Bug?api-version=6.0`

Python sends JSON payload with:
- System.Title - issue summary
- System.Description - full details
- Microsoft.VSTS.Common.Priority - 1=Critical, 2=High, 3=Medium, 4=Low
- System.AssignedTo - developer email
- System.IterationPath - sprint name

Python attaches Personal Access Token (PAT) for authentication.

### Azure Boards Internal Process

**Token Validation** - Checks PAT has "work_items_write" scope.

**Project Validation** - Verifies project exists.

**Work Item Type Validation** - Checks "Bug" is valid type in project.

**ID Generation** - Creates unique sequential integer ID like 12345.

**Database Insert** - Stores work item with versioning (every change creates new version).

**Backlog Addition** - Adds to product backlog for prioritization.

**Analytics Update** - Refreshes analytics engine for dashboards.

### Sprint Assignment

Product owner drags work item from backlog to sprint. Changes IterationPath field. Azure creates new version. Updates sprint capacity calculations.

### Status Tracking

Workflow states:
- New - Created, not reviewed
- Active - Someone working on it
- Resolved - Work done, awaiting verification
- Closed - Verified and complete

Each status change creates new version with timestamp and user.

---

## COMPLETE FLOW EXAMPLE

User submits: "The payroll system crashes when I try to generate reports. Critical bug because payroll is due tomorrow."

| Time | Action | System |
|------|--------|--------|
| 1 sec | Python saves ticket locally, detects bug | Local |
| 2 sec | Creates incident INC0012345 | ServiceNow |
| 3 sec | Creates bug DEV-5678 | Jira |
| 4 sec | Creates work item 12345 | Azure |
| 5 sec | Returns response to user | Python |
| 5 min | IT support confirms bug, escalates | ServiceNow → Python |
| 1 hr | Developer starts work | Jira → Python |
| 3 hr | Developer fixes bug, marks done | Jira → Python |
| 3 hr | Python closes incident and work item | ServiceNow, Azure |
| 4 hr | User sees resolved status | Browser |

---

## ERROR HANDLING

| Problem | Handling |
|---------|----------|
| API token expired | 401 error, log, queue retry, admin alert |
| ServiceNow down | Timeout after 30 seconds, queue retry |
| Rate limited (429) | Read Retry-After header, wait and retry |
| Missing ticket mapping | Log webhook to dead letter file, manual reconciliation |

Background retry job runs every hour for failed requests.

---

## SECURITY

| System | Authentication | Token Lifespan |
|--------|----------------|----------------|
| Jira | Personal Access Token | 1 year |
| ServiceNow | Basic Auth over HTTPS | Service account |
| Azure Boards | Personal Access Token | 1 year |
| Webhooks | Secret token validation | Permanent |

All communication uses TLS encryption.

---

## API ENDPOINTS

**Jira:**
- POST `/rest/api/3/issue` - Create task
- GET `/rest/api/3/issue/{key}` - Get details
- POST `/rest/api/3/issue/{key}/transitions` - Update status

**ServiceNow:**
- POST `/api/now/table/incident` - Create incident
- GET `/api/now/table/incident/{sys_id}` - Get incident
- PUT `/api/now/table/incident/{sys_id}` - Update incident

**Azure Boards:**
- POST `/_apis/wit/workitems/${type}` - Create work item
- GET `/_apis/wit/workitems/{id}` - Get work item
- PATCH `/_apis/wit/workitems/{id}` - Update work item

---

## WEBHOOK CONFIGURATION

| System | Endpoint | Events |
|--------|----------|--------|
| Jira | `/webhook/jira` | Issue updated, status changed |
| ServiceNow | `/webhook/servicenow` | Incident state change |
| Azure | `/webhook/azure` | Work item updated |

Each webhook includes secret token validation to prevent fake requests.

---

## BENEFITS OF INTEGRATION

**Jira:**
- Developers track bugs in one place
- Status visible to all team members
- Priority based on business impact
- Complete change history

**ServiceNow:**
- Defined IT support workflow
- SLA tracking for response times
- Audit trail for compliance
- Knowledge base for recurring issues

**Azure Boards:**
- Agile sprint management
- Burndown charts
- Team velocity tracking
- Backlog prioritization
++~

