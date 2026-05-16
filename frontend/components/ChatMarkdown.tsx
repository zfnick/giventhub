"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders AI chat content as GitHub-flavored markdown. Element styles are
 * tuned to sit inside a chat bubble — tight spacing, small headings.
 */
export function ChatMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => (
          <p className="mb-2 leading-relaxed last:mb-0">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="mb-2 list-disc space-y-1 pl-4 last:mb-0">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-2 list-decimal space-y-1 pl-4 last:mb-0">{children}</ol>
        ),
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        strong: ({ children }) => (
          <strong className="font-semibold">{children}</strong>
        ),
        em: ({ children }) => <em className="italic">{children}</em>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium underline underline-offset-2 hover:opacity-80"
          >
            {children}
          </a>
        ),
        code: ({ children }) => (
          <code className="rounded bg-zinc-200/80 px-1 py-0.5 font-mono text-[0.85em]">
            {children}
          </code>
        ),
        pre: ({ children }) => (
          <pre className="mb-2 overflow-x-auto rounded-lg bg-zinc-900 p-3 text-xs text-zinc-50 last:mb-0 [&_code]:bg-transparent [&_code]:p-0 [&_code]:text-zinc-50">
            {children}
          </pre>
        ),
        h1: ({ children }) => (
          <h1 className="mb-2 mt-1 text-base font-bold first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="mb-2 mt-1 text-sm font-bold first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="mb-1 mt-1 text-sm font-semibold first:mt-0">{children}</h3>
        ),
        blockquote: ({ children }) => (
          <blockquote className="mb-2 border-l-2 border-zinc-300 pl-3 italic text-zinc-600 last:mb-0">
            {children}
          </blockquote>
        ),
        hr: () => <hr className="my-2 border-zinc-200" />,
        table: ({ children }) => (
          <div className="mb-2 overflow-x-auto last:mb-0">
            <table className="w-full border-collapse text-xs">{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-zinc-300 bg-zinc-100 px-2 py-1 text-left font-semibold">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-zinc-200 px-2 py-1">{children}</td>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
