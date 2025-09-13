# API Endpoints for datahub

## Endpoints

### `GET /cars`
- **Description**: Retrieves a list of cars with optional filters and pagination.
- **Parameters**:
  - `page` (query, int, optional): Page number.
  - `limit` (query, int, optional): Page size.
  - `source` (query, string, optional): Data source.
  - `brand` (query, string, optional): Car brand.
  - `city` (query, string, optional): City.
  - `year` (query, string, optional): Manufacturing year.
  - `search` (query, string, optional): Search term.
- **Response**: JSON object containing car data.

### `POST /checkcar`
- **Description**: Checks the details of a specific car.
- **Request Body**: JSON object with car details.
- **Response**: JSON object with the result of the check.

### `GET /update/:source/full`
- **Description**: Performs a full update for a specific data source.
- **Path Parameters**:
  - `source` (string): The data source (e.g., "dongchedi", "che168").
- **Response**: JSON object with update status.

### `POST /update/:source`
- **Description**: Performs an incremental update for a specific data source.
- **Path Parameters**:
  - `source` (string): The data source (e.g., "dongchedi", "che168").
- **Request Body**: JSON object with update details.
- **Response**: JSON object with update status.

### `GET /brands`
- **Description**: Retrieves a list of car brands.
- **Response**: JSON object containing brand data.

### `GET /swagger/*any`
- **Description**: Provides Swagger UI for API documentation.
- **Response**: Swagger UI page.
