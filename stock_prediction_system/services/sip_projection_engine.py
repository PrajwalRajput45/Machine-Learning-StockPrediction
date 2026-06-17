"""
SIP Projection Engine

Provides financial calculations for SIP investments:
- Simple SIP future value
- Step-up SIP calculations
- Projected returns
- Maturity value estimation

Used by SIP management system for Groww-style projections.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SIPProjection:
    """SIP projection result dataclass."""
    total_invested: float
    estimated_returns: float
    maturity_value: float
    cagr: float
    yearly_projections: List[Dict[str, Any]]
    monthly_breakdown: List[Dict[str, Any]]


def calculate_future_value(
    principal: float,
    monthly_contribution: float,
    annual_rate: float,
    months: int,
    step_up_pct: float = 0.0
) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    Calculate future value of SIP with optional annual step-up.

    Args:
        principal: Initial investment (₹)
        monthly_contribution: Monthly SIP amount (₹)
        annual_rate: Expected annual return rate (%)
        months: Duration in months
        step_up_pct: Annual step-up percentage (0-20%)

    Returns:
        Tuple of (total_invested, maturity_value, yearly_breakdown)
    """
    monthly_rate = annual_rate / 100 / 12
    total_invested = principal
    current_value = principal
    yearly_projections = []

    current_contribution = monthly_contribution
    year = 1

    for month in range(1, months + 1):
        # Apply monthly contribution
        current_value += current_contribution

        # Apply growth
        current_value *= (1 + monthly_rate)

        # Accumulate total invested
        total_invested += current_contribution

        # Year-end snapshot (every 12 months)
        if month % 12 == 0:
            yearly_projections.append({
                'year': year,
                'year_end_value': round(current_value, 2),
                'total_invested': round(total_invested, 2),
                'estimated_gain': round(current_value - total_invested, 2),
                'monthly_sip': round(current_contribution, 2)
            })

            # Apply step-up for next year
            if step_up_pct > 0:
                current_contribution *= (1 + step_up_pct / 100)
            year += 1

    # Calculate estimated returns
    estimated_returns = current_value - total_invested

    return total_invested, current_value, yearly_projections


def calculate_step_up_sip(
    base_amount: float,
    duration_months: int,
    annual_rate: float,
    step_up_pct: float = 0.0
) -> SIPProjection:
    """
    Calculate step-up SIP projection.

    Year 1 → base_amount/month
    Year 2 → base_amount * (1 + step_up_pct/100)/month
    etc.

    Args:
        base_amount: Starting monthly SIP amount (₹)
        duration_months: Duration in months
        annual_rate: Expected annual return rate (%)
        step_up_pct: Annual step-up percentage (0-20%)

    Returns:
        SIPProjection with full breakdown
    """
    monthly_rate = annual_rate / 100 / 12
    total_invested = 0.0
    current_value = 0.0
    current_contribution = base_amount
    yearly_projections = []
    monthly_breakdown = []

    year = 1
    months_remaining = duration_months

    while months_remaining > 0:
        months_this_year = min(12, months_remaining)

        for month in range(1, months_this_year + 1):
            # Apply monthly contribution
            current_value += current_contribution
            # Apply growth
            current_value *= (1 + monthly_rate)
            # Accumulate invested
            total_invested += current_contribution

            actual_month = (year - 1) * 12 + month
            monthly_breakdown.append({
                'month': actual_month,
                'contribution': round(current_contribution, 2),
                'value': round(current_value, 2),
                'invested': round(total_invested, 2),
                'gain': round(current_value - total_invested, 2)
            })

        # Year-end snapshot
        yearly_projections.append({
            'year': year,
            'year_end_value': round(current_value, 2),
            'total_invested': round(total_invested, 2),
            'estimated_gain': round(current_value - total_invested, 2),
            'monthly_sip': round(current_contribution, 2)
        })

        # Apply step-up for next year
        if step_up_pct > 0:
            current_contribution *= (1 + step_up_pct / 100)

        months_remaining -= 12
        year += 1

    # Calculate CAGR
    if total_invested > 0:
        cagr = (((current_value / total_invested) ** (12 / duration_months)) - 1) * 100
    else:
        cagr = 0.0

    return SIPProjection(
        total_invested=round(total_invested, 2),
        estimated_returns=round(current_value - total_invested, 2),
        maturity_value=round(current_value, 2),
        cagr=round(cagr, 2),
        yearly_projections=yearly_projections,
        monthly_breakdown=monthly_breakdown
    )


def calculate_simple_sip(
    monthly_amount: float,
    duration_months: int,
    annual_rate: float
) -> SIPProjection:
    """
    Calculate simple SIP projection (no step-up).

    Args:
        monthly_amount: Monthly SIP amount (₹)
        duration_months: Duration in months
        annual_rate: Expected annual return rate (%)

    Returns:
        SIPProjection with full breakdown
    """
    total_invested, maturity_value, yearly_projections = calculate_future_value(
        principal=0.0,
        monthly_contribution=monthly_amount,
        annual_rate=annual_rate,
        months=duration_months,
        step_up_pct=0.0
    )

    # Calculate CAGR
    cagr = annual_rate  # For simple SIP, CAGR equals annual rate

    # Generate monthly breakdown
    monthly_rate = annual_rate / 100 / 12
    current_value = 0.0
    monthly_breakdown = []

    for month in range(1, duration_months + 1):
        current_value += monthly_amount
        current_value *= (1 + monthly_rate)

        monthly_breakdown.append({
            'month': month,
            'contribution': monthly_amount,
            'value': round(current_value, 2),
            'invested': round(monthly_amount * month, 2),
            'gain': round(current_value - (monthly_amount * month), 2)
        })

    return SIPProjection(
        total_invested=round(total_invested, 2),
        estimated_returns=round(maturity_value - total_invested, 2),
        maturity_value=round(maturity_value, 2),
        cagr=round(cagr, 2),
        yearly_projections=yearly_projections,
        monthly_breakdown=monthly_breakdown
    )


