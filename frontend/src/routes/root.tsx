import React from 'react';

import '../components/layout/layout.css';

export function RootRoute() {
  return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 48px', backgroundColor: 'var(--color-bg)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '64px', maxWidth: '1000px', width: '100%', fontFamily: 'Inter, system-ui, sans-serif' }}>

        <div style={{ flex: '1 1 50%', display: 'flex', justifyContent: 'flex-end' }}>
          <img
            src="/hero-illustration-v3.jpg"
            alt="Lumi Illustration"
            style={{
              maxWidth: '100%',
              height: 'auto',
              maxHeight: '420px',
              objectFit: 'contain',
              mixBlendMode: 'darken'
            }}
          />
        </div>

        <div style={{ flex: '1 1 50%', textAlign: 'left' }}>
          <h1 style={{
            margin: 0,
            marginBottom: '20px',
            fontWeight: 700,
            fontSize: '42px',
            lineHeight: 1.15,
            color: '#111111'
          }}>
            Welcome to Lumi
          </h1>
          <p style={{
            margin: 0,
            marginBottom: '16px',
            fontWeight: 400,
            fontSize: '24px',
            lineHeight: 1.4,
            color: '#4A4A4A'
          }}>
            Turn your meetings into something you can explore.
          </p>
          <p style={{
            margin: 0,
            fontWeight: 400,
            fontSize: '17px',
            lineHeight: 1.5,
            color: '#6B6B6B'
          }}>
            Upload a recording to get started.
          </p>
        </div>

      </div>
    </div>
  );
}

