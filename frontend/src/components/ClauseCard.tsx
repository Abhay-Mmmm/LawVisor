'use client';

import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  ExternalLink,
  Lightbulb,
} from 'lucide-react';
import { cn, getRiskColorClass, formatClauseType, truncateText } from '@/lib/utils';
import { RiskBadge, RiskScoreBar } from './RiskScore';
import type { ClauseRisk } from '@/lib/api';

interface ClauseCardProps {
  clause: ClauseRisk;
  isExpanded?: boolean;
  onToggle?: () => void;
}

export function ClauseCard({
  clause,
  isExpanded = false,
  onToggle,
}: ClauseCardProps) {
  const colors = getRiskColorClass(clause.risk_level);

  return (
    <div
      className={cn(
        'bg-white rounded-lg border transition-all duration-200',
        colors.border,
        'border-l-4',
        isExpanded ? 'shadow-lg' : 'shadow-sm hover:shadow-md'
      )}
    >
      {/* Header */}
      <div
        onClick={onToggle}
        className="flex items-center justify-between p-4 cursor-pointer"
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <button className="text-gray-400 hover:text-gray-600">
            {isExpanded ? (
              <ChevronDown className="w-5 h-5" />
            ) : (
              <ChevronRight className="w-5 h-5" />
            )}
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-semibold text-gray-900 truncate">
                {clause.clause_title}
              </h4>
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                {formatClauseType(clause.clause_type)}
              </span>
            </div>
            <p className="text-sm text-gray-500 truncate mt-1">
              {truncateText(clause.clause_text_preview, 100)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 ml-4">
          <RiskBadge level={clause.risk_level} size="sm" />
          <div className="text-right">
            <span className={cn('text-lg font-bold', colors.text)}>
              {Math.round(clause.risk_score)}
            </span>
            <p className="text-xs text-gray-400">Risk Score</p>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-gray-100 animate-slide-up">
          {/* Clause Text */}
          <div className="p-4 bg-gray-50">
            <h5 className="text-sm font-medium text-gray-700 mb-2">
              Clause Text
            </h5>
            <p className="text-sm text-gray-600 leading-relaxed">
              {clause.clause_text_preview}
            </p>
          </div>

          {/* Risk Score Breakdown */}
          <div className="p-4 border-t border-gray-100">
            <h5 className="text-sm font-medium text-gray-700 mb-3">
              Risk Score Breakdown
            </h5>
            <div className="mb-4">
              <RiskScoreBar
                score={clause.risk_score}
                level={clause.risk_level}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {clause.contributing_factors.map((factor, idx) => (
                <div
                  key={idx}
                  className="bg-gray-50 rounded-lg p-3 text-sm"
                >
                  <p className="font-medium text-gray-700">{factor.factor}</p>
                  <p className="text-lg font-bold text-gray-900">
                    {typeof factor.value === 'number'
                      ? factor.value.toFixed(2)
                      : factor.value}
                  </p>
                  <p className="text-xs text-gray-500">{factor.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Violated Regulations */}
          {clause.violated_regulations.length > 0 && (
            <div className="p-4 border-t border-gray-100">
              <h5 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Potentially Violated Regulations
              </h5>
              <div className="flex flex-wrap gap-2">
                {clause.violated_regulations.map((reg, idx) => (
                  <a
                    key={idx}
                    href={`https://gdpr-info.eu/art-${reg.match(/\d+/)?.[0] || ''}-gdpr/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-sm hover:bg-red-100 transition-colors"
                  >
                    {reg}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Explanation */}
          <div className="p-4 border-t border-gray-100 bg-blue-50">
            <h5 className="text-sm font-medium text-blue-800 mb-2">
              Analysis Explanation
            </h5>
            <p className="text-sm text-blue-700 leading-relaxed">
              {clause.explanation}
            </p>
            <p className="text-xs text-blue-500 mt-2">
              Confidence: {(clause.confidence * 100).toFixed(0)}%
            </p>
          </div>

          {/* Recommendations */}
          {clause.recommendations.length > 0 && (
            <div className="p-4 border-t border-gray-100">
              <h5 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                Recommendations
              </h5>
              <ul className="space-y-2">
                {clause.recommendations.map((rec, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-sm text-gray-600"
                  >
                    <span className="text-green-500 mt-0.5">•</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface ClauseListProps {
  clauses: ClauseRisk[];
  title?: string;
}

export function ClauseList({ clauses, title }: ClauseListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (clauses.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No clauses to display
      </div>
    );
  }

  return (
    <div>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      )}
      <div className="space-y-3">
        {clauses.map((clause) => (
          <ClauseCard
            key={clause.clause_id}
            clause={clause}
            isExpanded={expandedId === clause.clause_id}
            onToggle={() =>
              setExpandedId(
                expandedId === clause.clause_id ? null : clause.clause_id
              )
            }
          />
        ))}
      </div>
    </div>
  );
}
