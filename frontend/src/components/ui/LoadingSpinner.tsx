import React from 'react';
import './ui.css';

export function LoadingSpinner({ size = 24 }: { size?: number }) {
  return (
    <div className="loading-spinner-wrapper" style={{ width: size, height: size }}>
      <div className="spinner" style={{ width: size, height: size }}></div>
    </div>
  );
}
