"""
Business Logic Layer - Sales analytics calculations.
"""

from collections import defaultdict
from datetime import datetime
from typing import Any


class BusinessLogicError(Exception):
    """Base exception for business logic errors."""
    pass


class CalculationError(BusinessLogicError):
    """Raised when calculation fails."""
    pass


class ValidationError(BusinessLogicError):
    """Raised when business rules are violated."""
    pass


class SalesAnalytics:
    """Performs sales analytics calculations on transaction data."""

    def __init__(self, transactions: list[dict[str, Any]]):
        """
        Initialize analytics with transaction data.

        Args:
            transactions: List of transaction dictionaries
        """
        self.transactions = transactions
        self._validate_transactions()

    def _validate_transactions(self) -> None:
        """
        Validate transaction data meets business rules.

        Raises:
            ValidationError: If data violates business rules
        """
        if not self.transactions:
            raise ValidationError("No transactions provided")

        for idx, txn in enumerate(self.transactions):
            # Validate quantity is positive
            if txn['quantity'] <= 0:
                raise ValidationError(
                    f"Transaction {txn['transaction_id']}: quantity must be positive, got {txn['quantity']}"
                )

            # Validate unit price is non-negative
            if txn['unit_price'] < 0:
                raise ValidationError(
                    f"Transaction {txn['transaction_id']}: unit_price cannot be negative, got {txn['unit_price']}"
                )

    def calculate_total_revenue(self, simulate_error: str | None = None) -> float:
        """
        Calculate total revenue from all transactions.

        Args:
            simulate_error: Error type to simulate (CALCULATION_ERROR)

        Returns:
            Total revenue

        Raises:
            CalculationError: If calculation fails
        """
        if simulate_error == 'CALCULATION_ERROR':
            # Simulate division by zero
            return 1.0 / 0.0

        try:
            total = sum(txn['quantity'] * txn['unit_price'] for txn in self.transactions)
            return round(total, 2)
        except (TypeError, KeyError) as e:
            raise CalculationError(f"Failed to calculate total revenue: {e}")

    def get_top_products(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Get top-selling products by revenue.

        Args:
            limit: Number of top products to return

        Returns:
            List of top products with revenue
        """
        product_revenue = defaultdict(float)
        product_quantity = defaultdict(int)
        product_names = {}

        for txn in self.transactions:
            product_id = txn['product_id']
            revenue = txn['quantity'] * txn['unit_price']
            product_revenue[product_id] += revenue
            product_quantity[product_id] += txn['quantity']
            product_names[product_id] = txn['product_name']

        # Sort by revenue
        sorted_products = sorted(
            product_revenue.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {
                'product_id': product_id,
                'product_name': product_names[product_id],
                'total_revenue': round(revenue, 2),
                'total_quantity': product_quantity[product_id]
            }
            for product_id, revenue in sorted_products
        ]

    def calculate_average_transaction_value(self) -> float:
        """
        Calculate average transaction value.

        Returns:
            Average transaction value

        Raises:
            CalculationError: If calculation fails
        """
        if not self.transactions:
            raise CalculationError("Cannot calculate average: no transactions")

        try:
            total_revenue = self.calculate_total_revenue()
            avg = total_revenue / len(self.transactions)
            return round(avg, 2)
        except ZeroDivisionError:
            raise CalculationError("Division by zero in average calculation")

    def get_regional_breakdown(self) -> dict[str, dict[str, Any]]:
        """
        Get sales breakdown by region.

        Returns:
            Dictionary of regional sales data
        """
        regional_data = defaultdict(lambda: {
            'revenue': 0.0,
            'transactions': 0,
            'customers': set()
        })

        for txn in self.transactions:
            region = txn['region']
            revenue = txn['quantity'] * txn['unit_price']

            regional_data[region]['revenue'] += revenue
            regional_data[region]['transactions'] += 1
            regional_data[region]['customers'].add(txn['customer_id'])

        # Convert to serializable format
        return {
            region: {
                'revenue': round(data['revenue'], 2),
                'transactions': data['transactions'],
                'unique_customers': len(data['customers'])
            }
            for region, data in regional_data.items()
        }

    def calculate_sales_trends(self) -> dict[str, Any]:
        """
        Calculate sales trends over time.

        Returns:
            Dictionary with trend data
        """
        if not self.transactions:
            return {'daily_sales': {}, 'total_days': 0}

        daily_sales = defaultdict(float)

        for txn in self.transactions:
            date_key = txn['date'].strftime('%Y-%m-%d')
            revenue = txn['quantity'] * txn['unit_price']
            daily_sales[date_key] += revenue

        # Sort by date
        sorted_daily_sales = {
            date: round(revenue, 2)
            for date, revenue in sorted(daily_sales.items())
        }

        return {
            'daily_sales': sorted_daily_sales,
            'total_days': len(sorted_daily_sales),
            'average_daily_revenue': round(
                sum(daily_sales.values()) / len(daily_sales), 2
            ) if daily_sales else 0.0
        }

    def generate_summary(self, simulate_error: str | None = None) -> dict[str, Any]:
        """
        Generate comprehensive analytics summary.

        Args:
            simulate_error: Error type to simulate

        Returns:
            Complete analytics summary
        """
        return {
            'total_revenue': self.calculate_total_revenue(simulate_error),
            'average_transaction_value': self.calculate_average_transaction_value(),
            'total_transactions': len(self.transactions),
            'top_products': self.get_top_products(),
            'regional_breakdown': self.get_regional_breakdown(),
            'sales_trends': self.calculate_sales_trends(),
            'date_range': {
                'start': min(txn['date'] for txn in self.transactions).strftime('%Y-%m-%d'),
                'end': max(txn['date'] for txn in self.transactions).strftime('%Y-%m-%d')
            }
        }
