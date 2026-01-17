import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind CSS classes with clsx.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format bytes to human-readable size.
 */
export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Format date to locale string.
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Get risk level color classes.
 */
export function getRiskColorClass(level: string): {
  text: string;
  bg: string;
  border: string;
  bgLight: string;
} {
  switch (level.toLowerCase()) {
    case 'critical':
      return {
        text: 'text-red-600',
        bg: 'bg-red-600',
        border: 'border-red-600',
        bgLight: 'bg-red-50',
      };
    case 'high':
      return {
        text: 'text-orange-600',
        bg: 'bg-orange-600',
        border: 'border-orange-600',
        bgLight: 'bg-orange-50',
      };
    case 'medium':
      return {
        text: 'text-amber-600',
        bg: 'bg-amber-600',
        border: 'border-amber-600',
        bgLight: 'bg-amber-50',
      };
    case 'low':
      return {
        text: 'text-green-600',
        bg: 'bg-green-600',
        border: 'border-green-600',
        bgLight: 'bg-green-50',
      };
    case 'minimal':
      return {
        text: 'text-emerald-600',
        bg: 'bg-emerald-600',
        border: 'border-emerald-600',
        bgLight: 'bg-emerald-50',
      };
    default:
      return {
        text: 'text-gray-600',
        bg: 'bg-gray-600',
        border: 'border-gray-600',
        bgLight: 'bg-gray-50',
      };
  }
}

/**
 * Get risk level label.
 */
export function getRiskLabel(level: string): string {
  const labels: Record<string, string> = {
    critical: 'Critical Risk',
    high: 'High Risk',
    medium: 'Medium Risk',
    low: 'Low Risk',
    minimal: 'Minimal Risk',
  };
  return labels[level.toLowerCase()] || level;
}

/**
 * Format clause type for display.
 */
export function formatClauseType(type: string): string {
  return type
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Truncate text with ellipsis.
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}
