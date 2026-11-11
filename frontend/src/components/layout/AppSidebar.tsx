import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Search, 
  Cpu, 
  Zap, 
  Database,
  Calendar,
  Hash,
  BarChart3,
  Play,
  Loader2 
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { useAppStore } from '@/stores/useAppStore';
import { ApiService } from '@/services/api';
import { toast } from '@/hooks/use-toast';

interface SystemStatusCardProps {
  collapsed: boolean;
}

function SystemStatusCard({ collapsed }: SystemStatusCardProps) {
  const { systemStatus } = useAppStore();

  if (collapsed) {
    return (
      <Card className="border border-border shadow-soft">
        <CardContent className="p-2 space-y-2">
          <div className="flex flex-col items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${
              systemStatus.gpu.device === 'cuda' ? 'status-online' : 'bg-amber-400'
            }`} title="GPU Status"></div>
            <div className={`w-3 h-3 rounded-full ${
              systemStatus.llmAvailable ? 'status-online' : 'status-offline'
            }`} title="LLM Status"></div>
            <div className={`w-3 h-3 rounded-full ${
              systemStatus.embeddingsAvailable ? 'status-online' : 'status-offline'
            }`} title="Vector DB Status"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border shadow-soft">
      <CardContent className="p-4 space-y-3">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-foreground-secondary">GPU</span>
            <Badge variant={systemStatus.gpu.device === 'cuda' ? 'default' : 'secondary'} className="text-xs">
              {systemStatus.gpu.device.toUpperCase()}
            </Badge>
          </div>
          {systemStatus.gpu.total && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-foreground-muted">
                <span>Memory Usage</span>
                <span>{systemStatus.gpu.allocated}MB / {systemStatus.gpu.total}MB</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div 
                  className="bg-primary h-2 rounded-full transition-all duration-500"
                  style={{ width: `${(systemStatus.gpu.allocated! / systemStatus.gpu.total) * 100}%` }}
                ></div>
              </div>
            </div>
          )}
        </div>
        
        <Separator />
        
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-500" />
              <span className="text-sm font-medium">LLM Engine</span>
            </div>
            <div className={`w-2 h-2 rounded-full ${
              systemStatus.llmAvailable ? 'status-online' : 'status-offline'
            }`}></div>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-blue-500" />
              <span className="text-sm font-medium">Vector DB</span>
            </div>
            <div className={`w-2 h-2 rounded-full ${
              systemStatus.embeddingsAvailable ? 'status-online' : 'status-offline'
            }`}></div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface SearchConfigCardProps {
  collapsed: boolean;
}

function SearchConfigCard({ collapsed }: SearchConfigCardProps) {
  const { 
    searchConfig, 
    updateSearchConfig, 
    isAnalyzing, 
    setIsAnalyzing, 
    setProgress, 
    setAnalysisData 
  } = useAppStore();

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: currentYear - 2000 + 1 }, (_, i) => 2000 + i).reverse();

  const handleAnalyze = async () => {
    if (!searchConfig.query.trim()) {
      toast({
        title: "Query Required",
        description: "Please enter a research query to analyze.",
        variant: "destructive"
      });
      return;
    }

    setIsAnalyzing(true);
    
    try {
      // Simulate progress steps
      const steps = [
        { step: 1, total: 5, message: "Initializing search...", percentage: 20 },
        { step: 2, total: 5, message: "Fetching papers...", percentage: 40 },
        { step: 3, total: 5, message: "Processing data...", percentage: 60 },
        { step: 4, total: 5, message: "Generating insights...", percentage: 80 },
        { step: 5, total: 5, message: "Finalizing analysis...", percentage: 100 }
      ];

      for (const step of steps) {
        setProgress(step);
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      const result = await ApiService.analyzeResearch(searchConfig);
      setAnalysisData(result);
      
      toast({
        title: "Analysis Complete",
        description: `Found ${result.papers.length} papers matching your query.`,
      });
    } catch (error) {
      toast({
        title: "Analysis Failed",
        description: error instanceof Error ? error.message : "An error occurred during analysis.",
        variant: "destructive"
      });
    } finally {
      setIsAnalyzing(false);
      setProgress(null);
    }
  };

  if (collapsed) {
    return (
      <Card className="border border-border shadow-soft">
        <CardContent className="p-2">
          <Button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !searchConfig.query.trim()}
            className="w-full bg-gradient-primary hover:opacity-90 text-white border-0 shadow-sm"
            size="sm"
          >
            {isAnalyzing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border shadow-soft">
      <CardHeader className="pb-4">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Search className="h-5 w-5 text-primary" />
          Search Configuration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="query" className="text-sm font-medium">Research Query</Label>
          <Input
            id="query"
            placeholder="Enter your research topic..."
            value={searchConfig.query}
            onChange={(e) => updateSearchConfig({ query: e.target.value })}
            className="bg-background border-border focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label className="text-sm flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Start Year
            </Label>
            <Select 
              value={searchConfig.startYear.toString()} 
              onValueChange={(value) => updateSearchConfig({ startYear: parseInt(value) })}
            >
              <SelectTrigger className="bg-background/50 border-border/50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {years.map(year => (
                  <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-sm">End Year</Label>
            <Select 
              value={searchConfig.endYear.toString()} 
              onValueChange={(value) => updateSearchConfig({ endYear: parseInt(value) })}
            >
              <SelectTrigger className="bg-background/50 border-border/50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {years.map(year => (
                  <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label className="text-sm flex items-center gap-1">
              <Hash className="h-3 w-3" />
              Max Papers
            </Label>
            <Badge variant="outline">{searchConfig.maxPapers}</Badge>
          </div>
          <Slider
            value={[searchConfig.maxPapers]}
            onValueChange={([value]) => updateSearchConfig({ maxPapers: value })}
            max={1000}
            min={100}
            step={50}
            className="w-full"
          />
        </div>

        <Separator />

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="llm-toggle" className="text-sm">Enable LLM Insights</Label>
            <Switch
              id="llm-toggle"
              checked={searchConfig.enableLLM}
              onCheckedChange={(checked) => updateSearchConfig({ enableLLM: checked })}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="semantic-toggle" className="text-sm">Enable Semantic Search</Label>
            <Switch
              id="semantic-toggle"
              checked={searchConfig.enableEmbeddings}
              onCheckedChange={(checked) => updateSearchConfig({ enableEmbeddings: checked })}
            />
          </div>
        </div>

        <Button
          onClick={handleAnalyze}
          disabled={isAnalyzing || !searchConfig.query.trim()}
          className="w-full bg-gradient-primary hover:opacity-90 text-primary-foreground border-0 glow-primary"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <BarChart3 className="mr-2 h-4 w-4" />
              Analyze Research
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

export function AppSidebar() {
  const { sidebarCollapsed } = useAppStore();

  return (
    <motion.aside
      initial={false}
      animate={{ 
        width: sidebarCollapsed ? 'var(--sidebar-width-collapsed)' : 'var(--sidebar-width)',
      }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="border-r border-border bg-background flex flex-col overflow-hidden"
    >
      <div className="p-4 space-y-4 overflow-y-auto">
        <SystemStatusCard collapsed={sidebarCollapsed} />
        <SearchConfigCard collapsed={sidebarCollapsed} />
      </div>
    </motion.aside>
  );
}