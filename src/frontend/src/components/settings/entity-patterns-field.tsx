import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ChevronDown, ChevronRight, Info } from 'lucide-react';
import { EntityPatternConfig } from '@/types/workflow-configurations';

interface EntityPatternsFieldProps {
  value: EntityPatternConfig[];
  onChange: (patterns: EntityPatternConfig[]) => void;
  entityTypes: string[];
}

export default function EntityPatternsField({ value, onChange, entityTypes }: EntityPatternsFieldProps) {
  const [activeTab, setActiveTab] = useState<string>(entityTypes[0] || 'contract');

  // Ensure we have a pattern config for each entity type
  const getPatternForType = (entityType: string): EntityPatternConfig => {
    const existing = value.find(p => p.entity_type === entityType);
    if (existing) return existing;
    
    // Return default config
    return {
      entity_type: entityType,
      enabled: false,
      key_pattern: '',
      value_extraction_source: 'key',
      value_extraction_pattern: ''
    };
  };

  const updatePattern = (entityType: string, updates: Partial<EntityPatternConfig>) => {
    const newPatterns = [...value];
    const index = newPatterns.findIndex(p => p.entity_type === entityType);
    
    if (index >= 0) {
      newPatterns[index] = { ...newPatterns[index], ...updates };
    } else {
      newPatterns.push({ ...getPatternForType(entityType), ...updates });
    }
    
    onChange(newPatterns);
  };

  const [filterExpanded, setFilterExpanded] = useState<Record<string, boolean>>({});

  return (
    <div className="space-y-4">
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Configure tag patterns for discovering and importing entities from Unity Catalog.
          Use regular expressions to match tag keys and extract entity names.
        </AlertDescription>
      </Alert>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${entityTypes.length}, 1fr)` }}>
          {entityTypes.map(type => (
            <TabsTrigger key={type} value={type} className="capitalize">
              {type}
            </TabsTrigger>
          ))}
        </TabsList>

        {entityTypes.map(entityType => {
          const pattern = getPatternForType(entityType);
          
          return (
            <TabsContent key={entityType} value={entityType}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="capitalize">{entityType} Discovery</span>
                    <div className="flex items-center gap-2">
                      <Label htmlFor={`${entityType}-enabled`}>Enable</Label>
                      <Switch
                        id={`${entityType}-enabled`}
                        checked={pattern.enabled}
                        onCheckedChange={(enabled) => updatePattern(entityType, { enabled })}
                      />
                    </div>
                  </CardTitle>
                  <CardDescription>
                    Configure patterns to discover {entityType}s from UC tags
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Filter Pattern (Optional) */}
                  <Collapsible
                    open={filterExpanded[entityType]}
                    onOpenChange={(open) => setFilterExpanded({ ...filterExpanded, [entityType]: open })}
                  >
                    <CollapsibleTrigger asChild>
                      <Button variant="ghost" className="w-full justify-between p-0 hover:no-underline">
                        <span className="text-sm font-medium">Filter Pattern (Optional)</span>
                        {filterExpanded[entityType] ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="space-y-3 pt-3">
                      <p className="text-sm text-muted-foreground">
                        Optionally filter which objects to consider by matching additional tag patterns
                      </p>
                      <div className="space-y-2">
                        <Label>Filter Source</Label>
                        <Select
                          value={pattern.filter_source || 'key'}
                          onValueChange={(source) => updatePattern(entityType, { filter_source: source })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="key">Tag Key</SelectItem>
                            <SelectItem value="value">Tag Value</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Filter Pattern (Regex)</Label>
                        <Input
                          value={pattern.filter_pattern || ''}
                          onChange={(e) => updatePattern(entityType, { filter_pattern: e.target.value })}
                          placeholder="^include-.*$"
                        />
                      </div>
                    </CollapsibleContent>
                  </Collapsible>

                  {/* Key Pattern (Required) */}
                  <div className="space-y-2">
                    <Label className="text-base font-semibold">Key Pattern (Required)</Label>
                    <p className="text-sm text-muted-foreground">
                      Regex pattern to match tag keys that identify this entity type
                    </p>
                    <Input
                      value={pattern.key_pattern}
                      onChange={(e) => updatePattern(entityType, { key_pattern: e.target.value })}
                      placeholder={`^data-${entityType}-.*$`}
                      required
                    />
                  </div>

                  {/* Value Extraction (Required) */}
                  <div className="space-y-3">
                    <Label className="text-base font-semibold">Value Extraction (Required)</Label>
                    <p className="text-sm text-muted-foreground">
                      Extract the {entityType} name from the matched tag
                    </p>
                    <div className="space-y-2">
                      <Label>Extraction Source</Label>
                      <Select
                        value={pattern.value_extraction_source}
                        onValueChange={(source) => updatePattern(entityType, { value_extraction_source: source })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="key">Tag Key</SelectItem>
                          <SelectItem value="value">Tag Value</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Extraction Pattern (Regex with Capture Group)</Label>
                      <Input
                        value={pattern.value_extraction_pattern}
                        onChange={(e) => updatePattern(entityType, { value_extraction_pattern: e.target.value })}
                        placeholder={`^data-${entityType}-(.+)$`}
                        required
                      />
                      <p className="text-xs text-muted-foreground">
                        Use parentheses () to capture the {entityType} name. Example: <code>^data-{entityType}-(.+)$</code> extracts "ABC" from "data-{entityType}-ABC"
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}

