# duebuddy-mcp

MCP server that reads incoming supplier invoices and returns structured data plus a file
ready for accounting. Works with Claude Desktop, Cursor, Cline and any MCP client.

## Install

```bash
pip install duebuddy-mcp
```

## Run

```bash
DUEBUDDY_API_KEY=your-key duebuddy-mcp
```

Transport is stdio. Get an API key in the DueBuddy cabinet; 5 invoices are free.

## What it reads

- PDF with embedded XML (ZUGFeRD, Factur-X), plain PDF, phone photos, scans
- E-invoices: XRechnung, FatturaPA, Peppol BIS, KSeF, UBL, ZATCA, 1C/УПД/ЭСФ
- QR bills

Country profiles: `de`, `fr`, `it`, `pl`, `ru`, `kz`, `by`, `us`, `ae`, `sa`, `ua`, `ge`.

## Tools

| Tool | What it does | Cost |
|---|---|---|
| `parse_invoice` | Reads one invoice, returns a `job_id` | XML and QR free, scans 0.07 EUR per page |
| `get_result` | Returns status, extracted fields and export links | free, read-only |
| `get_balance` | Remaining prepaid pages for the key | free, read-only |
| `topup_link` | Top-up page URL and minimum amount | free, builds a link only |

Plus a prompt `invoice_to_accounting` — a step-by-step plan for a batch: check balance, parse,
poll, validate totals, report.

Typical flow: `parse_invoice` → poll `get_result` → use the fields or the export file
(DATEV EXTF category 21, CSV, Excel, JSON).

## What it does not do

It does not issue invoices, does not take payments and does not post entries into 1C or DATEV.
It returns a file that those systems import.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DUEBUDDY_API_KEY` | – | API key, so it need not be passed on every call |
| `DUEBUDDY_BASE_URL` | `https://duebuddy.work` | API endpoint |
| `DUEBUDDY_TIMEOUT` | `90` | HTTP timeout in seconds |

## Docker

```bash
docker build -t duebuddy-mcp .
docker run -i --rm -e DUEBUDDY_API_KEY=your-key duebuddy-mcp
```

## License

MIT
