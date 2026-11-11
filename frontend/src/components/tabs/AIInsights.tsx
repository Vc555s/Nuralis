import { useState } from 'react';
import { motion } from 'framer-motion';
import { Brain, MessageSquare, ExternalLink, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useAppStore } from '@/stores/useAppStore';
import { ApiService } from '@/services/api';
import { toast } from '@/hooks/use-toast';

function ExecutiveSummary() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.advanced_insights?.executive_summary) return null;

  // Parse the executive summary to extract structured sections
  const parseExecutiveSummary = (text: string) => {
    const sections = [];
    const lines = text.split('\n').filter(line => line.trim());
    
    let currentSection = { title: '', content: '' };
    
    for (const line of lines) {
      const trimmedLine = line.trim();
      
      // Check if line is a section header (starts with **)
      if (trimmedLine.startsWith('**') && trimmedLine.endsWith('**')) {
        // Save previous section if it has content
        if (currentSection.title && currentSection.content) {
          sections.push({ ...currentSection });
        }
        // Start new section
        currentSection = {
          title: trimmedLine.replace(/\*\*/g, '').trim(),
          content: ''
        };
      } else if (trimmedLine) {
        // Add content to current section
        currentSection.content += (currentSection.content ? ' ' : '') + trimmedLine;
      }
    }
    
    // Add the last section
    if (currentSection.title && currentSection.content) {
      sections.push(currentSection);
    }
    
    // If no structured sections found, treat as single paragraph
    if (sections.length === 0) {
      sections.push({
        title: 'Executive Summary',
        content: text
      });
    }
    
    return sections;
  };

  const sections = parseExecutiveSummary(analysisData.advanced_insights.executive_summary);

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          Executive Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {sections.map((section, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.2 }}
              className="space-y-3"
            >
              <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full"></div>
                {section.title}
              </h3>
              <div className="pl-4">
                <p className="text-foreground-secondary leading-relaxed">
                  {section.content}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function KeyFindings() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.advanced_insights?.key_findings) return null;

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Key Research Findings</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {analysisData.advanced_insights.key_findings.map((finding, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="p-4 rounded-lg bg-background-secondary/30 border border-border/50"
            >
              <h4 className="font-medium text-foreground mb-2">{finding.finding}</h4>
              {finding.evidence && (
                <p className="text-sm text-foreground-secondary">{finding.evidence}</p>
              )}
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SemanticSearch() {
  const { searchConfig, semanticResults, setSemanticResults } = useAppStore();
  const [question, setQuestion] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!question.trim()) return;
    
    setIsSearching(true);
    try {
      const results = await ApiService.semanticSearch(question);
      setSemanticResults(results);
      toast({
        title: "Search Complete",
        description: `Found ${results.length} relevant papers.`
      });
    } catch (error) {
      toast({
        title: "Search Failed",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive"
      });
    } finally {
      setIsSearching(false);
    }
  };

  if (!searchConfig.enableEmbeddings) {
    return (
      <Card className="glass-effect border-border/50">
        <CardContent className="p-6 text-center">
          <MessageSquare className="h-8 w-8 text-foreground-muted mx-auto mb-3" />
          <p className="text-foreground-secondary">
            Semantic search is disabled. Enable it in the sidebar to use this feature.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-accent" />
          Semantic Search
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Ask a specific question about the research..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isSearching && handleSearch()}
            className="bg-background/50 border-border/50"
          />
          <Button 
            onClick={handleSearch} 
            disabled={isSearching || !question.trim()}
            className="bg-gradient-primary text-primary-foreground"
          >
            {isSearching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              'Search'
            )}
          </Button>
        </div>

        {semanticResults.length > 0 && (
          <div className="space-y-3">
            <Separator />
            <h4 className="font-medium text-foreground">Search Results</h4>
            {semanticResults.map((result, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="p-4 rounded-lg bg-background-secondary/30 border border-border/50 hover:bg-background-secondary/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <h5 className="font-medium text-foreground mb-1">
                      {result.metadata.title}
                    </h5>
                    <p className="text-sm text-foreground-secondary mb-2">
                      {Array.isArray(result.metadata.authors) 
                        ? result.metadata.authors.join(', ')
                        : result.metadata.authors}
                    </p>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        Relevance: {((1 - result.distance) * 100).toFixed(1)}%
                      </Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        asChild
                        className="h-auto p-1 text-primary hover:text-primary-hover"
                      >
                        <a 
                          href={result.metadata.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                          Read Paper
                        </a>
                      </Button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AIInsights() {
  const { analysisData, searchConfig } = useAppStore();

  if (!analysisData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Brain className="h-12 w-12 text-foreground-muted mx-auto mb-4" />
          <p className="text-foreground-secondary">Run an analysis to view AI insights</p>
        </div>
      </div>
    );
  }

  if (!searchConfig.enableLLM) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Brain className="h-12 w-12 text-foreground-muted mx-auto mb-4" />
          <p className="text-foreground-secondary">Enable LLM insights in the sidebar to use this feature</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      <ExecutiveSummary />
      <KeyFindings />
      <SemanticSearch />
    </motion.div>
  );
}