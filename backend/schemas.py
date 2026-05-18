"""
schemas.py - Pydantic request and response models for the PS-3 Rule Engine API.
All input validation and output serialization goes through these models.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime


# ─────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────

class ValidateRequest(BaseModel):
    """Single rule + single XML invoice validation."""
    rule_text: str = Field(..., min_length=5, max_length=500, description="Natural language rule in plain English (max 500 chars)")
    xml_content: str = Field(..., min_length=10, max_length=1000000, description="Raw XML invoice string (max 1MB)")

    @field_validator("rule_text")
    @classmethod
    def rule_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("rule_text cannot be blank")
        return v.strip()

    @field_validator("xml_content")
    @classmethod
    def xml_content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("xml_content cannot be blank")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "rule_text": "Tax amount must be greater than 0",
                "xml_content": "<Invoice><InvoiceID>INV-001</InvoiceID><TaxAmount>180</TaxAmount></Invoice>"
            }
        }
    }


class ValidateBatchRequest(BaseModel):
    """Single rule validated against multiple XML invoices."""
    rule_text: str = Field(..., min_length=5, description="Natural language rule in plain English")
    xml_files: List[str] = Field(..., min_length=1, description="List of raw XML invoice strings")

    @field_validator("rule_text")
    @classmethod
    def rule_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("rule_text cannot be blank")
        return v.strip()

    @field_validator("xml_files")
    @classmethod
    def xml_files_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("xml_files list cannot be empty")
        stripped = [x.strip() for x in v if x.strip()]
        if not stripped:
            raise ValueError("All xml_files entries are empty")
        return stripped

    model_config = {
        "json_schema_extra": {
            "example": {
                "rule_text": "Seller name is required",
                "xml_files": [
                    "<Invoice><SellerName>ABC Ltd</SellerName></Invoice>",
                    "<Invoice></Invoice>"
                ]
            }
        }
    }


class ValidateWorkspaceRequest(BaseModel):
    """Validate one XML invoice against a selected XSLT workspace file."""
    xml_content: str = Field(..., min_length=10, description="Raw XML invoice string")
    xslt_content: str = Field(..., min_length=10, description="XSLT content for the selected workspace file")
    xslt_name: Optional[str] = Field(default=None, description="Optional workspace file name for logging")

    @field_validator("xml_content", "xslt_content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content cannot be blank")
        return v.strip()


class UpdateWorkspaceRequest(BaseModel):
    """Request to update active workspace session."""
    sample_id: Optional[int] = None
    xslt_id: Optional[str] = None
    xslt_filename: Optional[str] = None


class SaveRuleRequest(BaseModel):
    """Persist a natural-language rule to the database."""
    rule_text: str = Field(..., min_length=5, max_length=500, description="Natural language rule in plain English (max 500 chars)")
    severity: str = Field(default="medium", description="Rule severity: low | medium | high | critical")
    xslt_id: Optional[str] = Field(default=None, description="XSLT file ID to bind the rule to")

    @field_validator("severity")
    @classmethod
    def severity_valid(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        v = v.lower().strip()
        if v not in allowed:
            raise ValueError(f"severity must be one of {sorted(allowed)}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "rule_text": "Payable amount must equal taxable amount plus tax amount",
                "severity": "high",
                "xslt_id": "some-xslt-id"
            }
        }
    }


class BatchEvaluateRequest(BaseModel):
    """Evaluate all saved rules against a single XML invoice."""
    xml_content: str = Field(..., min_length=10, description="Raw XML invoice string")

    @field_validator("xml_content")
    @classmethod
    def xml_content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("xml_content cannot be blank")
        return v.strip()


# ─────────────────────────────────────────────
# RESPONSE MODELS
# ─────────────────────────────────────────────

class ParsedRule(BaseModel):
    """The structured JSON produced by the rule parser."""
    rule_type: str
    field: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[Any] = None
    min: Optional[float] = None
    max: Optional[float] = None
    constraint: Optional[str] = None
    reference_field: Optional[str] = None
    expression: Optional[str] = None
    rate: Optional[float] = None
    tolerance: Optional[float] = 0.01
    description: Optional[str] = None
    confidence: Optional[float] = 1.0
    warnings: Optional[List[str]] = Field(default_factory=list)
    
    # Backward compatibility fields
    operation: Optional[str] = None
    base_field: Optional[str] = None
    condition_field: Optional[str] = None
    condition_value: Optional[str] = None
    extra: Optional[dict] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[str]] = None
    order: Optional[int] = None
    is_direct_tag: Optional[bool] = None
    xpath: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of a single rule validation against one XML invoice."""
    rule_id: Optional[int] = None
    rule_text: str
    parsed_rule: Optional[ParsedRule] = None
    result: str = Field(..., description="PASS or FAIL or ERROR")
    message: Optional[str] = None
    invoice_id: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "rule_id": None,
                "rule_text": "Tax amount must be greater than 0",
                "parsed_rule": {
                    "rule_type": "numeric_comparison",
                    "field": "tax_amount",
                    "operation": "greater_than",
                    "value": 0
                },
                "result": "PASS",
                "message": "tax_amount = 180.0 is greater than 0",
                "invoice_id": "INV-001"
            }
        }
    }


