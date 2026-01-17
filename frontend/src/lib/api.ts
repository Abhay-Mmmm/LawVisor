/**
 * LawVisor API Client
 * ===================
 * Type-safe API client for LawVisor backend.
 */

import axios, { AxiosError } from 'axios';

// API Base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 minute timeout for analysis
  headers: {
    'Content-Type': 'application/json',
  },
});

// === Types ===

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'minimal';

export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface UploadResponse {
  document_id: string;
  filename: string;
  file_size_bytes: number;
  upload_timestamp: string;
  status: AnalysisStatus;
  message: string;
}

export interface ContributingFactor {
  factor: string;
  value: number;
  description: string;
}

export interface ClauseRisk {
  clause_id: string;
  clause_type: string;
  clause_title: string;
  clause_text_preview: string;
  risk_score: number;
  risk_level: RiskLevel;
  contributing_factors: ContributingFactor[];
  violated_regulations: string[];
  recommendations: string[];
  explanation: string;
  confidence: number;
}

export interface CategoryRisk {
  category: string;
  category_display: string;
  risk_score: number;
  risk_level: RiskLevel;
  clause_count: number;
  high_risk_clauses: number;
  top_issues: string[];
}

export interface Citation {
  regulation_id: string;
  title: string;
  source_url: string;
  regulation_type: string;
}

export interface ScoringBreakdown {
  weighted_average: {
    value: number;
    weight: number;
    contribution: number;
  };
  max_risk_penalty: {
    max_clause_score: number;
    penalty: number;
  };
  high_risk_density: {
    high_risk_count: number;
    total_clauses: number;
    density: number;
    penalty: number;
  };
  formula: string;
}

export interface RiskReport {
  document_id: string;
  analyzed_at: string;
  overall_risk: number;
  overall_risk_level: RiskLevel;
  total_clauses_analyzed: number;
  high_risk_clause_count: number;
  medium_risk_clause_count: number;
  low_risk_clause_count: number;
  category_risks: CategoryRisk[];
  high_risk_clauses: ClauseRisk[];
  summary: string;
  citations: Citation[];
  confidence: number;
  scoring_breakdown: ScoringBreakdown;
}

export interface AnalyzeResponse {
  document_id: string;
  status: AnalysisStatus;
  risk_report: RiskReport | null;
  processing_time_seconds: number | null;
  error_message: string | null;
}

export interface DocumentStatus {
  document_id: string;
  filename: string;
  status: AnalysisStatus;
  upload_timestamp: string;
  analysis_started_at: string | null;
  analysis_completed_at: string | null;
  error_message: string | null;
}

export interface HealthCheck {
  status: string;
  version: string;
  timestamp: string;
  services: Record<string, string>;
}

export interface APIError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

// === API Functions ===

/**
 * Check API health status.
 */
export async function checkHealth(): Promise<HealthCheck> {
  const response = await api.get<HealthCheck>('/health');
  return response.data;
}

/**
 * Upload a PDF document for analysis.
 */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<UploadResponse>('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Analyze an uploaded document.
 */
export async function analyzeDocument(documentId: string): Promise<AnalyzeResponse> {
  const response = await api.post<AnalyzeResponse>(`/analyze/${documentId}`);
  return response.data;
}

/**
 * Get document analysis status.
 */
export async function getDocumentStatus(documentId: string): Promise<DocumentStatus> {
  const response = await api.get<DocumentStatus>(`/analyze/${documentId}/status`);
  return response.data;
}

/**
 * Get full risk report for a document.
 */
export async function getRiskReport(documentId: string): Promise<RiskReport> {
  const response = await api.get<RiskReport>(`/risk/${documentId}`);
  return response.data;
}

/**
 * Get risk summary for a document.
 */
export async function getRiskSummary(documentId: string): Promise<{
  document_id: string;
  overall_risk_score: number;
  overall_risk_level: RiskLevel;
  total_clauses: number;
  high_risk_clauses: number;
  summary: string;
  top_violations: string[];
}> {
  const response = await api.get(`/risk/${documentId}/summary`);
  return response.data;
}

/**
 * Get details for a specific clause.
 */
export async function getClauseDetails(
  documentId: string,
  clauseId: string
): Promise<ClauseRisk> {
  const response = await api.get<ClauseRisk>(
    `/risk/${documentId}/clauses/${clauseId}`
  );
  return response.data;
}

/**
 * Get available regulations.
 */
export async function getRegulations(): Promise<{
  gdpr: {
    name: string;
    version: string;
    article_count: number;
    articles: Array<{
      article_number: string;
      title: string;
      regulation_id: string;
    }>;
  };
  sec: {
    name: string;
    version: string;
    regulation_count: number;
    regulations: Array<{
      regulation_id: string;
      article_number: string;
      title: string;
    }>;
  };
}> {
  const response = await api.get('/risk/regulations');
  return response.data;
}

/**
 * Extract error message from API error response.
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<APIError>;
    if (axiosError.response?.data?.message) {
      return axiosError.response.data.message;
    }
    if (axiosError.message) {
      return axiosError.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
}

export default api;
