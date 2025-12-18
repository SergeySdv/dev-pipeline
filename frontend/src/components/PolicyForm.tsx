import React from 'react';
import { Button } from '@/components/ui/Button';
import { FormField } from '@/components/ui/Form';
import { Select } from '@/components/ui/Select';
import { cn } from '@/lib/cn';

interface PolicyPack {
  key: string;
  version: string;
  name: string;
  description?: string;
  status: string;
}

interface PolicyFormProps {
  policyPacks: PolicyPack[];
  currentPolicy?: {
    policy_pack_key?: string;
    policy_pack_version?: string;
    policy_enforcement_mode?: string;
    policy_repo_local_enabled?: boolean;
    policy_overrides?: Record<string, any>;
  };
  onSave: (data: PolicyFormData) => void;
  onPreview?: () => void;
  className?: string;
}

export interface PolicyFormData {
  policy_pack_key: string;
  policy_pack_version: string;
  policy_enforcement_mode: string;
  policy_repo_local_enabled: boolean;
  policy_overrides: string;
}

const enforcementModes = [
  { value: 'warn', label: 'warn (default)' },
  { value: 'block', label: 'block' },
];

export function PolicyForm({ 
  policyPacks, 
  currentPolicy, 
  onSave, 
  onPreview,
  className 
}: PolicyFormProps) {
  const [formData, setFormData] = React.useState<PolicyFormData>({
    policy_pack_key: currentPolicy?.policy_pack_key || '',
    policy_pack_version: currentPolicy?.policy_pack_version || 'latest',
    policy_enforcement_mode: currentPolicy?.policy_enforcement_mode || 'warn',
    policy_repo_local_enabled: currentPolicy?.policy_repo_local_enabled || false,
    policy_overrides: JSON.stringify(currentPolicy?.policy_overrides || {}, null, 2),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let overrides: Record<string, any> = {};
    try {
      overrides = JSON.parse(formData.policy_overrides);
    } catch (error) {
      // Handle JSON parse error
      return;
    }
    onSave({ ...formData, policy_overrides: JSON.stringify(overrides) });
  };

  const selectedPack = policyPacks.find(p => p.key === formData.policy_pack_key);
  const packVersions = selectedPack ? [
    { value: 'latest', label: 'latest (recommended)' },
    { value: selectedPack.version, label: selectedPack.version },
  ] : [];

  return (
    <form onSubmit={handleSubmit} className={cn('space-y-6', className)}>
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Policy Pack">
          <Select
            value={formData.policy_pack_key}
            onChange={(e) => setFormData(prev => ({ ...prev, policy_pack_key: e.target.value }))}
            options={policyPacks.map(p => ({ value: p.key, label: `${p.key} - ${p.name}` }))}
            placeholder="Select policy pack"
          />
        </FormField>
        
        <FormField label="Version">
          <Select
            value={formData.policy_pack_version}
            onChange={(e) => setFormData(prev => ({ ...prev, policy_pack_version: e.target.value }))}
            options={packVersions}
          />
        </FormField>
      </div>

      <FormField label="Enforcement Mode">
        <Select
          value={formData.policy_enforcement_mode}
          onChange={(e) => setFormData(prev => ({ ...prev, policy_enforcement_mode: e.target.value }))}
          options={enforcementModes}
        />
      </FormField>

      <FormField label="Repository-local Override">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={formData.policy_repo_local_enabled}
            onChange={(e) => setFormData(prev => ({ ...prev, policy_repo_local_enabled: e.target.checked }))}
            className="rounded border-gray-300"
          />
          <span className="text-sm text-gray-700">
            Enable repo-local override (`.tasksgodzilla/policy.json|yml`)
          </span>
        </label>
      </FormField>

      <FormField label="Policy Overrides (JSON)">
        <textarea
          value={formData.policy_overrides}
          onChange={(e) => setFormData(prev => ({ ...prev, policy_overrides: e.target.value }))}
          placeholder='{"defaults": {"models": {"exec": "zai-coding-plan/glm-4.6"}}}'
          className="w-full h-32 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono"
        />
      </FormField>

      <div className="flex items-center gap-3">
        <Button type="submit" variant="primary">
          Save Policy
        </Button>
        {onPreview && (
          <Button type="button" variant="secondary" onClick={onPreview}>
            Preview Effective Policy
          </Button>
        )}
      </div>
    </form>
  );
}