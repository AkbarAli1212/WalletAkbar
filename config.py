"""
Configuration module for the BudgetBakers Wallet Telegram Bot.
Loads and validates settings from environment variables using Pydantic Settings.
"""

from typing import Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Telegram Credentials
    telegram_bot_token: str = Field(
        default="",
        alias="TELEGRAM_BOT_TOKEN",
        description="Bot Token from @BotFather",
    )
    allowed_telegram_user_id: int = Field(
        default=0,
        alias="TELEGRAM_USER_ID",
        description="Authorized Telegram User ID for security whitelisting",
    )

    # BudgetBakers Wallet API Credentials
    wallet_api_token: str = Field(
        default="",
        alias="WALLET_API_TOKEN",
        description="BudgetBakers Wallet API Bearer Token",
    )
    wallet_api_base_url: str = Field(
        default="https://rest.budgetbakers.com/wallet/v1/api",
        alias="WALLET_API_BASE_URL",
        description="Base REST API URL for Wallet",
    )
    wallet_default_account_id: Optional[str] = Field(
        default=None,
        alias="WALLET_DEFAULT_ACCOUNT_ID",
        description="Default Account ID to log records against",
    )
    wallet_currency: str = Field(
        default="SAR",
        alias="WALLET_CURRENCY",
        description="Currency code for transactions (default: SAR)",
    )

    # Timezone for localizing transaction timestamps
    timezone: str = Field(
        default="Asia/Riyadh",
        alias="TIMEZONE",
        description="Local timezone (e.g. Asia/Riyadh)",
    )

    # Wallet Category IDs (Configurable or pre-populated with user's account IDs)
    category_fuel_id: str = Field(
        default="5c5c1388-0032-8000-8000-000000000000",
        alias="CATEGORY_FUEL_ID",
    )
    category_cafe_id: str = Field(
        default="5c5c03ea-000a-8000-8000-000000000000",
        alias="CATEGORY_CAFE_ID",
    )
    category_restaurant_id: str = Field(
        default="5c5c03e9-000a-8000-8000-000000000000",
        alias="CATEGORY_RESTAURANT_ID",
    )
    category_groceries_id: str = Field(
        default="5c5c03e8-000a-8000-8000-000000000000",
        alias="CATEGORY_GROCERIES_ID",
    )
    category_software_id: str = Field(
        default="5c5c1b5b-0046-8000-8000-000000000000",
        alias="CATEGORY_SOFTWARE_ID",
    )
    category_other_id: str = Field(
        default="5c5c2af8-006e-8000-8000-000000000000",
        alias="CATEGORY_OTHER_ID",
    )
    category_income_id: Optional[str] = Field(
        default="5c5c2af8-006e-8000-8000-000000000000",
        alias="CATEGORY_INCOME_ID",
    )

    # Application settings
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    def get_category_id(self, category_key: str) -> str:
        """Lookup category ID by normalized internal key."""
        mapping: Dict[str, str] = {
            "fuel": self.category_fuel_id,
            "cafe": self.category_cafe_id,
            "restaurant": self.category_restaurant_id,
            "groceries": self.category_groceries_id,
            "software": self.category_software_id,
            "other": self.category_other_id,
            "income": self.category_income_id or self.category_other_id,
        }
        return mapping.get(category_key.lower(), self.category_other_id)


# Global settings singleton
settings = Settings()
