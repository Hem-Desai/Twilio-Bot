#!/usr/bin/env python3
"""
Python Setup Helper for SignalWire Project
This script helps locate Python 3.12 and set up the virtual environment.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def find_python_312():
    """Find Python 3.12 installation"""
    possible_commands = [
        "python3.12",
        "python3.12.exe", 
        "python312",
        "python",
        "py -3.12",
        "py -3.12-64"
    ]
    
    # Common Windows installation paths
    if platform.system() == "Windows":
        possible_paths = [
            r"C:\Python312\python.exe",
            r"C:\Program Files\Python312\python.exe", 
            r"C:\Program Files (x86)\Python312\python.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Python\Python312\python.exe"),
            os.path.expanduser(r"~\AppData\Local\Microsoft\WindowsApps\python3.12.exe"),
        ]
        
        # Check direct paths first
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
                    if "Python 3.12" in result.stdout:
                        return path
                except:
                    continue
    
    # Check commands in PATH
    for cmd in possible_commands:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and "Python 3.12" in result.stdout:
                return cmd
        except:
            continue
    
    return None

def setup_virtual_environment(python_path):
    """Set up virtual environment with Python 3.12"""
    print(f"🐍 Using Python: {python_path}")
    
    # Create virtual environment
    venv_path = Path("venv")
    if venv_path.exists():
        print("🗑️ Removing existing virtual environment...")
        if platform.system() == "Windows":
            subprocess.run(["rmdir", "/s", "/q", "venv"], shell=True)
        else:
            subprocess.run(["rm", "-rf", "venv"])
    
    print("📦 Creating new virtual environment...")
    result = subprocess.run([python_path, "-m", "venv", "venv"])
    if result.returncode != 0:
        print("❌ Failed to create virtual environment")
        return False
    
    # Determine activation script
    if platform.system() == "Windows":
        activate_script = "venv\\Scripts\\activate.bat"
        python_exe = "venv\\Scripts\\python.exe"
        pip_exe = "venv\\Scripts\\pip.exe"
    else:
        activate_script = "venv/bin/activate"
        python_exe = "venv/bin/python"
        pip_exe = "venv/bin/pip"
    
    print("⬆️ Upgrading pip...")
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    
    print("📥 Installing dependencies...")
    result = subprocess.run([pip_exe, "install", "-r", "requirements.txt"])
    if result.returncode != 0:
        print("⚠️ Some dependencies may have failed to install, but continuing...")
    
    print("✅ Virtual environment setup complete!")
    print(f"\n🚀 To activate the environment:")
    if platform.system() == "Windows":
        print(f"   {activate_script}")
    else:
        print(f"   source {activate_script}")
    
    print(f"\n🧪 To test the setup:")
    print(f"   {python_exe} start.py --test-services")
    
    return True

def main():
    print("🔍 SignalWire Project Python Setup")
    print("=" * 40)
    
    # Check if we're already in the right directory
    if not Path("requirements.txt").exists():
        print("❌ Please run this script from the llm_convo_signalwire directory")
        return 1
    
    # Find Python 3.12
    python_path = find_python_312()
    if not python_path:
        print("❌ Python 3.12 not found!")
        print("\n💡 Please install Python 3.12 from:")
        print("   - https://www.python.org/downloads/")
        print("   - Microsoft Store (search 'Python 3.12')")
        print("   - chocolatey: choco install python312")
        return 1
    
    print(f"✅ Found Python 3.12: {python_path}")
    
    # Verify version
    try:
        result = subprocess.run([python_path, "--version"], capture_output=True, text=True)
        print(f"📍 Version: {result.stdout.strip()}")
    except:
        print("⚠️ Could not verify Python version")
    
    # Set up virtual environment
    if not setup_virtual_environment(python_path):
        return 1
    
    print("\n🎉 Setup complete! You can now run the SignalWire system.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 