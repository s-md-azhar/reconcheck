import csv
import random
import uuid
from datetime import datetime, timedelta
import json
import os

random.seed(42)

def random_date(start_date, end_date):
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)

def generate_data(num_records=180, discrepancy_rate=0.20):
    vendors = [
        "AWS Cloud", "GCP Services", "Stripe", "Twilio", "Slack",
        "Atlassian", "GitHub", "Zoom", "Salesforce", "Mailchimp"
    ]
    
    descriptions = [
        "Monthly Subscription", "Usage Fees", "Enterprise License",
        "Overage Charges", "Annual Renewal", "API Credits"
    ]

    start_date = datetime(2026, 8, 1)
    end_date = datetime(2026, 8, 31)

    ledger_data = []
    bank_data = []
    ground_truth = {}

    num_discrepancies = int(num_records * discrepancy_rate)
    discrepancy_types = [
        "MISSING_IN_BANK", "MISSING_IN_LEDGER", 
        "AMOUNT_MISMATCH", "DATE_MISMATCH", 
        "DUPLICATE_IN_LEDGER", "DUPLICATE_IN_BANK",
        "FUZZY_MATCH"
    ]
    
    discrepancy_assignments = [random.choice(discrepancy_types) for _ in range(num_discrepancies)]
    
    for i in range(num_records):
        txn_id = f"TXN-{1000 + i}"
        date = random_date(start_date, end_date)
        amount = round(random.uniform(50.0, 5000.0), 2)
        vendor = random.choice(vendors)
        desc = random.choice(descriptions)
        
        base_record = {
            "transaction_id": txn_id,
            "date": date.strftime("%Y-%m-%d"),
            "amount": amount,
            "vendor": vendor,
            "description": desc
        }

        if i < num_discrepancies:
            dtype = discrepancy_assignments[i]
            ground_truth[txn_id] = dtype
            
            if dtype == "MISSING_IN_BANK":
                ledger_data.append(base_record)
                
            elif dtype == "MISSING_IN_LEDGER":
                bank_data.append(base_record)
                
            elif dtype == "AMOUNT_MISMATCH":
                ledger_data.append(base_record)
                bank_record = base_record.copy()
                alteration = round(random.uniform(1.0, 50.0), 2)
                bank_record["amount"] = round(amount + (alteration if random.choice([True, False]) else -alteration), 2)
                bank_data.append(bank_record)
                
            elif dtype == "DATE_MISMATCH":
                ledger_data.append(base_record)
                bank_record = base_record.copy()
                offset = random.randint(1, 3)
                bank_date = date + timedelta(days=offset)
                bank_record["date"] = bank_date.strftime("%Y-%m-%d")
                bank_data.append(bank_record)
                
            elif dtype == "DUPLICATE_IN_LEDGER":
                ledger_data.append(base_record)
                ledger_data.append(base_record)
                bank_data.append(base_record)
                
            elif dtype == "DUPLICATE_IN_BANK":
                ledger_data.append(base_record)
                bank_data.append(base_record)
                bank_data.append(base_record)
                
            elif dtype == "FUZZY_MATCH":
                # transaction_id is missing/changed in bank, but vendor/amount are similar
                ledger_data.append(base_record)
                bank_record = base_record.copy()
                bank_record["transaction_id"] = f"UNKNOWN-{uuid.uuid4().hex[:6]}"
                bank_record["vendor"] = bank_record["vendor"] + " INC"
                # amount slightly off
                bank_record["amount"] = round(amount + random.uniform(-2, 2), 2)
                bank_data.append(bank_record)
        else:
            ground_truth[txn_id] = "MATCHED"
            ledger_data.append(base_record)
            bank_data.append(base_record)
            
    random.shuffle(ledger_data)
    random.shuffle(bank_data)
    
    def write_csv(filename, data):
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["transaction_id", "date", "amount", "vendor", "description"])
            writer.writeheader()
            writer.writerows(data)
            
    write_csv("ledger.csv", ledger_data)
    write_csv("bank_statement.csv", bank_data)
    
    with open("ground_truth.json", "w") as f:
        json.dump(ground_truth, f, indent=4)
        
    print(f"Generated {len(ledger_data)} ledger records and {len(bank_data)} bank statement records.")
    print(f"Injected {num_discrepancies} discrepancies.")

if __name__ == "__main__":
    generate_data()
