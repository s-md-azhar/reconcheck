import pytest
import pandas as pd
import sqlite3
from reconcheck.engine import run_reconciliation

def test_sql_engine_direct_query():
    """
    Directly tests that the SQL FULL OUTER JOIN equivalent logic works inside a temp SQLite DB.
    """
    conn = sqlite3.connect(':memory:')
    
    # Setup mock tables
    ledger_data = [
        {"transaction_id": "TXN-1", "date": "2026-08-01", "amount": 100.0, "vendor": "AWS", "description": "Cloud"}
    ]
    bank_data = [
        {"transaction_id": "TXN-2", "date": "2026-08-01", "amount": 200.0, "vendor": "GCP", "description": "Cloud"}
    ]
    
    pd.DataFrame(ledger_data).to_sql('ledger', conn, index=False)
    pd.DataFrame(bank_data).to_sql('bank_statement', conn, index=False)
    
    # Run the SQL join
    query = """
    SELECT l.transaction_id AS l_id, b.transaction_id AS b_id
    FROM ledger l LEFT JOIN bank_statement b ON l.transaction_id = b.transaction_id
    UNION ALL
    SELECT l.transaction_id AS l_id, b.transaction_id AS b_id
    FROM bank_statement b LEFT JOIN ledger l ON l.transaction_id = b.transaction_id
    WHERE l.transaction_id IS NULL
    """
    
    res = pd.read_sql_query(query, conn)
    assert len(res) == 2
    assert "TXN-1" in res['l_id'].values
    assert "TXN-2" in res['b_id'].values
    conn.close()

def test_run_reconciliation_exact_match():
    ledger = pd.DataFrame([{"transaction_id": "TXN-1", "date": "2026-08-01", "amount": 100.0, "vendor": "AWS", "description": "x"}])
    bank = pd.DataFrame([{"transaction_id": "TXN-1", "date": "2026-08-01", "amount": 100.0, "vendor": "AWS", "description": "x"}])
    
    res = run_reconciliation(ledger, bank)
    assert len(res) == 1
    assert res.iloc[0]['category'] == 'MATCHED'

def test_run_reconciliation_mismatches():
    ledger = pd.DataFrame([
        {"transaction_id": "TXN-1", "date": "2026-08-01", "amount": 100.0, "vendor": "AWS", "description": "x"},
        {"transaction_id": "TXN-2", "date": "2026-08-01", "amount": 200.0, "vendor": "GCP", "description": "y"}
    ])
    bank = pd.DataFrame([
        {"transaction_id": "TXN-1", "date": "2026-08-01", "amount": 110.0, "vendor": "AWS", "description": "x"}, # Amount mismatch
        {"transaction_id": "TXN-2", "date": "2026-08-05", "amount": 200.0, "vendor": "GCP", "description": "y"}  # Date mismatch
    ])
    
    res = run_reconciliation(ledger, bank, amount_tolerance=5.0, date_window=2)
    assert len(res) == 2
    
    txn1 = res[res['l_id'] == 'TXN-1'].iloc[0]
    assert txn1['category'] == 'AMOUNT_MISMATCH'
    
    txn2 = res[res['l_id'] == 'TXN-2'].iloc[0]
    assert txn2['category'] == 'DATE_MISMATCH'

def test_run_reconciliation_fuzzy_match():
    ledger = pd.DataFrame([
        {"transaction_id": "TXN-3", "date": "2026-08-01", "amount": 100.0, "vendor": "Stripe", "description": "fee"}
    ])
    bank = pd.DataFrame([
        # Missing original ID, slightly off amount, modified vendor name
        {"transaction_id": "UNKNOWN-123", "date": "2026-08-01", "amount": 101.0, "vendor": "Stripe Inc", "description": "fee"}
    ])
    
    res = run_reconciliation(ledger, bank, amount_tolerance=5.0)
    assert len(res) == 1
    assert res.iloc[0]['category'] == 'FUZZY_MATCH'
    assert res.iloc[0]['l_id'] == 'TXN-3'
    assert res.iloc[0]['b_id'] == 'UNKNOWN-123'
