'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';

interface AnalysisProgressProps {
  step: number;
  totalSteps: number;
  currentStepName: string;
  elapsedTime: number;
}

const ANALYSIS_STEPS = [
  { name: 'OCR Processing', description: 'Extracting text from document...' },
  { name: 'Clause Extraction', description: 'Identifying and classifying legal clauses...' },
  { name: 'Compliance Analysis', description: 'Checking against GDPR and SEC regulations...' },
  { name: 'Risk Calculation', description: 'Computing risk scores...' },
];

export function AnalysisProgress({
  step,
  totalSteps,
  currentStepName,
  elapsedTime,
}: AnalysisProgressProps) {
  const progress = ((step + 1) / totalSteps) * 100;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
      <div className="flex items-center justify-center mb-6">
        <div className="relative">
          <Loader2 className="w-16 h-16 text-primary-600 animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-bold text-primary-600">
              {Math.round(progress)}%
            </span>
          </div>
        </div>
      </div>

      <h3 className="text-xl font-semibold text-gray-900 text-center mb-2">
        Analyzing Document
      </h3>

      <p className="text-gray-500 text-center mb-6">
        This may take a minute for large documents
      </p>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-6">
        <div
          className="bg-primary-600 h-2 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {ANALYSIS_STEPS.map((s, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
              idx < step
                ? 'bg-green-50'
                : idx === step
                ? 'bg-primary-50'
                : 'bg-gray-50'
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                idx < step
                  ? 'bg-green-500 text-white'
                  : idx === step
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-300 text-gray-600'
              }`}
            >
              {idx < step ? '✓' : idx + 1}
            </div>
            <div className="flex-1">
              <p
                className={`font-medium ${
                  idx === step ? 'text-primary-700' : 'text-gray-700'
                }`}
              >
                {s.name}
              </p>
              <p className="text-sm text-gray-500">{s.description}</p>
            </div>
            {idx === step && (
              <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
            )}
          </div>
        ))}
      </div>

      <p className="text-center text-sm text-gray-400 mt-6">
        Elapsed: {elapsedTime}s
      </p>
    </div>
  );
}

export function AnalysisLoading() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
      <Loader2 className="w-12 h-12 text-primary-600 animate-spin mx-auto mb-4" />
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Processing your document...
      </h3>
      <p className="text-gray-500">
        This may take up to a minute for large documents
      </p>
    </div>
  );
}
