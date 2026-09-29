import sqlite3
import pandas as pd
from typing import Tuple
from rapidfuzz import fuzz
from datetime import datetime

def run_reconciliation(ledger_df: pd.DataFrame, bank_df: pd.DataFrame, 
                      amount_tolerance: float = 5.0, date_window: int = 2) -> pd.DataFrame:
    """
    Runs the core SQL reconciliation engine and fallback fuzzy matching.
    Returns a classified DataFrame of all records.
    """
    conn = sqlite3.connect(':memory:')
    ledger_df.to_sql('ledger', conn, index=False, if_exists='replace')
    bank_df.to_sql('bank_statement', conn, index=False, if_exists='replace')
    
    query = """
    WITH l_flagged AS (
        SELECT *, COUNT(*) OVER(PARTITION BY transaction_id) as dup_count
        FROM ledger
    ),
    b_flagged AS (
        SELECT *, COUNT(*) OVER(PARTITION BY transaction_id) as dup_count
        FROM bank_statement
    )
    SELECT 
        l.transaction_id AS l_id, l.date AS l_date, l.amount AS l_amount, l.vendor AS l_vendor, l.description AS l_desc, l.dup_count AS l_dup_count,
        b.transaction_id AS b_id, b.date AS b_date, b.amount AS b_amount, b.vendor AS b_vendor, b.description AS b_desc, b.dup_count AS b_dup_count
    FROM l_flagged l
    LEFT JOIN b_flagged b ON l.transaction_id = b.transaction_id
    
    UNION ALL
    
    SELECT 
        l.transaction_id AS l_id, l.date AS l_date, l.amount AS l_amount, l.vendor AS l_vendor, l.description AS l_desc, l.dup_count AS l_dup_count,
        b.transaction_id AS b_id, b.date AS b_date, b.amount AS b_amount, b.vendor AS b_vendor, b.description AS b_desc, b.dup_count AS b_dup_count
    FROM b_flagged b
    LEFT JOIN l_flagged l ON l.transaction_id = b.transaction_id
    WHERE l.transaction_id IS NULL
    """
    
    df = pd.read_sql_query(query, conn)
    
    def classify(row):
        if pd.notna(row['l_dup_count']) and row['l_dup_count'] > 1:
            return 'DUPLICATE'
        if pd.notna(row['b_dup_count']) and row['b_dup_count'] > 1:
            return 'DUPLICATE'
            
        if pd.isna(row['b_id']):
            return 'MISSING_IN_BANK'
        if pd.isna(row['l_id']):
            return 'MISSING_IN_LEDGER'
            
        amount_diff = abs(row['l_amount'] - row['b_amount'])
        if amount_diff > amount_tolerance:
            return 'AMOUNT_MISMATCH'
            
        l_date = datetime.strptime(row['l_date'], '%Y-%m-%d')
        b_date = datetime.strptime(row['b_date'], '%Y-%m-%d')
        date_diff = abs((l_date - b_date).days)
        if date_diff > date_window:
            return 'DATE_MISMATCH'
            
        return 'MATCHED'
        
    df['category'] = df.apply(classify, axis=1)
    
    # Fallback Fuzzy Match
    missing_ledger = df[df['category'] == 'MISSING_IN_LEDGER']
    missing_bank = df[df['category'] == 'MISSING_IN_BANK']
    
    fuzzy_matches = []
    used_b_indices = set()
    used_l_indices = set()
    
    for l_idx, l_row in missing_bank.iterrows():
        for b_idx, b_row in missing_ledger.iterrows():
            if b_idx in used_b_indices: continue
            
            amt_diff = abs(l_row['l_amount'] - b_row['b_amount'])
            l_dt = datetime.strptime(l_row['l_date'], '%Y-%m-%d')
            b_dt = datetime.strptime(b_row['b_date'], '%Y-%m-%d')
            dt_diff = abs((l_dt - b_dt).days)
            
            if amt_diff <= amount_tolerance and dt_diff <= date_window:
                score = fuzz.token_sort_ratio(str(l_row['l_vendor']), str(b_row['b_vendor']))
                if score >= 70:
                    fuzzy_matches.append((l_idx, b_idx))
                    used_b_indices.add(b_idx)
                    used_l_indices.add(l_idx)
                    break
                    
    for l_idx, b_idx in fuzzy_matches:
        df.at[l_idx, 'b_id'] = df.at[b_idx, 'b_id']
        df.at[l_idx, 'b_date'] = df.at[b_idx, 'b_date']
        df.at[l_idx, 'b_amount'] = df.at[b_idx, 'b_amount']
        df.at[l_idx, 'b_vendor'] = df.at[b_idx, 'b_vendor']
        df.at[l_idx, 'b_desc'] = df.at[b_idx, 'b_desc']
        df.at[l_idx, 'category'] = 'FUZZY_MATCH'
        
    df = df.drop(index=list(used_b_indices)).reset_index(drop=True)
    
    conn.close()
    return df
