export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ExtractedStudent {
  row_index: number;
  school_no: string;
  name: string;
  exam1: number | null;
  exam2: number | null;
  perf1: number | null;
  perf2: number | null;
  calculated_average: number | null;
  status: string;
  is_new_student: boolean;
  
  // Gelişim Değerlendirme Puanları
  growth_attendance: number | null;
  growth_activities: number | null;
  growth_product: number | null;
  growth_social_emotional: number | null;
  growth_progress: number | null;
  
  // Koordinatlar
  bbox_school_no?: BBox | null;
  bbox_name?: BBox | null;
  bbox_exam1?: BBox | null;
  bbox_exam2?: BBox | null;
  bbox_perf1?: BBox | null;
  bbox_perf2?: BBox | null;
}
