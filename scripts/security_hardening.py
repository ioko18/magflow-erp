#!/usr/bin/env python3
"""
MagFlow ERP - Security Hardening Script

This script implements comprehensive security hardening measures
for the MagFlow ERP application.
"""

import os
import sys
import secrets
import json
from pathlib import Path
from typing import Dict, Any
import subprocess


class SecurityHardening:
    """Security hardening implementation for MagFlow ERP."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.security_report = {
            "timestamp": None,
            "checks": [],
            "recommendations": [],
            "score": 0
        }
    
    def generate_secure_secret_key(self) -> str:
        """Generate a cryptographically secure secret key."""
        return secrets.token_hex(32)
    
    def check_environment_security(self) -> Dict[str, Any]:
        """Check environment variable security."""
        env_file = self.project_root / ".env"
        issues = []
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
                
            # Check for default/weak values
            weak_patterns = [
                ("SECRET_KEY", ["changeme", "secret", "default", "test"]),
                ("DATABASE_PASSWORD", ["password", "admin", "root", ""]),
                ("REDIS_PASSWORD", ["", "password", "redis"]),
                ("JWT_SECRET_KEY", ["secret", "jwt", "changeme"]),
            ]
            
            for var_name, weak_values in weak_patterns:
                for weak_value in weak_values:
                    if f"{var_name}={weak_value}" in content:
                        issues.append(f"Weak {var_name}: {weak_value}")
        else:
            issues.append("No .env file found")
        
        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "recommendations": [
                "Use strong, unique passwords",
                "Generate secure secret keys",
                "Never commit .env files to version control"
            ]
        }
    
    def check_dependency_vulnerabilities(self) -> Dict[str, Any]:
        """Check for known vulnerabilities in dependencies."""
        try:
            # Run safety check
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return {
                    "status": "PASS",
                    "vulnerabilities": [],
                    "message": "No known vulnerabilities found"
                }
            else:
                try:
                    vulns = json.loads(result.stdout)
                    return {
                        "status": "FAIL",
                        "vulnerabilities": vulns,
                        "message": f"Found {len(vulns)} vulnerabilities"
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "ERROR",
                        "message": "Could not parse safety output"
                    }
        except FileNotFoundError:
            return {
                "status": "SKIP",
                "message": "Safety tool not installed"
            }
    
    def check_file_permissions(self) -> Dict[str, Any]:
        """Check file permissions for security issues."""
        sensitive_files = [
            ".env",
            "app/core/security.py",
            "scripts/",
            "docker-compose.yml"
        ]
        
        issues = []
        
        for file_path in sensitive_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                stat = full_path.stat()
                mode = oct(stat.st_mode)[-3:]
                
                # Check if file is world-readable/writable
                if int(mode[2]) > 0:
                    issues.append(f"{file_path}: World-accessible ({mode})")
        
        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "recommendations": [
                "Restrict sensitive file permissions",
                "Use chmod 600 for .env files",
                "Use chmod 755 for scripts"
            ]
        }
    
    def check_code_security(self) -> Dict[str, Any]:
        """Run static code security analysis."""
        try:
            # Run bandit security scan
            result = subprocess.run(
                ["bandit", "-r", "app/", "-f", "json"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return {
                    "status": "PASS",
                    "issues": [],
                    "message": "No security issues found in code"
                }
            else:
                try:
                    report = json.loads(result.stdout)
                    issues = report.get("results", [])
                    return {
                        "status": "FAIL" if issues else "PASS",
                        "issues": [
                            f"{issue['filename']}:{issue['line_number']} - {issue['issue_text']}"
                            for issue in issues
                        ],
                        "message": f"Found {len(issues)} security issues"
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "ERROR",
                        "message": "Could not parse bandit output"
                    }
        except FileNotFoundError:
            return {
                "status": "SKIP",
                "message": "Bandit tool not installed"
            }
    
    def check_docker_security(self) -> Dict[str, Any]:
        """Check Docker configuration security."""
        dockerfile = self.project_root / "Dockerfile"
        compose_file = self.project_root / "docker-compose.yml"
        
        issues = []
        
        if dockerfile.exists():
            with open(dockerfile, 'r') as f:
                content = f.read()
                
            # Check for security issues
            if "USER root" in content:
                issues.append("Dockerfile: Running as root user")
            if "--privileged" in content:
                issues.append("Dockerfile: Using privileged mode")
        
        if compose_file.exists():
            with open(compose_file, 'r') as f:
                content = f.read()
                
            # Check for security issues
            if "privileged: true" in content:
                issues.append("Docker Compose: Using privileged mode")
            if "network_mode: host" in content:
                issues.append("Docker Compose: Using host networking")
        
        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "recommendations": [
                "Run containers as non-root user",
                "Avoid privileged mode",
                "Use specific network configurations"
            ]
        }
    
    def apply_security_fixes(self) -> Dict[str, Any]:
        """Apply automatic security fixes."""
        fixes_applied = []
        
        # Generate secure secret key if needed
        env_file = self.project_root / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
            
            if "SECRET_KEY=changeme" in content or "SECRET_KEY=secret" in content:
                new_key = self.generate_secure_secret_key()
                content = content.replace("SECRET_KEY=changeme", f"SECRET_KEY={new_key}")
                content = content.replace("SECRET_KEY=secret", f"SECRET_KEY={new_key}")
                
                with open(env_file, 'w') as f:
                    f.write(content)
                
                fixes_applied.append("Generated secure SECRET_KEY")
        
        # Fix file permissions
        sensitive_files = [".env"]
        for file_path in sensitive_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                os.chmod(full_path, 0o600)
                fixes_applied.append(f"Fixed permissions for {file_path}")
        
        return {
            "status": "SUCCESS",
            "fixes_applied": fixes_applied,
            "message": f"Applied {len(fixes_applied)} security fixes"
        }
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        print("🔒 Running MagFlow ERP Security Hardening...")
        
        # Run all security checks
        checks = {
            "environment": self.check_environment_security(),
            "dependencies": self.check_dependency_vulnerabilities(),
            "file_permissions": self.check_file_permissions(),
            "code_security": self.check_code_security(),
            "docker_security": self.check_docker_security()
        }
        
        # Calculate security score
        total_checks = len(checks)
        passed_checks = sum(1 for check in checks.values() if check["status"] == "PASS")
        security_score = int((passed_checks / total_checks) * 100)
        
        # Generate recommendations
        recommendations = []
        for check_name, check_result in checks.items():
            if check_result["status"] == "FAIL":
                recommendations.extend(check_result.get("recommendations", []))
        
        report = {
            "timestamp": subprocess.check_output(["date"], text=True).strip(),
            "checks": checks,
            "security_score": security_score,
            "recommendations": list(set(recommendations)),
            "overall_status": "SECURE" if security_score >= 80 else "NEEDS_IMPROVEMENT"
        }
        
        return report
    
    def run_hardening(self, apply_fixes: bool = False) -> None:
        """Run complete security hardening process."""
        print("=" * 50)
        print("🛡️  MagFlow ERP Security Hardening")
        print("=" * 50)
        
        # Generate security report
        report = self.generate_security_report()
        
        # Print summary
        print(f"\n📊 Security Score: {report['security_score']}%")
        print(f"🔍 Overall Status: {report['overall_status']}")
        
        # Print check results
        print("\n📋 Security Check Results:")
        for check_name, result in report["checks"].items():
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"  {status_icon} {check_name.replace('_', ' ').title()}: {result['status']}")
            
            if result.get("issues"):
                for issue in result["issues"][:3]:  # Show first 3 issues
                    print(f"    - {issue}")
                if len(result["issues"]) > 3:
                    print(f"    ... and {len(result['issues']) - 3} more")
        
        # Print recommendations
        if report["recommendations"]:
            print("\n💡 Security Recommendations:")
            for i, rec in enumerate(report["recommendations"][:5], 1):
                print(f"  {i}. {rec}")
        
        # Apply fixes if requested
        if apply_fixes:
            print("\n🔧 Applying Security Fixes...")
            fixes = self.apply_security_fixes()
            for fix in fixes["fixes_applied"]:
                print(f"  ✅ {fix}")
        
        # Save report
        report_file = self.project_root / f"security_report_{report['timestamp'].replace(' ', '_').replace(':', '-')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        print("=" * 50)


def main():
    """Main entry point."""
    hardening = SecurityHardening()
    
    # Check command line arguments
    apply_fixes = "--fix" in sys.argv
    
    try:
        hardening.run_hardening(apply_fixes=apply_fixes)
    except KeyboardInterrupt:
        print("\n⚠️  Security hardening interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during security hardening: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
