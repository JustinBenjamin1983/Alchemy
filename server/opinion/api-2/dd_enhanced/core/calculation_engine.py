"""
LexVerse Financial Calculation Engine
=====================================
A deterministic calculation engine for legal due diligence financial exposures.
Separates AI-driven formula identification from code-based arithmetic.

Version: 1.0
Author: LexVerse Development Team
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Callable
from enum import Enum
import json
import uuid
from abc import ABC, abstractmethod


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class FormulaCategory(Enum):
    PENALTY = "penalty"
    EMPLOYMENT = "employment"
    LEASE = "lease"
    DEBT = "debt"
    ENVIRONMENTAL = "environmental"
    REGULATORY = "regulatory"
    TRANSACTION = "transaction"
    TIERED = "tiered"
    TIME = "time"
    CUSTOM = "custom"


class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class CalculationStatus(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    MANUAL_REVIEW = "manual_review"


# Currency codes supported
SUPPORTED_CURRENCIES = ["ZAR", "USD", "EUR", "GBP", "AUD", "CAD", "CHF", "JPY", "CNY"]

# Default decimal precision
DECIMAL_PLACES = 2


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CalculationStep:
    """Represents a single step in the calculation audit trail."""
    step_number: int
    operation: str
    calculation: str
    result: Optional[Decimal] = None
    notes: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule_id: str
    severity: ValidationSeverity
    message: str
    passed: bool
    details: Optional[Dict] = None


@dataclass
class CalculationResult:
    """Complete result of a financial calculation."""
    extraction_id: str
    formula_id: str
    status: CalculationStatus
    result_value: Optional[Decimal]
    result_currency: str
    calculation_steps: List[CalculationStep]
    confidence_score: float
    validations: List[ValidationResult]
    warnings: List[str]
    errors: List[str]
    metadata: Dict = field(default_factory=dict)
    
    @property
    def validation_passed(self) -> bool:
        """Check if all validations passed without errors."""
        return not any(v.severity == ValidationSeverity.ERROR and not v.passed 
                      for v in self.validations)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "extraction_id": self.extraction_id,
            "formula_id": self.formula_id,
            "status": self.status.value,
            "result_value": str(self.result_value) if self.result_value else None,
            "result_currency": self.result_currency,
            "calculation_steps": [
                {
                    "step": s.step_number,
                    "operation": s.operation,
                    "calculation": s.calculation,
                    "result": str(s.result) if s.result else None,
                    "notes": s.notes
                }
                for s in self.calculation_steps
            ],
            "confidence_score": self.confidence_score,
            "validations": [
                {
                    "rule_id": v.rule_id,
                    "severity": v.severity.value,
                    "message": v.message,
                    "passed": v.passed
                }
                for v in self.validations
            ],
            "warnings": self.warnings,
            "errors": self.errors,
            "validation_passed": self.validation_passed,
            "metadata": self.metadata
        }


# =============================================================================
# VALIDATION RULES
# =============================================================================

class ValidationRules:
    """Validation rules for calculation results."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.transaction_value = Decimal(str(config.get("transaction_value", 0)))
        
        # Reasonableness bounds by formula category (as % of transaction value)
        self.bounds = {
            FormulaCategory.PENALTY: {"warn": Decimal("0.50"), "error": Decimal("1.50")},
            FormulaCategory.EMPLOYMENT: {"warn": Decimal("0.30"), "error": Decimal("1.00")},
            FormulaCategory.LEASE: {"warn": Decimal("0.75"), "error": Decimal("2.00")},
            FormulaCategory.ENVIRONMENTAL: {"warn": Decimal("0.60"), "error": Decimal("1.50")},
            FormulaCategory.REGULATORY: {"warn": Decimal("0.20"), "error": Decimal("0.50")},
            FormulaCategory.DEBT: {"warn": Decimal("1.00"), "error": Decimal("2.00")},
            FormulaCategory.TRANSACTION: {"warn": Decimal("0.50"), "error": Decimal("1.00")},
        }
    
    def validate(self, result: Decimal, extraction: Dict, formula_id: str) -> List[ValidationResult]:
        """Run all validation rules against a calculation result."""
        validations = []
        
        # VAL_001: Transaction value ratio warning
        if self.transaction_value > 0 and result:
            ratio = result / self.transaction_value
            if ratio > Decimal("0.50"):
                validations.append(ValidationResult(
                    rule_id="VAL_001",
                    severity=ValidationSeverity.WARNING,
                    message=f"Single exposure is {ratio:.1%} of transaction value",
                    passed=True,  # Warning, not failure
                    details={"ratio": float(ratio)}
                ))
        
        # VAL_002: Transaction value breach
        if self.transaction_value > 0 and result:
            if result > self.transaction_value:
                validations.append(ValidationResult(
                    rule_id="VAL_002",
                    severity=ValidationSeverity.ERROR,
                    message=f"Exposure ({result:,.2f}) exceeds transaction value ({self.transaction_value:,.2f})",
                    passed=False,
                    details={"exposure": float(result), "transaction_value": float(self.transaction_value)}
                ))
        
        # VAL_003: Negative result
        if result is not None and result < 0:
            validations.append(ValidationResult(
                rule_id="VAL_003",
                severity=ValidationSeverity.ERROR,
                message="Calculated exposure is negative",
                passed=False,
                details={"result": float(result)}
            ))
        
        # VAL_004: Zero result
        if result is not None and result == 0:
            validations.append(ValidationResult(
                rule_id="VAL_004",
                severity=ValidationSeverity.WARNING,
                message="Calculated exposure is exactly zero - verify this is correct",
                passed=True
            ))
        
        # VAL_005: Unit consistency (check extraction variables)
        unit_issues = self._check_unit_consistency(extraction)
        if unit_issues:
            validations.append(ValidationResult(
                rule_id="VAL_005",
                severity=ValidationSeverity.ERROR,
                message=f"Unit inconsistency detected: {unit_issues}",
                passed=False
            ))
        
        # VAL_007: Percentage bounds
        percentage_vars = [v for v in extraction.get("variables", {}).get("primary", [])
                         if v.get("unit") == "percent"]
        for pv in percentage_vars:
            val = pv.get("value", 0)
            if val < 0 or val > 100:
                validations.append(ValidationResult(
                    rule_id="VAL_007",
                    severity=ValidationSeverity.WARNING,
                    message=f"Percentage value {val} outside 0-100 range for {pv.get('name')}",
                    passed=True
                ))
        
        return validations
    
    def _check_unit_consistency(self, extraction: Dict) -> Optional[str]:
        """Check for unit consistency issues in extraction."""
        variables = extraction.get("variables", {}).get("primary", [])
        
        # Check for mixed currency units
        currencies = set()
        for v in variables:
            unit = v.get("unit", "")
            if unit in SUPPORTED_CURRENCIES:
                currencies.add(unit)
        
        if len(currencies) > 1:
            return f"Mixed currencies detected: {', '.join(currencies)}"
        
        return None


