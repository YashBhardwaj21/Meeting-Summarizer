import React, { useRef, useState } from 'react';
import { useUpload } from '../../hooks/useUpload';
import './composer.css';

interface MeetingComposerProps {
  chatId?: string;
}

export function MeetingComposer({ chatId }: MeetingComposerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { uploadFile, isUploading, progress, status, error } = useUpload(chatId);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (isUploading) return;
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleSubmit = () => {
    if (selectedFile && !isUploading) {
      uploadFile(selectedFile);
    }
  };

  const handleClear = () => {
    if (!isUploading) {
      setSelectedFile(null);
    }
  };

  const renderStatus = () => {
    if (!status || status === 'idle') return null;
    
    let text = status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ');
    if (status === 'uploading' && progress !== null) {
      text += ` — ${progress}%`;
    }
    return <div className="composer-status-text">{text}</div>;
  };

  const formatSize = (bytes: number) => {
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <div className="meeting-composer-wrapper">
      {error && <div className="composer-error">{error.message}</div>}
      
      <div 
        className={`meeting-composer ${selectedFile ? 'has-file' : ''} ${isUploading ? 'is-uploading' : ''}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileChange}
          style={{ display: 'none' }} 
        />
        
        <div className="composer-inner">
          {!selectedFile ? (
            <div 
              className="composer-empty-state" 
              onClick={() => fileInputRef.current?.click()}
            >
              Upload or drop a meeting recording...
            </div>
          ) : (
            <div className="composer-file-state">
              <div className="composer-file-info">
                <span className="composer-file-name">
                  {isUploading ? `Uploading ${selectedFile.name}` : selectedFile.name}
                </span>
                {!isUploading && (
                  <span className="composer-file-size">{formatSize(selectedFile.size)}</span>
                )}
              </div>
              
              {isUploading ? (
                <div className="composer-progress-section">
                  {renderStatus()}
                </div>
              ) : (
                <button className="btn-icon btn-cancel" onClick={handleClear} aria-label="Remove file">
                  ✕
                </button>
              )}
            </div>
          )}

          {!isUploading && (
            <button 
              className={`btn-icon btn-submit ${selectedFile ? 'active' : ''}`} 
              onClick={selectedFile ? handleSubmit : () => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              ➤
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
