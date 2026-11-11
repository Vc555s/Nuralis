import { motion } from 'framer-motion';
import { TrendingUp, PieChart, Target, Award } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  ScatterChart, 
  Scatter, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { useAppStore } from '@/stores/useAppStore';

function GrowthBubbleChart() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.trends_data?.growth_analysis) return null;

  const bubbleData = Object.entries(analysisData.trends_data.growth_analysis)
    .map(([keyword, data]) => ({
      x: data.growth_rate,
      y: Math.random() * 100, // Random Y position for visual separation
      z: data.total_papers,
      keyword,
      growth_rate: data.growth_rate,
      total_papers: data.total_papers
    }))
    .sort((a, b) => b.z - a.z); // Sort by paper count for consistent layering

  const getColor = (growthRate: number) => {
    if (growthRate > 20) return '#10B981'; // Green
    if (growthRate > 0) return '#F59E0B';  // Yellow
    return '#EF4444'; // Red
  };

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Growth Rate vs Impact Analysis
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="x" 
                name="Growth Rate %" 
                stroke="hsl(var(--foreground-secondary))"
                fontSize={12}
              />
              <YAxis 
                dataKey="y" 
                name="Position"
                stroke="hsl(var(--foreground-secondary))"
                fontSize={12}
                hide
              />
              <Tooltip 
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (active && payload && payload[0]) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-card border border-border rounded-lg p-3 shadow-medium">
                        <p className="font-medium text-foreground">{data.keyword}</p>
                        <p className="text-sm text-foreground-secondary">
                          Growth Rate: {data.growth_rate.toFixed(1)}%
                        </p>
                        <p className="text-sm text-foreground-secondary">
                          Total Papers: {data.total_papers}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Scatter data={bubbleData} fill="#00D4FF">
                {bubbleData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={getColor(entry.growth_rate)}
                    r={Math.max(5, Math.min(20, entry.z / 20))} // Scale bubble size
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function CategoryBreakdown() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.papers) return null;

  // Count papers by category
  const categoryCount: Record<string, number> = {};
  analysisData.papers.forEach(paper => {
    paper.categories.forEach(category => {
      categoryCount[category] = (categoryCount[category] || 0) + 1;
    });
  });

  const pieData = Object.entries(categoryCount)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 8) // Top 8 categories
    .map(([name, value], index) => ({
      name,
      value,
      fill: [
        '#00D4FF', '#8B5CF6', '#10B981', '#F59E0B', 
        '#EF4444', '#06B6D4', '#84CC16', '#F97316'
      ][index]
    }));

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PieChart className="h-5 w-5 text-accent" />
          Research Category Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <RechartsPieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={120}
                paddingAngle={2}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  color: 'hsl(var(--foreground))'
                }}
              />
              <Legend 
                wrapperStyle={{
                  color: 'hsl(var(--foreground))',
                  fontSize: '12px'
                }}
              />
            </RechartsPieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function KeyGrowthInsights() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.trends_data?.growth_analysis) return null;

  const growthData = Object.entries(analysisData.trends_data.growth_analysis);
  
  const fastestGrowing = growthData.reduce((max, [keyword, data]) => 
    data.growth_rate > max.growth_rate ? { keyword, ...data } : max,
    { keyword: '', growth_rate: -Infinity, total_papers: 0 }
  );

  const mostStudied = growthData.reduce((max, [keyword, data]) => 
    data.total_papers > max.total_papers ? { keyword, ...data } : max,
    { keyword: '', growth_rate: 0, total_papers: 0 }
  );

  const insights = [
    {
      title: "Fastest Growing Topic",
      value: fastestGrowing.keyword,
      metric: `+${fastestGrowing.growth_rate.toFixed(1)}%`,
      icon: <TrendingUp className="h-5 w-5 text-brand-success" />,
      description: "Highest year-over-year growth rate"
    },
    {
      title: "Most Studied Topic",
      value: mostStudied.keyword,
      metric: `${mostStudied.total_papers} papers`,
      icon: <Target className="h-5 w-5 text-primary" />,
      description: "Largest volume of research papers"
    }
  ];

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Award className="h-5 w-5 text-brand-warning" />
          Key Growth Insights
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {insights.map((insight, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.2 }}
              className="p-4 rounded-lg bg-background-secondary/30 border border-border/50"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-full bg-primary/10 border border-primary/20">
                  {insight.icon}
                </div>
                <div className="flex-1">
                  <h4 className="font-medium text-foreground mb-1">{insight.title}</h4>
                  <p className="text-sm text-foreground-secondary mb-2">{insight.description}</p>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-medium">
                      {insight.value}
                    </Badge>
                    <Badge variant="secondary">
                      {insight.metric}
                    </Badge>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function GrowthAnalysis() {
  const { analysisData } = useAppStore();

  if (!analysisData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <TrendingUp className="h-12 w-12 text-foreground-muted mx-auto mb-4" />
          <p className="text-foreground-secondary">Run an analysis to view growth metrics</p>
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GrowthBubbleChart />
        <CategoryBreakdown />
      </div>
      <KeyGrowthInsights />
    </motion.div>
  );
}