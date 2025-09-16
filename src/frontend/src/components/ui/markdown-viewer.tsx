import React from 'react';
import ReactMarkdown from 'react-markdown';

interface MarkdownViewerProps {
  markdown: string;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

function extractText(children: React.ReactNode): string {
  const parts: string[] = [];
  React.Children.forEach(children, (child) => {
    if (typeof child === 'string') {
      parts.push(child);
    } else if (typeof child === 'number') {
      parts.push(String(child));
    } else if (React.isValidElement(child)) {
      parts.push(extractText(child.props.children));
    }
  });
  return parts.join(' ');
}

const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ markdown }) => {
  return (
    <div className="prose prose-lg dark:prose-invert max-w-none leading-relaxed">
      <ReactMarkdown
        components={{
          h1: ({ children }) => {
            const id = slugify(extractText(children));
            return <h1 id={id} className="scroll-mt-24 tracking-tight text-4xl font-bold mb-4">{children}</h1>;
          },
          h2: ({ children }) => {
            const id = slugify(extractText(children));
            return <h2 id={id} className="scroll-mt-24 tracking-tight text-3xl font-semibold mb-3">{children}</h2>;
          },
          h3: ({ children }) => {
            const id = slugify(extractText(children));
            return <h3 id={id} className="scroll-mt-24 tracking-tight text-2xl font-semibold mb-2">{children}</h3>;
          },
          p: ({ children }) => (
            <p className="text-base mb-4">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-6 my-4">
              {children}
            </ul>
          ),
          li: ({ children }) => (
            <li className="mb-1">
              {children}
            </li>
          ),
          hr: () => <hr className="my-8 border-muted" />,
          a: ({ children, href }) => (
            <a href={href} className="text-primary underline-offset-4 hover:underline">
              {children}
            </a>
          ),
          img: ({ src, alt }) => (
            // @ts-ignore
            <img src={src as string} alt={alt as string} className="mx-auto my-6 rounded-lg border shadow-sm" />
          ),
          code: ({ children }) => (
            <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="bg-muted p-4 rounded-lg overflow-x-auto mb-4">
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-muted-foreground pl-4 italic mb-4">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-6 rounded-lg border overflow-hidden">
              <table className="w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/50 text-foreground">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="text-left px-3 py-2 border-b font-medium">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 border-b align-top">{children}</td>
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownViewer; 