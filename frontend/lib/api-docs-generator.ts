import { API_ENDPOINTS } from './api-config';

interface EndpointDocumentation {
  path: string;
  description: string;
  requiresAuth: boolean;
  methods: string[];
  parameters?: {
    query?: Record<string, ParameterDoc>;
    path?: Record<string, ParameterDoc>;
    body?: Record<string, ParameterDoc>;
  };
  responses?: Record<string, ResponseDoc>;
  examples?: {
    request?: Record<string, any>;
    response?: Record<string, any>;
  };
}

interface ParameterDoc {
  type: string;
  description: string;
  required?: boolean;
  example?: any;
}

interface ResponseDoc {
  description: string;
  schema?: Record<string, any>;
  example?: any;
}

/**
 * Generates documentation for the API endpoints based on the API_ENDPOINTS configuration
 * and any additional information provided.
 */
export function generateApiDocumentation(
  additionalDocs: Record<string, Partial<EndpointDocumentation>> = {}
): Record<string, EndpointDocumentation> {
  const documentation: Record<string, EndpointDocumentation> = {};
  
  // Process each endpoint from the API_ENDPOINTS configuration
  Object.entries(API_ENDPOINTS).forEach(([path, config]) => {
    // Base documentation derived from API_ENDPOINTS
    const baseDoc: EndpointDocumentation = {
      path,
      description: config.description || 'No description provided',
      requiresAuth: config.requiresAuth ?? true,
      methods: config.methods || ['GET'],
      parameters: {},
      responses: {
        '200': {
          description: 'Successful operation',
        },
        '401': {
          description: 'Unauthorized - Authentication required',
        },
        '500': {
          description: 'Internal server error',
        },
      },
    };
    
    // Merge with any additional documentation provided
    documentation[path] = {
      ...baseDoc,
      ...additionalDocs[path],
      // Ensure parameters and responses are merged properly
      parameters: {
        ...baseDoc.parameters,
        ...additionalDocs[path]?.parameters,
      },
      responses: {
        ...baseDoc.responses,
        ...additionalDocs[path]?.responses,
      },
      examples: {
        ...baseDoc.examples,
        ...additionalDocs[path]?.examples,
      },
    };
  });
  
  return documentation;
}

/**
 * Generates OpenAPI specification based on the API documentation
 */
export function generateOpenApiSpec(
  apiDocs: Record<string, EndpointDocumentation>,
  info: {
    title: string;
    version: string;
    description?: string;
  }
): Record<string, any> {
  const paths: Record<string, any> = {};
  
  // Convert each endpoint documentation to OpenAPI path format
  Object.values(apiDocs).forEach((endpoint) => {
    const pathItem: Record<string, any> = {};
    
    // Process each HTTP method for this endpoint
    endpoint.methods.forEach((method) => {
      const methodLower = method.toLowerCase();
      
      // Create the operation object for this method
      const operation: Record<string, any> = {
        summary: endpoint.description,
        description: endpoint.description,
        tags: [endpoint.path.split('/')[1] || 'default'], // Use first segment of path as tag
        responses: {},
        security: endpoint.requiresAuth ? [{ bearerAuth: [] }] : [],
      };
      
      // Add parameters
      if (endpoint.parameters) {
        operation.parameters = [];
        
        // Add query parameters
        if (endpoint.parameters.query) {
          Object.entries(endpoint.parameters.query).forEach(([name, param]) => {
            operation.parameters.push({
              name,
              in: 'query',
              description: param.description,
              required: param.required || false,
              schema: {
                type: param.type,
                example: param.example,
              },
            });
          });
        }
        
        // Add path parameters
        if (endpoint.parameters.path) {
          Object.entries(endpoint.parameters.path).forEach(([name, param]) => {
            operation.parameters.push({
              name,
              in: 'path',
              description: param.description,
              required: true, // Path parameters are always required
              schema: {
                type: param.type,
                example: param.example,
              },
            });
          });
        }
      }
      
      // Add request body if this is not a GET method
      if (methodLower !== 'get' && endpoint.parameters?.body) {
        operation.requestBody = {
          description: 'Request body',
          required: true,
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: Object.fromEntries(
                  Object.entries(endpoint.parameters.body).map(([name, param]) => [
                    name,
                    {
                      type: param.type,
                      description: param.description,
                      example: param.example,
                    },
                  ])
                ),
                required: Object.entries(endpoint.parameters.body)
                  .filter(([_, param]) => param.required)
                  .map(([name]) => name),
              },
              example: endpoint.examples?.request || {},
            },
          },
        };
      }
      
      // Add responses
      if (endpoint.responses) {
        Object.entries(endpoint.responses).forEach(([statusCode, response]) => {
          operation.responses[statusCode] = {
            description: response.description,
            content: {
              'application/json': {
                schema: response.schema || {},
                example: response.example || {},
              },
            },
          };
        });
      }
      
      // Add the operation to the path item
      pathItem[methodLower] = operation;
    });
    
    // Add the path item to the paths object
    const apiPath = endpoint.path.startsWith('/') 
      ? endpoint.path 
      : `/${endpoint.path}`;
    
    paths[apiPath] = pathItem;
  });
  
  // Construct the complete OpenAPI spec
  return {
    openapi: '3.0.0',
    info: {
      title: info.title,
      version: info.version,
      description: info.description || '',
    },
    servers: [
      {
        url: process.env.NEXT_PUBLIC_API_BASE_URL || '/',
        description: 'API server',
      },
    ],
    paths,
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
        },
      },
    },
  };
}