def calculate_sip_projection(
    base_amount: float,
    duration_months: int,
    expected_return_rate: float = 12.0,
    step_up_percentage: float = 0.0,
    frequency: str = 'monthly'
) -> Dict[str, Any]:
    """
    Main projection calculation function.

    Args:
        base_amount: Starting SIP amount (₹)
        duration_months: Duration in months
        expected_return_rate: Expected annual return (%)\n        step_up_percentage: Annual step-up (%)
        frequency: Payment frequency (daily/weekly/monthly)

    Returns:
        Dictionary with projection data
    """
    # Convert to monthly equivalent
    if frequency == 'daily':
        monthly_equivalent = base_amount * 30
        periods_per_year = 12  # For CAGR calculation
    elif frequency == 'weekly':
        monthly_equivalent = base_amount * 4
        periods_per_year = 12
    else:  # monthly
        monthly_equivalent = base_amount
        periods_per_year = 12

    # Calculate based on type
    if step_up_percentage > 0:
        projection = calculate_step_up_sip(
            base_amount=monthly_equivalent,
            duration_months=duration_months,
            annual_rate=expected_return_rate,
            step_up_pct=step_up_percentage
        )
    else:
        projection = calculate_simple_sip(
            monthly_amount=monthly_equivalent,
            duration_months=duration_months,
            annual_rate=expected_return_rate
        )

    return {
        'base_amount': base_amount,
        'duration_months': duration_months,
        'expected_return_rate': expected_return_rate,
        'step_up_percentage': step_up_percentage,
        'frequency': frequency,
        'total_invested': projection.total_invested,
        'estimated_returns': projection.estimated_returns,
        'maturity_value': projection.maturity_value,
        'cagr': projection.cagr,
        'total_gain_percent': round(
            (projection.estimated_returns / projection.total_invested * 100)
            if projection.total_invested > 0 else 0, 2
        ),
        'yearly_projections': projection.yearly_projections,
        'monthly_breakdown': projection.monthly_breakdown[:12] if projection.monthly_breakdown else [],  # First year only for preview
        'growth_type': 'step_up' if step_up_percentage > 0 else 'simple'
    }


def calculate_sip_summary(sip_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
    """
    Calculate summary for a single SIP including actual vs projected.

    Args:
        sip_data: SIP data from database
        current_price: Current stock price

    Returns:
        Summary dictionary
    """
    amount = sip_data.get('amount_per_installment', 0)
    installments = sip_data.get('installments_completed', 0)
    total_installments = sip_data.get('total_installments', 12)
    step_up = sip_data.get('step_up_percentage', 0) or sip_data.get('annual_step_up', 0) or 0
    expected_return = sip_data.get('expected_return_rate', 12.0) or 12.0
    duration = sip_data.get('duration_months', 12)
    frequency = sip_data.get('frequency', 'monthly')
    shares = sip_data.get('shares_accumulated', 0)

    # Actual values
    total_invested = amount * installments
    current_value = shares * current_price if shares > 0 else total_invested
    actual_gain = current_value - total_invested
    progress = (installments / total_installments * 100) if total_installments > 0 else 0

    # Projected values (using remaining duration)
    remaining_months = duration - installments
    if remaining_months > 0:
        projection = calculate_sip_projection(
            base_amount=amount,
            duration_months=remaining_months,
            expected_return_rate=expected_return,
            step_up_percentage=step_up,
            frequency=frequency
        )
        projected_maturity = projection.get('maturity_value', 0)
        projected_invested = projection.get('total_invested', 0)
        projected_returns = projection.get('estimated_returns', 0)
    else:
        projected_maturity = current_value
        projected_invested = total_invested
        projected_returns = actual_gain

    return {
        'sip_id': sip_data.get('id'),
        'stock_symbol': sip_data.get('stock_symbol'),
        'status': sip_data.get('status', 'active'),

        # Actual values
        'total_invested': round(total_invested, 2),
        'current_value': round(current_value, 2),
        'actual_gain': round(actual_gain, 2),
        'actual_gain_percent': round((actual_gain / total_invested * 100) if total_invested > 0 else 0, 2),
        'progress_percent': round(progress, 1),
        'installments_completed': installments,
        'installments_remaining': total_installments - installments,
        'shares_accumulated': round(shares, 4),

        # Projected values
        'projected_maturity_value': round(projected_maturity, 2),
        'projected_invested': round(projected_invested, 2),
        'projected_returns': round(projected_returns, 2),
        'projected_total_gain_percent': round((projected_returns / projected_invested * 100) if projected_invested > 0 else 0, 2),

        # Configuration
        'monthly_amount': amount,
        'step_up_percentage': step_up,
        'expected_return_rate': expected_return,
        'duration_months': duration,
        'frequency': frequency
    }


# ============================================================================
# SINGLETON
# ============================================================================

_projection_engine = None


def get_projection_engine():
    """Get singleton projection engine instance."""
    global _projection_engine
    if _projection_engine is None:
        _projection_engine = {
            'calculate_sip_projection': calculate_sip_projection,
            'calculate_sip_summary': calculate_sip_summary,
            'calculate_simple_sip': calculate_simple_sip,
            'calculate_step_up_sip': calculate_step_up_sip,
            'calculate_future_value': calculate_future_value
        }
    return _projection_engine