# =============================================================================
# BASE FORMULA CLASS
# =============================================================================

class BaseFormula(ABC):
    """Abstract base class for all formula implementations."""
    
    formula_id: str
    category: FormulaCategory
    description: str
    required_variables: List[str]
    
    @abstractmethod
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        """Execute the calculation and return steps with result."""
        pass
    
    def validate_inputs(self, variables: Dict) -> List[str]:
        """Validate that all required variables are present."""
        missing = []
        primary_vars = {v["name"]: v for v in variables.get("primary", [])}
        
        for req in self.required_variables:
            if req not in primary_vars:
                missing.append(req)
            elif primary_vars[req].get("value") is None:
                missing.append(f"{req} (null value)")
        
        return missing
    
    def get_variable(self, variables: Dict, name: str) -> Decimal:
        """Safely extract a variable value as Decimal."""
        primary_vars = {v["name"]: v for v in variables.get("primary", [])}
        if name in primary_vars:
            val = primary_vars[name].get("value")
            if val is not None:
                return Decimal(str(val))
        raise ValueError(f"Variable '{name}' not found or null")


# =============================================================================
# PENALTY FORMULAS (PEN_*)
# =============================================================================

class PEN001VolumeRatePeriod(BaseFormula):
    """Volume × Rate × Period calculation (e.g., liquidated damages)."""
    
    formula_id = "PEN_001"
    category = FormulaCategory.PENALTY
    description = "Volume × Rate × Period Factor"
    required_variables = ["volume", "rate", "period"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        volume = self.get_variable(variables, "volume")
        rate = self.get_variable(variables, "rate")
        period_months = self.get_variable(variables, "period")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"volume={volume:,.0f}, rate={rate:,.2f}, period_months={period_months}"
        ))
        
        # Calculate period factor (convert months to years)
        period_factor = period_months / Decimal("12")
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate period factor",
            calculation=f"{period_months} ÷ 12 = {period_factor:.4f}",
            result=period_factor
        ))
        
        # Calculate annual value
        annual_value = volume * rate
        steps.append(CalculationStep(
            step_number=3,
            operation="Calculate annual value",
            calculation=f"{volume:,.0f} × {rate:,.2f} = {annual_value:,.2f}",
            result=annual_value
        ))
        
        # Calculate total exposure
        result = annual_value * period_factor
        steps.append(CalculationStep(
            step_number=4,
            operation="Calculate total exposure",
            calculation=f"{annual_value:,.2f} × {period_factor:.4f} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PEN002DailyPenalty(BaseFormula):
    """Daily rate × Days calculation."""
    
    formula_id = "PEN_002"
    category = FormulaCategory.PENALTY
    description = "Daily Rate × Days Count"
    required_variables = ["daily_rate", "days"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        daily_rate = self.get_variable(variables, "daily_rate")
        days = self.get_variable(variables, "days")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"daily_rate={daily_rate:,.2f}, days={days:,.0f}"
        ))
        
        result = daily_rate * days
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate total penalty",
            calculation=f"{daily_rate:,.2f} × {days:,.0f} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PEN003MultipliedDamages(BaseFormula):
    """Base amount × Multiplier (double/treble damages)."""
    
    formula_id = "PEN_003"
    category = FormulaCategory.PENALTY
    description = "Base Amount × Multiplier"
    required_variables = ["base_amount", "multiplier"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        base_amount = self.get_variable(variables, "base_amount")
        multiplier = self.get_variable(variables, "multiplier")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"base_amount={base_amount:,.2f}, multiplier={multiplier}"
        ))
        
        result = base_amount * multiplier
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate multiplied damages",
            calculation=f"{base_amount:,.2f} × {multiplier} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PEN004PercentageOfContract(BaseFormula):
    """Contract value × Percentage."""
    
    formula_id = "PEN_004"
    category = FormulaCategory.PENALTY
    description = "Contract Value × Percentage"
    required_variables = ["contract_value", "percentage"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        contract_value = self.get_variable(variables, "contract_value")
        percentage = self.get_variable(variables, "percentage")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"contract_value={contract_value:,.2f}, percentage={percentage}%"
        ))
        
        pct_decimal = percentage / Decimal("100")
        result = contract_value * pct_decimal
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate percentage penalty",
            calculation=f"{contract_value:,.2f} × {percentage}% = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PEN005CappedPenalty(BaseFormula):
    """min(cap, calculated_penalty)."""
    
    formula_id = "PEN_005"
    category = FormulaCategory.PENALTY
    description = "Capped Penalty"
    required_variables = ["calculated_penalty", "cap_amount"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        calculated = self.get_variable(variables, "calculated_penalty")
        cap = self.get_variable(variables, "cap_amount")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"calculated_penalty={calculated:,.2f}, cap_amount={cap:,.2f}"
        ))
        
        result = min(cap, calculated)
        cap_applied = "YES" if calculated > cap else "NO"
        steps.append(CalculationStep(
            step_number=2,
            operation="Apply cap",
            calculation=f"min({cap:,.2f}, {calculated:,.2f}) = {result:,.2f}",
            result=result,
            notes=f"Cap applied: {cap_applied}"
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# EMPLOYMENT FORMULAS (EMP_*)
# =============================================================================

class EMP001MonthsSalary(BaseFormula):
    """Monthly salary × Months (notice period, severance)."""
    
    formula_id = "EMP_001"
    category = FormulaCategory.EMPLOYMENT
    description = "Monthly Salary × Months"
    required_variables = ["monthly_salary", "months"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        monthly_salary = self.get_variable(variables, "monthly_salary")
        months = self.get_variable(variables, "months")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"monthly_salary={monthly_salary:,.2f}, months={months}"
        ))
        
        result = monthly_salary * months
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate severance",
            calculation=f"{monthly_salary:,.2f} × {months} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class EMP002TotalRemuneration(BaseFormula):
    """(Base salary + Benefits) × Months."""
    
    formula_id = "EMP_002"
    category = FormulaCategory.EMPLOYMENT
    description = "(Base + Benefits) × Months"
    required_variables = ["base_salary", "benefits", "months"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        base = self.get_variable(variables, "base_salary")
        benefits = self.get_variable(variables, "benefits")
        months = self.get_variable(variables, "months")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"base_salary={base:,.2f}, benefits={benefits:,.2f}, months={months}"
        ))
        
        total_monthly = base + benefits
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate total monthly remuneration",
            calculation=f"{base:,.2f} + {benefits:,.2f} = {total_monthly:,.2f}",
            result=total_monthly
        ))
        
        result = total_monthly * months
        steps.append(CalculationStep(
            step_number=3,
            operation="Calculate total severance",
            calculation=f"{total_monthly:,.2f} × {months} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class EMP004ChangeOfControl(BaseFormula):
    """Change of Control severance package calculation."""
    
    formula_id = "EMP_004"
    category = FormulaCategory.EMPLOYMENT
    description = "CoC Severance: (Base × Months) + Bonus + Medical + Outplacement"
    required_variables = ["base_monthly", "severance_months", "bonus", "medical", "outplacement"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        base = self.get_variable(variables, "base_monthly")
        months = self.get_variable(variables, "severance_months")
        bonus = self.get_variable(variables, "bonus")
        medical = self.get_variable(variables, "medical")
        outplacement = self.get_variable(variables, "outplacement")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"base={base:,.2f}/mo, months={months}, bonus={bonus:,.2f}, medical={medical:,.2f}, outplacement={outplacement:,.2f}"
        ))
        
        base_severance = base * months
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate base severance",
            calculation=f"{base:,.2f} × {months} = {base_severance:,.2f}",
            result=base_severance
        ))
        
        result = base_severance + bonus + medical + outplacement
        steps.append(CalculationStep(
            step_number=3,
            operation="Calculate total CoC package",
            calculation=f"{base_severance:,.2f} + {bonus:,.2f} + {medical:,.2f} + {outplacement:,.2f} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class EMP005LTIAcceleration(BaseFormula):
    """Unvested units × Unit value."""
    
    formula_id = "EMP_005"
    category = FormulaCategory.EMPLOYMENT
    description = "LTI Acceleration: Unvested Units × Unit Value"
    required_variables = ["unvested_units", "unit_value"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        units = self.get_variable(variables, "unvested_units")
        value = self.get_variable(variables, "unit_value")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"unvested_units={units:,.0f}, unit_value={value:,.2f}"
        ))
        
        result = units * value
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate LTI acceleration value",
            calculation=f"{units:,.0f} × {value:,.2f} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# LEASE FORMULAS (LSE_*)
# =============================================================================

class LSE001RemainingObligation(BaseFormula):
    """Monthly rent × Remaining months."""
    
    formula_id = "LSE_001"
    category = FormulaCategory.LEASE
    description = "Monthly Rent × Remaining Months"
    required_variables = ["monthly_rent", "remaining_months"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        rent = self.get_variable(variables, "monthly_rent")
        months = self.get_variable(variables, "remaining_months")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"monthly_rent={rent:,.2f}, remaining_months={months}"
        ))
        
        result = rent * months
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate remaining obligation",
            calculation=f"{rent:,.2f} × {months} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class LSE003ProductionRoyalty(BaseFormula):
    """Production × Rate per unit."""
    
    formula_id = "LSE_003"
    category = FormulaCategory.LEASE
    description = "Production × Rate per Unit"
    required_variables = ["production", "rate_per_unit"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        production = self.get_variable(variables, "production")
        rate = self.get_variable(variables, "rate_per_unit")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"production={production:,.0f}, rate_per_unit={rate:,.2f}"
        ))
        
        result = production * rate
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate royalty",
            calculation=f"{production:,.0f} × {rate:,.2f} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# ENVIRONMENTAL FORMULAS (ENV_*)
