"""Raw IG `metadata.allowance` JSON field names, as returned by
GET /prices/{epic} (see doc/ig-api.md)."""


class AllowanceField:
    """Raw IG historical-data allowance field names."""
    REMAINING_ALLOWANCE = "remainingAllowance"
    TOTAL_ALLOWANCE = "totalAllowance"
    ALLOWANCE_EXPIRY = "allowanceExpiry"
