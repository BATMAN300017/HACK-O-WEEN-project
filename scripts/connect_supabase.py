#!/usr/bin/env python3
"""
SentinelFlow AI — Automated Supabase Connection & Setup Wizard
Usage:
    python scripts/connect_supabase.py
    python scripts/connect_supabase.py --url https://xyz.supabase.co --key eyJ... --db-url postgresql://...
"""

import os
import sys
import json
import urllib.request
import urllib.error
import argparse

def test_supabase_rest(url: str, key: str) -> bool:
    print(f"\n[1/3] Testing Supabase REST API at: {url}...")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    # Check health/users table via PostgREST
    test_url = f"{url.rstrip('/')}/rest/v1/users?select=id&limit=1"
    try:
        req = urllib.request.Request(test_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
            print("  ✔ Supabase REST API connected successfully! (Status 200 OK)")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404 or "relation \"public.users\" does not exist" in str(e.read()):
            print("  ! Connected to Supabase, but tables have not been created yet.")
            print("  -> Please run 'scripts/supabase_schema.sql' in your Supabase SQL Editor!")
            return True
        print(f"  ✖ HTTP Error {e.code}: {e.reason}")
        return False
    except Exception as e:
        print(f"  ✖ Connection failed: {e}")
        return False

def test_supabase_storage(url: str, key: str, bucket_name: str = "evidence-files") -> bool:
    print(f"\n[2/3] Checking Supabase Storage Bucket ('{bucket_name}')...")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    buckets_url = f"{url.rstrip('/')}/storage/v1/bucket"
    try:
        req = urllib.request.Request(buckets_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            buckets = json.loads(res.read().decode())
            names = [b.get("name") for b in buckets] if isinstance(buckets, list) else []
            if bucket_name in names:
                print(f"  ✔ Bucket '{bucket_name}' is active and ready for PDF/evidence uploads.")
                return True
            else:
                print(f"  ! Bucket '{bucket_name}' not found. Attempting auto-creation...")
                create_req = urllib.request.Request(
                    buckets_url,
                    headers=headers,
                    data=json.dumps({"name": bucket_name, "id": bucket_name, "public": True}).encode(),
                    method="POST"
                )
                with urllib.request.urlopen(create_req, timeout=10) as create_res:
                    print(f"  ✔ Bucket '{bucket_name}' created successfully!")
                    return True
    except Exception as e:
        print(f"  ! Storage bucket notice: {e}")
        return False

def update_env_file(supabase_url: str, anon_key: str, service_key: str, db_url: str):
    print("\n[3/3] Updating .env file with Supabase credentials...")
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    
    # Read existing .env if present
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()
            
    env_dict = {}
    for line in existing_lines:
        line_clean = line.strip()
        if line_clean and not line_clean.startswith("#") and "=" in line_clean:
            k, v = line_clean.split("=", 1)
            env_dict[k.strip()] = v.strip()

    # Update or add Supabase variables
    if db_url:
        env_dict["DATABASE_URL"] = db_url
    if supabase_url:
        env_dict["SUPABASE_URL"] = supabase_url
    if anon_key:
        env_dict["SUPABASE_ANON_KEY"] = anon_key
    if service_key:
        env_dict["SUPABASE_SERVICE_ROLE_KEY"] = service_key
    env_dict["SUPABASE_STORAGE_BUCKET"] = "evidence-files"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# SentinelFlow AI — Production Environment Configuration\n\n")
        for k, v in env_dict.items():
            f.write(f"{k}={v}\n")
            
    print(f"  ✔ Successfully saved credentials to: {env_path}")

def main():
    parser = argparse.ArgumentParser(description="Connect SentinelFlow AI with your Supabase account")
    parser.add_argument("--url", help="Your Supabase Project URL (https://xyz.supabase.co)")
    parser.add_argument("--key", help="Your Supabase anon or service_role API key")
    parser.add_argument("--db-url", help="Your Supabase PostgreSQL connection string (Transaction pooler on port 6543)")
    args = parser.parse_args()

    print("=" * 70)
    print(" SentinelFlow AI — Supabase Cloud Connection Wizard")
    print("=" * 70)

    url = args.url or input("\nEnter your Supabase Project URL (e.g. https://xxxx.supabase.co): ").strip()
    key = args.key or input("Enter your Supabase API Key (anon key or service_role key): ").strip()
    db_url = args.db_url or input("Enter your Supabase Database Connection String (optional, press Enter to skip): ").strip()

    if not url or not key:
        print("\nError: Supabase URL and API Key are required.")
        sys.exit(1)

    rest_ok = test_supabase_rest(url, key)
    test_supabase_storage(url, key)
    update_env_file(url, key, key, db_url)

    print("\n" + "=" * 70)
    print(" SUPABASE SETUP COMPLETE!")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. If you haven't yet, copy 'scripts/supabase_schema.sql' into your")
    print("   Supabase Dashboard -> SQL Editor and click 'Run'.")
    print("2. Start your local server:")
    print("   python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000")
    print("=" * 70)

if __name__ == "__main__":
    main()
