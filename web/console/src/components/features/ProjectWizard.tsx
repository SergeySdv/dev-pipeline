import * as React from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useMutation } from '@tanstack/react-query';
import {
    FolderGit2,
    GitBranch,
    Shield,
    Rocket,
    ChevronLeft,
    ChevronRight,
    Check,
    Loader2,
    AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { apiFetchJson } from '@/api/client';

interface WizardStep {
    id: string;
    title: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
}

const steps: WizardStep[] = [
    {
        id: 'repository',
        title: 'Repository',
        description: 'Connect your Git repository',
        icon: FolderGit2,
    },
    {
        id: 'branch',
        title: 'Branch',
        description: 'Select the base branch',
        icon: GitBranch,
    },
    {
        id: 'policy',
        title: 'Policy',
        description: 'Configure enforcement mode',
        icon: Shield,
    },
    {
        id: 'launch',
        title: 'Launch',
        description: 'Review and create project',
        icon: Rocket,
    },
];

interface ProjectFormData {
    name: string;
    gitUrl: string;
    baseBranch: string;
    policyMode: 'enforce' | 'warn' | 'disabled';
}

interface ProjectWizardProps {
    onComplete?: (projectId: number) => void;
    onCancel?: () => void;
    className?: string;
}

export function ProjectWizard({ onComplete, onCancel, className }: ProjectWizardProps) {
    const navigate = useNavigate();
    const [currentStep, setCurrentStep] = React.useState(0);
    const [formData, setFormData] = React.useState<ProjectFormData>({
        name: '',
        gitUrl: '',
        baseBranch: 'main',
        policyMode: 'warn',
    });
    const [errors, setErrors] = React.useState<Record<string, string>>({});

    const createMutation = useMutation({
        mutationFn: async (data: ProjectFormData) => {
            const response = await apiFetchJson<{ id: number }>('/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: data.name,
                    git_url: data.gitUrl,
                    base_branch: data.baseBranch,
                    policy_enforcement_mode: data.policyMode,
                }),
            });
            return response;
        },
        onSuccess: (data) => {
            if (onComplete) {
                onComplete(data.id);
            } else {
                navigate({ to: '/projects/$projectId', params: { projectId: String(data.id) } });
            }
        },
    });

    const validateStep = (stepIndex: number): boolean => {
        const newErrors: Record<string, string> = {};

        if (stepIndex === 0) {
            if (!formData.name.trim()) {
                newErrors.name = 'Project name is required';
            }
            if (!formData.gitUrl.trim()) {
                newErrors.gitUrl = 'Repository URL is required';
            } else if (!formData.gitUrl.match(/^https?:\/\/.+\.git$|^git@.+:.+\.git$/)) {
                newErrors.gitUrl = 'Please enter a valid Git URL';
            }
        }

        if (stepIndex === 1) {
            if (!formData.baseBranch.trim()) {
                newErrors.baseBranch = 'Branch name is required';
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleNext = () => {
        if (validateStep(currentStep)) {
            if (currentStep < steps.length - 1) {
                setCurrentStep(currentStep + 1);
            }
        }
    };

    const handleBack = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
        }
    };

    const handleSubmit = () => {
        if (validateStep(currentStep)) {
            createMutation.mutate(formData);
        }
    };

    const updateField = <K extends keyof ProjectFormData>(field: K, value: ProjectFormData[K]) => {
        setFormData((prev) => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors((prev) => {
                const next = { ...prev };
                delete next[field];
                return next;
            });
        }
    };

    const renderStepContent = () => {
        switch (currentStep) {
            case 0:
                return (
                    <div className="space-y-4">
                        <div>
                            <label className="text-sm font-medium">Project Name</label>
                            <Input
                                placeholder="my-awesome-project"
                                value={formData.name}
                                onChange={(e) => updateField('name', e.target.value)}
                                className={cn('mt-1', errors.name && 'border-destructive')}
                            />
                            {errors.name && <p className="text-xs text-destructive mt-1">{errors.name}</p>}
                        </div>
                        <div>
                            <label className="text-sm font-medium">Repository URL</label>
                            <Input
                                placeholder="https://github.com/user/repo.git"
                                value={formData.gitUrl}
                                onChange={(e) => updateField('gitUrl', e.target.value)}
                                className={cn('mt-1', errors.gitUrl && 'border-destructive')}
                            />
                            {errors.gitUrl && <p className="text-xs text-destructive mt-1">{errors.gitUrl}</p>}
                        </div>
                    </div>
                );

            case 1:
                return (
                    <div className="space-y-4">
                        <div>
                            <label className="text-sm font-medium">Base Branch</label>
                            <Input
                                placeholder="main"
                                value={formData.baseBranch}
                                onChange={(e) => updateField('baseBranch', e.target.value)}
                                className={cn('mt-1', errors.baseBranch && 'border-destructive')}
                            />
                            {errors.baseBranch && <p className="text-xs text-destructive mt-1">{errors.baseBranch}</p>}
                            <p className="text-xs text-muted-foreground mt-1">
                                This is the branch that protocols will be created from
                            </p>
                        </div>
                    </div>
                );

            case 2:
                return (
                    <div className="space-y-3">
                        <label className="text-sm font-medium">Policy Enforcement Mode</label>
                        {(['enforce', 'warn', 'disabled'] as const).map((mode) => (
                            <button
                                key={mode}
                                onClick={() => updateField('policyMode', mode)}
                                className={cn(
                                    'w-full p-4 rounded-lg border text-left transition-colors',
                                    formData.policyMode === mode
                                        ? 'border-primary bg-primary/5'
                                        : 'border-border hover:border-muted-foreground'
                                )}
                            >
                                <div className="flex items-center justify-between">
                                    <div>
                                        <div className="font-medium capitalize">{mode}</div>
                                        <div className="text-sm text-muted-foreground">
                                            {mode === 'enforce' && 'Block operations that violate policies'}
                                            {mode === 'warn' && 'Allow but warn about policy violations'}
                                            {mode === 'disabled' && 'No policy enforcement'}
                                        </div>
                                    </div>
                                    {formData.policyMode === mode && <Check className="h-5 w-5 text-primary" />}
                                </div>
                            </button>
                        ))}
                    </div>
                );

            case 3:
                return (
                    <div className="space-y-4">
                        <div className="rounded-lg border border-border p-4 space-y-3">
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Name</span>
                                <span className="font-medium">{formData.name}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Repository</span>
                                <span className="font-mono text-sm truncate max-w-xs">{formData.gitUrl}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Base Branch</span>
                                <Badge variant="outline">{formData.baseBranch}</Badge>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Policy Mode</span>
                                <Badge variant="secondary" className="capitalize">{formData.policyMode}</Badge>
                            </div>
                        </div>
                        {createMutation.isError && (
                            <div className="flex items-center gap-2 text-destructive text-sm">
                                <AlertCircle className="h-4 w-4" />
                                Failed to create project. Please try again.
                            </div>
                        )}
                    </div>
                );

            default:
                return null;
        }
    };

    return (
        <Card className={cn('w-full max-w-2xl', className)}>
            {/* Progress Steps */}
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between mb-6">
                    {steps.map((step, idx) => {
                        const Icon = step.icon;
                        const isCompleted = idx < currentStep;
                        const isCurrent = idx === currentStep;

                        return (
                            <React.Fragment key={step.id}>
                                <div className="flex flex-col items-center">
                                    <div
                                        className={cn(
                                            'w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors',
                                            isCompleted && 'bg-primary border-primary text-primary-foreground',
                                            isCurrent && 'border-primary text-primary',
                                            !isCompleted && !isCurrent && 'border-muted text-muted-foreground'
                                        )}
                                    >
                                        {isCompleted ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                                    </div>
                                    <span className={cn('text-xs mt-1', isCurrent ? 'text-foreground font-medium' : 'text-muted-foreground')}>
                                        {step.title}
                                    </span>
                                </div>
                                {idx < steps.length - 1 && (
                                    <div className={cn('flex-1 h-0.5 mx-2', isCompleted ? 'bg-primary' : 'bg-border')} />
                                )}
                            </React.Fragment>
                        );
                    })}
                </div>
                <CardTitle>{steps[currentStep].title}</CardTitle>
                <CardDescription>{steps[currentStep].description}</CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
                {renderStepContent()}

                {/* Navigation */}
                <div className="flex items-center justify-between pt-4 border-t border-border">
                    <Button variant="ghost" onClick={onCancel || handleBack} disabled={createMutation.isPending}>
                        {currentStep === 0 ? (
                            'Cancel'
                        ) : (
                            <>
                                <ChevronLeft className="h-4 w-4 mr-1" />
                                Back
                            </>
                        )}
                    </Button>
                    {currentStep < steps.length - 1 ? (
                        <Button onClick={handleNext}>
                            Next
                            <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                    ) : (
                        <Button onClick={handleSubmit} disabled={createMutation.isPending}>
                            {createMutation.isPending ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Creating...
                                </>
                            ) : (
                                <>
                                    <Rocket className="h-4 w-4 mr-2" />
                                    Create Project
                                </>
                            )}
                        </Button>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
