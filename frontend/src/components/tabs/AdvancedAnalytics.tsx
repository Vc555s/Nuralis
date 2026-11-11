import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, BarChart3, Activity, Layers } from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend
} from 'recharts';
import { useAppStore } from '@/stores/useAppStore';

function TrendsChart() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.trends_data) return null;

  const { years, keywords } = analysisData.trends_data;
  
  // Transform data for chart
  const chartData = years.map(year => {
    const dataPoint: any = { year };
    Object.entries(keywords).forEach(([keyword, values]) => {
      dataPoint[keyword] = values[year] || 0;
    });
    return dataPoint;
  });

  const colors = ['#00D4FF', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444'];

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          Research Trends Timeline
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="year" 
                stroke="hsl(var(--foreground-secondary))"
                fontSize={12}
              />
              <YAxis 
                stroke="hsl(var(--foreground-secondary))"
                fontSize={12}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  boxShadow: 'var(--shadow-medium)'
                }}
              />
              <Legend />
              {Object.keys(keywords).map((keyword, index) => (
                <Line
                  key={keyword}
                  type="monotone"
                  dataKey={keyword}
                  stroke={colors[index % colors.length]}
                  strokeWidth={2}
                  dot={{ fill: colors[index % colors.length], strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: colors[index % colors.length] }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function IndexedTimeline() {
  const { analysisData } = useAppStore();
  const enrichment = analysisData?.trends_data?.enrichment;
  if (!enrichment?.index_base_100) return null;

  // Build data rows
  const anySeries = Object.values(enrichment.index_base_100)[0];
  const years = Object.keys(anySeries || {}).map(y => Number(y)).sort((a,b)=>a-b);
  const chartData = years.map(year => {
    const row: any = { year };
    Object.entries(enrichment.index_base_100!).forEach(([keyword, series]) => {
      row[keyword] = series[String(year)] ?? 0;
    });
    return row;
  });

  const colors = ['#22d3ee','#a78bfa','#34d399','#f59e0b','#ef4444'];

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-primary" />
          Indexed Research Momentum (Base=100)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="year" stroke="hsl(var(--foreground-secondary))" fontSize={12} />
              <YAxis stroke="hsl(var(--foreground-secondary))" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', boxShadow: 'var(--shadow-medium)' }} />
              <Legend />
              {Object.keys(enrichment.index_base_100).map((keyword, index) => (
                <Line key={keyword} type="monotone" dataKey={keyword} stroke={colors[index % colors.length]} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function TrendingKeywords() {
  const { analysisData } = useAppStore();
  
  if (!analysisData?.trends_data?.growth_analysis) return null;

  const trends = Object.entries(analysisData.trends_data.growth_analysis)
    .sort(([,a], [,b]) => b.total_papers - a.total_papers)
    .slice(0, 10);

  return (
    <Card className="glass-effect border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-accent" />
          Trending Keywords
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {trends.map(([keyword, data], index) => (
            <motion.div
              key={keyword}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center justify-between p-3 rounded-lg bg-background-secondary/30 hover:bg-background-secondary/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-foreground-muted w-6">
                  #{index + 1}
                </span>
                <div>
                  <p className="font-medium text-foreground">{keyword}</p>
                  <p className="text-sm text-foreground-secondary">
                    {data.total_papers} papers total
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Badge 
                  variant={data.growth_rate > 20 ? 'default' : data.growth_rate > 0 ? 'secondary' : 'destructive'}
                  className="flex items-center gap-1"
                >
                  {data.growth_rate > 0 ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  {data.growth_rate > 0 ? '+' : ''}{data.growth_rate.toFixed(1)}%
                </Badge>
              </div>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function AdvancedAnalytics() {
  const { analysisData } = useAppStore();

  if (!analysisData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <BarChart3 className="h-12 w-12 text-foreground-muted mx-auto mb-4" />
          <p className="text-foreground-secondary">Run an analysis to view advanced analytics</p>
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
      <TrendsChart />
      <IndexedTimeline />
      <TrendingKeywords />
    </motion.div>
  );
}