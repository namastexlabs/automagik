from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi

# Create docs router (no auth required)
router = APIRouter()

@router.get("/api/v1/docs", include_in_schema=False)
async def custom_docs():
    """Swagger UI documentation endpoint."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI - Swagger UI</title>
        <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            const ui = SwaggerUIBundle({
                url: '/api/v1/openapi.json',
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true,
                displayRequestDuration: true,
                filter: true
            });
        </script>
    </body>
    </html>
    """)

@router.get("/api/v1/redoc", include_in_schema=False)
async def custom_redoc():
    """ReDoc documentation endpoint."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI - ReDoc</title>
        <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body>
        <div id="redoc"></div>
        <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
        <script>
            Redoc.init('/api/v1/openapi.json', {}, document.getElementById('redoc'));
        </script>
    </body>
    </html>
    """)

@router.get("/api/v1/openapi.json", include_in_schema=False)
async def get_openapi_json(request: Request):
    """OpenAPI schema endpoint."""
    # Get the app from the request
    app = request.app
    
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add API Key security scheme
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key",
            "description": "API key authentication"
        },
        "APIKeyQuery": {
            "type": "apiKey",
            "in": "query",
            "name": "x-api-key",
            "description": "API key authentication via query parameter"
        }
    }
    
    # Apply security to all endpoints except those that don't need auth
    security_requirement = [{"APIKeyHeader": []}, {"APIKeyQuery": []}]
    no_auth_paths = ["/", "/health", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"]
    
    # Update the schema to use /api/v1 prefix in the OpenAPI docs
    paths = {}
    for path, path_item in openapi_schema["paths"].items():
        if not path.startswith("/api/v1") and path not in ["/", "/health"]:
            continue
        
        # Add security requirement to protected endpoints
        if path not in no_auth_paths:
            for operation in path_item.values():
                operation["security"] = security_requirement
                
                # Add authentication description to each endpoint
                if "description" in operation:
                    operation["description"] += "\n\n**Requires Authentication**: This endpoint requires an API key."
                else:
                    operation["description"] = "**Requires Authentication**: This endpoint requires an API key."
        
        paths[path] = path_item
        
    openapi_schema["paths"] = paths
    
    # Apply global security if needed (alternative approach)
    # openapi_schema["security"] = security_requirement
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema 