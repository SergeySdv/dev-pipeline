import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Search, Plus, LayoutGrid, List, GitBranch, Shield } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { useProjects } from './hooks';
import { cn } from '@/lib/cn';

type ViewMode = 'grid' | 'list';

export function ProjectsListPage() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  
  const { data: projects, isLoading } = useProjects();

  const handleCreateProject = () => {
    navigate({ to: '/projects/new' });
  };

  const handleSelectProject = (projectId: number) => {
    navigate({ to: '/projects/$projectId', params: { projectId: String(projectId) } });
  };

  const filteredProjects = projects?.filter(p => 
    p.name.toLowerCase().includes(filter.toLowerCase()) || 
    (p.git_url && p.git_url.toLowerCase().includes(filter.toLowerCase()))
  );

  if (isLoading) {
    return <LoadingState message="Loading projects..." />;
  }

  return (
    <div className="container py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-muted-foreground mt-1">Manage your software projects and their configurations</p>
        </div>
        <Button onClick={handleCreateProject}>
          <Plus className="mr-2 h-4 w-4" />
          Create Project
        </Button>
      </div>

      {/* Filters and View Toggle */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Filter by name or URL..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex items-center border border-border rounded-lg p-1 bg-muted/30">
          <Button
            variant={viewMode === 'grid' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('grid')}
            className="px-2"
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('list')}
            className="px-2"
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Projects Display */}
      {filteredProjects && filteredProjects.length > 0 ? (
        viewMode === 'grid' ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredProjects.map((project) => (
              <Card 
                key={project.id} 
                className="cursor-pointer transition-all hover:border-primary/50 hover:shadow-md"
                onClick={() => handleSelectProject(project.id)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg">{project.name}</CardTitle>
                    {project.policy_enforcement_mode === 'warn' && (
                      <Badge variant="secondary" className="text-xs">warn</Badge>
                    )}
                    {project.policy_enforcement_mode === 'enforce' && (
                      <Badge variant="default" className="text-xs">enforce</Badge>
                    )}
                  </div>
                  {project.git_url && (
                    <CardDescription className="text-xs font-mono truncate">
                      {project.git_url}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <GitBranch className="h-3 w-3" />
                      <span>{project.base_branch || 'main'}</span>
                    </div>
                    {project.policy_pack_key && (
                      <div className="flex items-center gap-1">
                        <Shield className="h-3 w-3" />
                        <span className="truncate max-w-[100px]">{project.policy_pack_key}</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="p-0">
              <div className="divide-y divide-border">
                {filteredProjects.map((project) => (
                  <div
                    key={project.id}
                    className="flex items-center justify-between p-4 hover:bg-muted/50 cursor-pointer transition-colors"
                    onClick={() => handleSelectProject(project.id)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{project.name}</span>
                        {project.policy_enforcement_mode === 'warn' && (
                          <Badge variant="secondary" className="text-xs">warn</Badge>
                        )}
                        {project.policy_enforcement_mode === 'enforce' && (
                          <Badge variant="default" className="text-xs">enforce</Badge>
                        )}
                      </div>
                      {project.git_url && (
                        <p className="text-xs text-muted-foreground font-mono truncate mt-1">
                          {project.git_url}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <GitBranch className="h-3 w-3" />
                        <span>{project.base_branch || 'main'}</span>
                      </div>
                      {project.policy_pack_key && (
                        <Badge variant="outline">
                          <Shield className="h-3 w-3 mr-1" />
                          {project.policy_pack_key}
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-12">
            {projects && projects.length > 0 ? (
              <div className="flex flex-col items-center justify-center text-center">
                <Search className="h-12 w-12 mb-4 text-muted-foreground opacity-20" />
                <h3 className="text-lg font-medium">No matching projects</h3>
                <p className="mt-1 text-muted-foreground">Try adjusting your filter criteria</p>
                <Button variant="link" onClick={() => setFilter('')} className="mt-4">
                  Clear filter
                </Button>
              </div>
            ) : (
              <EmptyState
                title="No projects yet"
                description="Get started by creating your first project to onboard and manage protocols."
                action={
                  <Button onClick={handleCreateProject} className="mt-4">
                    <Plus className="mr-2 h-4 w-4" />
                    Create Project
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
