import argparse
import pandas as pd
import json
import time
from reconcheck.engine import run_reconciliation
import os

def main():
    parser = argparse.ArgumentParser(description="ReconCheck: Automated Transaction Reconciliation Tool")
    parser.add_argument("--ledger", required=True, help="Path to ledger CSV")
    parser.add_argument("--bank", required=True, help="Path to bank statement CSV")
    parser.add_argument("--output", default="exceptions.xlsx", help="Path for output exceptions report (Excel)")
    parser.add_argument("--tolerance", type=float, default=5.0, help="Amount mismatch tolerance (default 5.0)")
    parser.add_argument("--date-window", type=int, default=2, help="Date mismatch window in days (default 2)")
    parser.add_argument("--verify", action="store_true", help="Verify against ground_truth.json if present")
    
    args = parser.parse_args()
    
    print(f"Loading data...")
    start_time = time.time()
    
    try:
        ledger_df = pd.read_csv(args.ledger)
        bank_df = pd.read_csv(args.bank)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
        
    print(f"Running reconciliation engine (Tolerance: INR {args.tolerance}, Date Window: {args.date_window} days)...")
    
    results_df = run_reconciliation(ledger_df, bank_df, args.tolerance, args.date_window)
    
    runtime = time.time() - start_time
    
    total_records = len(results_df)
    summary = results_df['category'].value_counts()
    
    print("\n" + "="*50)
    print(" RECONCILIATION SUMMARY ")
    print("="*50)
    print(f"Total Records Processed: {total_records}")
    print(f"Execution Time: {runtime:.2f} seconds\n")
    
    for cat, count in summary.items():
        pct = (count / total_records) * 100
        print(f"{cat:<20}: {count:>4} ({pct:>5.1f}%)")
        
    exceptions = results_df[results_df['category'] != 'MATCHED']
    def get_amount(row):
        return row['l_amount'] if pd.notna(row['l_amount']) else row['b_amount']
    
    if not exceptions.empty:
        total_discrepancy_val = exceptions.apply(get_amount, axis=1).sum()
        print(f"\nTotal Discrepancy Value: INR {total_discrepancy_val:,.2f}")
    
    print("="*50)
    
    if not exceptions.empty:
        print(f"\nExporting {len(exceptions)} exceptions to {args.output}...")
        cols = ['category', 'l_id', 'b_id', 'l_date', 'b_date', 'l_amount', 'b_amount', 'l_vendor', 'b_vendor', 'l_desc', 'b_desc']
        export_df = exceptions[cols]
        export_df.to_excel(args.output, index=False)
        export_df.to_csv(args.output.replace('.xlsx', '.csv'), index=False)
        
        written_df = pd.read_excel(args.output)
        if len(written_df) != len(exceptions):
            print("ERROR: Written exception count does not match in-memory count!")
        else:
            print(f"Verified {len(written_df)} records written to disk.")
    else:
        print("\nNo exceptions found. All records matched!")

    if args.verify and os.path.exists('ground_truth.json'):
        print("\n" + "-"*50)
        print(" SELF-VERIFICATION AGAINST GROUND TRUTH")
        print("-"*50)
        with open('ground_truth.json') as f:
            truth = json.load(f)
            
        correct = 0
        total = 0
        
        for _, row in results_df.iterrows():
            l_id = row['l_id']
            b_id = row['b_id']
            cat = row['category']
            
            txn_id = l_id if pd.notna(l_id) and not str(l_id).startswith("UNKNOWN") else b_id
            
            if pd.isna(txn_id):
                continue
                
            expected = truth.get(txn_id)
            if not expected:
                continue
                
            total += 1
            
            match = False
            if cat == expected:
                match = True
            elif cat == 'DUPLICATE' and 'DUPLICATE' in expected:
                match = True
            
            if match:
                correct += 1
                
        if total > 0:
            accuracy = (correct / total) * 100
            print(f"Detection Accuracy: {correct}/{total} ({accuracy:.1f}%)")
        else:
            print("Could not verify accuracy: no matching transaction IDs found.")

if __name__ == "__main__":
    main()
