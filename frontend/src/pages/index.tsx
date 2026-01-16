'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import {
  Scale,
  Shield,
  FileSearch,
  AlertTriangle,
  RefreshCw,
  Github,
} from 'lucide-react';
import {
  FileUpload,
  RiskReportView,
  AnalysisLoading,
} from '@/components';
import {
  UploadResponse,
  RiskReport,
  analyzeDocument,
  getErrorMessage,
} from '@/lib/api';

type AppState = 'upload' | 'analyzing' | 'results' | 'error';

export default function Home() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [uploadedDoc, setUploadedDoc] = useState<UploadResponse | null>(null);
  const [riskReport, setRiskReport] = useState<RiskReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Timer for elapsed time during analysis
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (appState === 'analyzing') {
      interval = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [appState]);

  const handleUploadComplete = useCallback(async (response: UploadResponse) => {
    setUploadedDoc(response);
    setAppState('analyzing');
    setElapsedTime(0);
    setError(null);

    try {
      const analysisResult = await analyzeDocument(response.document_id);
      
      if (analysisResult.status === 'completed' && analysisResult.risk_report) {
        setRiskReport(analysisResult.risk_report);
        setAppState('results');
      } else if (analysisResult.status === 'failed') {
        throw new Error(analysisResult.error_message || 'Analysis failed');
      }
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      setAppState('error');
    }
  }, []);

  const handleUploadError = useCallback((errorMessage: string) => {
    setError(errorMessage);
    setAppState('error');
  }, []);

  const handleReset = () => {
    setAppState('upload');
    setUploadedDoc(null);
    setRiskReport(null);
    setError(null);
    setElapsedTime(0);
  };

  return (
    <>
      <Head>
        <title>LawVisor - AI Legal Document Analysis</title>
        <meta
          name="description"
          content="Analyze legal documents for regulatory compliance with AI"
        />
      </Head>

      <div className="min-h-screen flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                  <Scale className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">LawVisor</h1>
                  <p className="text-xs text-gray-500">AI Legal Assistant</p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                {appState !== 'upload' && (
                  <button
                    onClick={handleReset}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    New Analysis
                  </button>
                )}
                <a
                  href="https://github.com/Abhay-Mmmm/LawVisor"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-400 hover:text-gray-600"
                >
                  <Github className="w-5 h-5" />
                </a>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {/* Upload State */}
            {appState === 'upload' && (
              <div className="max-w-3xl mx-auto">
                {/* Hero Section */}
                <div className="text-center mb-12">
                  <h2 className="text-4xl font-bold text-gray-900 mb-4">
                    AI-Powered Legal Document Analysis
                  </h2>
                  <p className="text-xl text-gray-600 mb-8">
                    Upload your legal contracts and get instant compliance analysis
                    against GDPR, SEC, and other regulations.
                  </p>

                  {/* Features */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                    <FeatureCard
                      icon={<FileSearch className="w-8 h-8" />}
                      title="Smart OCR"
                      description="Handles both scanned and native PDFs with high accuracy"
                    />
                    <FeatureCard
                      icon={<Shield className="w-8 h-8" />}
                      title="Compliance Check"
                      description="Cross-reference against GDPR, SEC, and live regulatory sources"
                    />
                    <FeatureCard
                      icon={<AlertTriangle className="w-8 h-8" />}
                      title="Risk Scoring"
                      description="Clause-level risk assessment with full explainability"
                    />
                  </div>
                </div>

                {/* Upload Area */}
                <FileUpload
                  onUploadComplete={handleUploadComplete}
                  onUploadError={handleUploadError}
                />

                {/* Trust Badges */}
                <div className="mt-8 flex items-center justify-center gap-6 text-sm text-gray-400">
                  <span className="flex items-center gap-1">
                    <Shield className="w-4 h-4" />
                    Secure Processing
                  </span>
                  <span>•</span>
                  <span>No data stored</span>
                  <span>•</span>
                  <span>Enterprise-grade AI</span>
                </div>
              </div>
            )}

            {/* Analyzing State */}
            {appState === 'analyzing' && (
              <div className="max-w-2xl mx-auto">
                <AnalysisLoading />
                <p className="text-center text-gray-400 mt-4">
                  Analyzing: {uploadedDoc?.filename} ({elapsedTime}s)
                </p>
              </div>
            )}

            {/* Results State */}
            {appState === 'results' && riskReport && (
              <RiskReportView report={riskReport} />
            )}

            {/* Error State */}
            {appState === 'error' && (
              <div className="max-w-2xl mx-auto">
                <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
                  <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    Analysis Failed
                  </h3>
                  <p className="text-gray-600 mb-6">{error}</p>
                  <button
                    onClick={handleReset}
                    className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-200 py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-primary-600" />
                <span className="font-semibold text-gray-900">LawVisor</span>
                <span className="text-gray-400">v1.0.0</span>
              </div>
              <p className="text-sm text-gray-500">
                AI-powered legal analysis. Not a substitute for professional legal advice.
              </p>
              <div className="flex items-center gap-4 text-sm text-gray-400">
                <a href="#" className="hover:text-gray-600">
                  Documentation
                </a>
                <a href="#" className="hover:text-gray-600">
                  API
                </a>
                <a href="#" className="hover:text-gray-600">
                  Privacy
                </a>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center text-primary-600 mb-4 mx-auto">
        {icon}
      </div>
      <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-500">{description}</p>
    </div>
  );
}
