# Smart Trade AI — Data Directory Structure Design

> ⚠️ **This design is fully compatible with Windows and macOS.** All paths use `pathlib`, filenames follow the slug format uniformly, and directories are at most 3 levels deep.
>
> Referencing the Hermes `~/.hermes/` design pattern, establishing a cross-platform standardized local data organization system for the Foreign Trade Assistant.

---

## 0. Cross-Platform Path Design

### Design Basis

Hermes Agent's path resolution logic (`hermes_constants.py`):

```python
def get_hermes_home() -> Path:
    val = os.environ.get("HERMES_HOME", "").strip()
    if val:
        return Path(val)
    return Path.home() / ".hermes"   # Path.home() automatically adapts to each platform
```

| Platform | Path.home() | Default Hermes Directory | Default Trade Directory |
|----------|------------|-------------------------|------------------------|
| macOS | `/Users/{user}` | `~/.hermes/` | `~/.trade/` |
| Linux | `/home/{user}` | `~/.hermes/` | `~/.trade/` |
| WSL2 | `/home/{user}` | `~/.hermes/` | `~/.trade/` |
| Windows native | `C:\Users\{user}` | `%LOCALAPPDATA%\hermes\` | `%LOCALAPPDATA%\trade\` |

> Custom path: Set the `TRADE_HOME` environment variable to override the default location.

**Windows native installation**: Use a PowerShell one-click script to automatically set the `HERMES_HOME` and `TRADE_HOME` environment variables to point to `%LOCALAPPDATA%`, and bundle MinGit (portable Git Bash) for shell command execution.

1. **Path separators**: All handled using `Path` / `pathlib`, never hardcoding `/` or `\`
2. **Filename restrictions**: Windows filenames cannot contain `<>:"/\|?*`; company/client slugs use only alphanumeric characters and hyphens
3. **Path length**: Windows default MAX_PATH = 260 characters; directory depth should not be excessive (current design is 3 levels, safe)
4. **Case sensitivity**: Windows is case-insensitive; filenames uniformly use lowercase + hyphens (slug format)
5. **Git Bash**: Hermes bundles MinGit on Windows; Trade can reuse this Git Bash to execute shell commands

---

## 1. Design Principles

1. **Unified structure**: Every company, every client, every document library uses the same directory structure and filenames
2. **Progressive filling**: Only the directory skeleton is needed initially; content can be filled in gradually
3. **Agent-readable**: All files are in Markdown format; the Agent can read them directly via `read_file` for context
4. **Coexistence with Hermes**: Trade's data directory is independent of `~/.hermes/`, using `~/.trade/`
5. **Fixed filenames**: Filenames under each directory are fixed; missing files indicate that the information has not yet been filled in

## 2. Repository Template vs Runtime Directory

| | Repository (`.trade-template/`) | Runtime (`~/.trade/`) |
|--|-------------------------------|-----------------------|
| Location | Project repository root | User home directory |
| Purpose | Show directory skeleton + template files | Store actual user data |
| Version controlled | Yes (`.gitignore` already excludes runtime directories) | No (auto-created at runtime) |

> **The `.trade-template/` in the repository** is the complete template directory structure under this path. During installation, commands like `trade init-company` create the actual runtime directory `~/.trade/` in the user's home directory.

## 3. Top-Level Directory Structure

```
~/.trade/
├── config.yaml                     # Trade-specific configuration (currently active company, etc.)
├── companies/                      # Company directories (can manage multiple companies)
│   └── {company_slug}/            # One subdirectory per company (slug = English abbreviation)
│       ├── company-profile.md      # [Required] Company introduction
│       ├── products.md             # [Required] Product catalog and advantages
│       ├── business-scope.md       # [Required] Business scope
│       ├── agent-identity.md       # [Required] Agent role definition for this company
│       ├── competitors.md          # [Optional] Competitor analysis
│       ├── certifications.md       # [Optional] Certifications and qualifications
│       ├── marketing-strategy.md   # [Optional] Marketing strategy
│       ├── sales-playbook.md       # [Optional] Sales scripts and negotiation strategies
│       │
│       ├── libraries/             # Document libraries (one subdirectory per library)
│       │   └── {library_slug}/
│       │       ├── index.md        # [Required] File index
│       │       ├── changelog.md    # [Required] Content change log
│       │       ├── metadata.md     # [Required] Document library metadata
│       │       └── extracts/       # [Optional] Document analysis extracts
│       │           └── {filename}.md
│       │
│       └── clients/               # Clients (one subdirectory per client)
│           └── {client_slug}/
│               ├── profile.md      # [Required] Client profile
│               ├── contacts.md     # [Required] Contact information
│               ├── interactions.md # [Required] Communication records and taboos
│               ├── requirements.md # [Optional] Requirements records
│               ├── quotes.md       # [Optional] Quote history
│               ├── orders.md       # [Optional] Order records
│               └── notes.md        # [Optional] Notes
│
├── prompts/                        # User-customized system prompts
│   └── system.md                  # Global system prompt (overrides code defaults)
│
└── data/                           # Database
    └── trade.db                    # SQLite database (user runtime data)
```

