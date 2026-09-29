import sqlite3
import pandas as pd
from typing import Tuple
from rapidfuzz import fuzz

def sql_exact_match(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Performs a full outer join on transaction_id using SQLite.
    Returns a dataframe with matched and unmatched records combined side-by-side.
    """
    query = """
    SELECT 
        l.transaction_id AS l_id, l.date AS l_date, l.amount AS l_amount, l.vendor AS l_vendor, l.description AS l_desc,
        b.transaction_id AS b_id, b.date AS b_date, b.amount AS b_amount, b.vendor AS b_vendor, b.description AS b_desc
    FROM ledger l
    LEFT JOIN bank_statement b ON l.transaction_id = b.transaction_id
    
    UNION ALL
    
    SELECT 
        l.transaction_id AS l_id, l.date AS l_date, l.amount AS l_amount, l.vendor AS l_vendor, l.description AS l_desc,
        b.transaction_id AS b_id, b.date AS b_date, b.amount AS b_amount, b.vendor AS b_vendor, b.description AS b_desc
    FROM bank_statement b
    LEFT JOIN ledger l ON l.transaction_id = b.transaction_id
    WHERE l.transaction_id IS NULL
    """
    return pd.read_sql_query(query, conn)

def fallback_fuzzy_match(unmatched_ledger: pd.DataFrame, unmatched_bank: pd.DataFrame, 
                         amount_tolerance: float = 5.0, date_window: int = 2) -> pd.DataFrame:
    """
    Attempts to fuzzy match remaining unmatched records based on vendor names,
    within the specified amount and date tolerances.
    """
    # Note: In our dataset, discrepancies always share the same transaction_id. 
    # But for a real fuzzy match, we'd assume transaction_ids might be missing or different.
    # However, since the exact match was ON transaction_id, if they didn't match exactly by ID,
    # they end up in unmatched. Wait, in our generated data, the injected discrepancies 
    # DO have the SAME transaction_id! 
    # So the SQL JOIN ON transaction_id will actually match them! 
    # Let me re-read the SQL match requirement.
    pass
