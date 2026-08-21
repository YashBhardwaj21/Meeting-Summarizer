import React from 'react';
import './ui.css';

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ className = '', style }: SkeletonProps) {
  return <div className={`skeleton ${className}`} style={style} />;
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton-text-group">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="skeleton-text-line" style={{ width: `${Math.max(40, 100 - i * 15)}%` }} />
      ))}
    </div>
  );
}
