"""
eMAG Response Validator - v4.4.9

Validates eMAG API responses according to official specifications.
Implements critical validation rules from eMAG API documentation.
"""

from typing import Dict, Any, List
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmagResponseValidator:
    """
    Validates eMAG API responses per v4.4.9 specifications.
    
    Critical requirements from eMAG API docs:
    1. Every response MUST have 'isError' field
    2. Missing 'isError' requires immediate alerting
    3. Documentation errors still result in offer being saved
    4. All requests/responses must be logged for 30 days
    """

    def __init__(self):
        """Initialize the validator."""
        self.validation_errors = []
        self.warnings = []

    def validate(self, response: Dict[str, Any], url: str, operation: str = "") -> Dict[str, Any]:
        """
        Validate eMAG API response.
        
        Args:
            response: API response dictionary
            url: Request URL for logging
            operation: Operation description for context
            
        Returns:
            Validated response dictionary
            
        Raises:
            ValueError: If response structure is invalid
            EmagApiError: If API returns non-documentation error
        """
        # CRITICAL: Check for isError field (per eMAG docs)
        if 'isError' not in response:
            error_msg = f"CRITICAL ALERT: Missing isError field in response from {url}"
            logger.critical(error_msg)
            self._send_critical_alert("Missing isError Field", url, response, operation)
            raise ValueError("Invalid eMAG response structure: missing isError field")

        # Check if there's an error
        if response.get('isError'):
            messages = response.get('messages', [])

            # Check if it's a documentation error
            if self._is_documentation_error(messages):
                # Per eMAG docs: Documentation errors still save the offer
                warning_msg = f"Documentation error for {operation} but offer saved: {messages}"
                logger.warning(warning_msg)
                self.warnings.append({
                    'type': 'documentation_error',
                    'operation': operation,
                    'url': url,
                    'messages': messages
                })
                # Don't raise error - offer is saved
                return response
            else:
                # Real API error
                error_msg = f"eMAG API error for {operation}: {messages}"
                logger.error(error_msg)
                from app.core.exceptions import ServiceError
                raise ServiceError(f"eMAG API error: {messages}")

        # Success - log and return
        logger.debug(f"Valid eMAG response for {operation} from {url}")
        return response

    def _is_documentation_error(self, messages: List[Any]) -> bool:
        """
        Check if error messages indicate documentation errors.
        
        Per eMAG API docs: Documentation errors still result in offer being saved.
        We need to treat these as warnings, not errors.
        
        Args:
            messages: List of error messages from API
            
        Returns:
            True if documentation error, False otherwise
        """
        documentation_keywords = [
            'documentation',
            'document',
            'validare',
            'validation',
            'caracteristic',
            'characteristic',
            'descriere',
            'description',
            'imagine',
            'image',
            'categorie',
            'category'
        ]

        for msg in messages:
            text = str(msg).lower()
            if any(keyword in text for keyword in documentation_keywords):
                return True

        return False

    def _send_critical_alert(
        self,
        alert_type: str,
        url: str,
        response: Dict[str, Any],
        operation: str
    ):
        """
        Send critical alert for missing isError field.
        
        Per eMAG docs: If response lacks isError field, set up alerts.
        This indicates the call was not interpreted correctly.
        
        Args:
            alert_type: Type of alert
            url: Request URL
            response: Response data
            operation: Operation description
        """
        alert_data = {
            'alert_type': alert_type,
            'severity': 'CRITICAL',
            'url': url,
            'operation': operation,
            'response_keys': list(response.keys()) if response else [],
            'response_sample': str(response)[:500]  # First 500 chars
        }

        # Log to critical channel
        logger.critical(f"EMAG API ALERT: {alert_type} - {alert_data}")

        # TODO: Integrate with alerting system (email, Slack, PagerDuty, etc.)
        # For now, just log critically
        self.validation_errors.append(alert_data)

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get summary of validation results.
        
        Returns:
            Dictionary with validation statistics
        """
        return {
            'total_errors': len(self.validation_errors),
            'total_warnings': len(self.warnings),
            'errors': self.validation_errors,
            'warnings': self.warnings
        }

    def reset(self):
        """Reset validation state."""
        self.validation_errors = []
        self.warnings = []


# Global validator instance
_validator = EmagResponseValidator()


def get_validator() -> EmagResponseValidator:
    """Get global validator instance."""
    return _validator


def validate_emag_response(
    response: Dict[str, Any],
    url: str,
    operation: str = ""
) -> Dict[str, Any]:
    """
    Convenience function to validate eMAG response.
    
    Args:
        response: API response dictionary
        url: Request URL
        operation: Operation description
        
    Returns:
        Validated response
    """
    return _validator.validate(response, url, operation)