# =============================================================================

class ENV001RehabProvision(BaseFormula):
    """Disturbed area × Rate per hectare."""
    
    formula_id = "ENV_001"
    category = FormulaCategory.ENVIRONMENTAL
    description = "Disturbed Area × Rate per Hectare"
    required_variables = ["disturbed_area", "rate_per_hectare"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        area = self.get_variable(variables, "disturbed_area")
        rate = self.get_variable(variables, "rate_per_hectare")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"disturbed_area={area:,.2f} ha, rate_per_hectare={rate:,.2f}"
        ))
        
        result = area * rate
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate rehabilitation provision",
            calculation=f"{area:,.2f} × {rate:,.2f} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ENV002ProvisionShortfall(BaseFormula):
    """Required provision - Actual provision."""
    
    formula_id = "ENV_002"
    category = FormulaCategory.ENVIRONMENTAL
    description = "Required Provision - Actual Provision"
    required_variables = ["required_provision", "actual_provision"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        required = self.get_variable(variables, "required_provision")
        actual = self.get_variable(variables, "actual_provision")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"required_provision={required:,.2f}, actual_provision={actual:,.2f}"
        ))
        
        result = required - actual
        status = "SHORTFALL" if result > 0 else "ADEQUATE"
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate shortfall",
            calculation=f"{required:,.2f} - {actual:,.2f} = {result:,.2f}",
            result=result,
            notes=f"Status: {status}"
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ENV004AggregateGuarantees(BaseFormula):
    """Sum of all environmental guarantees."""
    
    formula_id = "ENV_004"
    category = FormulaCategory.ENVIRONMENTAL
    description = "Aggregate Environmental Guarantees"
    required_variables = ["guarantees"]  # expects list
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        # Get guarantees from variables - may be in primary or as special list
        primary_vars = {v["name"]: v for v in variables.get("primary", [])}
        guarantees_var = primary_vars.get("guarantees", {})
        guarantee_values = guarantees_var.get("value", [])
        
        if not isinstance(guarantee_values, list):
            guarantee_values = [guarantee_values]
        
        guarantee_decimals = [Decimal(str(g)) for g in guarantee_values]
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify guarantee amounts",
            calculation=f"guarantees={[float(g) for g in guarantee_decimals]}"
        ))
        
        result = sum(guarantee_decimals)
        calc_str = " + ".join([f"{g:,.2f}" for g in guarantee_decimals])
        steps.append(CalculationStep(
            step_number=2,
            operation="Sum guarantees",
            calculation=f"{calc_str} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# TRANSACTION FORMULAS (TXN_*)
# =============================================================================

class TXN001BreakFee(BaseFormula):
    """Purchase price × Break fee percentage."""
    
    formula_id = "TXN_001"
    category = FormulaCategory.TRANSACTION
    description = "Purchase Price × Break Fee Percentage"
    required_variables = ["purchase_price", "break_fee_percentage"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        price = self.get_variable(variables, "purchase_price")
        pct = self.get_variable(variables, "break_fee_percentage")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"purchase_price={price:,.2f}, break_fee_percentage={pct}%"
        ))
        
        result = price * (pct / Decimal("100"))
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate break fee",
            calculation=f"{price:,.2f} × {pct}% = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class TXN005Escrow(BaseFormula):
    """Purchase price × Escrow percentage."""
    
    formula_id = "TXN_005"
    category = FormulaCategory.TRANSACTION
    description = "Purchase Price × Escrow Percentage"
    required_variables = ["purchase_price", "escrow_percentage"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        price = self.get_variable(variables, "purchase_price")
        pct = self.get_variable(variables, "escrow_percentage")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"purchase_price={price:,.2f}, escrow_percentage={pct}%"
        ))
        
        result = price * (pct / Decimal("100"))
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate escrow amount",
            calculation=f"{price:,.2f} × {pct}% = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# DEBT FORMULAS (DBT_*)
