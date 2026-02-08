import { apiClient } from '../api-client';
import { Tenant, CreateTenantRequest } from '../types';

export const tenantsApi = {
  async getAll(): Promise<Tenant[]> {
    return apiClient.get<Tenant[]>('/tenants');
  },

  async getById(tenantId: string): Promise<Tenant> {
    return apiClient.get<Tenant>(`/tenants/${tenantId}`);
  },

  async create(data: CreateTenantRequest): Promise<Tenant> {
    return apiClient.post<Tenant>('/tenants', data);
  },

  async delete(tenantId: string): Promise<void> {
    return apiClient.delete<void>(`/tenants/${tenantId}`);
  },
};