/**
 * Render HTML documentation from API docs
 */
export function renderHtmlDocs(
  apiDocs: Record<string, EndpointDocumentation>,
  title: string
): string {
  let html = `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>${title}</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
          line-height: 1.6;
          color: #333;
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }
        h1, h2, h3, h4 {
          color: #0055FF;
        }
        .endpoint {
          margin-bottom: 30px;
          border: 1px solid #ddd;
          border-radius: 4px;
          overflow: hidden;
        }
        .endpoint-header {
          padding: 15px;
          background-color: #f5f5f5;
          border-bottom: 1px solid #ddd;
        }
        .endpoint-body {
          padding: 15px;
        }
        .method {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 3px;
          margin-right: 10px;
          font-weight: bold;
          color: white;
        }
        .get { background-color: #61affe; }
        .post { background-color: #49cc90; }
        .put { background-color: #fca130; }
        .delete { background-color: #f93e3e; }
        .patch { background-color: #50e3c2; }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 15px;
        }
        th, td {
          padding: 8px;
          border: 1px solid #ddd;
          text-align: left;
        }
        th {
          background-color: #f5f5f5;
        }
        pre {
          background-color: #f5f5f5;
          padding: 10px;
          border-radius: 3px;
          overflow: auto;
        }
        code {
          font-family: 'Courier New', Courier, monospace;
        }
        .auth-required {
          display: inline-block;
          padding: 3px 6px;
          border-radius: 3px;
          background-color: #ddd;
          margin-left: 10px;
          font-size: 0.8em;
        }
      </style>
    </head>
    <body>
      <h1>${title}</h1>
  `;
  
  // Group endpoints by category (first segment of path)
  const groupedEndpoints: Record<string, EndpointDocumentation[]> = {};
  
  Object.values(apiDocs).forEach((endpoint) => {
    const category = endpoint.path.split('/')[1] || 'other';
    if (!groupedEndpoints[category]) {
      groupedEndpoints[category] = [];
    }
    groupedEndpoints[category].push(endpoint);
  });
  
  // Generate HTML for each category and its endpoints
  Object.entries(groupedEndpoints).forEach(([category, endpoints]) => {
    html += `<h2>${category.toUpperCase()}</h2>`;
    
    endpoints.forEach((endpoint) => {
      html += `
        <div class="endpoint">
          <div class="endpoint-header">
            <h3>
              ${endpoint.methods.map((method) => `
                <span class="method ${method.toLowerCase()}">${method}</span>
              `).join('')}
              <code>${endpoint.path}</code>
              ${endpoint.requiresAuth 
                ? '<span class="auth-required">Requires Authentication</span>' 
                : ''}
            </h3>
            <p>${endpoint.description}</p>
          </div>
          <div class="endpoint-body">
      `;
      
      // Parameters
      if (endpoint.parameters && (
        endpoint.parameters.query || 
        endpoint.parameters.path || 
        endpoint.parameters.body
      )) {
        html += '<h4>Parameters</h4>';
        
        // Query parameters
        if (endpoint.parameters.query && Object.keys(endpoint.parameters.query).length > 0) {
          html += `
            <h5>Query Parameters</h5>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Required</th>
                  <th>Description</th>
                  <th>Example</th>
                </tr>
              </thead>
              <tbody>
          `;
          
          Object.entries(endpoint.parameters.query).forEach(([name, param]) => {
            html += `
              <tr>
                <td>${name}</td>
                <td><code>${param.type}</code></td>
                <td>${param.required ? 'Yes' : 'No'}</td>
                <td>${param.description}</td>
                <td>${param.example !== undefined ? `<code>${JSON.stringify(param.example)}</code>` : ''}</td>
              </tr>
            `;
          });
          
          html += `
              </tbody>
            </table>
          `;
        }
        
        // Path parameters
        if (endpoint.parameters.path && Object.keys(endpoint.parameters.path).length > 0) {
          html += `
            <h5>Path Parameters</h5>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Example</th>
                </tr>
              </thead>
              <tbody>
          `;
          
          Object.entries(endpoint.parameters.path).forEach(([name, param]) => {
            html += `
              <tr>
                <td>${name}</td>
                <td><code>${param.type}</code></td>
                <td>${param.description}</td>
                <td>${param.example !== undefined ? `<code>${JSON.stringify(param.example)}</code>` : ''}</td>
              </tr>
            `;
          });
          
          html += `
              </tbody>
            </table>
          `;
        }
        
        // Body parameters
        if (
          endpoint.parameters.body && 
          Object.keys(endpoint.parameters.body).length > 0 &&
          endpoint.methods.some(m => m.toLowerCase() !== 'get')
        ) {
          html += `
            <h5>Request Body</h5>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Required</th>
                  <th>Description</th>
                  <th>Example</th>
                </tr>
              </thead>
              <tbody>
          `;
          
          Object.entries(endpoint.parameters.body).forEach(([name, param]) => {
            html += `
              <tr>
                <td>${name}</td>
                <td><code>${param.type}</code></td>
                <td>${param.required ? 'Yes' : 'No'}</td>
                <td>${param.description}</td>
                <td>${param.example !== undefined ? `<code>${JSON.stringify(param.example)}</code>` : ''}</td>
              </tr>
            `;
          });
          
          html += `
              </tbody>
            </table>
          `;
        }
      }
      
      // Responses
      if (endpoint.responses && Object.keys(endpoint.responses).length > 0) {
        html += '<h4>Responses</h4>';
        html += `
          <table>
            <thead>
              <tr>
                <th>Status Code</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
        `;
        
        Object.entries(endpoint.responses).forEach(([statusCode, response]) => {
          html += `
            <tr>
              <td>${statusCode}</td>
              <td>${response.description}</td>
            </tr>
          `;
        });
        
        html += `
            </tbody>
          </table>
        `;
      }
      
      // Examples
      if (endpoint.examples) {
        html += '<h4>Examples</h4>';
        
        if (endpoint.examples.request) {
          html += `
            <h5>Request Example</h5>
            <pre><code>${JSON.stringify(endpoint.examples.request, null, 2)}</code></pre>
          `;
        }
        
        if (endpoint.examples.response) {
          html += `
            <h5>Response Example</h5>
            <pre><code>${JSON.stringify(endpoint.examples.response, null, 2)}</code></pre>
          `;
        }
      }
      
      html += `
          </div>
        </div>
      `;
    });
  });
  
  html += `
    </body>
    </html>
  `;
  
  return html;
}

export default {
  generateApiDocumentation,
  generateOpenApiSpec,
  renderHtmlDocs,
};