# =============================================================================

class DBT001PrepaymentPenalty(BaseFormula):
    """Principal × Prepayment penalty rate."""
    
    formula_id = "DBT_001"
    category = FormulaCategory.DEBT
    description = "Principal × Prepayment Penalty Rate"
    required_variables = ["principal", "penalty_rate"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        principal = self.get_variable(variables, "principal")
        rate = self.get_variable(variables, "penalty_rate")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"principal={principal:,.2f}, penalty_rate={rate}%"
        ))
        
        result = principal * (rate / Decimal("100"))
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate prepayment penalty",
            calculation=f"{principal:,.2f} × {rate}% = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class DBT002AccruedInterest(BaseFormula):
    """Outstanding × Interest rate × (Days/365)."""
    
    formula_id = "DBT_002"
    category = FormulaCategory.DEBT
    description = "Outstanding × Rate × (Days/365)"
    required_variables = ["outstanding", "interest_rate", "days"]
    
    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []
        
        outstanding = self.get_variable(variables, "outstanding")
        rate = self.get_variable(variables, "interest_rate")
        days = self.get_variable(variables, "days")
        
        steps.append(CalculationStep(
            step_number=1,
            operation="Identify variables",
            calculation=f"outstanding={outstanding:,.2f}, interest_rate={rate}%, days={days}"
        ))
        
        day_factor = days / Decimal("365")
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate day factor",
            calculation=f"{days} ÷ 365 = {day_factor:.6f}",
            result=day_factor
        ))
        
        result = outstanding * (rate / Decimal("100")) * day_factor
        steps.append(CalculationStep(
            step_number=3,
            operation="Calculate accrued interest",
            calculation=f"{outstanding:,.2f} × {rate}% × {day_factor:.6f} = {result:,.2f}",
            result=result
        ))
        
        return steps, result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# REGULATORY FORMULAS (REG_*)
