"""
Asynchronous HTTP Client for BudgetBakers Wallet REST API.
Handles authentication, error handling, rate limiting with exponential backoff,
and provides methods to create, list, and delete financial records.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx

from config import settings

logger = logging.getLogger(__name__)


class WalletAPIError(Exception):
    """Base exception for BudgetBakers Wallet API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class RateLimitError(WalletAPIError):
    """Raised when the Wallet API rate limit is exceeded (HTTP 429)."""
    pass


class UnauthorizedError(WalletAPIError):
    """Raised when the API token is invalid or expired (HTTP 401)."""
    pass


class WalletClient:
    """Async client for BudgetBakers Wallet API."""

    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 20.0,
        max_retries: int = 3,
    ):
        self.api_token = api_token or settings.wallet_api_token
        self.base_url = (base_url or settings.wallet_api_base_url).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self._headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "BudgetBakers-TelegramBot/1.0",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Executes an HTTP request with automatic retry logic for rate limits and transient errors.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retries = 0
        backoff_delay = 1.0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                try:
                    logger.debug("Wallet API %s %s (params: %s)", method, url, params)
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self._headers,
                        json=data,
                        params=params,
                    )

                    # Handle Success
                    if response.status_code in (200, 201, 204):
                        if response.status_code == 204 or not response.content:
                            return None
                        try:
                            return response.json()
                        except Exception:
                            return response.text

                    # Handle Rate Limiting (429)
                    if response.status_code == 429:
                        retries += 1
                        if retries > self.max_retries:
                            raise RateLimitError(
                                "BudgetBakers Wallet API rate limit exceeded (300 requests/hr).",
                                status_code=429,
                                details=response.text,
                            )
                        retry_after = float(response.headers.get("Retry-After", backoff_delay))
                        logger.warning("Rate limit hit. Waiting %.2fs before retry %d...", retry_after, retries)
                        await asyncio.sleep(retry_after)
                        backoff_delay *= 2
                        continue

                    # Handle Unauthorized (401)
                    if response.status_code == 401:
                        raise UnauthorizedError(
                            "Invalid or expired Wallet API Token. Please check WALLET_API_TOKEN.",
                            status_code=401,
                        )

                    # Handle Transient Server Errors (500, 502, 503, 504)
                    if response.status_code in (500, 502, 503, 504):
                        retries += 1
                        if retries > self.max_retries:
                            raise WalletAPIError(
                                f"Wallet API server error {response.status_code}: {response.text}",
                                status_code=response.status_code,
                            )
                        logger.warning(
                            "Server error %d on %s. Retrying in %.2fs (attempt %d)...",
                            response.status_code,
                            url,
                            backoff_delay,
                            retries,
                        )
                        await asyncio.sleep(backoff_delay)
                        backoff_delay *= 2
                        continue

                    # Client errors (400, 403, 404, etc.)
                    err_msg = f"Wallet API request failed ({response.status_code}): {response.text}"
                    logger.error(err_msg)
                    raise WalletAPIError(err_msg, status_code=response.status_code, details=response.text)

                except httpx.RequestError as exc:
                    retries += 1
                    if retries > self.max_retries:
                        raise WalletAPIError(f"HTTP connection error to Wallet API: {exc}") from exc
                    logger.warning("Connection error: %s. Retrying in %.2fs...", exc, backoff_delay)
                    await asyncio.sleep(backoff_delay)
                    backoff_delay *= 2

    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Fetch all user accounts from Wallet."""
        res = await self._request("GET", "accounts", params={"limit": 50})
        if isinstance(res, dict) and "accounts" in res:
            return res["accounts"]
        elif isinstance(res, list):
            return res
        return []

    async def get_categories(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Fetch all user categories from Wallet."""
        res = await self._request("GET", "categories", params={"limit": limit})
        if isinstance(res, dict) and "categories" in res:
            return res["categories"]
        elif isinstance(res, list):
            return res
        return []

    async def get_records(
        self,
        limit: int = 50,
        record_date_gte: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch records from Wallet with optional date filter."""
        params: Dict[str, Any] = {"limit": limit}
        if record_date_gte:
            params["recordDate"] = f"gte.{record_date_gte}"
        res = await self._request("GET", "records", params=params)
        if isinstance(res, dict) and "records" in res:
            return res["records"]
        elif isinstance(res, list):
            return res
        return []

    async def create_record(
        self,
        amount: float,
        category_id: str,
        account_id: Optional[str] = None,
        note: Optional[str] = None,
        payee: Optional[str] = None,
        record_date: Optional[datetime] = None,
        is_income: bool = False,
        payment_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new transaction record in BudgetBakers Wallet.
        Note: The Wallet API expects a list of CreateRecordRequest objects.
        Expenses must have a negative value; Incomes must have a positive value.
        """
        acc_id = account_id or settings.wallet_default_account_id
        if not acc_id:
            raise WalletAPIError("No accountId provided and WALLET_DEFAULT_ACCOUNT_ID is not configured.")

        # Ensure correct date format: ISO 8601 UTC
        dt = record_date or datetime.utcnow()
        if dt.tzinfo is not None:
            # Convert to UTC ISO string
            date_iso = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        else:
            date_iso = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Amount signing: negative for expense, positive for income
        val = abs(amount) if is_income else -abs(amount)

        record_item: Dict[str, Any] = {
            "accountId": acc_id,
            "recordDate": date_iso,
            "amount": val,
            "categoryId": category_id,
            "recordState": "cleared",
        }

        # Format note to include payee and notes (Wallet stores merchant description in note)
        full_note_parts = []
        if payee:
            full_note_parts.append(payee)
        if note and note != payee:
            full_note_parts.append(note)

        if full_note_parts:
            record_item["note"] = " - ".join(full_note_parts)

        if payment_type:
            record_item["paymentType"] = payment_type

        # Wallet API expects an array of records
        payload = [record_item]
        logger.info(
            "Creating record: amount=%.2f, category=%s, account=%s, payee=%s",
            val,
            category_id,
            acc_id,
            payee,
        )

        res = await self._request("POST", "records", data=payload)

        # Inspect response format
        record_id = None
        if isinstance(res, dict):
            # Check results list
            results = res.get("results", [])
            if results and isinstance(results, list):
                first = results[0]
                if not first.get("success", True):
                    raise WalletAPIError(
                        f"Wallet API rejected record: {first.get('error')}",
                        details=first,
                    )
                record_id = first.get("recordId") or first.get("id")
        elif isinstance(res, list) and res:
            first = res[0]
            if isinstance(first, dict):
                record_id = first.get("id")

        return {
            "success": True,
            "record_id": record_id,
            "amount": val,
            "is_income": is_income,
            "category_id": category_id,
            "account_id": acc_id,
            "payee": payee,
            "note": note,
            "raw_response": res,
        }

    async def delete_record(self, record_id: str) -> bool:
        """Delete a record by its unique ID using BudgetBakers DELETE /records."""
        if not record_id:
            raise ValueError("record_id is required to delete a record.")
        payload = {"ids": [record_id]}
        try:
            await self._request("DELETE", "records", data=payload)
            logger.info("Successfully deleted record %s", record_id)
            return True
        except WalletAPIError as e:
            logger.error("Failed to delete record %s: %s", record_id, e)
            raise

    async def update_record_category(self, record_id: str, new_category_id: str) -> bool:
        """Update category of an existing record using BudgetBakers PATCH /records."""
        if not record_id or not new_category_id:
            raise ValueError("Both record_id and new_category_id are required.")
        patch_payload = [
            {"id": record_id, "categoryId": new_category_id}
        ]
        try:
            await self._request("PATCH", "records", data=patch_payload)
            logger.info("Successfully updated category for record %s to %s", record_id, new_category_id)
            return True
        except WalletAPIError as e:
            logger.error("Failed to update record category %s: %s", record_id, e)
            raise


# Global client instance
wallet_client = WalletClient()
