import { cn } from '@/lib/cn';

interface CodeBlockProps {
  code: string;
  language?: string;
  className?: string;
  maxHeight?: string;
}

export function CodeBlock({ code, language = 'json', className, maxHeight }: CodeBlockProps) {
  return (
    <div className={cn('relative', className)}>
      <pre 
        className={cn(
          'overflow-auto rounded-md bg-gray-900 text-gray-100 p-4 text-sm font-mono',
          maxHeight && `max-h-[${maxHeight}]`
        )}
      >
        <code className={`language-${language}`}>{code}</code>
      </pre>
    </div>
  );
}