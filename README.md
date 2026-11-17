# duebuddy-mcp

MCP server that reads incoming supplier invoices and returns structured data plus a file ready
for accounting. One endpoint for PDF, photos, scans, QR bills and electronic invoices.

Works with Claude Desktop, Cursor, Cline, Windsurf and any MCP client that supports stdio.

```bash
pip install duebuddy-mcp
DUEBUDDY_API_KEY=your-key duebuddy-mcp
```

Hosted alternative: `https://duebuddy.work/mcp` (streamable HTTP), no install needed.
Docs: https://duebuddy.work/mcp-docs

## Why this exists

An accountant receives forty invoices a quarter. Half of them already contain the data in
machine-readable form — ZUGFeRD, XRechnung, Factur-X, FatturaPA, Peppol, KSeF, UBL — but they
arrive as `invoice.pdf`, so they get retyped by hand. The other half are scans and phone photos
where no data exists at all. This server handles both cases and returns fields plus an import
file, so the human checks instead of retyping.

## Quick start

### 1. Get an API key

Sign up at https://duebuddy.work, open the cabinet, create an API key. Five invoices are free,
no card required.

### 2. Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "duebuddy": {
      "command": "duebuddy-mcp",
      "env": { "DUEBUDDY_API_KEY": "your-key" }
    }
  }
}
```

### 3. Cursor

`.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "duebuddy": {
      "command": "duebuddy-mcp",
      "env": { "DUEBUDDY_API_KEY": "your-key" }
    }
  }
}
```

### 4. Ask

> Read the invoice at https://duebuddy.work/files/invoice-218.pdf, country de, and give me
> supplier, number, date, net, VAT, gross and the DATEV export link.

The assistant calls `parse_invoice`, then polls `get_result`, then reports.

## Tools

| Tool | What it does | When to use | When NOT to use | Cost |
|---|---|---|---|---|
| `parse_invoice` | Reads one invoice, returns `job_id` | One document needs field extraction | The user wants to issue an invoice, take a payment or post entries | XML and QR free; scans 0.07 EUR per page |
| `get_result` | Status, fields, export links for a `job_id` | You already have a `job_id` | You have no `job_id` yet | free, read-only |
| `get_balance` | Remaining prepaid pages | Before a batch; after `insufficient_balance` | The question is about invoice content | free, read-only |
| `topup_link` | Top-up page URL, minimum 8 EUR | Balance is empty or too low | Balance is sufficient | free, builds a link only |

Prompt `invoice_to_accounting` returns a safe order of operations for a batch: check balance,
parse each document, poll, validate totals, report.

## What it reads

| Input | Example | Cost |
|---|---|---|
| XML e-invoice | ZUGFeRD, XRechnung, Factur-X, FatturaPA, Peppol BIS, KSeF, UBL, ZATCA, 1C/УПД/ЭСФ | free |
| PDF with embedded XML | ZUGFeRD 2.x, Factur-X | free |
| Text PDF | ordinary invoice export | per page |
| Scan or phone photo | JPG, PNG, PDF from scanner | 0.07 EUR per page |
| QR bill | Swiss and similar payment slips | free |

Country profiles select field names and tax rules: `de`, `fr`, `it`, `pl`, `ru`, `kz`, `by`,
`us`, `ae`, `sa`, `ua`, `ge`. The profile does not change the price.

## Output

Structured fields: supplier, invoice number, issue date, due date, currency, net, VAT, gross,
line items. Export files: DATEV EXTF category 21, CSV, Excel, JSON. The file is what accounting
systems import — the server does not post entries itself.

## Cost model

Prepaid balance, charged per scanned page. XML and QR invoices are parsed by code and cost
nothing. No subscription is required to try it: five invoices are free.

## What it does not do

- does not issue or send invoices
- does not take payments
- does not post entries into 1C or DATEV, it produces the file those systems import
- does not store your documents beyond processing

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DUEBUDDY_API_KEY` | – | API key, so it need not be passed on every call |
| `DUEBUDDY_BASE_URL` | `https://duebuddy.work` | API endpoint |
| `DUEBUDDY_TIMEOUT` | `90` | HTTP timeout, seconds |

## CLI

```bash
duebuddy-mcp --version       # print version
duebuddy-mcp --help          # usage
duebuddy-mcp --list-tools    # tool names without starting the server
```

## Docker

```bash
docker build -t duebuddy-mcp .
docker run -i --rm -e DUEBUDDY_API_KEY=your-key duebuddy-mcp
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `api_key_required` | No key passed and env var unset | add `api_key` argument or `DUEBUDDY_API_KEY` |
| `insufficient_balance` | Prepaid balance is empty | `topup_link` → top up from 8 EUR |
| `invalid_file_url` | URL is not https or not on duebuddy.work | upload the file to the cabinet first |
| `unsupported_country` | Country code outside the list | use one of the 12 supported codes |
| Server exits at once in a terminal | Transport is stdio | run it from an MCP client, not manually |

## Security

The server only reads documents. It never posts entries, never issues invoices and never takes
payments. `file_url` must be an https link on `duebuddy.work`; redirects and other hosts are
rejected to prevent server-side request forgery. Each call is one HTTP request; nothing is cached
between calls.

## License

MIT
