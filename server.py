"""DueBuddy MCP server — reading incoming invoices for AI assistants.

Thin, stateless client over the public DueBuddy HTTP API (https://duebuddy.work).
No customer data is stored here: every tool call proxies one HTTP request.

Transport: stdio. Auth: DueBuddy API key (X-Api-Key), passed per call or once
through the API_KEY environment variable.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

BASE_URL = os.environ.get("DUEBUDDY_BASE_URL", "https://duebuddy.work").rstrip("/")
DEFAULT_KEY = os.environ.get("DUEBUDDY_API_KEY", "").strip()
TIMEOUT = float(os.environ.get("DUEBUDDY_TIMEOUT", "90"))

COUNTRIES = ("de", "fr", "it", "pl", "ru", "kz", "by", "us", "ae", "sa", "ua", "ge")

mcp = FastMCP(
    name="duebuddy",
    instructions=(
        "Use this server to turn incoming supplier invoices into structured data. "
        "Supported inputs: PDF (text or scan), phone photos, XML e-invoices "
        "(ZUGFeRD, X-Rechnung, Factur-X, FatturaPA, Peppol BIS, KSeF, UBL) and QR bills. "
        "Supported countries: de, fr, it, pl, ru, kz, by, us, ae, sa, ua, ge. "
        "Typical flow: parse_invoice -> poll get_result -> export fields or a file for accounting. "
        "Cost model: XML and QR invoices are parsed by code and cost nothing; scans and photos "
        "cost 0.07 EUR per page from the prepaid balance. Check the balance with get_balance "
        "before batch work. This server only READS invoices: it does not issue invoices, does not "
        "take payments and does not post entries into DATEV or 1C — it returns a file that those "
        "systems import."
    ),
)


def _key(api_key: str) -> str:
    return (api_key or DEFAULT_KEY).strip()


def _missing_key() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "api_key_required",
        "message": (
            "No DueBuddy API key. Pass api_key on the call or set DUEBUDDY_API_KEY. "
            "A key is created in the DueBuddy cabinet after sign-up."
        ),
        "how_to_get_key": f"{BASE_URL}/pricing",
    }


@mcp.tool(
    name="parse_invoice",
    annotations=ToolAnnotations(
        title="Parse one incoming invoice",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
    description=(
        "Reads ONE incoming supplier invoice and returns a job id for polling.\n\n"
        "Use when: the user has a single invoice (PDF, photo, scan, XML e-invoice or QR bill) and "
        "wants supplier, invoice number, dates, amounts, VAT or line items extracted.\n"
        "Do not use when: the user asks to ISSUE an invoice, to send a payment, or to post entries "
        "into DATEV/1C — this tool only reads documents. For several documents call it once per "
        "document; the returned job ids can be polled independently.\n\n"
        "Side effects and cost: the document is downloaded and queued for parsing. XML and QR "
        "invoices are parsed by code and cost nothing; scans and photos cost 0.07 EUR per page and "
        "are charged to the prepaid balance. The call is not idempotent: each call creates a new "
        "job and a new charge for scans, so do not retry blindly after a timeout — poll get_result "
        "with the job id instead.\n\n"
        "Parameters: file_url must be a public https link to a single document on duebuddy.work "
        "(upload first via the cabinet); country is a two-letter code from the supported list and "
        "selects the parsing profile — it changes field names and tax rules, but does not change "
        "the price.\n\n"
        "Returns: {ok, job_id, status}. Next step: call get_result with that job_id."
    ),
)
def parse_invoice(
    file_url: str,
    country: str = "de",
    api_key: str = "",
) -> dict[str, Any]:
    """Start parsing of a single invoice document.

    Args:
        file_url: Public https URL of one invoice file on duebuddy.work.
        country: Two-letter country profile: de, fr, it, pl, ru, kz, by, us, ae, sa, ua, ge.
        api_key: DueBuddy API key; optional if DUEBUDDY_API_KEY is set.
    """
    key = _key(api_key)
    if not key:
        return _missing_key()
    if country not in COUNTRIES:
        return {"ok": False, "error": "unsupported_country", "supported": list(COUNTRIES)}

    from urllib.parse import urlparse

    parsed = urlparse(file_url or "")
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith("duebuddy.work"):
        return {
            "ok": False,
            "error": "invalid_file_url",
            "message": "file_url must be an https link to a file hosted on duebuddy.work",
        }

    try:
        with httpx.Client(follow_redirects=False, timeout=TIMEOUT) as client:
            got = client.get(file_url, headers={"User-Agent": "duebuddy-mcp/1.1"})
            if got.status_code != 200:
                return {"ok": False, "error": "download_failed", "http_status": got.status_code}
            payload = got.content
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "download_failed", "detail": type(exc).__name__}

    filename = parsed.path.rsplit("/", 1)[-1] or "invoice.pdf"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(
                f"{BASE_URL}/v1/parse",
                headers={"X-Api-Key": key},
                data={"country": country},
                files={"file": (filename, payload, "application/octet-stream")},
            )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "request_failed", "detail": type(exc).__name__}

    if resp.status_code == 402:
        return {
            "ok": False,
            "error": "insufficient_balance",
            "message": "Prepaid balance is empty. Top up from 8 EUR, then repeat the call.",
            "topup_url": f"{BASE_URL}/pricing",
        }
    if resp.status_code not in (200, 201, 202):
        return {"ok": False, "error": "parse_rejected", "http_status": resp.status_code,
                "detail": resp.text[:500]}

    body = resp.json()
    return {
        "ok": True,
        "job_id": body.get("job_id") or body.get("id"),
        "status": body.get("status"),
        "next_step": "call get_result with this job_id",
    }


@mcp.tool(
    name="get_result",
    annotations=ToolAnnotations(
        title="Get parsed invoice result",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
    description=(
        "Returns the result of a parse job started by parse_invoice: structured fields "
        "(supplier, invoice number, dates, net/VAT/gross, currency, line items) plus export links "
        "for accounting systems.\n\n"
        "Use when: you already have a job_id and want its status or its extracted data.\n"
        "Do not use when: you have no job_id yet — start with parse_invoice. Do not poll in a tight "
        "loop; one call every few seconds is enough, and jobs for text PDFs or XML usually finish "
        "in under a minute.\n\n"
        "Side effects and cost: none. This call is read-only and idempotent, reads nothing from the "
        "prepaid balance, and can be repeated safely.\n\n"
        "Parameters: job_id is the identifier returned by parse_invoice for the same API key.\n\n"
        "Returns: {ok, result} where result.status is one of queued, processing, done, failed; on "
        "done it also carries fields and export links."
    ),
)
def get_result(job_id: str, api_key: str = "") -> dict[str, Any]:
    """Fetch status and data of a parse job.

    Args:
        job_id: Identifier returned by parse_invoice.
        api_key: DueBuddy API key; optional if DUEBUDDY_API_KEY is set.
    """
    key = _key(api_key)
    if not key:
        return _missing_key()
    if not job_id:
        return {"ok": False, "error": "job_id_required"}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{BASE_URL}/v1/parse/{job_id}", headers={"X-Api-Key": key})
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "request_failed", "detail": type(exc).__name__}
    if resp.status_code != 200:
        return {"ok": False, "error": "not_found_or_forbidden", "http_status": resp.status_code}
    return {"ok": True, "result": resp.json()}


@mcp.tool(
    name="get_balance",
    annotations=ToolAnnotations(
        title="Check prepaid balance",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
    description=(
        "Shows how many scanned pages are left on the prepaid balance for this API key.\n\n"
        "Use when: before a batch of scans or photos, or when parse_invoice answered "
        "insufficient_balance and you need to confirm the remaining amount.\n"
        "Do not use when: the user asks about invoice content — that is get_result.\n\n"
        "Side effects and cost: none; read-only and idempotent.\n\n"
        "Parameters: api_key is the DueBuddy key; optional if DUEBUDDY_API_KEY is set.\n\n"
        "Returns: {ok, balance} with the remaining pages and the current plan."
    ),
)
def get_balance(api_key: str = "") -> dict[str, Any]:
    """Return remaining prepaid pages for the API key.

    Args:
        api_key: DueBuddy API key; optional if DUEBUDDY_API_KEY is set.
    """
    key = _key(api_key)
    if not key:
        return _missing_key()
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{BASE_URL}/v1/usage", headers={"X-Api-Key": key})
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "request_failed", "detail": type(exc).__name__}
    if resp.status_code != 200:
        return {"ok": False, "error": "request_failed", "http_status": resp.status_code}
    return {"ok": True, "balance": resp.json()}


@mcp.tool(
    name="topup_link",
    annotations=ToolAnnotations(
        title="Get top-up link",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    description=(
        "Returns the page where the prepaid balance can be topped up, and the minimum amount.\n\n"
        "Use when: the balance is empty or too low for the documents the user wants to process.\n"
        "Do not use when: the balance is sufficient — check it with get_balance first.\n\n"
        "Side effects and cost: none. The call only builds a link; the payment itself happens in "
        "the browser and is handled by the payment provider, never by this server.\n\n"
        "Parameters: amount_eur is informational only and does not create an order.\n\n"
        "Returns: {ok, url, minimum_eur}."
    ),
)
def topup_link(amount_eur: float = 8.0) -> dict[str, Any]:
    """Return the top-up page URL and the minimum amount.

    Args:
        amount_eur: Requested amount in euro, informational only.
    """
    return {
        "ok": True,
        "url": f"{BASE_URL}/pricing",
        "minimum_eur": 8,
        "requested_eur": amount_eur,
        "note": "payment is handled by the payment provider inside the browser",
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
