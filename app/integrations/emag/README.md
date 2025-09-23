# eMAG Marketplace Integration

This module provides integration with the eMAG Marketplace API, supporting both Seller-Fulfilled (MAIN) and Fulfilled by eMAG (FBE) account types.

## Features

- Support for both MAIN (Seller-Fulfilled) and FBE (Fulfilled by eMAG) accounts
- Automatic rate limiting and retry logic
- Comprehensive error handling
- Async/await support
- Type hints and data validation
- Environment-based configuration

## Installation

1. Install dependencies:
   ```bash
   pip install aiohttp pydantic python-dotenv
   ```

2. Copy the example environment file:
   ```bash
   cp config/examples/.env.emag.example .env
   ```

3. Update the `.env` file with your eMAG API credentials and settings.

## Usage

### Basic Example

```python
import asyncio
from app.integrations.emag import get_client, EmagAccountType

async def main():
    # Get a client for the MAIN account
    async with get_client(account_type=EmagAccountType.MAIN) as client:
        try:
            # Example: Get categories
            categories = await client.get("category/read")
            print(f"Found {len(categories)} categories")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Available Account Types

- `EmagAccountType.MAIN`: Seller-Fulfilled Network (SFN)
- `EmagAccountType.FBE`: Fulfilled by eMAG

### Configuration

Configuration is done through environment variables. See `.env.emag.example` for all available options.

## API Reference

### Client Methods

- `get(endpoint, **kwargs)`: Make a GET request
- `post(endpoint, data=None, **kwargs)`: Make a POST request
- `put(endpoint, data=None, **kwargs)`: Make a PUT request
- `delete(endpoint, **kwargs)`: Make a DELETE request

### Error Handling

The client raises specific exceptions for different types of errors:

- `EmagAPIError`: Base exception for all API errors
- `EmagRateLimitError`: Rate limiting error (status 429)
- `EmagAuthenticationError`: Authentication failed (status 401)
- `EmagValidationError`: Request validation failed (status 422)
- `EmagResourceNotFoundError`: Resource not found (status 404)
- `EmagConflictError`: Conflict with current state (status 409)
- `EmagServerError`: Server error (5xx)
- `EmagConnectionError`: Connection error
- `EmagTimeoutError`: Request timeout

## Rate Limiting

The client enforces rate limiting according to eMAG's API guidelines:

- Orders API: 12 requests per second (720 per minute)
- Other APIs: 3 requests per second (180 per minute)

## Testing

Run the test suite with:

```bash
pytest tests/integrations/emag/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
