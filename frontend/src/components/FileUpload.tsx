'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { cn, formatBytes } from '@/lib/utils';
import { uploadDocument, UploadResponse, getErrorMessage } from '@/lib/api';

interface FileUploadProps {
  onUploadComplete: (response: UploadResponse) => void;
  onUploadError: (error: string) => void;
}

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

export function FileUpload({ onUploadComplete, onUploadError }: FileUploadProps) {
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      
      if (!file) return;

      // Validate file type
      if (file.type !== 'application/pdf') {
        setErrorMessage('Please upload a PDF file');
        setUploadState('error');
        return;
      }

      // Validate file size (50MB max)
      if (file.size > 50 * 1024 * 1024) {
        setErrorMessage('File size must be less than 50MB');
        setUploadState('error');
        return;
      }

      setSelectedFile(file);
      setUploadState('uploading');
      setErrorMessage('');
      setUploadProgress(0);

      try {
        // Simulate progress for better UX
        const progressInterval = setInterval(() => {
          setUploadProgress((prev) => Math.min(prev + 10, 90));
        }, 200);

        const response = await uploadDocument(file);
        
        clearInterval(progressInterval);
        setUploadProgress(100);
        setUploadState('success');
        onUploadComplete(response);
      } catch (error) {
        const message = getErrorMessage(error);
        setErrorMessage(message);
        setUploadState('error');
        onUploadError(message);
      }
    },
    [onUploadComplete, onUploadError]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    disabled: uploadState === 'uploading',
  });

  const resetUpload = () => {
    setUploadState('idle');
    setSelectedFile(null);
    setErrorMessage('');
    setUploadProgress(0);
  };

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={cn(
          'relative border-2 border-dashed rounded-xl p-8 md:p-12 transition-all duration-200 cursor-pointer',
          'bg-white hover:bg-gray-50',
          isDragActive && !isDragReject && 'border-primary-500 bg-primary-50',
          isDragReject && 'border-red-500 bg-red-50',
          uploadState === 'uploading' && 'cursor-not-allowed opacity-75',
          uploadState === 'error' && 'border-red-300',
          uploadState === 'success' && 'border-green-300 bg-green-50',
          !isDragActive && uploadState === 'idle' && 'border-gray-300'
        )}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center justify-center text-center">
          {uploadState === 'idle' && (
            <>
              <div className="w-16 h-16 mb-4 rounded-full bg-primary-100 flex items-center justify-center">
                <Upload className="w-8 h-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {isDragActive ? 'Drop your PDF here' : 'Upload Legal Document'}
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Drag and drop a PDF file, or click to browse
              </p>
              <p className="text-xs text-gray-400">
                Supports scanned and native PDFs up to 50MB
              </p>
            </>
          )}

          {uploadState === 'uploading' && selectedFile && (
            <>
              <div className="w-16 h-16 mb-4 rounded-full bg-primary-100 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Uploading...
              </h3>
              <div className="flex items-center gap-3 mb-4">
                <FileText className="w-5 h-5 text-gray-400" />
                <span className="text-sm text-gray-600">{selectedFile.name}</span>
                <span className="text-xs text-gray-400">
                  ({formatBytes(selectedFile.size)})
                </span>
              </div>
              {/* Progress bar */}
              <div className="w-full max-w-xs bg-gray-200 rounded-full h-2">
                <div
                  className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-2">{uploadProgress}% complete</p>
            </>
          )}

          {uploadState === 'success' && selectedFile && (
            <>
              <div className="w-16 h-16 mb-4 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Upload Complete!
              </h3>
              <div className="flex items-center gap-3 mb-4">
                <FileText className="w-5 h-5 text-green-600" />
                <span className="text-sm text-gray-600">{selectedFile.name}</span>
              </div>
              <p className="text-sm text-green-600">
                Document ready for analysis
              </p>
            </>
          )}

          {uploadState === 'error' && (
            <>
              <div className="w-16 h-16 mb-4 rounded-full bg-red-100 flex items-center justify-center">
                <AlertCircle className="w-8 h-8 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Upload Failed
              </h3>
              <p className="text-sm text-red-600 mb-4">{errorMessage}</p>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  resetUpload();
                }}
                className="px-4 py-2 text-sm font-medium text-primary-600 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors"
              >
                Try Again
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
