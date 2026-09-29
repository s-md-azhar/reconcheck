import sqlite3
import pandas as pd

def load_data_to_sqlite(ledger_df: pd.DataFrame, bank_df: pd.DataFrame) -> sqlite3.Connection:
    """
    Loads ledger and bank statement dataframes into an in-memory SQLite database.
    Returns the database connection.
    """
    conn = sqlite3.connect(':memory:')
    
    ledger_df.to_sql('ledger', conn, index=False, if_exists='replace')
    bank_df.to_sql('bank_statement', conn, index=False, if_exists='replace')
    
    return conn
