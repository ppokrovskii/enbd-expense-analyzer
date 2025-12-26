"use client";

import { useState } from "react";
import Link from "next/link";
import FileUpload from "./components/FileUpload";

export default function Home() {
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [uploadResult, setUploadResult] = useState<any>(null);

  const handleUploadComplete = (result: any) => {
    setUploadResult(result);
    setUploadStatus("success");
  };

  const handleUploadError = (error: string) => {
    setUploadStatus("error");
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-3">
        <h1 className="text-title text-[var(--color-text-primary)]">
          Upload Transactions
        </h1>
        <p className="text-body text-[var(--color-text-secondary)] max-w-xl mx-auto">
          Upload your ENBD bank statement Excel files to automatically categorize and analyze your spending patterns
        </p>
      </div>

      {/* File Upload */}
      <FileUpload 
        onUploadComplete={handleUploadComplete}
        onUploadError={handleUploadError}
      />

      {/* Success State */}
      {uploadStatus === "success" && uploadResult && (
        <div className="card p-6 bg-green-50 border border-green-200">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-heading text-green-900 mb-2">Upload Successful!</h3>
              <div className="text-body text-green-800 space-y-1">
                <p><span className="font-semibold">{uploadResult.transactions_added || 0}</span> transactions added</p>
                <p><span className="font-semibold">{uploadResult.duplicates_skipped || 0}</span> duplicates skipped</p>
              </div>
              <div className="mt-4">
                <Link 
                  href="/transactions"
                  className="btn btn-primary"
                >
                  View Transactions →
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {uploadStatus === "error" && (
        <div className="card p-6 bg-red-50 border border-red-200">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h3 className="text-heading text-red-900 mb-1">Upload Failed</h3>
              <p className="text-body text-red-700">Please check your file format and try again</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

