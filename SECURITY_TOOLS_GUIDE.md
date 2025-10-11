# 🔒 Security Tools Quick Start Guide

## Installed Tools

1. **Bandit** - Python security linter
2. **Safety** - Dependency vulnerability scanner
3. **pip-audit** - Python package auditor
4. **Semgrep** - Static analysis tool
5. **Ruff** - Fast Python linter
6. **mypy** - Static type checker

## Usage

### Run Complete Security Scan
```bash
./scripts/security/run_security_scan.sh
```

### Run Individual Tools

#### Bandit (Security Linter)
```bash
bandit -r app/ -ll
```

#### Safety (Dependency Scanner)
```bash
safety check
```

#### pip-audit (Package Auditor)
```bash
pip-audit
```

#### Ruff (Fast Linter)
```bash
ruff check app/
```

#### mypy (Type Checker)
```bash
mypy app/
```

### Pre-commit Hook

The pre-commit hook runs automatically on `git commit`. To bypass (not recommended):
```bash
git commit --no-verify
```

### View Reports

Security scan reports are saved in `security-reports/`:
```bash
ls -la security-reports/
```

## CI/CD Integration

Add to your CI/CD pipeline:
```yaml
- name: Run Security Scan
  run: ./scripts/security/run_security_scan.sh
```

## Troubleshooting

### Tool not found
```bash
pip install bandit safety pip-audit semgrep ruff mypy
```

### Permission denied
```bash
chmod +x scripts/security/run_security_scan.sh
chmod +x .git/hooks/pre-commit
```
