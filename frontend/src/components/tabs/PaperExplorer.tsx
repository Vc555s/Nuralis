import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Search, Calendar, Tag, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { useAppStore } from '@/stores/useAppStore';
import { Paper } from '@/types';

interface PaperCardProps {
  paper: Paper;
  index: number;
}

function PaperCard({ paper, index }: PaperCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const authors = Array.isArray(paper.authors) ? paper.authors : [paper.authors];
  const categories = Array.isArray(paper.categories) ? paper.categories : [paper.categories];
  
  // Truncate abstract for preview
  const truncatedAbstract = paper.abstract.length > 200 
    ? paper.abstract.substring(0, 200) + '...'
    : paper.abstract;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <Card className="glass-effect border-border/50 hover:shadow-medium transition-all duration-300">
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <CardTitle className="text-lg font-semibold leading-tight mb-2">
                  {paper.title}
                </CardTitle>
                <div className="flex flex-wrap items-center gap-2 text-sm text-foreground-secondary">
                  <span>{authors.join(', ')}</span>
                  <span>•</span>
                  <span>{paper.date}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  asChild
                  className="text-primary hover:text-primary-hover"
                >
                  <a 
                    href={paper.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center gap-1"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Read
                  </a>
                </Button>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="sm">
                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </Button>
                </CollapsibleTrigger>
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="pt-0">
            <div className="space-y-3">
              <div className="flex flex-wrap gap-1">
                {categories.map((category, idx) => (
                  <Badge key={idx} variant="secondary" className="text-xs">
                    {category}
                  </Badge>
                ))}
              </div>
              
              <CollapsibleContent className="space-y-3">
                <div className="p-3 rounded-lg bg-background-secondary/30 border border-border/50">
                  <h4 className="font-medium text-sm mb-2">Abstract</h4>
                  <p className="text-sm text-foreground-secondary leading-relaxed">
                    {paper.abstract}
                  </p>
                </div>
              </CollapsibleContent>
              
              {!isExpanded && (
                <p className="text-sm text-foreground-secondary leading-relaxed">
                  {truncatedAbstract}
                </p>
              )}
            </div>
          </CardContent>
        </Collapsible>
      </Card>
    </motion.div>
  );
}

export function PaperExplorer() {
  const { analysisData } = useAppStore();
  const [selectedYear, setSelectedYear] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const filteredPapers = useMemo(() => {
    if (!analysisData?.papers) return [];

    return analysisData.papers.filter(paper => {
      const yearMatch = selectedYear === 'all' || 
        (paper.date && paper.date.toString().includes(selectedYear));
      
      const categoryMatch = selectedCategory === 'all' ||
        paper.categories.some(cat => cat.toLowerCase().includes(selectedCategory.toLowerCase()));

      return yearMatch && categoryMatch;
    }).slice(0, 20); // Limit to 20 papers for performance
  }, [analysisData?.papers, selectedYear, selectedCategory]);

  // Extract unique years and categories for filters
  const availableYears = useMemo(() => {
    if (!analysisData?.papers) return [];
    
    const years = new Set<string>();
    analysisData.papers.forEach(paper => {
      if (paper.date) {
        const year = paper.date.toString().substring(0, 4);
        years.add(year);
      }
    });
    
    return Array.from(years).sort().reverse();
  }, [analysisData?.papers]);

  const availableCategories = useMemo(() => {
    if (!analysisData?.papers) return [];
    
    const categories = new Set<string>();
    analysisData.papers.forEach(paper => {
      const paperCategories = Array.isArray(paper.categories) ? paper.categories : [paper.categories];
      paperCategories.forEach(cat => categories.add(cat));
    });
    
    return Array.from(categories).sort();
  }, [analysisData?.papers]);

  if (!analysisData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Search className="h-12 w-12 text-foreground-muted mx-auto mb-4" />
          <p className="text-foreground-secondary">Run an analysis to explore papers</p>
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
      {/* Filters */}
      <Card className="glass-effect border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5 text-primary" />
            Paper Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">Year</label>
              <Select value={selectedYear} onValueChange={setSelectedYear}>
                <SelectTrigger className="bg-background/50 border-border/50">
                  <SelectValue placeholder="All Years" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Years</SelectItem>
                  {availableYears.map(year => (
                    <SelectItem key={year} value={year}>{year}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">Category</label>
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger className="bg-background/50 border-border/50">
                  <SelectValue placeholder="All Categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {availableCategories.map(category => (
                    <SelectItem key={category} value={category}>{category}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="mt-3 text-sm text-foreground-secondary">
            Showing {filteredPapers.length} of {analysisData.papers.length} papers
          </div>
        </CardContent>
      </Card>

      {/* Papers List */}
      <div className="space-y-4">
        {filteredPapers.map((paper, index) => (
          <PaperCard key={index} paper={paper} index={index} />
        ))}
        
        {filteredPapers.length === 0 && (
          <Card className="glass-effect border-border/50">
            <CardContent className="p-8 text-center">
              <Search className="h-8 w-8 text-foreground-muted mx-auto mb-3" />
              <p className="text-foreground-secondary">
                No papers match the selected filters
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </motion.div>
  );
}