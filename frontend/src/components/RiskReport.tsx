'use client';

import React from 'react';
import {
  FileText,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  BookOpen,
  Clock,
} from 'lucide-react';
import { cn, getRiskColorClass, formatDate, getRiskLabel } from '@/lib/utils';
import { RiskScoreGauge, RiskScoreBar, RiskBadge } from './RiskScore';
import { ClauseList } from './ClauseCard';
import type { RiskReport, CategoryRisk } from '@/lib/api';

interface RiskReportViewProps {
  report: RiskReport;
}

export function RiskReportView({ report }: RiskReportViewProps) {
  const overallColors = getRiskColorClass(report.overall_risk_level);

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Summary Header */}
      <div className={cn('rounded-xl p-6 border-2', overallColors.border, overallColors.bgLight)}>
        <div className="flex flex-col md:flex-row items-center gap-6">
          {/* Risk Gauge */}
          <div className="flex-shrink-0">
            <RiskScoreGauge
              score={report.overall_risk}
              level={report.overall_risk_level}
              size="lg"
            />
          </div>

          {/* Summary Text */}
          <div className="flex-1 text-center md:text-left">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Contract Risk Assessment
            </h2>
            <p className="text-gray-600 leading-relaxed mb-4">
              {report.summary}
            </p>
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-4 text-sm">
              <span className="flex items-center gap-1.5 text-gray-500">
                <FileText className="w-4 h-4" />
                {report.total_clauses_analyzed} clauses analyzed
              </span>
              <span className="flex items-center gap-1.5 text-gray-500">
                <Clock className="w-4 h-4" />
                {formatDate(report.analyzed_at)}
              </span>
              <span className="flex items-center gap-1.5 text-gray-500">
                Confidence: {(report.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<BarChart3 className="w-5 h-5" />}
          label="Total Clauses"
          value={report.total_clauses_analyzed}
          color="blue"
        />
        <StatCard
          icon={<AlertTriangle className="w-5 h-5" />}
          label="High Risk"
          value={report.high_risk_clause_count}
          color="red"
        />
        <StatCard
          icon={<AlertTriangle className="w-5 h-5" />}
          label="Medium Risk"
          value={report.medium_risk_clause_count}
          color="amber"
        />
        <StatCard
          icon={<CheckCircle className="w-5 h-5" />}
          label="Low Risk"
          value={report.low_risk_clause_count}
          color="green"
        />
      </div>

      {/* Category Breakdown */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-primary-600" />
          Risk by Category
        </h3>
        <div className="space-y-4">
          {report.category_risks.map((category) => (
            <CategoryRiskRow key={category.category} category={category} />
          ))}
        </div>
      </div>

      {/* High Risk Clauses */}
      {report.high_risk_clauses.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            High Risk Clauses ({report.high_risk_clauses.length})
          </h3>
          <ClauseList clauses={report.high_risk_clauses} />
        </div>
      )}

      {/* Citations */}
      {report.citations.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-primary-600" />
            Regulatory Citations
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {report.citations.map((citation, idx) => (
              <a
                key={idx}
                href={citation.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
              >
                <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center flex-shrink-0">
                  <BookOpen className="w-5 h-5 text-primary-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 group-hover:text-primary-600 transition-colors">
                    {citation.regulation_id}
                  </p>
                  <p className="text-sm text-gray-500 truncate">
                    {citation.title}
                  </p>
                  <span className="text-xs text-gray-400 uppercase">
                    {citation.regulation_type}
                  </span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Scoring Methodology */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Scoring Methodology
        </h3>
        <div className="bg-gray-50 rounded-lg p-4 font-mono text-sm text-gray-600 mb-4">
          {report.scoring_breakdown.formula}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 rounded-lg p-4">
            <p className="text-sm font-medium text-blue-800">Weighted Average</p>
            <p className="text-2xl font-bold text-blue-600">
              {report.scoring_breakdown.weighted_average.value?.toFixed(1) || 'N/A'}
            </p>
            <p className="text-xs text-blue-600">
              Weight: {report.scoring_breakdown.weighted_average.weight}
            </p>
          </div>
          <div className="bg-amber-50 rounded-lg p-4">
            <p className="text-sm font-medium text-amber-800">Max Risk Penalty</p>
            <p className="text-2xl font-bold text-amber-600">
              +{report.scoring_breakdown.max_risk_penalty.penalty?.toFixed(1) || '0'}
            </p>
            <p className="text-xs text-amber-600">
              Max clause: {report.scoring_breakdown.max_risk_penalty.max_clause_score?.toFixed(1) || 'N/A'}
            </p>
          </div>
          <div className="bg-red-50 rounded-lg p-4">
            <p className="text-sm font-medium text-red-800">Density Penalty</p>
            <p className="text-2xl font-bold text-red-600">
              +{report.scoring_breakdown.high_risk_density.penalty?.toFixed(1) || '0'}
            </p>
            <p className="text-xs text-red-600">
              {report.scoring_breakdown.high_risk_density.high_risk_count} high-risk of{' '}
              {report.scoring_breakdown.high_risk_density.total_clauses}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: 'blue' | 'red' | 'amber' | 'green';
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    red: 'bg-red-50 text-red-600',
    amber: 'bg-amber-50 text-amber-600',
    green: 'bg-green-50 text-green-600',
  };

  const iconColors = {
    blue: 'text-blue-600',
    red: 'text-red-600',
    amber: 'text-amber-600',
    green: 'text-green-600',
  };

  return (
    <div className={cn('rounded-xl p-4', colorClasses[color])}>
      <div className={cn('mb-2', iconColors[color])}>{icon}</div>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm opacity-80">{label}</p>
    </div>
  );
}

interface CategoryRiskRowProps {
  category: CategoryRisk;
}

function CategoryRiskRow({ category }: CategoryRiskRowProps) {
  const colors = getRiskColorClass(category.risk_level);

  return (
    <div className="flex items-center gap-4">
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="font-medium text-gray-700">
            {category.category_display}
          </span>
          <div className="flex items-center gap-2">
            <RiskBadge level={category.risk_level} size="sm" />
            <span className="text-sm text-gray-500">
              {category.clause_count} clause{category.clause_count !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
        <RiskScoreBar
          score={category.risk_score}
          level={category.risk_level}
          showValue={false}
        />
        {category.top_issues.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {category.top_issues.slice(0, 3).map((issue, idx) => (
              <span
                key={idx}
                className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded"
              >
                {issue}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
