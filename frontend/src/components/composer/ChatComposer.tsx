import React, { useRef, useState, useEffect } from 'react';
import { useUpload } from '../../hooks/useUpload';
import { useChatMessages } from '../../hooks/useChatMessages';
import './composer.css';

interface ChatComposerProps {
  chatId?: string;
  disabled?: boolean;
}

export function ChatComposer({ chatId, disabled }: ChatComposerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  
  const { uploadFile, isUploading, progress, status, error: uploadError } = useUpload(chatId);
  const { askQuestion, asking, error: askError } = useChatMessages(chatId);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (isUploading || disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleSubmit = async () => {
    if (isUploading || asking || disabled) return;
    
    if (selectedFile) {
      // Upload takes priority
      uploadFile(selectedFile);
    } else if (text.trim()) {
      // Ask question
      const question = text.trim();
      setText('');
      await askQuestion(question);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleClearFile = () => {
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

  const canSubmit = (selectedFile || text.trim()) && !isUploading && !asking && !disabled;
  const showFileUI = selectedFile !== null;
  const isBusy = isUploading || asking;

  return (
    <div className="chat-composer-wrapper">
      {(uploadError || askError) && (
        <div className="composer-error">
          {uploadError?.message || askError?.message}
        </div>
      )}
      
      <div 
        className={`chat-composer-box ${showFileUI ? 'has-file' : ''} ${isBusy ? 'is-busy' : ''}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileChange}
          style={{ display: 'none' }} 
        />
        
        {showFileUI && (
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
              <button className="btn-icon btn-cancel" onClick={handleClearFile} aria-label="Remove file">
                ✕
              </button>
            )}
          </div>
        )}

        <div className="composer-input-row">
          {!isBusy && !showFileUI && (
            <button 
              className="btn-icon btn-attach" 
              onClick={() => fileInputRef.current?.click()}
              disabled={isBusy || disabled}
              title="Attach a meeting recording"
            >
              +
            </button>
          )}

          <textarea
            ref={textareaRef}
            className="composer-textarea"
            placeholder={showFileUI ? "Add a message (optional)..." : "Ask anything about your meetings..."}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isBusy || disabled}
            rows={1}
            style={{ resize: 'none' }}
          />

          <button 
            className={`btn-icon btn-submit ${canSubmit ? 'active' : ''}`} 
            onClick={handleSubmit}
            disabled={!canSubmit}
            title="Send"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
