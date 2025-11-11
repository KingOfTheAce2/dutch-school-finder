/**
 * API client for Dutch School Finder backend
 */
import axios from 'axios';
import { School, SearchFilters } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const schoolAPI = {
  /**
   * Get all schools with pagination
   */
  getSchools: async (limit: number = 100, offset: number = 0): Promise<School[]> => {
    const response = await api.get('/schools', {
      params: { limit, offset },
    });
    return response.data;
  },

  /**
   * Get a single school by ID
   */
  getSchoolById: async (id: number): Promise<School> => {
    const response = await api.get(`/schools/${id}`);
    return response.data;
  },

  /**
   * Search schools with filters
   */
  searchSchools: async (filters: SearchFilters): Promise<School[]> => {
    const params: Record<string, any> = {};

    if (filters.city) params.city = filters.city;
    if (filters.school_type) params.school_type = filters.school_type;
    if (filters.name) params.name = filters.name;
    if (filters.min_rating !== undefined) params.min_rating = filters.min_rating;
    if (filters.bilingual !== undefined) params.bilingual = filters.bilingual;
    if (filters.international !== undefined) params.international = filters.international;

    const response = await api.get('/schools/search', { params });
    return response.data;
  },

  /**
   * Get all cities
   */
  getCities: async (): Promise<string[]> => {
    const response = await api.get('/cities');
    return response.data;
  },

  /**
   * Get all school types
   */
  getSchoolTypes: async (): Promise<string[]> => {
    const response = await api.get('/types');
    return response.data;
  },

  /**
   * Search schools near an address
   */
  searchNearbySchools: async (
    address: string,
    radius_km: number = 5.0,
    filters: SearchFilters = {}
  ): Promise<School[]> => {
    const params: Record<string, any> = {
      address,
      radius_km,
    };

    if (filters.school_type) params.school_type = filters.school_type;
    if (filters.min_rating !== undefined) params.min_rating = filters.min_rating;
    if (filters.bilingual !== undefined) params.bilingual = filters.bilingual;
    if (filters.international !== undefined) params.international = filters.international;

    const response = await api.get('/schools/nearby', { params });
    return response.data;
  },

  /**
   * Geocode an address
   */
  geocodeAddress: async (address: string): Promise<{ latitude: number; longitude: number }> => {
    const response = await api.get('/geocode', {
      params: { address },
    });
    return response.data;
  },

  /**
   * Refresh school data (admin function)
   */
  refreshData: async (): Promise<any> => {
    const response = await api.post('/admin/refresh-data');
    return response.data;
  },
};

export default api;
