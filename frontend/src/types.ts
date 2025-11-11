/**
 * Type definitions for Dutch School Finder
 */

export interface School {
  id: number;
  name: string;
  brin_code?: string;
  city: string;
  postal_code?: string;
  address?: string;
  school_type?: string;
  education_structure?: string;
  latitude?: number;
  longitude?: number;
  inspection_rating?: string;
  inspection_score?: number;
  cito_score?: number;
  is_bilingual: boolean;
  is_international: boolean;
  offers_english: boolean;
  phone?: string;
  email?: string;
  website?: string;
  denomination?: string;
  student_count?: number;
  description?: string;
}

export interface SearchFilters {
  city?: string;
  school_type?: string;
  min_rating?: number;
  name?: string;
  bilingual?: boolean;
  international?: boolean;
}

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}
