#!/usr/bin/env python3
"""
Setup script for Social Media Analytics Platform
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {command}")
            print(f"Error output: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command {command}: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    dependencies = {
        'docker': 'Docker',
        'docker-compose': 'Docker Compose',
        'python': 'Python 3.11+',
        'node': 'Node.js 18+'
    }
    
    missing = []
    for cmd, name in dependencies.items():
        if not shutil.which(cmd):
            missing.append(name)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("\nPlease install the missing dependencies and try again.")
        return False
    
    print("✅ All dependencies found!")
    return True

def setup_environment():
    """Setup environment variables"""
    print("🔧 Setting up environment...")
    
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from .env.example")
        print("📝 Please edit .env file with your configuration")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("❌ No .env.example file found")
        return False
    
    return True

def build_services():
    """Build Docker services"""
    print("🏗️  Building Docker services...")
    
    if not run_command("docker-compose build"):
        print("❌ Failed to build Docker services")
        return False
    
    print("✅ Docker services built successfully!")
    return True

def start_services():
    """Start the services"""
    print("🚀 Starting services...")
    
    if not run_command("docker-compose up -d"):
        print("❌ Failed to start services")
        return False
    
    print("✅ Services started successfully!")
    return True

def check_services():
    """Check if services are running"""
    print("🔍 Checking service health...")
    
    import time
    import requests
    
    services = {
        'API Gateway': 'http://localhost:8000/health',
        'ML Service': 'http://localhost:8001/health',
        'Analytics API': 'http://localhost:8002/health',
        'Frontend': 'http://localhost:3000'
    }
    
    print("⏳ Waiting for services to start (this may take a few minutes)...")
    time.sleep(30)  # Give services time to start
    
    for service, url in services.items():
        for attempt in range(5):
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    print(f"✅ {service} is healthy")
                    break
            except:
                if attempt < 4:
                    print(f"⏳ Waiting for {service}... (attempt {attempt + 1}/5)")
                    time.sleep(10)
                else:
                    print(f"❌ {service} is not responding")

def install_frontend_deps():
    """Install frontend dependencies"""
    print("📦 Installing frontend dependencies...")
    
    frontend_dir = Path('frontend')
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    if not run_command("npm install", cwd=frontend_dir):
        print("❌ Failed to install frontend dependencies")
        return False
    
    print("✅ Frontend dependencies installed!")
    return True

def show_urls():
    """Show service URLs"""
    print("\n🌐 Service URLs:")
    print("=" * 50)
    print("📊 Dashboard:        http://localhost:3000")
    print("🔌 API Gateway:      http://localhost:8000")
    print("📚 API Docs:         http://localhost:8000/docs")
    print("🤖 ML Service:       http://localhost:8001")
    print("📈 Analytics API:    http://localhost:8002")
    print("🐘 PostgreSQL:       localhost:5432")
    print("🔴 Redis:            localhost:6379")
    print("📊 Grafana:          http://localhost:3001 (admin/admin)")
    print("🔍 Prometheus:       http://localhost:9090")
    print("=" * 50)

def main():
    """Main setup function"""
    print("🚀 Social Media Analytics Platform Setup")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Install frontend dependencies (optional for Docker setup)
    print("\n📦 Would you like to install frontend dependencies for local development? (y/n)")
    if input().lower().startswith('y'):
        install_frontend_deps()
    
    # Build and start services
    if not build_services():
        sys.exit(1)
    
    if not start_services():
        sys.exit(1)
    
    # Check service health
    check_services()
    
    # Show URLs
    show_urls()
    
    print("\n🎉 Setup complete!")
    print("\n📝 Next steps:")
    print("1. Visit http://localhost:3000 to see the dashboard")
    print("2. Check the API documentation at http://localhost:8000/docs")
    print("3. Monitor services with 'docker-compose logs -f'")
    print("4. Stop services with 'docker-compose down'")
    
    print("\n💡 Tips:")
    print("- The system generates sample data automatically")
    print("- Check the logs if any service isn't working")
    print("- Edit .env file to customize configuration")

if __name__ == "__main__":
    main()