---

## 4. File Specifications

### 4.1 Company-Level Files (8 files)

#### `company-profile.md` [Required]

```markdown
# {Company Full Name}

## Basic Information
- Founded:
- City:
- Employee Count:
- Annual Revenue:
- Main Business:

## Core Strengths
1. 
2. 
3. 

## Organizational Structure
- Foreign Trade Dept: X people
- Factory: X people
- R&D: X people

## Representative Clients
- 
- 
```

#### `products.md` [Required]

```markdown
# Product Catalog

## Product Line 1: {Name}
- Core Models:
- Technical Highlights:
- Target Applications:
- Certifications:

## Product Line 2: {Name}
- ...

## Price Range
- Low-end: $X - $Y
- Mid-range: $X - $Y
- High-end: $X - $Y

## Minimum Order Quantity (MOQ)
- 

## Lead Time
- Samples: X days
- Bulk order: X days
```

#### `business-scope.md` [Required]

```markdown
# Business Scope

## Target Markets
- Primary export regions:
- Secondary export regions:
- Regions to develop:

## Customer Types
- Distributors / EPC Contractors / Trading Companies / OEM Customers

## Trade Terms
- FOB / CIF / EXW / DDP

## Payment Terms
- New customers:
- Existing customers:

## Annual Export Volume
- 
```

#### `agent-identity.md` [Required]

```markdown
# Agent Identity Definition

## Role
You are the foreign trade business assistant for {Company Name}. Your responsibilities
include assisting the business team with client development, inquiry replies, quotation
preparation, social media content, client background checks, and more.

## Communication Style
- Tone: Professional, confident, not flashy
- Language: English for overseas clients, Chinese for internal teams
- Principle: Do not fabricate data; clearly state when uncertain

## Areas of Expertise
- 
- 

## Company Differentiators
1. 
2. 
3. 

## Pre-set Responses to Common Customer Objections
- "Price is too high" → 
- "Already have a supplier" → 
- "MOQ is too large" → 
```

#### `competitors.md` [Optional]

```markdown
# Competitor Analysis

## Domestic Competitors
| Company | Strengths | Weaknesses | Our Differentiation |
|---------|-----------|------------|--------------------|
|         |           |            |                    |

## International Competitors
| Company | Strengths | Weaknesses | Our Differentiation |
|---------|-----------|------------|--------------------|
|         |           |            |                    |
```

#### `certifications.md` [Optional]

```markdown
# Certifications & Qualifications

| Certification | Number | Issuing Body | Validity | Applicable Products |
|---------------|--------|--------------|----------|---------------------|
|               |        |              |          |                     |
```

#### `marketing-strategy.md` [Optional]

```markdown
# Marketing Strategy

## B2B Platforms
- Alibaba International Station:
- Made-in-China.com:
- Independent Website:

## Social Media Matrix
- LinkedIn:
- Facebook:
- Instagram:
- TikTok:
- YouTube:

## Annual Marketing Calendar
| Month | Key Activities | Promoted Products |
|-------|----------------|-------------------|
```

#### `sales-playbook.md` [Optional]

```markdown
# Sales Playbook

## Inquiry Reply SOP
1. 
2. 
3. 

## Pricing Strategy
- 

## Common Objection Handling
- Price objection →
- Supplier objection →
- MOQ objection →

## Negotiation Techniques
- 

## Order Follow-up Process
1. PI Confirmation →
2. Deposit Collection →
3. Production Follow-up →
4. Shipping Notification →
5. Delivery Follow-up →
```

---

### 4.2 Client-Level Files (7 files)

#### `profile.md` [Required]

```markdown
# {Client Company Name}

## Basic Information
- Country/Region:
- Company Size:
- Main Products:
- Market Position:
- Annual Purchase Volume (estimated):

## Purchasing Characteristics
- Procurement Categories:
- Procurement Cycle:
- Decision Chain (who is the key decision maker):
- Price Sensitivity: High / Medium / Low
- Quality Requirements: High / Medium / Low

## Customer Type
- Distributor / EPC / Trading Company / End User

## Fit with Our Company
- Matching Products:
- Competitive Advantages:
- Potential Barriers:
```

#### `contacts.md` [Required]

```markdown
# Contacts

## Primary Contact
- Name:
- Title:
- Email:
- Phone/WhatsApp:
- LinkedIn:
- Personality Traits:
- Communication Preference (Email/WhatsApp/Phone):

## Secondary Contacts
- ...
```

#### `interactions.md` [Required]

```markdown
# Communication Records

## Communication Taboos
- Topics to avoid:
- Sensitive matters:

## Best Time to Contact
- Local time: XX:00
- Beijing time: XX:00

## Communication History Summary
| Date | Method | Content | Result |
|------|--------|---------|--------|
|      |        |         |        |
```

