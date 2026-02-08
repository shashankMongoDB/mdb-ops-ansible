export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001',
  environment: import.meta.env.VITE_ENVIRONMENT || 'DEV',
  mongodbUri: import.meta.env.VITE_MONGODB_URI || '',
  dbName: import.meta.env.VITE_DB_NAME || 'mdb_control_plane',
};
