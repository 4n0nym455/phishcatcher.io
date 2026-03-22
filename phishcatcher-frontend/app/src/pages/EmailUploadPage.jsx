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

export default function EmailUploadPage() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);

  useEffect(() => {
    // Component mounted
  }, []);

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

  const handleFiles = (files) => {
    const validFiles = Array.from(files).filter(file => {
      const ext = file.name.split('.').pop().toLowerCase();
      return ['eml', 'txt', 'msg'].includes(ext);
    });

    if (validFiles.length === 0) {
      toast.error('Please upload .eml, .txt, or .msg files only');
      return;
    }

    validFiles.forEach(file => {
      setUploadedFiles(prev => [...prev, { name: file.name, size: file.size, status: 'pending' }]);
      analyzeFile(file);
    });
  };

  const analyzeFile = (file) => {
    setIsAnalyzing(true);
    
    // Simulate analysis - in real implementation, this would call your API
    setTimeout(() => {
      setIsAnalyzing(false);
      setUploadedFiles(prev => 
        prev.map(f => f.name === file.name ? { ...f, status: 'analyzed' } : f)
      );
      toast.success(`Analysis complete for ${file.name}`);
    }, 2000);
  };

  const removeFile = (fileName) => {
    setUploadedFiles(prev => prev.filter(f => f.name !== fileName));
  };

  const clearAllFiles = () => {
    setUploadedFiles([]);
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
        <div className="glass-card rounded-2xl p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-6">Upload Email Files</h2>
          
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
              <div className="flex flex-col items-center gap-4">
                <div className="w-20 h-20 rounded-2xl bg-violet-500/15 flex items-center justify-center">
                  <Upload className="w-10 h-10 text-violet-400" />
                </div>
                <div className="text-center">
                  <p className="text-white font-medium text-lg mb-2">
                    Drop your email files here, or <span className="text-violet-400">click to browse</span>
                  </p>
                  <p className="text-sm text-gray-400">
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
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">
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

            <div className="space-y-3">
              {uploadedFiles.map((file, index) => (
                <div 
                  key={index}
                  className="flex items-center gap-4 p-4 rounded-xl bg-secondary-30/50 border border-violet-500/15"
                >
                  <div className="w-12 h-12 rounded-lg bg-violet-500/15 flex items-center justify-center flex-shrink-0">
                    <File className="w-6 h-6 text-violet-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white font-medium truncate">{file.name}</p>
                    <p className="text-xs text-gray-400">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
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
                    <button
                      onClick={() => removeFile(file.name)}
                      className="p-2 rounded-lg hover:bg-pink-500/15 text-gray-400 hover:text-pink-400 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {uploadedFiles.length === 0 && !isAnalyzing && (
          <div className="glass-card rounded-2xl p-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-violet-500/15 flex items-center justify-center mx-auto mb-4">
              <File className="w-8 h-8 text-violet-400" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">No files uploaded yet</h3>
            <p className="text-gray-400 mb-6">
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