# =============================================================================

class REG001BEEDilution(BaseFormula):
    """
    BEE Shareholding Dilution Calculator.

    Calculates how new equity injection affects BEE ownership percentage.
    Critical for South African transactions where BEE thresholds (typically 26%)
    must be maintained for regulatory compliance and contract eligibility.

    Formula: New BEE % = (Current BEE Shares) / (Total Shares + New Shares)
    Where: New Shares = Equity Injection / Share Price (or implied price)
    """

    formula_id = "REG_001"
    category = FormulaCategory.REGULATORY
    description = "BEE Shareholding Dilution Impact"
    required_variables = ["current_bee_percentage", "equity_injection", "current_company_value"]

    # Standard BEE thresholds in South Africa
    BEE_THRESHOLDS = {
        "generic": Decimal("26"),      # Generic Codes requirement
        "mining": Decimal("30"),        # Mining Charter requirement
        "financial": Decimal("25"),     # Financial sector
        "ict": Decimal("30"),           # ICT sector
    }

    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []

        current_bee_pct = self.get_variable(variables, "current_bee_percentage")
        equity_injection = self.get_variable(variables, "equity_injection")
        current_value = self.get_variable(variables, "current_company_value")

        # Optional: sector-specific threshold
        sector = "generic"
        primary_vars = {v["name"]: v for v in variables.get("primary", [])}
        if "sector" in primary_vars and primary_vars["sector"].get("value"):
            sector = str(primary_vars["sector"]["value"]).lower()

        threshold = self.BEE_THRESHOLDS.get(sector, Decimal("26"))

        steps.append(CalculationStep(
            step_number=1,
            operation="Identify current shareholding",
            calculation=f"Current BEE ownership: {current_bee_pct}%, Company value: R{current_value:,.0f}",
            notes=f"BEE threshold for {sector} sector: {threshold}%"
        ))

        # Calculate implied BEE shareholding value
        bee_value = current_value * (current_bee_pct / Decimal("100"))
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate BEE shareholding value",
            calculation=f"R{current_value:,.0f} × {current_bee_pct}% = R{bee_value:,.0f}",
            result=bee_value
        ))

        # Calculate post-injection company value
        post_injection_value = current_value + equity_injection
        steps.append(CalculationStep(
            step_number=3,
            operation="Calculate post-injection company value",
            calculation=f"R{current_value:,.0f} + R{equity_injection:,.0f} = R{post_injection_value:,.0f}",
            result=post_injection_value
        ))

        # Calculate new BEE percentage (assuming BEE doesn't participate in new equity)
        new_bee_pct = (bee_value / post_injection_value) * Decimal("100")
        steps.append(CalculationStep(
            step_number=4,
            operation="Calculate diluted BEE percentage",
            calculation=f"R{bee_value:,.0f} ÷ R{post_injection_value:,.0f} × 100 = {new_bee_pct:.2f}%",
            result=new_bee_pct,
            notes="Assumes BEE shareholders do not participate pro-rata in new equity"
        ))

        # Calculate dilution impact
        dilution = current_bee_pct - new_bee_pct
        steps.append(CalculationStep(
            step_number=5,
            operation="Calculate dilution impact",
            calculation=f"{current_bee_pct}% - {new_bee_pct:.2f}% = {dilution:.2f}% dilution",
            result=dilution
        ))

        # Check if falls below threshold
        breach_amount = threshold - new_bee_pct if new_bee_pct < threshold else Decimal("0")
        if breach_amount > 0:
            steps.append(CalculationStep(
                step_number=6,
                operation="⚠️ THRESHOLD BREACH",
                calculation=f"New BEE % ({new_bee_pct:.2f}%) is {breach_amount:.2f}% below {threshold}% threshold",
                result=breach_amount,
                notes="CRITICAL: Transaction would breach BEE compliance threshold"
            ))
        else:
            steps.append(CalculationStep(
                step_number=6,
                operation="Threshold check",
                calculation=f"New BEE % ({new_bee_pct:.2f}%) remains above {threshold}% threshold",
                result=Decimal("0"),
                notes="BEE compliance maintained post-transaction"
            ))

        return steps, new_bee_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class REG002CovenantCompliance(BaseFormula):
    """
    Financial Covenant Compliance Calculator.

    Calculates whether financial ratios meet covenant requirements.
    Common ratios: Interest Cover, Debt/EBITDA, Current Ratio, etc.
    """

    formula_id = "REG_002"
    category = FormulaCategory.REGULATORY
    description = "Financial Covenant Compliance Check"
    required_variables = ["actual_ratio", "covenant_threshold", "covenant_type"]

    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []

        actual = self.get_variable(variables, "actual_ratio")
        threshold = self.get_variable(variables, "covenant_threshold")

        # Get covenant type (min or max)
        primary_vars = {v["name"]: v for v in variables.get("primary", [])}
        covenant_type = "minimum"  # default
        if "covenant_type" in primary_vars:
            covenant_type = str(primary_vars["covenant_type"].get("value", "minimum")).lower()

        steps.append(CalculationStep(
            step_number=1,
            operation="Identify covenant parameters",
            calculation=f"Actual ratio: {actual:.2f}x, Covenant: {covenant_type} {threshold:.2f}x"
        ))

        # Calculate headroom/breach
        if covenant_type == "minimum":
            headroom = actual - threshold
            breach = headroom < 0
        else:  # maximum
            headroom = threshold - actual
            breach = headroom < 0

        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate covenant headroom",
            calculation=f"Headroom: {abs(headroom):.2f}x {'BREACH' if breach else 'cushion'}",
            result=headroom
        ))

        # Calculate percentage headroom
        pct_headroom = (headroom / threshold) * Decimal("100") if threshold != 0 else Decimal("0")
        steps.append(CalculationStep(
            step_number=3,
            operation="Calculate percentage headroom",
            calculation=f"{headroom:.2f} ÷ {threshold:.2f} × 100 = {pct_headroom:.1f}%",
            result=pct_headroom,
            notes="BREACH" if breach else ("WARNING: <10% headroom" if abs(pct_headroom) < 10 else "Compliant")
        ))

        return steps, headroom.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class REG003DocumentExpiry(BaseFormula):
    """
    Document/Certificate Expiry Calculator.

    Calculates days until expiry and flags expired or expiring documents.
    Critical for: Tax clearances, BEE certificates, licenses, permits.
    """

    formula_id = "REG_003"
    category = FormulaCategory.REGULATORY
    description = "Document Expiry Check"
    required_variables = ["expiry_date", "warning_days"]

    def calculate(self, variables: Dict) -> Tuple[List[CalculationStep], Decimal]:
        steps = []

        # Get expiry date
        primary_vars = {v["name"]: v for v in variables.get("primary", [])}
        expiry_str = primary_vars.get("expiry_date", {}).get("value", "")
        warning_days = self.get_variable(variables, "warning_days")

        today = date.today()

        # Parse expiry date
        try:
            if isinstance(expiry_str, str):
                # Try common formats
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
                    try:
                        expiry_date = datetime.strptime(expiry_str, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f"Could not parse date: {expiry_str}")
            else:
                expiry_date = expiry_str
        except Exception as e:
            steps.append(CalculationStep(
                step_number=1,
                operation="Date parsing error",
                calculation=f"Could not parse expiry date: {expiry_str}",
                notes=str(e)
            ))
            return steps, Decimal("-999")  # Error indicator

        steps.append(CalculationStep(
            step_number=1,
            operation="Identify dates",
            calculation=f"Today: {today}, Expiry: {expiry_date}"
        ))

        # Calculate days until expiry
        days_until = (expiry_date - today).days
        steps.append(CalculationStep(
            step_number=2,
            operation="Calculate days until expiry",
            calculation=f"{expiry_date} - {today} = {days_until} days",
            result=Decimal(str(days_until))
        ))

        # Determine status
        if days_until < 0:
            status = f"⚠️ EXPIRED {abs(days_until)} days ago"
            severity = "CRITICAL"
        elif days_until <= int(warning_days):
            status = f"⚠️ EXPIRING in {days_until} days"
            severity = "WARNING"
        else:
            status = f"Valid for {days_until} days"
            severity = "OK"

        steps.append(CalculationStep(
            step_number=3,
            operation="Expiry status",
            calculation=status,
            result=Decimal(str(days_until)),
            notes=severity
        ))

        return steps, Decimal(str(days_until))


