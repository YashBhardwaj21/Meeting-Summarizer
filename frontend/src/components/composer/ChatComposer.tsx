import React, { useRef, useState, useEffect } from 'react';
import './composer.css';
import { useUpload } from '../../hooks/useUpload';
import type { ChatMessagesController } from '../../hooks/useChatMessages';

interface ChatComposerProps {
  chatId?: string;
  chatMessages: ChatMessagesController;
  selectedFile: File | null;
  setSelectedFile: (file: File | null) => void;
  disabled?: boolean;
}

export function ChatComposer({ chatId, disabled, chatMessages, selectedFile, setSelectedFile }: ChatComposerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [text, setText] = useState('');
  
  const { uploadFile, isUploading, progress, status, error: uploadError } = useUpload(chatId);
  const { askQuestion, asking, error: askError, loadMessages } = chatMessages;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setSelectedFile(f);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (isUploading || disabled) return;
    const f = e.dataTransfer.files?.[0];
    if (f) {
      setSelectedFile(f);
    }
  };

  const handleSubmit = async () => {
    if (isUploading || asking || disabled) return;
    
    if (selectedFile) {
      // Upload takes priority
      try {
        await uploadFile(selectedFile);
        setSelectedFile(null); // Clear file
        await loadMessages(); // Refresh message list to show the meeting event
        
        // We do not auto-send the text here, as the meeting processing just started.
        // The text is preserved in the composer.
      } catch (err) {
        // Error is handled by useUpload hook
      }
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
        
        <div className="composer-input-row">
          <button 
            className="btn-icon btn-attach" 
            onClick={() => fileInputRef.current?.click()}
            disabled={isBusy || disabled || showFileUI}
            title="Attach a meeting recording"
          >
            +
          </button>

          {showFileUI && selectedFile ? (
            <div className="composer-file-chip">
              <span className="composer-file-chip-name">
                🎵 {selectedFile.name}
              </span>
              {!isUploading && (
                <span className="composer-file-chip-size">| {formatSize(selectedFile.size)}</span>
              )}
              {isUploading ? (
                <span className="composer-file-chip-status">{progress !== null ? `${progress}%` : '...'}</span>
              ) : (
                <button className="btn-icon btn-cancel-chip" onClick={handleClearFile} aria-label="Remove file">
                  ✕
                </button>
              )}
            </div>
          ) : (
            <textarea
              ref={textareaRef}
              className="composer-textarea"
              placeholder="Ask anything about your meetings..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isBusy || disabled}
              rows={1}
              style={{ resize: 'none' }}
            />
          )}

          <button 
            className={`btn-icon btn-submit ${canSubmit ? 'active' : ''}`} 
            onClick={handleSubmit}
            disabled={!canSubmit}
            title={showFileUI ? "Upload Recording" : "Send"}
          >
            {showFileUI ? "⬆" : "➤"}
          </button>
        </div>
      </div>
    </div>
  );
}
