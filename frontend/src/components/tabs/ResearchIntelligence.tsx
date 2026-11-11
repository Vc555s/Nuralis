import { motion } from 'framer-motion';
import { Lightbulb, Brain, Users, BarChart3, TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useAppStore } from '@/stores/useAppStore';

function ExecutiveSummary() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.advanced_insights?.executive_summary) return null;

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          Executive Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-foreground-secondary leading-relaxed">
          {analysisData.advanced_insights.executive_summary}
        </p>
      </CardContent>
    </Card>
  );
}

function ResearchOpportunities() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.advanced_insights?.research_gaps) return null;

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-brand-warning" />
          Research Opportunities
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {analysisData.advanced_insights.research_gaps.map((gap, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="p-4 rounded-lg bg-background-secondary/30 border border-border/50"
            >
              <h4 className="font-medium text-foreground mb-2">{gap.description}</h4>
              {gap.opportunity && (
                <p className="text-sm text-foreground-secondary">{gap.opportunity}</p>
              )}
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ImpactMetrics() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.advanced_insights?.impact_analysis) return null;

  const { impact_analysis } = analysisData.advanced_insights;
  
  const metrics = [
    {
      label: "Research Volume",
      value: impact_analysis.research_volume,
      max: 2000,
      color: "bg-primary"
    },
    {
      label: "Keyword Diversity",
      value: impact_analysis.keyword_diversity,
      max: 100,
      color: "bg-accent"
    },
    {
      label: "Temporal Span",
      value: impact_analysis.temporal_span,
      max: 10,
      color: "bg-brand-success"
    },
    {
      label: "Growth Momentum",
      value: impact_analysis.growth_momentum,
      max: 50,
      color: "bg-brand-warning"
    }
  ];

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-accent" />
          Impact Metrics
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {metrics.map((metric, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
              className="space-y-2"
            >
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-foreground">{metric.label}</span>
                <Badge variant="outline">{metric.value}</Badge>
              </div>
              <Progress 
                value={(metric.value / metric.max) * 100} 
                className="h-2"
              />
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function EmergingTopics() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.advanced_insights?.trend_analysis) return null;

  const { emerging_topics, declining_topics } = analysisData.advanced_insights.trend_analysis;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Emerging Topics */}
      {emerging_topics && (
        <Card className="glass-effect border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-brand-success" />
              Emerging Topics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {emerging_topics.slice(0, 5).map((topic, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-center justify-between p-3 rounded-lg bg-background-secondary/30"
                >
                  <span className="font-medium text-foreground">{topic.topic}</span>
                  <Badge variant="default" className="bg-brand-success text-background">
                    +{topic.growth_rate.toFixed(1)}%
                  </Badge>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Declining Topics */}
      {declining_topics && (
        <Card className="glass-effect border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingDown className="h-5 w-5 text-destructive" />
              Declining Topics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {declining_topics.slice(0, 5).map((topic, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-center justify-between p-3 rounded-lg bg-background-secondary/30"
                >
                  <span className="font-medium text-foreground">{topic.topic}</span>
                  <Badge variant="destructive">
                    {topic.growth_rate.toFixed(1)}%
                  </Badge>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function CollaborationAnalysis() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.advanced_insights?.collaboration_insights) return null;

  const { collaboration_insights } = analysisData.advanced_insights;

  const stats = [
    {
      label: "Avg Authors per Paper",
      value: collaboration_insights.avg_authors_per_paper.toFixed(1),
      icon: <Users className="h-4 w-4" />
    },
    {
      label: "Collaboration Rate",
      value: `${(collaboration_insights.collaboration_rate * 100).toFixed(1)}%`,
      icon: <Users className="h-4 w-4" />
    },
    {
      label: "Multi-Author Papers",
      value: collaboration_insights.multi_author_papers.toString(),
      icon: <Users className="h-4 w-4" />
    }
  ];

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          Collaboration Analysis
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {stats.map((stat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="text-center p-4 rounded-lg bg-background-secondary/30"
            >
              <div className="flex justify-center mb-2 text-primary">
                {stat.icon}
              </div>
              <p className="text-2xl font-bold text-foreground">{stat.value}</p>
              <p className="text-sm text-foreground-secondary">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function ResearchIntelligence() {
  const { analysisData, searchConfig } = useAppStore();

  if (!analysisData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Lightbulb className="h-12 w-12 text-foreground-muted mx-auto mb-4" />
          <p className="text-foreground-secondary">Run an analysis to view research intelligence</p>
        </div>
      </div>
    );
  }

  if (!searchConfig.enableLLM || !analysisData.advanced_insights) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Brain className="h-12 w-12 text-foreground-muted mx-auto mb-4" />
          <p className="text-foreground-secondary">
            Enable LLM insights to access research intelligence features
          </p>
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
      <ImpactMetrics />
      <ResearchOpportunities />
      <EmergingTopics />
      <CollaborationAnalysis />
    </motion.div>
  );
}