# =============================================================================
# MAIN CALCULATION ENGINE
# =============================================================================

class CalculationEngine:
    """Main calculation engine that processes extractions and returns results."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.validators = ValidationRules(config)
        self.formula_registry = self._build_formula_registry()
    
    def _build_formula_registry(self) -> Dict[str, BaseFormula]:
        """Build registry of all available formulas."""
        formulas = [
            # Penalty formulas
            PEN001VolumeRatePeriod(),
            PEN002DailyPenalty(),
            PEN003MultipliedDamages(),
            PEN004PercentageOfContract(),
            PEN005CappedPenalty(),
            # Employment formulas
            EMP001MonthsSalary(),
            EMP002TotalRemuneration(),
            EMP004ChangeOfControl(),
            EMP005LTIAcceleration(),
            # Lease formulas
            LSE001RemainingObligation(),
            LSE003ProductionRoyalty(),
            # Environmental formulas
            ENV001RehabProvision(),
            ENV002ProvisionShortfall(),
            ENV004AggregateGuarantees(),
            # Transaction formulas
            TXN001BreakFee(),
            TXN005Escrow(),
            # Debt formulas
            DBT001PrepaymentPenalty(),
            DBT002AccruedInterest(),
            # Regulatory formulas
            REG001BEEDilution(),
            REG002CovenantCompliance(),
            REG003DocumentExpiry(),
        ]

        return {f.formula_id: f for f in formulas}
    
    def calculate(self, extraction: Dict) -> CalculationResult:
        """
        Process an extraction and return a calculation result.
        
        Args:
            extraction: Structured extraction JSON from the AI
            
        Returns:
            CalculationResult with value, steps, and validation
        """
        extraction_id = extraction.get("extraction_id", str(uuid.uuid4()))
        formula_id = extraction.get("formula_classification", {}).get("formula_id", "UNKNOWN")
        confidence = extraction.get("formula_classification", {}).get("confidence", 0.0)
        currency = extraction.get("currency", {}).get("primary", "ZAR")
        
        errors = []
        warnings = []
        steps = []
        result_value = None
        status = CalculationStatus.SUCCESS
        
        # Get formula implementation
        formula = self.formula_registry.get(formula_id)
        
        if not formula:
            # Handle unknown formula
            errors.append(f"Unknown formula ID: {formula_id}")
            status = CalculationStatus.MANUAL_REVIEW
            
            return CalculationResult(
                extraction_id=extraction_id,
                formula_id=formula_id,
                status=status,
                result_value=None,
                result_currency=currency,
                calculation_steps=[],
                confidence_score=confidence,
                validations=[],
                warnings=warnings,
                errors=errors,
                metadata={"requires_manual_review": True}
            )
        
        # Validate inputs
        variables = extraction.get("variables", {})
        missing = formula.validate_inputs(variables)
        
        if missing:
            errors.append(f"Missing required variables: {', '.join(missing)}")
            status = CalculationStatus.ERROR
            
            return CalculationResult(
                extraction_id=extraction_id,
                formula_id=formula_id,
                status=status,
                result_value=None,
                result_currency=currency,
                calculation_steps=[],
                confidence_score=confidence,
                validations=[],
                warnings=warnings,
                errors=errors
            )
        
        # Execute calculation
        try:
            steps, result_value = formula.calculate(variables)
        except Exception as e:
            errors.append(f"Calculation error: {str(e)}")
            status = CalculationStatus.ERROR
            
            return CalculationResult(
                extraction_id=extraction_id,
                formula_id=formula_id,
                status=status,
                result_value=None,
                result_currency=currency,
                calculation_steps=steps,
                confidence_score=confidence,
                validations=[],
                warnings=warnings,
                errors=errors
            )
        
        # Apply modifiers (caps, floors, escalation)
        result_value, modifier_steps = self._apply_modifiers(result_value, extraction)
        steps.extend(modifier_steps)
        
        # Run validation
        validations = self.validators.validate(result_value, extraction, formula_id)
        
        # Check for validation errors
        if any(v.severity == ValidationSeverity.ERROR and not v.passed for v in validations):
            status = CalculationStatus.WARNING
            warnings.append("Calculation completed but validation warnings exist")
        
        # Add any validation warnings to warnings list
        for v in validations:
            if v.severity == ValidationSeverity.WARNING:
                warnings.append(v.message)
        
        return CalculationResult(
            extraction_id=extraction_id,
            formula_id=formula_id,
            status=status,
            result_value=result_value,
            result_currency=currency,
            calculation_steps=steps,
            confidence_score=confidence,
            validations=validations,
            warnings=warnings,
            errors=errors,
            metadata={
                "formula_description": formula.description,
                "formula_category": formula.category.value
            }
        )
    
    def _apply_modifiers(self, result: Decimal, extraction: Dict) -> Tuple[Decimal, List[CalculationStep]]:
        """Apply any calculation modifiers (caps, floors, escalation)."""
        steps = []
        modifiers = extraction.get("calculation_modifiers", {})
        
        # Apply cap if exists
        cap = modifiers.get("cap", {})
        if cap.get("exists") and cap.get("amount") is not None:
            cap_amount = Decimal(str(cap["amount"]))
            if result > cap_amount:
                steps.append(CalculationStep(
                    step_number=len(steps) + 100,  # Modifier steps start at 100
                    operation="Apply cap",
                    calculation=f"min({result:,.2f}, {cap_amount:,.2f}) = {cap_amount:,.2f}",
                    result=cap_amount,
                    notes=f"Cap applied from: {cap.get('source', 'unspecified')}"
                ))
                result = cap_amount
        
        # Apply floor if exists
        floor = modifiers.get("floor", {})
        if floor.get("exists") and floor.get("amount") is not None:
            floor_amount = Decimal(str(floor["amount"]))
            if result < floor_amount:
                steps.append(CalculationStep(
                    step_number=len(steps) + 100,
                    operation="Apply floor",
                    calculation=f"max({result:,.2f}, {floor_amount:,.2f}) = {floor_amount:,.2f}",
                    result=floor_amount,
                    notes=f"Floor applied from: {floor.get('source', 'unspecified')}"
                ))
                result = floor_amount
        
        return result, steps
    
    def get_available_formulas(self) -> List[Dict]:
        """Return list of available formula descriptions."""
        return [
            {
                "formula_id": f.formula_id,
                "category": f.category.value,
                "description": f.description,
                "required_variables": f.required_variables
            }
            for f in self.formula_registry.values()
        ]


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Karoo Mining Eskom Coal Supply Agreement liquidated damages
    
    extraction = {
        "extraction_id": "eskom-coc-ld-001",
        "document_source": {
            "document_id": "doc-009",
            "document_name": "Karro-Eskom_COAL_SUPPLY_AGREEMENT.docx",
            "section_reference": "Clause 5.1(c)",
            "extracted_text": "Supplier must pay liquidated damages equal to 24 months of average monthly contract value"
        },
        "formula_classification": {
            "formula_id": "PEN_001",
            "formula_category": "penalty",
            "confidence": 0.92
        },
        "variables": {
            "primary": [
                {
                    "name": "volume",
                    "value": 500000,
                    "unit": "tonnes",
                    "source": "500,000 tonnes of coal per annum",
                    "source_location": "Clause 1.1",
                    "confidence": 0.98
                },
                {
                    "name": "rate",
                    "value": 927,
                    "unit": "ZAR",
                    "source": "R927 per tonne",
                    "source_location": "Clause 2.3",
                    "confidence": 0.95
                },
                {
                    "name": "period",
                    "value": 24,
                    "unit": "months",
                    "source": "24 months of average monthly contract value",
                    "source_location": "Clause 5.1(c)",
                    "confidence": 0.99
                }
            ]
        },
        "currency": {
            "primary": "ZAR",
            "conversion_required": False
        },
        "calculation_modifiers": {
            "cap": {"exists": False},
            "floor": {"exists": False}
        }
    }
    
    # Initialize engine with transaction context
    engine = CalculationEngine(config={"transaction_value": 850000000})
    
    # Calculate
    result = engine.calculate(extraction)
    
    # Print result
    print("\n" + "="*80)
    print("CALCULATION RESULT")
    print("="*80)
    print(f"Formula: {result.formula_id} - {result.metadata.get('formula_description', '')}")
    print(f"Result: {result.result_currency} {result.result_value:,.2f}")
    print(f"Status: {result.status.value}")
    print(f"Confidence: {result.confidence_score:.0%}")
    print(f"Validation Passed: {result.validation_passed}")
    
    print("\nCalculation Steps:")
    for step in result.calculation_steps:
        print(f"  Step {step.step_number}: {step.operation}")
        print(f"          {step.calculation}")
        if step.notes:
            print(f"          Note: {step.notes}")
    
    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  ⚠️  {w}")
    
    if result.errors:
        print("\nErrors:")
        for e in result.errors:
            print(f"  ❌ {e}")
    
    print("\n" + "="*80)