class BatchSummary(BaseModel):
    """Summary statistics for a batch validation run."""
    total: int
    passed: int
    failed: int
    errors: int


class BatchValidationResponse(BaseModel):
    """Response for /validate/batch."""
    results: List[ValidationResult]
    summary: BatchSummary


class SavedRuleResponse(BaseModel):
    """A rule as stored in the database."""
    id: int
    rule_text: str
    parsed_json: Optional[dict] = None
    severity: str
    created_at: str


class InvoiceResponse(BaseModel):
    """A stored invoice record."""
    id: int
    filename: str
    uploaded_at: str
    validation_status: Optional[str] = None


class ResultRecord(BaseModel):
    """A single stored validation result record."""
    id: int
    invoice_id: int
    rule_id: int
    status: str
    message: Optional[str] = None


class DashboardStats(BaseModel):
    """Aggregated stats for the dashboard stat cards."""
    total_rules: int
    total_invoices: int
    total_validations: int
    total_passed: int
    total_failed: int
    pass_rate: float = Field(..., description="Percentage 0-100")
    total_xslt_files: Optional[int] = 0
    fail_rate: Optional[float] = 0.0


class TrendPoint(BaseModel):
    """A single data point for the trend chart."""
    date: str
    passed: int
    failed: int


class TrendResponse(BaseModel):
    """Trend data for the dashboard chart."""
    points: List[TrendPoint]


class HealthResponse(BaseModel):
    """System health check."""
    status: str
    version: str
    timestamp: str


class DatasetGenerateResponse(BaseModel):
    """Response after generating synthetic dataset."""
    message: str
    files_created: List[str]
    invoice_count: int


class DeleteResponse(BaseModel):
    """Generic delete confirmation."""
    message: str
    id: int


class UpdateRuleRequest(BaseModel):
    """Request to update rule text or severity."""
    rule_text: Optional[str] = None
    severity: Optional[str] = None


class UpdateValidationLogicRequest(BaseModel):
    """Request to update rule's generated validation logic directly."""
    xpath_logic: Optional[str] = None
    xslt_logic: Optional[str] = None
    python_logic: Optional[str] = None


class ParseRuleRequest(BaseModel):
    """Parse a natural language rule without saving it."""
    rule_text: str = Field(..., min_length=5, max_length=500, description="Natural language rule in plain English (max 500 chars)")

    @field_validator("rule_text")
    @classmethod
    def rule_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("rule_text cannot be blank")
        return v.strip()


class ParseRuleResponse(BaseModel):
    """Response from parsing a rule."""
    rule_text: str
    parsed_rule: ParsedRule
    parsed_rules: List[ParsedRule] = Field(default_factory=list)
    rule_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    xslt: str = Field(..., description="Generated XSLT validation logic")
    xpath: Optional[str] = None
    python_logic: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "rule_text": "Tax amount must be greater than 0",
                "parsed_rule": {
                    "rule_type": "numeric_comparison",
                    "field": "tax_amount",
                    "operation": "greater_than",
                    "value": 0,
                    "condition_field": None,
                    "condition_value": None,
                    "extra": None
                },
                "xslt": "<xsl:if test='//tax_amount &lt;= 0'>...</xsl:if>",
                "xpath": "//tax_amount > 0",
                "python_logic": "if tax_amount <= 0: raise ValidationError('Tax amount must be greater than 0')"
            }
        }
    }
