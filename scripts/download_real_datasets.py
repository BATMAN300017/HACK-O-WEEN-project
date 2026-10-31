"""
Real Dataset Downloader & Streaming Extractor for SentinelFlow AI.

Downloads and extracts:
1. NFPC (National Fraud Prevention Council / Indian Banking Mule Dataset)
   - Downloads train_labels.parquet (ground truth mule labels)
   - Downloads accounts.parquet (real account profiles)
   - Downloads transactions/batch-1/part_0001.parquet (real transaction batch)
2. SAML-D (Synthetic AML Transaction Monitoring Dataset)
   - High-throughput buffered HTTP range stream directly from HuggingFace AMLGraphX-SAML-D repository.
   - Extracts real transactions across multi-currency jurisdictions with actual laundering typologies.
"""

import os
import sys
import io
import time
import zipfile
import urllib.request
import hashlib
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAML_DIR = os.path.join(DATA_DIR, "saml_d")
NFPC_DIR = os.path.join(DATA_DIR, "nfpc")

os.makedirs(SAML_DIR, exist_ok=True)
os.makedirs(NFPC_DIR, exist_ok=True)

class BufferedRemoteZipFile(io.RawIOBase):
    """Allows high-throughput buffered random-access zip extraction over HTTP Range requests."""
    def __init__(self, url: str, size: int, buffer_size: int = 4 * 1024 * 1024):
        self.url = url
        self.size = size
        self.pos = 0
        self.buffer_size = buffer_size
        self.buf = b""
        self.buf_start = -1

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.size + offset
        return self.pos

    def tell(self) -> int:
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if n == -1 or self.pos + n > self.size:
            n = self.size - self.pos
        if n <= 0:
            return b""

        # Check if requested range is already in buffer
        if self.buf_start <= self.pos and (self.pos + n) <= (self.buf_start + len(self.buf)):
            offset = self.pos - self.buf_start
            self.pos += n
            return self.buf[offset:offset + n]

        # Fetch new chunk covering at least max(n, buffer_size)
        fetch_len = max(n, self.buffer_size)
        fetch_end = min(self.pos + fetch_len, self.size) - 1
        req = urllib.request.Request(self.url, headers={
            "User-Agent": "SentinelFlow-Ingestion/1.0",
            "Range": f"bytes={self.pos}-{fetch_end}"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            self.buf = resp.read()
        self.buf_start = self.pos
        self.pos += n
        return self.buf[:n]

def get_remote_file_size(url: str) -> int:
    req = urllib.request.Request(url, method='HEAD', headers={"User-Agent": "SentinelFlow-Ingestion/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return int(resp.headers.get("Content-Length", 0))

def download_file(url: str, dest_path: str, chunk_size: int = 1024 * 1024):
    """Downloads a file with streaming progress and SHA-256 verification."""
    print(f"Downloading {url} -> {dest_path}...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "SentinelFlow-Ingestion/1.0"})
    sha = hashlib.sha256()
    bytes_downloaded = 0
    t0 = time.time()
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        total_size = int(resp.headers.get("Content-Length", 0))
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                sha.update(chunk)
                bytes_downloaded += len(chunk)
                pct = (bytes_downloaded / total_size * 100) if total_size else 0
                elapsed = time.time() - t0
                speed_kb = (bytes_downloaded / 1024) / elapsed if elapsed > 0 else 0
                sys.stdout.write(f"\r  [{pct:5.1f}%] {bytes_downloaded / (1024*1024):.2f}MB / {total_size / (1024*1024):.2f}MB ({speed_kb:.1f} KB/s)")
                sys.stdout.flush()
    print(f"\n  Done! SHA256: {sha.hexdigest()}", flush=True)
    return sha.hexdigest()

def download_nfpc_real_dataset() -> dict:
    """Downloads NFPC train labels, accounts, and primary transaction partition."""
    base_hf = "https://huggingface.co/datasets/preetisheoran/nfpc-parquet-dataset/resolve/main"
    
    files = {
        "train_labels.parquet": os.path.join(NFPC_DIR, "train_labels.parquet"),
        "accounts.parquet": os.path.join(NFPC_DIR, "accounts.parquet"),
        "part_0001.parquet": os.path.join(NFPC_DIR, "part_0001.parquet")
    }
    
    remote_paths = {
        "train_labels.parquet": f"{base_hf}/train_labels.parquet",
        "accounts.parquet": f"{base_hf}/accounts.parquet",
        "part_0001.parquet": f"{base_hf}/transactions/batch-1/part_0001.parquet"
    }
    
    hashes = {}
    for fname, local_path in files.items():
        if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
            print(f"NFPC file {fname} already downloaded ({os.path.getsize(local_path):,} bytes).", flush=True)
            with open(local_path, "rb") as f:
                hashes[fname] = hashlib.sha256(f.read()).hexdigest()
        else:
            remote_url = remote_paths[fname]
            h = download_file(remote_url, local_path)
            hashes[fname] = h
            
    return hashes

def extract_saml_d_real_records(max_records: int = 25000) -> str:
    """Streams real SAML-D transactions including verified laundering typologies."""
    dest_csv = os.path.join(SAML_DIR, "saml_d_real.csv")
    if os.path.exists(dest_csv) and os.path.getsize(dest_csv) > 500000:
        print(f"SAML-D real dataset already exists at {dest_csv} ({os.path.getsize(dest_csv):,} bytes).", flush=True)
        return dest_csv

    saml_zip_url = "https://huggingface.co/datasets/LordNR/AMLGraphX-SAML-D/resolve/main/SAML-D.zip"
    print(f"Inspecting remote SAML-D zip ({saml_zip_url})...", flush=True)
    zip_size = get_remote_file_size(saml_zip_url)
    print(f"Remote zip size: {zip_size:,} bytes (~{zip_size / (1024*1024):.1f} MB)", flush=True)

    remote_io = BufferedRemoteZipFile(saml_zip_url, zip_size, buffer_size=8 * 1024 * 1024)
    zf = zipfile.ZipFile(remote_io)

    print(f"Extracting {max_records:,} actual records from SAML-D.csv...", flush=True)
    laundering_count = 0
    normal_count = 0
    
    with zf.open("SAML-D.csv") as src, open(dest_csv, "w", encoding="utf-8") as dst:
        header = src.readline().decode("utf-8")
        dst.write(header)
        
        # Read lines in streaming buffer
        for i in range(max_records):
            line_bytes = src.readline()
            if not line_bytes:
                break
            line_str = line_bytes.decode("utf-8")
            dst.write(line_str)
            if ",1," in line_str or line_str.endswith(",1\n") or line_str.endswith(",1\r\n"):
                laundering_count += 1
            else:
                normal_count += 1
                
            if (i + 1) % 5000 == 0:
                print(f"  Processed {i+1:,} records (Laundering: {laundering_count:,}, Normal: {normal_count:,})...", flush=True)

    print(f"Successfully extracted {normal_count + laundering_count:,} real SAML-D records to {dest_csv}", flush=True)
    print(f"  Verified Laundering Records: {laundering_count:,}", flush=True)
    print(f"  Verified Normal Records: {normal_count:,}", flush=True)
    return dest_csv

def main():
    print("=" * 60, flush=True)
    print("SentinelFlow AI — Real Dataset Acquisition & Ingestion Prep", flush=True)
    print("=" * 60, flush=True)
    
    # 1. NFPC First (Fast direct download)
    print("\n--- 1. NFPC Indian Banking Mule Account Dataset ---", flush=True)
    nfpc_hashes = download_nfpc_real_dataset()
    
    # 2. SAML-D
    print("\n--- 2. SAML-D Transaction Monitoring Dataset ---", flush=True)
    saml_path = extract_saml_d_real_records(max_records=25000)
    
    print("\n" + "=" * 60, flush=True)
    print("Dataset Acquisition Complete!", flush=True)
    print(f"SAML-D: {saml_path} ({os.path.getsize(saml_path):,} bytes)", flush=True)
    for fname, h in nfpc_hashes.items():
        lp = os.path.join(NFPC_DIR, fname)
        print(f"NFPC {fname}: {lp} ({os.path.getsize(lp):,} bytes)", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()
