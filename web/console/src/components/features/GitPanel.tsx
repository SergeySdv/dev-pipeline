import * as React from 'react';
import { Link } from '@tanstack/react-router';
import { GitBranch, GitCommit, GitPullRequest, ExternalLink, RefreshCw, Check, X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Separator } from '@/components/ui/Separator';

interface Branch {
    name: string;
    isDefault: boolean;
    lastCommit?: {
        sha: string;
        message: string;
        author: string;
        date: string;
    };
    status?: 'ahead' | 'behind' | 'synced';
}

interface GitPanelProps {
    projectId: number;
    repoUrl?: string;
    defaultBranch?: string;
    branches?: Branch[];
    currentBranch?: string;
    isLoading?: boolean;
    onSync?: () => void;
    onBranchChange?: (branch: string) => void;
    className?: string;
}

export function GitPanel({
    projectId,
    repoUrl,
    defaultBranch = 'main',
    branches = [],
    currentBranch,
    isLoading = false,
    onSync,
    onBranchChange,
    className,
}: GitPanelProps) {
    const [selectedBranch, setSelectedBranch] = React.useState(currentBranch || defaultBranch);

    const handleBranchSelect = (branchName: string) => {
        setSelectedBranch(branchName);
        onBranchChange?.(branchName);
    };

    const getStatusBadge = (status?: Branch['status']) => {
        switch (status) {
            case 'ahead':
                return <Badge variant="default" className="text-xs">Ahead</Badge>;
            case 'behind':
                return <Badge variant="secondary" className="text-xs">Behind</Badge>;
            case 'synced':
                return <Badge variant="outline" className="text-xs">Synced</Badge>;
            default:
                return null;
        }
    };

    const formatDate = (dateStr?: string) => {
        if (!dateStr) return 'Unknown';
        const date = new Date(dateStr);
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    };

    return (
        <Card className={cn(className)}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <div>
                    <CardTitle className="flex items-center gap-2 text-lg">
                        <GitBranch className="h-5 w-5" />
                        Git Repository
                    </CardTitle>
                    {repoUrl && (
                        <CardDescription className="flex items-center gap-1 mt-1">
                            <a
                                href={repoUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hover:text-foreground flex items-center gap-1"
                            >
                                {repoUrl.replace(/^https?:\/\//, '').slice(0, 40)}
                                <ExternalLink className="h-3 w-3" />
                            </a>
                        </CardDescription>
                    )}
                </div>
                {onSync && (
                    <Button variant="outline" size="sm" onClick={onSync} disabled={isLoading}>
                        <RefreshCw className={cn('h-4 w-4 mr-2', isLoading && 'animate-spin')} />
                        Sync
                    </Button>
                )}
            </CardHeader>

            <CardContent>
                {branches.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                        <GitBranch className="h-8 w-8 mx-auto mb-2 opacity-20" />
                        <p>No branches found</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {branches.map((branch, idx) => (
                            <React.Fragment key={branch.name}>
                                <button
                                    onClick={() => handleBranchSelect(branch.name)}
                                    className={cn(
                                        'w-full text-left p-3 rounded-lg transition-colors',
                                        'hover:bg-muted',
                                        selectedBranch === branch.name && 'bg-muted border border-border'
                                    )}
                                >
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <GitBranch className="h-4 w-4 text-muted-foreground shrink-0" />
                                                <span className="font-medium truncate">{branch.name}</span>
                                                {branch.isDefault && (
                                                    <Badge variant="outline" className="text-xs">default</Badge>
                                                )}
                                                {getStatusBadge(branch.status)}
                                            </div>
                                            {branch.lastCommit && (
                                                <div className="mt-2 ml-6 space-y-1">
                                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                        <GitCommit className="h-3 w-3" />
                                                        <code className="bg-muted px-1 rounded">{branch.lastCommit.sha.slice(0, 7)}</code>
                                                        <span className="truncate">{branch.lastCommit.message}</span>
                                                    </div>
                                                    <div className="text-xs text-muted-foreground">
                                                        {branch.lastCommit.author} • {formatDate(branch.lastCommit.date)}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                        {selectedBranch === branch.name && (
                                            <Check className="h-4 w-4 text-primary shrink-0" />
                                        )}
                                    </div>
                                </button>
                                {idx < branches.length - 1 && <Separator />}
                            </React.Fragment>
                        ))}
                    </div>
                )}

                <Separator className="my-4" />

                <div className="flex items-center justify-between text-sm">
                    <Link
                        to="/projects/$projectId"
                        params={{ projectId: String(projectId) }}
                        search={{ tab: 'branches' }}
                        className="text-primary hover:underline flex items-center gap-1"
                    >
                        <GitPullRequest className="h-4 w-4" />
                        Manage branches
                    </Link>
                    <span className="text-muted-foreground">
                        {branches.length} branch{branches.length !== 1 ? 'es' : ''}
                    </span>
                </div>
            </CardContent>
        </Card>
    );
}
