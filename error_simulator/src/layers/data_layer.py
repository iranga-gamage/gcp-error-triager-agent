"""
Data Layer - Handles CSV file reading and data validation.
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any


class DataLayerError(Exception):
    """Base exception for data layer errors."""
    pass


class FileNotFoundError(DataLayerError):
    """Raised when data file is not found."""
    pass


class DataValidationError(DataLayerError):
    """Raised when data validation fails."""
    pass


class TransactionDataReader:
    """Reads and validates sales transaction data from CSV."""

    REQUIRED_FIELDS = [
        'transaction_id',
        'date',
        'product_id',
        'product_name',
        'quantity',
        'unit_price',
        'customer_id',
        'region'
    ]

    def __init__(self, data_file_path: str | None = None):
        """
        Initialize the data reader.

        Args:
            data_file_path: Path to CSV file. Defaults to data/transactions.csv
        """
        if data_file_path is None:
            # Default to data/transactions.csv relative to src directory
            src_dir = Path(__file__).parent.parent
            data_file_path = src_dir / 'data' / 'transactions.csv'

        self.data_file_path = Path(data_file_path)

    def read_transactions(self, simulate_error: str | None = None) -> list[dict[str, Any]]:
        """
        Read transactions from CSV file.

        Args:
            simulate_error: Error type to simulate (FILE_NOT_FOUND, INVALID_DATA)

        Returns:
            List of transaction dictionaries

        Raises:
            FileNotFoundError: If file doesn't exist
            DataValidationError: If data is invalid
        """
        # Simulate file not found error
        if simulate_error == 'FILE_NOT_FOUND':
            raise FileNotFoundError(f"Data file not found: {self.data_file_path}")

        # Check if file exists
        if not self.data_file_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_file_path}")

        transactions = []

        try:
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Validate headers
                if not all(field in reader.fieldnames for field in self.REQUIRED_FIELDS):
                    missing = set(self.REQUIRED_FIELDS) - set(reader.fieldnames or [])
                    raise DataValidationError(f"Missing required fields: {missing}")

                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    # Simulate invalid data error
                    if simulate_error == 'INVALID_DATA' and row_num == 3:
                        raise DataValidationError(f"Invalid data at row {row_num}: corrupted data")

                    # Validate and parse row
                    try:
                        transaction = self._parse_transaction(row, row_num)
                        transactions.append(transaction)
                    except (ValueError, KeyError) as e:
                        raise DataValidationError(f"Invalid data at row {row_num}: {e}")

        except csv.Error as e:
            raise DataValidationError(f"CSV parsing error: {e}")

        return transactions

    def _parse_transaction(self, row: dict[str, str], row_num: int) -> dict[str, Any]:
        """
        Parse and validate a single transaction row.

        Args:
            row: Raw CSV row
            row_num: Row number for error reporting

        Returns:
            Parsed transaction dictionary

        Raises:
            ValueError: If data cannot be parsed
        """
        try:
            return {
                'transaction_id': row['transaction_id'].strip(),
                'date': datetime.strptime(row['date'].strip(), '%Y-%m-%d'),
                'product_id': row['product_id'].strip(),
                'product_name': row['product_name'].strip(),
                'quantity': int(row['quantity']),
                'unit_price': float(row['unit_price']),
                'customer_id': row['customer_id'].strip(),
                'region': row['region'].strip(),
            }
        except ValueError as e:
            raise ValueError(f"Failed to parse field: {e}")
        except KeyError as e:
            raise KeyError(f"Missing field: {e}")

    def filter_by_date_range(
        self,
        transactions: list[dict[str, Any]],
        start_date: str | None = None,
        end_date: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Filter transactions by date range.

        Args:
            transactions: List of transactions
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Filtered list of transactions
        """
        if not start_date and not end_date:
            return transactions

        filtered = transactions

        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            filtered = [t for t in filtered if t['date'] >= start]

        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            filtered = [t for t in filtered if t['date'] <= end]

        return filtered
