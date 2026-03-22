import { useEffect, useState, useCallback } from 'react';
import { 
  Upload, 
  File, 
  CheckCircle, 
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { generateUUID } from '@/lib/uuid';
import { uploadApi, utils } from '@/lib/api';

export default function EmailUploadPage() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);

  useEffect(() => {
    // Load user's existing files on component mount
    loadUserFiles();
  }, []);

  const loadUserFiles = async () => {
    try {
      const response = await uploadApi.getUserFiles();
      if (response.items) {
        setUploadedFiles(response.items.map(file => ({
          id: file.id,
          name: file.file_name,
          size: file.file_size || 0,
          status: file.status,
          riskScore: file.risk_score,
          threatCategory: file.threat_category,
          createdAt: file.created_at,
        })));
      }
    } catch (error) {
      console.error('Failed to load user files:', error);
    }
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  }, []);

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = async (files) => {
    const validFiles = Array.from(files).filter(file => {
      if (!utils.isValidEmailFile(file.name)) {
        toast.error(`Invalid file type: ${file.name}. Please upload .eml, .txt, or .msg files only`);
        return false;
      }
      return true;
    });

    if (validFiles.length === 0) {
      return;
    }

    // Upload files one by one
    for (const file of validFiles) {
      await uploadFile(file);
    }
  };

  const uploadFile = async (file) => {
    try {
      // Add file to UI with pending status
      const tempFile = {
        id: generateUUID(),
        name: file.name,
        size: file.size,
        status: 'pending',
        isUploading: true
      };
      
      setUploadedFiles(prev => [...prev, tempFile]);
      
      // Upload to backend
      const response = await uploadApi.uploadEmail(file);
      
      // Update file with backend response
      setUploadedFiles(prev => 
        prev.map(f => f.id === tempFile.id ? { 
          ...f, 
          id: response.id,
          status: response.status || 'processing',
          isUploading: false
        } : f)
      );
      
      // Start polling for status
      if (response.id) {
        pollAnalysisStatus(response.id);
      }
      
      toast.success(`File "${file.name}" uploaded successfully`);
      
    } catch (error) {
      console.error('Upload failed:', error);
      
      // Remove temporary file and show error
      setUploadedFiles(prev => prev.filter(f => f.id !== tempFile.id));
      toast.error(`Failed to upload "${file.name}": ${error.message}`);
    }
  };

  const pollAnalysisStatus = async (analysisId) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await uploadApi.getAnalysisStatus(analysisId);
        
        setUploadedFiles(prev => 
          prev.map(f => f.id === analysisId ? { 
            ...f, 
            status: status.status,
            riskScore: status.risk_score,
            threatCategory: status.threat_category,
            progress: status.progress_percent
          } : f)
        );
        
        // Stop polling if analysis is complete or failed
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollInterval);
          
          if (status.status === 'completed') {
            toast.success(`Analysis completed for analysis ${analysisId}`);
          } else {
            toast.error(`Analysis failed for analysis ${analysisId}`);
          }
        }
      } catch (error) {
        console.error('Failed to get analysis status:', error);
        clearInterval(pollInterval);
      }
    }, 2000); // Poll every 2 seconds
    
    // Stop polling after 5 minutes max
    setTimeout(() => {
      clearInterval(pollInterval);
    }, 300000);
  };

  const removeFile = async (fileId) => {
    try {
      // Delete from backend
      await uploadApi.deleteFile(fileId);
      
      // Remove from UI
      setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
      
      toast.success('File deleted successfully');
    } catch (error) {
      console.error('Failed to delete file:', error);
      toast.error(`Failed to delete file: ${error.message}`);
    }
  };

  const clearAllFiles = async () => {
    try {
      // Delete all files from backend
      await Promise.all(
        uploadedFiles.map(file => uploadApi.deleteFile(file.id))
      );
      
      // Clear UI
      setUploadedFiles([]);
      
      toast.success('All files deleted successfully');
    } catch (error) {
      console.error('Failed to clear files:', error);
      toast.error('Failed to clear some files');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Email Upload</h1>
          <p className="text-gray-400">Upload and analyze emails for phishing threats</p>
        </div>

        {/* Upload Section */}
        <div className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6 mb-6">
          <h2 className="text-lg sm:text-xl font-heading font-semibold text-white mb-6">Upload Email Files</h2>
          
          <div 
            className={`file-upload-zone ${dragActive ? 'dragover' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              id="file-upload"
              multiple
              accept=".eml,.txt,.msg"
              onChange={handleFileInput}
              className="hidden"
            />
            <label htmlFor="file-upload" className="cursor-pointer block">
              <div className="flex flex-col items-center gap-4 sm:gap-6">
                <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-violet-500/15 flex items-center justify-center">
                  <Upload className="w-8 h-8 sm:w-10 sm:h-10 text-violet-400" />
                </div>
                <div className="text-center">
                  <p className="text-white font-medium text-lg sm:text-xl mb-2">
                    Drop your email files here, or <span className="text-violet-400">click to browse</span>
                  </p>
                  <p className="text-sm sm:text-base text-muted-foreground">
                    Supports .eml, .txt, and .msg files up to 10MB
                  </p>
                </div>
              </div>
            </label>
          </div>

          {/* Analysis Status */}
          {isAnalyzing && (
            <div className="mt-6 flex items-center gap-3 p-4 rounded-xl bg-violet-500/10 border border-violet-500/25">
              <div className="w-5 h-5 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
              <span className="text-sm text-violet-400">Analyzing email content...</span>
            </div>
          )}
        </div>

        {/* Uploaded Files */}
        {uploadedFiles.length > 0 && (
          <div className="glass-card rounded-xl sm:rounded-2xl p-4 sm:p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg sm:text-xl font-heading font-semibold text-white">
                Uploaded Files ({uploadedFiles.length})
              </h2>
              <Button
                variant="outline"
                size="sm"
                onClick={clearAllFiles}
                className="border-violet-500/30 text-violet-400 hover:bg-violet-500/10"
              >
                Clear All
              </Button>
            </div>

            <div className="space-y-3 sm:space-y-4">
              {uploadedFiles.map((file) => (
                <div 
                  key={file.id}
                  className="flex items-center gap-3 sm:gap-4 p-3 sm:p-4 rounded-xl bg-secondary-30/50 border border-violet-500/15"
                >
                  <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-violet-500/15 flex items-center justify-center flex-shrink-0">
                    <File className="w-5 h-5 sm:w-6 sm:h-6 text-violet-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white font-medium truncate">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    {file.status === 'analyzing' ? (
                      <div className="w-5 h-5 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
                    ) : file.status === 'analyzed' ? (
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-5 h-5 text-teal-400" />
                        <Badge className="bg-teal-500/20 text-teal-400 border-teal-500/30">
                          Analyzed
                        </Badge>
                      </div>
                    ) : (
                      <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
                        Pending
                      </Badge>
                    )}
                  </div>
                  <button
                    onClick={() => removeFile(file.id)}
                    className="p-2 rounded-lg hover:bg-pink-500/15 text-muted-foreground hover:text-pink-400 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {uploadedFiles.length === 0 && !isAnalyzing && (
          <div className="glass-card rounded-xl sm:rounded-2xl p-8 sm:p-12 text-center">
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-violet-500/15 flex items-center justify-center mx-auto mb-4">
              <File className="w-8 h-8 sm:w-10 sm:h-10 text-violet-400" />
            </div>
            <h3 className="text-lg sm:text-xl font-semibold text-white mb-2">No files uploaded yet</h3>
            <p className="text-sm sm:text-base text-muted-foreground mb-6">
              Upload your first email file to start analyzing for phishing threats
            </p>
            <label htmlFor="file-upload-empty" className="cursor-pointer">
              <Button className="bg-violet-500 hover:bg-violet-600">
                <Upload className="w-4 h-4 mr-2" />
                Upload Files
              </Button>
              <input
                type="file"
                id="file-upload-empty"
                multiple
                accept=".eml,.txt,.msg"
                onChange={handleFileInput}
                className="hidden"
              />
            </label>
          </div>
        )}
      </div>

      <style jsx>{`
        .file-upload-zone {
          border: 2px dashed rgba(139, 92, 246, 0.3);
          border-radius: 1rem;
          padding: 3rem 2rem;
          text-align: center;
          transition: all 0.3s ease;
          background: rgba(139, 92, 246, 0.05);
        }
        
        .file-upload-zone:hover,
        .file-upload-zone.dragover {
          border-color: rgba(139, 92, 246, 0.6);
          background: rgba(139, 92, 246, 0.1);
        }
        
        .glass-card {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(139, 92, 246, 0.2);
        }
        
        .secondary-30\/50 {
          background: rgba(139, 92, 246, 0.15);
        }
      `}</style>
    </div>
  );
}
