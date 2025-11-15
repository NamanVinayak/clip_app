#!/usr/bin/env python3
"""
Setup Checker - Verify your Shorts Generator is ready to run
"""

import sys
import subprocess
from pathlib import Path


def check_python():
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (need 3.10+)")
        return False


def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg installed: {version_line}")
            return True
    except FileNotFoundError:
        print("❌ FFmpeg not found")
        print("   Install with: brew install ffmpeg")
        return False


def check_venv():
    """Check if virtual environment exists"""
    venv_path = Path('venv')
    if venv_path.exists():
        print("✅ Virtual environment exists")
        return True
    else:
        print("⚠️  Virtual environment not found")
        print("   Create with: python3 -m venv venv")
        return False


def check_dependencies():
    """Check if key dependencies are installed"""
    try:
        import fastapi
        import ultralytics
        import cv2
        import httpx
        print("✅ Python dependencies installed")
        print(f"   - FastAPI: {fastapi.__version__}")
        print(f"   - Ultralytics (YOLO): {ultralytics.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Install with: pip install -r requirements.txt")
        return False


def check_env_file():
    """Check if .env file exists and has required keys"""
    env_path = Path('.env')

    if not env_path.exists():
        print("❌ .env file not found")
        print("   Create with: cp .env.example .env")
        print("   Then edit with your API keys")
        return False

    # Read .env and check for keys
    with open(env_path, 'r') as f:
        content = f.read()

    required_keys = [
        'RUNPOD_API_KEY',
        'RUNPOD_ENDPOINT',
        'OPENROUTER_API_KEY'
    ]

    missing = []
    configured = []

    for key in required_keys:
        if key not in content:
            missing.append(key)
        elif f'{key}=' in content:
            # Check if it has a value (not just the example text)
            line = [l for l in content.split('\n') if l.startswith(key)][0]
            value = line.split('=')[1].strip()
            if value and 'your_' not in value.lower():
                configured.append(key)
            else:
                missing.append(key)

    if configured:
        print(f"✅ .env file exists with {len(configured)}/{len(required_keys)} keys configured")
        for key in configured:
            print(f"   ✓ {key}")

    if missing:
        print(f"⚠️  Missing or unconfigured keys:")
        for key in missing:
            print(f"   ✗ {key}")
        return False

    return len(missing) == 0


def check_folders():
    """Check if required folders exist"""
    folders = ['static', 'modules', 'utils']
    all_exist = True

    for folder in folders:
        path = Path(folder)
        if path.exists():
            print(f"✅ {folder}/ exists")
        else:
            print(f"❌ {folder}/ missing")
            all_exist = False

    return all_exist


def main():
    print("=" * 60)
    print("🔍 Automated Shorts Generator - Setup Checker")
    print("=" * 60)
    print()

    checks = [
        ("Python Version", check_python),
        ("FFmpeg", check_ffmpeg),
        ("Virtual Environment", check_venv),
        ("Python Dependencies", check_dependencies),
        ("Configuration (.env)", check_env_file),
        ("Project Folders", check_folders),
    ]

    results = []

    for name, check_func in checks:
        print(f"\n📋 Checking: {name}")
        print("-" * 60)
        results.append(check_func())
        print()

    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\n✅ Passed: {passed}/{total} checks")

    if passed == total:
        print("\n🎉 All checks passed! You're ready to run the app!")
        print("\nNext steps:")
        print("  1. source venv/bin/activate")
        print("  2. python main.py")
        print("  3. Open http://localhost:8000")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nQuick fixes:")
        if not results[0]:  # Python
            print("  - Install Python 3.10+")
        if not results[1]:  # FFmpeg
            print("  - brew install ffmpeg")
        if not results[2]:  # venv
            print("  - python3 -m venv venv")
        if not results[3]:  # Dependencies
            print("  - source venv/bin/activate")
            print("  - pip install -r requirements.txt")
        if not results[4]:  # .env
            print("  - cp .env.example .env")
            print("  - Edit .env with your API keys")

    print()


if __name__ == "__main__":
    main()
