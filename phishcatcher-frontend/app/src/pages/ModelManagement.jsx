import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Brain, 
  ArrowLeft,
  RefreshCw,
  Loader2,
  CheckCircle,
  AlertTriangle,
  BarChart3,
  Clock,
  Database,
  Zap,
  Play,
  Settings,
  FileText,
  ChevronRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { adminApi } from '@/lib/api';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';

export default function ModelManagement() {
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [showRetrainDialog, setShowRetrainDialog] = useState(false);

  const fetchModelInfo = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getModelInfo();
      setModelInfo(data);
    } catch (error) {
      toast.error('Failed to load model information');
      console.error('Error fetching model info:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModelInfo();
  }, []);

  const handleRetrainModel = async () => {
    try {
      setRetraining(true);
      setShowRetrainDialog(false);
      await adminApi.retrainModel();
      toast.success('Model retraining has been queued. This may take several minutes.');
    } catch (error) {
      toast.error('Failed to start model retraining');
    } finally {
      setRetraining(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-violet-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" className="bg-transparent border-violet-500/25" asChild>
            <Link to="/admin">
              <ArrowLeft className="w-4 h-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl sm:text-3xl font-heading font-bold text-white">ML Model Management</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Manage phishing detection model
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            variant="outline" 
            className="bg-transparent border-violet-500/25 text-white"
            onClick={fetchModelInfo}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button 
            className="bg-violet-500 hover:bg-violet-600"
            onClick={() => setShowRetrainDialog(true)}
            disabled={retraining}
          >
            {retraining ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Play className="w-4 h-4 mr-2" />
            )}
            Retrain Model
          </Button>
        </div>
      </div>

      {/* Model Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="glass-card border-violet-500/15">
          <CardHeader className="pb-2">
            <CardDescription className="text-muted-foreground">Model Status</CardDescription>
            <CardTitle className="text-lg flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-teal-400" />
              <span className="text-white">Active</span>
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className="glass-card border-violet-500/15">
          <CardHeader className="pb-2">
            <CardDescription className="text-muted-foreground">Accuracy</CardDescription>
            <CardTitle className="text-lg text-white">
              {modelInfo?.accuracy ? `${(modelInfo.accuracy * 100).toFixed(1)}%` : 'N/A'}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className="glass-card border-violet-500/15">
          <CardHeader className="pb-2">
            <CardDescription className="text-muted-foreground">Training Samples</CardDescription>
            <CardTitle className="text-lg text-white">
              {modelInfo?.training_samples?.toLocaleString() || 'N/A'}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className="glass-card border-violet-500/15">
          <CardHeader className="pb-2">
            <CardDescription className="text-muted-foreground">Model Version</CardDescription>
            <CardTitle className="text-lg text-white">
              {modelInfo?.version || 'N/A'}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Model Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Model Information */}
        <Card className="glass-card border-violet-500/15">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Brain className="w-5 h-5 text-violet-400" />
              Model Information
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Current model configuration and metadata
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-violet-500/10">
              <span className="text-sm text-muted-foreground">Algorithm</span>
              <span className="text-sm font-medium text-white">{modelInfo?.algorithm || 'Gradient Boosting'}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-violet-500/10">
              <span className="text-sm text-muted-foreground">Features</span>
              <span className="text-sm font-medium text-white">{modelInfo?.feature_count || 'N/A'}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-violet-500/10">
              <span className="text-sm text-muted-foreground">Last Training</span>
              <span className="text-sm font-medium text-white">
                {modelInfo?.last_training_date ? new Date(modelInfo.last_training_date).toLocaleDateString() : 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-violet-500/10">
              <span className="text-sm text-muted-foreground">Model Size</span>
              <span className="text-sm font-medium text-white">{modelInfo?.model_size || 'N/A'}</span>
            </div>
          </CardContent>
        </Card>

        {/* Performance Metrics */}
        <Card className="glass-card border-violet-500/15">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-teal-400" />
              Performance Metrics
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Model performance on test dataset
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-violet-500/10">
              <span className="text-sm text-muted-foreground">Precision</span>
              <span className="text-sm font-medium text-white">
                {modelInfo?.precision ? `${(modelInfo.precision * 100).toFixed(1)}%` : 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-violet-500/10">
              <span className="text-sm text-muted-foreground">Recall</span>
              <span className="text-sm font-medium text-white">
                {modelInfo?.recall ? `${(modelInfo.recall * 100).toFixed(1)}%` : 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-violet-500/10">
              <span className="text-sm text-muted-foreground">F1 Score</span>
              <span className="text-sm font-medium text-white">
                {modelInfo?.f1_score ? `${(modelInfo.f1_score * 100).toFixed(1)}%` : 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-violet-500/10">
              <span className="text-sm text-muted-foreground">AUC-ROC</span>
              <span className="text-sm font-medium text-white">
                {modelInfo?.auc_roc ? `${(modelInfo.auc_roc * 100).toFixed(1)}%` : 'N/A'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="glass-card border-violet-500/15">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-400" />
            Quick Actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Button 
              variant="outline" 
              className="h-auto py-4 flex flex-col items-start gap-2 bg-transparent border-violet-500/25 hover:bg-violet-500/10"
              onClick={() => setShowRetrainDialog(true)}
            >
              <Play className="w-5 h-5 text-violet-400" />
              <div className="text-left">
                <p className="font-medium text-white">Retrain Model</p>
                <p className="text-xs text-muted-foreground">Start full model retraining</p>
              </div>
            </Button>

            <Button 
              variant="outline" 
              className="h-auto py-4 flex flex-col items-start gap-2 bg-transparent border-violet-500/25 hover:bg-violet-500/10"
              asChild
            >
              <Link to="/admin">
                <BarChart3 className="w-5 h-5 text-teal-400" />
                <div className="text-left">
                  <p className="font-medium text-white">View Statistics</p>
                  <p className="text-xs text-muted-foreground">See system-wide stats</p>
                </div>
              </Link>
            </Button>

            <Button 
              variant="outline" 
              className="h-auto py-4 flex flex-col items-start gap-2 bg-transparent border-violet-500/25 hover:bg-violet-500/10"
            >
              <FileText className="w-5 h-5 text-pink-400" />
              <div className="text-left">
                <p className="font-medium text-white">Export Report</p>
                <p className="text-xs text-muted-foreground">Download model report</p>
              </div>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Retrain Confirmation Dialog */}
      <Dialog open={showRetrainDialog} onOpenChange={setShowRetrainDialog}>
        <DialogContent className="glass-card border-violet-500/25">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Retrain Model
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Are you sure you want to retrain the model? This process may take several minutes and will use significant computational resources.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4" />
              <span>Estimated time: 10-30 minutes</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Database className="w-4 h-4" />
              <span>Will use latest training data</span>
            </div>
          </div>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setShowRetrainDialog(false)}
              className="bg-transparent border-violet-500/25"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleRetrainModel}
              className="bg-violet-500 hover:bg-violet-600"
              disabled={retraining}
            >
              {retraining ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              Start Retraining
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
