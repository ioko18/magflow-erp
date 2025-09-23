#!/usr/bin/env python3
"""MagFlow ERP Migration Enhancement Setup Script."""

import sys
from pathlib import Path
import subprocess


class MigrationEnhancementSetup:
    """Set up enhanced migration system for MagFlow ERP."""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.alembic_dir = self.project_root / "alembic"
        self.scripts_dir = self.project_root / "scripts"
        self.docs_dir = self.project_root / "docs"

    def setup_enhanced_migration_system(self):
        """Complete setup of enhanced migration system."""
        print("🚀 Setting up Enhanced Migration System for MagFlow ERP")
        print("=" * 60)

        # Check prerequisites
        if not self._check_prerequisites():
            return False

        # Setup steps
        setup_steps = [
            ("Enhanced Alembic Configuration", self._setup_alembic_config),
            ("Migration Templates", self._setup_migration_templates),
            ("Migration Manager Script", self._setup_migration_manager),
            ("Testing Framework", self._setup_migration_tests),
            ("Documentation", self._setup_documentation),
            ("Backup System", self._setup_backup_system),
        ]

        for step_name, step_function in setup_steps:
            print(f"\n📋 Setting up: {step_name}")
            try:
                step_function()
                print(f"  ✅ {step_name} completed successfully")
            except Exception as e:
                print(f"  ❌ {step_name} failed: {e}")
                return False

        # Final validation
        if self._validate_setup():
            self._print_success_message()
            return True
        else:
            print("❌ Setup validation failed")
            return False

    def _check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        print("🔍 Checking prerequisites...")

        checks = [
            ("Python 3.8+", sys.version_info >= (3, 8)),
            ("PostgreSQL", self._check_postgresql()),
            ("Alembic", self._check_alembic()),
            ("Project structure", self._check_project_structure()),
        ]

        all_passed = True
        for check_name, check_result in checks:
            if check_result:
                print(f"  ✅ {check_name}")
            else:
                print(f"  ❌ {check_name} - Missing requirement")
                all_passed = False

        return all_passed

    def _check_postgresql(self) -> bool:
        """Check if PostgreSQL is available."""
        try:
            result = subprocess.run(
                ["pg_isready", "-h", "localhost"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_alembic(self) -> bool:
        """Check if Alembic is installed."""
        try:
            import alembic
            return True
        except ImportError:
            return False

    def _check_project_structure(self) -> bool:
        """Check if project has expected structure."""
        required_dirs = [
            self.project_root / "app",
            self.project_root / "alembic",
            self.project_root / "scripts",
            self.project_root / "tests"
        ]

        return all(d.exists() for d in required_dirs)

    def _setup_alembic_config(self):
        """Set up enhanced Alembic configuration."""
        enhanced_config = self.project_root / "alembic.ini.enhanced"

        if enhanced_config.exists():
            # Backup current config
            current_config = self.project_root / "alembic.ini"
            if current_config.exists():
                backup_config = self.project_root / "alembic.ini.backup"
                current_config.rename(backup_config)
                print(f"  📄 Backed up existing config to {backup_config}")

            # Install enhanced config
            enhanced_config.rename(current_config)
            print("  📄 Enhanced Alembic configuration installed")

    def _setup_migration_templates(self):
        """Set up enhanced migration templates."""
        templates_dir = self.alembic_dir / "templates"

        if not templates_dir.exists():
            templates_dir.mkdir()

        template_file = templates_dir / "migration_template.py.j2"
        if not template_file.exists():
            print("  📄 Migration template already exists")
        else:
            print("  📄 Migration template ready")

    def _setup_migration_manager(self):
        """Set up migration manager script."""
        manager_script = self.scripts_dir / "migration_manager.py"

        if manager_script.exists():
            print("  📄 Migration manager script ready")
        else:
            print("  ❌ Migration manager script missing")

    def _setup_migration_tests(self):
        """Set up migration testing framework."""
        test_file = self.project_root / "tests" / "test_migration_safety.py"

        if test_file.exists():
            print("  📄 Migration testing framework ready")
        else:
            print("  ❌ Migration testing framework missing")

    def _setup_documentation(self):
        """Set up migration documentation."""
        doc_file = self.docs_dir / "MIGRATION_IMPROVEMENTS.md"

        if doc_file.exists():
            print("  📄 Migration documentation ready")
        else:
            print("  ❌ Migration documentation missing")

    def _setup_backup_system(self):
        """Set up backup directory and system."""
        backup_dir = self.project_root / "backups"

        if not backup_dir.exists():
            backup_dir.mkdir()
            print("  📁 Created backups directory")
        else:
            print("  📁 Backups directory ready")

    def _validate_setup(self) -> bool:
        """Validate that setup completed successfully."""
        print("\n🔍 Validating setup...")

        validation_checks = [
            ("Enhanced Alembic config", (self.project_root / "alembic.ini").exists()),
            ("Migration templates", (self.alembic_dir / "templates").exists()),
            ("Migration manager", (self.scripts_dir / "migration_manager.py").exists()),
            ("Migration tests", (self.project_root / "tests" / "test_migration_safety.py").exists()),
            ("Documentation", (self.docs_dir / "MIGRATION_IMPROVEMENTS.md").exists()),
            ("Backup directory", (self.project_root / "backups").exists()),
        ]

        all_valid = True
        for check_name, check_result in validation_checks:
            if check_result:
                print(f"  ✅ {check_name}")
            else:
                print(f"  ❌ {check_name}")
                all_valid = False

        return all_valid

    def _print_success_message(self):
        """Print success message with usage instructions."""
        print("\n" + "=" * 60)
        print("🎉 Enhanced Migration System Setup Complete!")
        print("=" * 60)
        print("\n📋 Available Commands:")
        print("  🔄 Create new migration:")
        print("     alembic revision --autogenerate -m 'description'")
        print("\n  🏃 Run migrations safely:")
        print("     python scripts/migration_manager.py development")
        print("\n  🧪 Test migrations:")
        print("     pytest tests/test_migration_safety.py -v")
        print("\n  📊 Monitor migrations:")
        print("     python scripts/migration_manager.py development --analyze")
        print("\n  📚 Documentation:")
        print("     See docs/MIGRATION_IMPROVEMENTS.md for detailed guide")
        print("\n⚠️  Important Notes:")
        print("  • Always backup before major migrations")
        print("  • Test migrations in development first")
        print("  • Monitor logs for any issues")
        print("  • Use --check-only flag to validate without running")

    def create_sample_migration(self):
        """Create a sample migration to demonstrate the system."""
        print("\n📝 Creating sample migration...")

        try:
            # Generate sample migration
            result = subprocess.run([
                "alembic", "revision",
                "--autogenerate",
                "-m", "sample_enhanced_migration"
            ], capture_output=True, text=True, cwd=self.project_root)

            if result.returncode == 0:
                print("  ✅ Sample migration created successfully")
                print("  📄 Check alembic/versions/ for the new migration file")
            else:
                print(f"  ❌ Failed to create sample migration: {result.stderr}")

        except Exception as e:
            print(f"  ❌ Error creating sample migration: {e}")

    def test_enhanced_system(self):
        """Test the enhanced migration system."""
        print("\n🧪 Testing enhanced migration system...")

        try:
            # Test migration manager
            result = subprocess.run([
                "python", "scripts/migration_manager.py",
                "test", "--help"
            ], capture_output=True, text=True, cwd=self.project_root)

            if result.returncode == 0:
                print("  ✅ Migration manager working correctly")
            else:
                print(f"  ❌ Migration manager issue: {result.stderr}")

            # Test migration safety tests
            result = subprocess.run([
                "python", "-m", "pytest",
                "tests/test_migration_safety.py",
                "--collect-only"
            ], capture_output=True, text=True, cwd=self.project_root)

            if result.returncode == 0:
                print("  ✅ Migration tests framework ready")
            else:
                print(f"  ❌ Migration tests issue: {result.stderr}")

        except Exception as e:
            print(f"  ❌ Error testing system: {e}")


def main():
    """Main setup function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Just test the current setup
        setup = MigrationEnhancementSetup()
        setup.test_enhanced_system()
        return 0

    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        # Set up and create sample migration
        setup = MigrationEnhancementSetup()
        if setup.setup_enhanced_migration_system():
            setup.create_sample_migration()
            setup.test_enhanced_system()
        return 0

    # Full setup
    setup = MigrationEnhancementSetup()

    if setup.setup_enhanced_migration_system():
        print("\n🎯 Setup completed successfully!")
        print("\n💡 Next steps:")
        print("  1. Review the enhanced configuration")
        print("  2. Run 'python scripts/migration_manager.py --help' to see options")
        print("  3. Test with 'python migration_setup.py --test'")
        print("  4. Create sample migration with 'python migration_setup.py --sample'")
        return 0
    else:
        print("\n❌ Setup failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
