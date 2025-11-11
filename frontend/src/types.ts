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
  // Distance fields (for proximity search)
  distance_km?: number;
  distance_formatted?: string;
}

export interface SearchFilters {
  city?: string;
  school_type?: string;
  min_rating?: number;
  name?: string;
  bilingual?: boolean;
  international?: boolean;
  // Proximity search
  address?: string;
  radius_km?: number;
}

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

// Extended Features Types

export interface TransportationRoute {
  id: number;
  school_id: number;
  mode: 'walking' | 'cycling' | 'public_transit' | 'driving' | 'school_bus';
  duration_minutes?: number;
  distance_km?: number;
  transit_details?: {
    lines?: string[];
    transfers?: number;
    wait_time_minutes?: number;
  };
  bus_route_name?: string;
  bus_pickup_time?: string;
  bus_pickup_location?: string;
  from_address?: string;
  display?: string;
  icon?: string;
}

export interface AdmissionTimeline {
  id: number;
  school_id: number;
  academic_year: string;
  enrollment_opens?: string;
  enrollment_deadline?: string;
  acceptance_notification_date?: string;
  school_year_start?: string;
  required_documents?: string[];
  municipality?: string;
  enrollment_system?: string;
  enrollment_url?: string;
  notes?: string;
}

export interface ApplicationStatus {
  id: number;
  school_id: number;
  user_email: string;
  status: 'interested' | 'applied' | 'waiting' | 'accepted' | 'enrolled' | 'declined';
  applied_date?: string;
  waiting_list_position?: number;
  reminder_sent: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface SchoolEvent {
  id: number;
  school_id: number;
  title: string;
  event_type?: 'open_house' | 'info_evening' | 'tour' | 'application_period' | 'other';
  description?: string;
  start_datetime: string;
  end_datetime?: string;
  location?: string;
  is_virtual: boolean;
  virtual_tour_url?: string;
  requires_booking: boolean;
  booking_url?: string;
  max_attendees?: number;
  current_attendees: number;
  language?: string;
  is_active: boolean;
}

export interface AfterSchoolCare {
  id: number;
  school_id: number;
  provider_name: string;
  provider_website?: string;
  provider_phone?: string;
  provider_email?: string;
  same_location_as_school: boolean;
  address?: string;
  latitude?: number;
  longitude?: number;
  opening_time?: string;
  closing_time?: string;
  operates_school_holidays: boolean;
  activities?: string[];
  offers_homework_help: boolean;
  offers_sports: boolean;
  offers_arts_crafts: boolean;
  offers_outdoor_play: boolean;
  monthly_cost_euros?: number;
  hourly_cost_euros?: number;
  subsidy_eligible: boolean;
  capacity?: number;
  current_occupancy?: number;
  has_waiting_list: boolean;
  registration_url?: string;
  registration_deadline?: string;
  inspection_rating?: string;
  staff_child_ratio?: string;
}

export interface SpecialNeedsSupport {
  id: number;
  school_id: number;
  supports_dyslexia: boolean;
  supports_adhd: boolean;
  supports_autism: boolean;
  supports_gifted: boolean;
  supports_physical_disability: boolean;
  supports_visual_impairment: boolean;
  supports_hearing_impairment: boolean;
  offers_speech_therapy: boolean;
  offers_occupational_therapy: boolean;
  offers_special_education_classrooms: boolean;
  wheelchair_accessible: boolean;
  has_elevator: boolean;
  has_accessible_restrooms: boolean;
  special_education_staff_count?: number;
  support_staff_ratio?: string;
  programs_offered?: string[];
  referral_process?: string;
  funding_info?: string;
  notes?: string;
  parent_testimonials?: Array<{
    author: string;
    text: string;
    date: string;
  }>;
}

export interface AcademicPerformance {
  id: number;
  school_id: number;
  academic_year: string;
  year_start: number;
  cito_score?: number;
  inspection_rating?: string;
  inspection_score?: number;
  student_count?: number;
  teacher_count?: number;
  teacher_turnover_rate?: number;
  graduation_rate?: number;
  university_acceptance_rate?: number;
  year_over_year_change?: number;
  data_source?: string;
}

export interface PerformanceTrend {
  school_id: number;
  school_name: string;
  trend_direction: 'improving' | 'stable' | 'declining';
  years_of_data: number;
  total_change: number;
  average_annual_change: number;
  badge?: 'rising_star' | 'consistent_excellence' | 'needs_attention';
  performance_history: AcademicPerformance[];
}

export interface ShareableComparison {
  id: number;
  share_id: string;
  school_ids: number[];
  filters_applied?: Record<string, any>;
  created_at: string;
  expires_at?: string;
  view_count: number;
}

export interface ExtendedSchool extends School {
  transportation?: TransportationRoute[];
  admission_timeline?: AdmissionTimeline;
  upcoming_events?: SchoolEvent[];
  after_school_care?: AfterSchoolCare[];
  special_needs_support?: SpecialNeedsSupport;
  performance_history?: AcademicPerformance[];
  performance_trend?: 'improving' | 'stable' | 'declining';
}

export interface ExtendedSearchFilters extends SearchFilters {
  // Special needs filters
  supports_dyslexia?: boolean;
  supports_adhd?: boolean;
  supports_autism?: boolean;
  supports_gifted?: boolean;
  wheelchair_accessible?: boolean;

  // BSO filters
  has_after_school_care?: boolean;
  max_bso_cost?: number;
  bso_offers_homework_help?: boolean;

  // Event filters
  has_upcoming_events?: boolean;
  event_language?: 'Dutch' | 'English' | 'Both';
}
