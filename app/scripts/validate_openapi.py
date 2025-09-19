#!/usr/bin/env python3
"""
OpenAPI Schema Validator

This script validates the generated OpenAPI schema against the OpenAPI 3.1.1 specification.
It checks for common issues like missing examples, descriptions, and response schemas.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import jsonschema
import yaml
import requests

# Constants
PROJECT_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = PROJECT_ROOT / "api" / "openapi.json"
OPENAPI_3_1_1_SCHEMA_URL = "https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/schemas/v3.1/schema.json"

class OpenAPIValidator:
    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        self.openapi_schema = self._load_schema()
        self.issues: List[Dict[str, str]] = []

    def _load_schema(self) -> Dict[str, Any]:
        """Load the OpenAPI schema from file."""
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            if self.schema_path.suffix == '.yaml':
                return yaml.safe_load(f)
            return json.load(f)

    def _add_issue(self, path: str, message: str, level: str = "error") -> None:
        """Add an issue to the list of found issues."""
        self.issues.append({
            "path": path,
            "message": message,
            "level": level
        })

    def _check_required_fields(self) -> None:
        """Check for required fields in the OpenAPI schema."""
        required_fields = ["openapi", "info", "paths"]
        for field in required_fields:
            if field not in self.openapi_schema:
                self._add_issue("/", f"Missing required field: {field}")

    def _check_info_section(self) -> None:
        """Validate the info section of the OpenAPI schema."""
        info = self.openapi_schema.get("info", {})
        
        if not info.get("description"):
            self._add_issue("/info/description", "API description is missing")
            
        if not info.get("version"):
            self._add_issue("/info/version", "API version is missing")
            
        if not info.get("contact", {}).get("email"):
            self._add_issue("/info/contact/email", "Contact email is missing")

    def _check_paths(self) -> None:
        """Check all paths in the OpenAPI schema."""
        for path, path_item in self.openapi_schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.startswith("x-") or method == "parameters":
                    continue
                    
                self._check_operation(path, method, operation)

    def _check_operation(self, path: str, method: str, operation: Dict[str, Any]) -> None:
        """Check a single operation in the OpenAPI schema."""
        op_path = f"paths.{path}.{method}"
        
        # Check for operation summary and description
        if not operation.get("summary"):
            self._add_issue(f"{op_path}.summary", "Operation summary is missing", "warning")
            
        if not operation.get("description"):
            self._add_issue(f"{op_path}.description", "Operation description is missing", "warning")
        
        # Check for tags
        if not operation.get("tags"):
            self._add_issue(f"{op_path}.tags", "Operation is missing tags", "warning")
        
        # Check for parameters
        for param in operation.get("parameters", []):
            self._check_parameter(op_path, param)
        
        # Check for request body
        if "requestBody" in operation:
            self._check_request_body(op_path, operation["requestBody"])
        
        # Check for responses
        self._check_responses(op_path, operation.get("responses", {}))

    def _check_parameter(self, op_path: str, param: Dict[str, Any]) -> None:
        """Check a single parameter in an operation."""
        param_path = f"{op_path}.parameters.{param.get('name', 'unknown')}"
        
        if not param.get("description"):
            self._add_issue(f"{param_path}.description", "Parameter description is missing", "warning")
            
        if "schema" in param and "example" not in param:
            self._add_issue(f"{param_path}.example", "Parameter example is missing", "info")

    def _check_request_body(self, op_path: str, request_body: Dict[str, Any]) -> None:
        """Check the request body of an operation."""
        body_path = f"{op_path}.requestBody"
        
        if not request_body.get("description"):
            self._add_issue(f"{body_path}.description", "Request body description is missing", "warning")
        
        for content_type, media_type in request_body.get("content", {}).items():
            if "example" not in media_type and "examples" not in media_type:
                self._add_issue(
                    f"{body_path}.content.{content_type}.example",
                    f"Example is missing for content type {content_type}",
                    "info"
                )

    def _check_responses(self, op_path: str, responses: Dict[str, Any]) -> None:
        """Check the responses of an operation."""
        if not responses:
            self._add_issue(f"{op_path}.responses", "No responses defined", "error")
            return
            
        # Check for at least one successful response
        if not any(status.startswith('2') for status in responses):
            self._add_issue(
                f"{op_path}.responses",
                "No successful (2xx) response defined",
                "warning"
            )
            
        # Check each response
        for status_code, response in responses.items():
            self._check_response(op_path, status_code, response)

    def _check_response(self, op_path: str, status_code: str, response: Dict[str, Any]) -> None:
        """Check a single response in an operation."""
        resp_path = f"{op_path}.responses.{status_code}"
        
        if not response.get("description"):
            self._add_issue(f"{resp_path}.description", "Response description is missing")
            
        # Check response content
        for content_type, media_type in response.get("content", {}).items():
            if "example" not in media_type and "examples" not in media_type:
                self._add_issue(
                    f"{resp_path}.content.{content_type}.example",
                    f"Example is missing for content type {content_type}",
                    "info"
                )

    def validate_against_spec(self) -> bool:
        """Validate the schema against the OpenAPI 3.1.1 specification."""
        try:
            # Download the OpenAPI 3.1.1 schema
            response = requests.get(OPENAPI_3_1_1_SCHEMA_URL, timeout=10)
            response.raise_for_status()
            schema_validator = jsonschema.Draft7Validator(response.json())
            
            # Validate against the schema
            errors = list(schema_validator.iter_errors(self.openapi_schema))
            
            for error in errors:
                self._add_issue(
                    ".".join(map(str, error.absolute_path)),
                    f"Schema validation error: {error.message}"
                )
                
            return not errors
            
        except Exception as e:
            self._add_issue("", f"Failed to validate against OpenAPI 3.1.1 schema: {str(e)}")
            return False

    def run_checks(self) -> bool:
        """Run all validation checks."""
        self._check_required_fields()
        self._check_info_section()
        self._check_paths()
        
        # Only run schema validation if other checks pass
        if not self.issues:
            self.validate_against_spec()
        
        return not any(issue["level"] == "error" for issue in self.issues)

    def print_report(self) -> None:
        """Print a report of all found issues."""
        if not self.issues:
            print("✅ No issues found in the OpenAPI schema!")
            return
            
        # Group issues by level
        issues_by_level = {"error": [], "warning": [], "info": []}
        for issue in self.issues:
            issues_by_level[issue["level"]].append(issue)
        
        # Print summary
        print(f"\nOpenAPI Schema Validation Report for {self.schema_path}")
        print("=" * 80)
        print(f"Errors: {len(issues_by_level['error'])}")
        print(f"Warnings: {len(issues_by_level['warning'])}")
        print(f"Info: {len(issues_by_level['info'])}")
        print("=" * 80)
        
        # Print details
        for level in ["error", "warning", "info"]:
            if issues_by_level[level]:
                print(f"\n{level.upper()}S:")
                for issue in issues_by_level[level]:
                    print(f"- [{level.upper()}] {issue['path']}: {issue['message']}")

def main() -> int:
    """Main function to run the validator."""
    if not SCHEMA_PATH.exists():
        print(f"Error: OpenAPI schema not found at {SCHEMA_PATH}")
        print("Please run 'make openapi' to generate the schema first.")
        return 1
    
    print(f"Validating OpenAPI schema at {SCHEMA_PATH}...")
    
    validator = OpenAPIValidator(SCHEMA_PATH)
    is_valid = validator.run_checks()
    validator.print_report()
    
    return 0 if is_valid else 1

if __name__ == "__main__":
    sys.exit(main())
