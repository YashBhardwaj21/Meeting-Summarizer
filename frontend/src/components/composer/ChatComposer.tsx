import React, { useRef, useState, useEffect } from 'react';
import { useUpload } from '../../hooks/useUpload';
import { useChatMessages } from '../../hooks/useChatMessages';
import './composer.css';

interface ChatComposerProps {
  chatId?: string;
  disabled?: boolean;
  chatMessages?: ReturnType<typeof useChatMessages>;
  selectedFile?: File | null;
  setSelectedFile?: (file: File | null) => void;
}

export function ChatComposer({ chatId, disabled, chatMessages, selectedFile, setSelectedFile }: ChatComposerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [localFile, setLocalFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  
  const file = selectedFile !== undefined ? selectedFile : localFile;
  const setFile = setSelectedFile || setLocalFile;
  
  const { uploadFile, isUploading, progress, status, error: uploadError } = useUpload(chatId);
  const fallbackChatMessages = useChatMessages(chatId);
  const actualChatMessages = chatMessages || fallbackChatMessages;
  const { askQuestion, asking, error: askError, loadMessages } = actualChatMessages;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (isUploading || disabled) return;
    const f = e.dataTransfer.files?.[0];
    if (f) {
      setFile(f);
    }
  };

  const handleSubmit = async () => {
    if (isUploading || asking || disabled) return;
    
    if (file) {
      // Upload takes priority
      try {
        await uploadFile(file);
        setFile(null); // Clear file, but keep text in composer!
        await loadMessages(); // Refresh message list to show the meeting event!
        
        // If there's text, ask it as a question after upload
        if (text.trim()) {
          const question = text.trim();
          setText('');
          await askQuestion(question);
        }
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
      setFile(null);
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

  const canSubmit = (file || text.trim()) && !isUploading && !asking && !disabled;
  const showFileUI = file !== null && file !== undefined;
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
            disabled={isBusy || disabled}
            title="Attach a meeting recording"
          >
            +
          </button>

          {showFileUI && file && (
            <div className="composer-file-chip">
              <span className="composer-file-chip-name">
                🎵 {file.name}
              </span>
              {!isUploading && (
                <span className="composer-file-chip-size">| {formatSize(file.size)}</span>
              )}
              {isUploading ? (
                <span className="composer-file-chip-status">{progress !== null ? `${progress}%` : '...'}</span>
              ) : (
                <button className="btn-icon btn-cancel-chip" onClick={handleClearFile} aria-label="Remove file">
                  ✕
                </button>
              )}
            </div>
          )}

          <textarea
            ref={textareaRef}
            className="composer-textarea"
            placeholder={showFileUI ? "Ask anything..." : "Ask anything about your meetings..."}
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