#### `requirements.md` [Optional]

```markdown
# Requirements Records

## Current Requirements
- Product:
- Quantity:
- Delivery:
- Budget:

## Historical Requirements
- 

## Potential Requirements (Speculative)
- 
```

#### `quotes.md` [Optional]

```markdown
# Quote History

| Date | Product | Quantity | Unit Price | Total Price | Payment Terms | Validity | Status |
|------|---------|----------|------------|-------------|---------------|----------|--------|
|      |         |          |            |             |               |          |        |

Status: pending / accepted / rejected / expired
```

#### `orders.md` [Optional]

```markdown
# Order Records

| PI # | Date | Product | Quantity | Amount | Payment | Ship Date | Status |
|------|------|---------|----------|--------|---------|-----------|--------|
|      |      |         |          |        |         |           |        |
```

#### `notes.md` [Optional]

```markdown
# Notes

- Other information to record
- Customer special requirements
- Next contact plan
```

---

### 4.3 Document Library-Level Files (3 files + extracts/)

#### `index.md` [Required]

```markdown
# {Document Library Name} — File Index

> Root path: {root_path}
> Last scan: {time}
> Total files: {N}

## File List

| # | Filename | Type | Size | Pages/Lines | Content Summary |
|---|----------|------|------|-------------|-----------------|
| 1 |          |      |      |             |                 |

## Count by Category
- Quotations: N files
- Product specifications: N files
- Customer materials: N files
- Transaction records: N files
- Certificates: N files
- Other: N files
```

#### `changelog.md` [Required]

```markdown
# Document Library Change Log

| Date | Change Type | Filename | Description |
|------|-------------|----------|-------------|
|      | Added/Modified/Deleted |    |             |
```

#### `metadata.md` [Required]

```markdown
# Document Library Metadata

- Created:
- Root directory path:
- Total file count:
- Last full scan:
- Last incremental update:
- Cognee dataset name:
```

---

## 5. How the Agent Uses This Structure

### 5.1 Auto-Loaded on Startup

When the Agent's working directory is set to `~/.trade/companies/{company_slug}/`, Hermes automatically injects the `AGENTS.md` and `SOUL.md` files from that directory. Trade can leverage this mechanism:

```
~/.trade/companies/example-co/
├── agent-identity.md    ← Copied as SOUL.md for Hermes auto-loading
├── company-profile.md   ← Agent reads via read_file
├── products.md
└── ...
```

### 5.2 Context Injection Flow

At the start of each Agent conversation:

1. Agent reads the current company's `agent-identity.md` → determines role and communication style
2. Agent reads `products.md` → understands product lines
3. Agent reads `company-profile.md` → understands company background
4. If the user references a client name → Agent looks up files under `clients/{slug}/`
5. If the user references a document library → Agent reads `libraries/{slug}/index.md`

### 5.3 Cognee Knowledge Graph Sync

Analysis results from document library content will:
1. Be stored in the knowledge graph via `cognee_remember`
2. Also be written as Markdown files in the `extracts/` directory (textual backup)

---

## 6. Initialization Script

The `trade init-company` command creates the standard directory skeleton with one command:

```bash
trade init-company --name "ExampleCo" --slug "example-co"
```

Output:
```
Creating company directory: ~/.trade/companies/example-co/
  ✓ company-profile.md
  ✓ products.md
  ✓ business-scope.md
  ✓ agent-identity.md
  ✓ competitors.md
  ✓ certifications.md
  ✓ marketing-strategy.md
  ✓ sales-playbook.md
  ✓ libraries/ (empty)
  ✓ clients/ (empty)

Next steps:
  1. Edit company-profile.md to fill in basic company information
  2. Edit products.md to fill in the product catalog
  3. Use trade library create to create the first document library
```

---

## 7. Relationship with Database and Desktop Working Directory

### Three Data Storage Layers

| Data Type | Storage Location | Purpose |
|-----------|-----------------|---------|
| Structured data (CRUD) | `~/.trade/data/trade.db` (SQLite) | Fast queries, API responses |
| Unstructured knowledge | `~/.trade/companies/*.md` | Agent context, manual editing |
| Business documents | `~/Desktop/{Company Name}/` (Desktop working directory) | Quotations, contracts, client materials and other original files |

### Desktop Working Directory

A working directory is automatically created on the desktop when a company is set up, organized by foreign trade business process:

```
~/Desktop/{Company Name}/
├── Quotations/
├── Contracts/
├── Client Materials/
├── Product Specifications/
├── Invoices/
├── Shipping Documents/
├── Certifications/
└── Marketing Materials/
```

Each subdirectory is automatically registered as a document library. Users simply place files into the corresponding folder, and the Agent reads them directly via `read_file`. No file upload needed.

---

*Design reference: Hermes `~/.hermes/` directory structure + foreign trade business requirements*
