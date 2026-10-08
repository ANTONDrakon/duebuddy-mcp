# DueBuddy MCP server

Read incoming invoices from your AI assistant and get structured data plus a file ready
for accounting. Remote MCP server — nothing to install.

**Endpoint:** `https://duebuddy.work/mcp` (streamable HTTP)
**Docs:** https://duebuddy.work/mcp-docs

## What it does

- Reads supplier invoices: PDF, photo, scan, XML (ZUGFeRD, XRechnung, Factur-X, FatturaPA, KSeF, Peppol, ZATCA), QR codes, 1C/УПД/ЭСФ/ЭСЧФ
- Returns structured fields: number, date, supplier, net, VAT, total, currency, due date
- Produces an import file for accounting: DATEV EXTF (category 21), CSV, Excel, JSON
- Sends polite payment reminders from the client's own mailbox (Google authorisation)

## Tools

| Tool | What it does |
|---|---|
| `parse_invoice(api_key, file_url, country)` | reads one incoming invoice, returns a job id |
| `get_result(api_key, job_id)` | returned fields plus export links |
| `get_balance(api_key)` | pages left on the balance |
| `topup_link(amount_eur)` | where to top up (from 8 EUR) |

## Connect

Claude Desktop / Cursor / any MCP client:

```json
{
  "mcpServers": {
    "duebuddy": {
      "url": "https://duebuddy.work/mcp"
    }
  }
}
```

Then ask the assistant to call `parse_invoice` with your API key, a file URL and a country code.

## Pricing

- Scanned pages: **0.07 EUR per page**
- Electronic invoices (XML, QR): **free** — parsed by code, no model involved
- No subscription; pre-paid balance, minimum top-up **8 EUR**
- First 5 pages free once per key

## What we do not do

- We do not issue invoices in your name and do not take payments.
- We have **no DATEV API integration** — we deliver a file (EXTF, category 21); the booking in DATEV is done by your accountant.
- We do not connect to your 1C database: one direction only (document in, data and file out).
- We do not replace your accountant and do not give tax advice.

## Privacy

Documents are processed to extract data and are not used for model training. Mailbox access is
read-only and revocable at any time. See https://duebuddy.work/security
