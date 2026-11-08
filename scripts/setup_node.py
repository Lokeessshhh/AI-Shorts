"""
Script to install portable Node.js LTS into tools/node if not present.
Requires zero admin privileges.
"""
import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
NODE_DIR = TOOLS_DIR / "node"
NODE_EXE = NODE_DIR / "node.exe"
NPM_CMD = NODE_DIR / "npm.cmd"

# Node.js 20.18.0 LTS 64-bit Windows binary zip
NODE_ZIP_URL = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-win-x64.zip"
ZIP_DEST = TOOLS_DIR / "node_temp.zip"

def setup_node():
    if NODE_EXE.exists() and NPM_CMD.exists():
        print(f"Node.js already present at: {NODE_EXE}")
        try:
            res = subprocess.run([str(NODE_EXE), "--version"], capture_output=True, text=True)
            print(f"Version: {res.stdout.strip()}")
            return str(NODE_DIR)
        except Exception as e:
            print(f"Error checking version: {e}")

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Node.js from {NODE_ZIP_URL}...")
    
    urllib.request.urlretrieve(NODE_ZIP_URL, ZIP_DEST)
    print(f"Downloaded to {ZIP_DEST}. Extracting...")

    with zipfile.ZipFile(ZIP_DEST, 'r') as zip_ref:
        zip_ref.extractall(TOOLS_DIR)

    extracted_dir = TOOLS_DIR / "node-v20.18.0-win-x64"
    if NODE_DIR.exists():
        shutil.rmtree(NODE_DIR, ignore_errors=True)
        
    extracted_dir.rename(NODE_DIR)
    if ZIP_DEST.exists():
        ZIP_DEST.unlink()

    print(f"Node.js installed successfully to {NODE_DIR}!")
    
    # Test execution
    res_node = subprocess.run([str(NODE_EXE), "--version"], capture_output=True, text=True)
    res_npm = subprocess.run([str(NPM_CMD), "--version"], capture_output=True, text=True)
    print(f"Node version: {res_node.stdout.strip()}")
    print(f"NPM version:  {res_npm.stdout.strip()}")
    return str(NODE_DIR)

if __name__ == "__main__":
    setup_node()
