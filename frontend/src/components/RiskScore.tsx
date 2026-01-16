'use client';

import React from 'react';
import { cn, getRiskColorClass } from '@/lib/utils';

interface RiskScoreGaugeProps {
  score: number;
  level: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function RiskScoreGauge({
  score,
  level,
  size = 'md',
  showLabel = true,
}: RiskScoreGaugeProps) {
  const colors = getRiskColorClass(level);

  const sizeClasses = {
    sm: { wrapper: 'w-24 h-24', text: 'text-2xl', label: 'text-xs' },
    md: { wrapper: 'w-36 h-36', text: 'text-4xl', label: 'text-sm' },
    lg: { wrapper: 'w-48 h-48', text: 'text-5xl', label: 'text-base' },
  };

  const { wrapper, text, label } = sizeClasses[size];

  // Calculate stroke dash for circular progress
  const radius = size === 'sm' ? 40 : size === 'md' ? 60 : 80;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className={cn('relative', wrapper)}>
      {/* Background circle */}
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="50%"
          cy="50%"
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={size === 'sm' ? 6 : size === 'md' ? 8 : 10}
        />
        {/* Progress circle */}
        <circle
          cx="50%"
          cy="50%"
          r={radius}
          fill="none"
          className={cn(
            'transition-all duration-1000 ease-out',
            level === 'critical' && 'stroke-red-600',
            level === 'high' && 'stroke-orange-600',
            level === 'medium' && 'stroke-amber-600',
            level === 'low' && 'stroke-green-600',
            level === 'minimal' && 'stroke-emerald-600'
          )}
          strokeWidth={size === 'sm' ? 6 : size === 'md' ? 8 : 10}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn('font-bold', text, colors.text)}>
          {Math.round(score)}
        </span>
        {showLabel && (
          <span className={cn('font-medium capitalize', label, colors.text)}>
            {level}
          </span>
        )}
      </div>
    </div>
  );
}

interface RiskScoreBarProps {
  score: number;
  level: string;
  label?: string;
  showValue?: boolean;
}

export function RiskScoreBar({
  score,
  level,
  label,
  showValue = true,
}: RiskScoreBarProps) {
  const colors = getRiskColorClass(level);

  return (
    <div className="w-full">
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-1">
          {label && (
            <span className="text-sm font-medium text-gray-700">{label}</span>
          )}
          {showValue && (
            <span className={cn('text-sm font-semibold', colors.text)}>
              {Math.round(score)}/100
            </span>
          )}
        </div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={cn(
            'h-2.5 rounded-full transition-all duration-500 ease-out',
            colors.bg
          )}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
    </div>
  );
}

interface RiskBadgeProps {
  level: string;
  size?: 'sm' | 'md';
}

export function RiskBadge({ level, size = 'md' }: RiskBadgeProps) {
  const colors = getRiskColorClass(level);

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full capitalize',
        colors.text,
        colors.bgLight,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
      )}
    >
      <span
        className={cn(
          'rounded-full mr-1.5',
          colors.bg,
          size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'
        )}
      />
      {level}
    </span>
  );
}
