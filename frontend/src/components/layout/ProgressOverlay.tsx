import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { useAppStore } from '@/stores/useAppStore';

export function ProgressOverlay() {
  const { isAnalyzing, progress } = useAppStore();

  return (
    <AnimatePresence>
      {isAnalyzing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="bg-card border border-border rounded-lg p-8 max-w-md w-full mx-4 shadow-large backdrop-blur-sm"
          >
            <div className="text-center space-y-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-full bg-gradient-primary flex items-center justify-center mx-auto">
                  <Loader2 className="h-8 w-8 text-white animate-spin" />
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  Analyzing Research Data
                </h3>
                {progress && (
                  <p className="text-sm text-foreground-secondary mb-4">
                    {progress.message}
                  </p>
                )}
              </div>

              {progress && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-foreground-secondary">
                      Step {progress.step} of {progress.total}
                    </span>
                    <span className="text-primary font-medium">
                      {progress.percentage}%
                    </span>
                  </div>
                  <Progress value={progress.percentage} className="h-2" />
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}