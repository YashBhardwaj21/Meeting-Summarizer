import React, { useRef, useState } from 'react';
import { useUpload } from '../../hooks/useUpload';
import './upload.css';

interface UploadModalProps {
  chatId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function UploadModal({ chatId, isOpen, onClose }: UploadModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { uploadFile, isUploading, progress, error } = useUpload(chatId);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleStartUpload = () => {
    if (selectedFile) {
      uploadFile(selectedFile);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content upload-modal">
        <div className="modal-header">
          <h2>Upload Media</h2>
          {!isUploading && (
            <button className="btn-close" onClick={onClose}>×</button>
          )}
        </div>
        
        <div className="modal-body">
          {error && <div className="upload-error">{error.message}</div>}

          {!isUploading ? (
            <>
              <div 
                className={`dropzone ${selectedFile ? 'has-file' : ''}`}
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  accept="audio/*,video/*" 
                  style={{ display: 'none' }} 
                />
                
                {selectedFile ? (
                  <div className="selected-file">
                    <span className="file-icon">📄</span>
                    <span className="file-name">{selectedFile.name}</span>
                    <span className="file-size">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</span>
                  </div>
                ) : (
                  <div className="upload-text">
                  <div className="upload-primary-text">Click to upload or drag and drop</div>
                  <div className="upload-secondary-text">Supports MP3, MP4, WAV, M4A, OGG, WebM, MOV, MKV</div>
                </div>
              )}
              </div>
            
            {error && <div className="upload-error">{error.message}</div>}
            
            <div className="modal-actions">
              <button 
                className="btn-secondary" 
                onClick={onClose}
                disabled={isUploading}
              >
                Cancel
              </button>
              <button 
                className="btn-primary" 
                onClick={handleStartUpload}
                disabled={!selectedFile || isUploading}
              >
                {isUploading ? 'Uploading...' : 'Upload & Process →'}
              </button>
              </div>
            </>
          ) : (
            <div className="upload-progress-container">
              <h3>Uploading...</h3>
              <p className="text-muted">Please do not close this window</p>
              <div className="upload-progress-bar">
                <div 
                  className="upload-progress-fill" 
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <div className="upload-progress-text">{progress}%</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
