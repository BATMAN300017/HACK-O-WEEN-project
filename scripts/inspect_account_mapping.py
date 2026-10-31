import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.core.database import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.account_number, a.customer_id, a.account_type, a.currency, a.balance, a.status,
               c.full_name, c.risk_tier, c.kyc_status
        FROM accounts a
        JOIN customers c ON a.customer_id = c.id
        WHERE a.id LIKE 'ACCT_%'
        LIMIT 5;
    """)
    for r in cur.fetchall():
        print(dict(r._dict))
        
    cur.execute("SELECT count(*) as cnt FROM accounts WHERE id LIKE 'ACCT_%';")
    print("Total ACCT_% in accounts table:", cur.fetchone()['cnt'])
    
    cur.execute("SELECT count(*) as cnt FROM customers WHERE id LIKE 'CUST-IND-%';")
    print("Total CUST-IND-% in customers table:", cur.fetchone()['cnt'])
    cur.close()
