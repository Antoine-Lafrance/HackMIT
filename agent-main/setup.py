#!/usr/bin/env python3
"""
Deployment and setup script for the minimalist agent
"""

import os
import subprocess
import sys


def run_command(cmd, description):
    """Run a command and show the result."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"❌ {description} failed")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False


def check_python_version():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is supported")
        return True
    else:
        print(
            f"❌ Python {version.major}.{version.minor}.{version.micro} is not supported. Need Python 3.8+"
        )
        return False


def install_dependencies():
    """Install required dependencies."""
    dependencies = ["modal", "anthropic", "mcp"]

    for dep in dependencies:
        if not run_command(f"pip install {dep}", f"Installing {dep}"):
            return False
    return True


def setup_modal():
    """Set up Modal authentication."""
    print("🚀 Setting up Modal...")
    print("If you don't have a Modal account, create one at https://modal.com")

    # Check if modal is already set up
    result = subprocess.run(
        "modal token current", shell=True, capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ Modal is already authenticated")
        return True

    print("Setting up Modal authentication...")
    return run_command("modal setup", "Modal authentication")


def create_modal_secret():
    """Create Modal secret for Anthropic API key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY=your_api_key_here")
        return False

    # Create the secret
    return run_command(
        f'modal secret create anthropic-api-key ANTHROPIC_API_KEY="{api_key}"',
        "Creating Modal secret for Anthropic API key",
    )


def test_deployment():
    """Test the deployment."""
    print("🧪 Testing deployment...")

    # Test local agent
    print("Testing local agent functionality...")
    if not run_command("python test_agent.py", "Local agent test"):
        print("⚠️  Local test failed, but Modal deployment might still work")

    # Test Modal deployment
    print("Testing Modal deployment...")
    return run_command("modal run agent.py", "Modal deployment test")


def main():
    """Main deployment script."""
    print("🚀 MINIMALIST AGENT DEPLOYMENT SETUP")
    print("=" * 50)

    steps = [
        ("Check Python version", check_python_version),
        ("Install dependencies", install_dependencies),
        ("Setup Modal", setup_modal),
        ("Create Modal secret", create_modal_secret),
        ("Test deployment", test_deployment),
    ]

    for step_name, step_func in steps:
        print(f"\n📋 Step: {step_name}")
        if not step_func():
            print(f"❌ Setup failed at step: {step_name}")
            print("\nTroubleshooting:")
            print("1. Make sure you have set ANTHROPIC_API_KEY environment variable")
            print("2. Ensure you have a Modal account at https://modal.com")
            print("3. Check that all dependencies installed correctly")
            sys.exit(1)

    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Run locally: python test_agent.py")
    print("2. Deploy to Modal: modal run agent.py")
    print("3. Check the README.md for more usage examples")

    print("\nExample usage:")
    print(
        """
from agent import MinimalistAgent, AgentConfig

# Create agent
config = AgentConfig(anthropic_api_key="your-key")
agent = MinimalistAgent(config)

# Process context
result = await agent.process_context({
    "question": "What's 2 + 2?",
    "context": "Simple math question"
})
print(result)
    """
    )


if __name__ == "__main__":
    main()
