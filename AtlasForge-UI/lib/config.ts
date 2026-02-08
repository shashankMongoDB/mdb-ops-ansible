export const config = {
  apiBaseUrl: process.env.NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL || 'http://localhost:8001',
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT || 'DEV',
  mongodbUri: process.env.MCP_MONGODB_URI || '',
  dbName: process.env.MCP_DB_NAME || 'mdb_control_plane',
};
