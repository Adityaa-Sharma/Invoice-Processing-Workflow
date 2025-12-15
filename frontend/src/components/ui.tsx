// Reusable UI primitives

import { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';

// Status Badge
type BadgeVariant = 'success' | 'error' | 'warning' | 'info' | 'pending';

const badgeStyles: Record<BadgeVariant, string> = {
  success: 'bg-green-100 text-green-700',
  error: 'bg-red-100 text-red-700',
  warning: 'bg-amber-100 text-amber-700',
  info: 'bg-blue-100 text-blue-700',
  pending: 'bg-gray-100 text-gray-500',
};

export const Badge = ({ variant, children }: { variant: BadgeVariant; children: ReactNode }) => (
  <span className={`px-2 py-1 rounded-full text-xs font-medium ${badgeStyles[variant]}`}>
    {children}
  </span>
);

// Card wrapper
export const Card = ({ title, icon, children, className = '' }: { 
  title?: string; 
  icon?: string; 
  children: ReactNode;
  className?: string;
}) => (
  <section className={`bg-white rounded-xl shadow-lg p-6 ${className}`}>
    {title && (
      <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
        {icon && <span>{icon}</span>}
        {title}
      </h2>
    )}
    {children}
  </section>
);

// Button
type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';

const buttonStyles: Record<ButtonVariant, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  ghost: 'bg-transparent text-gray-600 hover:bg-gray-100',
};

export const Button = ({ 
  variant = 'primary' as ButtonVariant, 
  loading, 
  children, 
  ...props 
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; loading?: boolean }) => (
  <button
    {...props}
    disabled={props.disabled || loading}
    className={`px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 ${buttonStyles[variant]} ${props.className || ''}`}
  >
    {loading ? <Spinner /> : children}
  </button>
);

// Input
export const Input = ({ label, ...props }: InputHTMLAttributes<HTMLInputElement> & { label?: string }) => (
  <label className="block">
    {label && <span className="block text-sm font-medium text-gray-700 mb-1">{label}</span>}
    <input
      {...props}
      className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${props.className || ''}`}
    />
  </label>
);

// Spinner
export const Spinner = () => (
  <svg className="animate-spin h-5 w-5 mx-auto" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
  </svg>
);

// Status Dot
export const StatusDot = ({ active }: { active: boolean }) => (
  <span className={`w-2 h-2 rounded-full ${active ? 'bg-green-500' : 'bg-red-500'}`} />
);

// Progress Bar
export const ProgressBar = ({ value, max = 100 }: { value: number; max?: number }) => (
  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
    <div 
      className="h-full bg-blue-600 transition-all duration-500"
      style={{ width: `${(value / max) * 100}%` }}
    />
  </div>
);
