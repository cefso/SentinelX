import { useState, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, Brain } from 'lucide-react'
import { parseAIContent } from './parseAIContent'

const markdownComponents = {
  h1: ({ children }: { children?: ReactNode }) => (
    <h1 className="text-lg font-semibold text-gray-900 mt-4 mb-2 first:mt-0">{children}</h1>
  ),
  h2: ({ children }: { children?: ReactNode }) => (
    <h2 className="text-base font-semibold text-gray-900 mt-4 mb-2 first:mt-0">{children}</h2>
  ),
  h3: ({ children }: { children?: ReactNode }) => (
    <h3 className="text-sm font-semibold text-gray-800 mt-3 mb-1.5 first:mt-0">{children}</h3>
  ),
  p: ({ children }: { children?: ReactNode }) => (
    <p className="text-sm text-gray-700 leading-relaxed mb-2 last:mb-0">{children}</p>
  ),
  ul: ({ children }: { children?: ReactNode }) => (
    <ul className="list-disc pl-5 mb-2 space-y-1 text-sm text-gray-700">{children}</ul>
  ),
  ol: ({ children }: { children?: ReactNode }) => (
    <ol className="list-decimal pl-5 mb-2 space-y-1 text-sm text-gray-700">{children}</ol>
  ),
  li: ({ children }: { children?: ReactNode }) => (
    <li className="leading-relaxed">{children}</li>
  ),
  code: ({
    className,
    children,
    inline,
    ...props
  }: {
    className?: string
    children?: ReactNode
    inline?: boolean
  }) => {
    const isBlock = inline === false || Boolean(className?.includes('language-'))
    if (isBlock) {
      return (
        <code
          className={`block text-xs font-mono bg-gray-900 text-gray-100 p-3 rounded-md overflow-x-auto my-2 ${className || ''}`}
          {...props}
        >
          {children}
        </code>
      )
    }
    return (
      <code className="px-1 py-0.5 rounded bg-gray-200/80 text-gray-800 text-xs font-mono" {...props}>
        {children}
      </code>
    )
  },
  pre: ({ children }: { children?: ReactNode }) => (
    <pre className="my-2 overflow-x-auto rounded-md">{children}</pre>
  ),
  blockquote: ({ children }: { children?: ReactNode }) => (
    <blockquote className="border-l-4 border-purple-300 pl-3 my-2 text-sm text-gray-600 italic">
      {children}
    </blockquote>
  ),
  a: ({ href, children }: { href?: string; children?: ReactNode }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 hover:text-blue-800 underline"
    >
      {children}
    </a>
  ),
  table: ({ children }: { children?: ReactNode }) => (
    <div className="my-2 overflow-x-auto">
      <table className="min-w-full text-sm border border-gray-200 rounded">{children}</table>
    </div>
  ),
  th: ({ children }: { children?: ReactNode }) => (
    <th className="border border-gray-200 bg-gray-50 px-2 py-1 text-left font-medium">{children}</th>
  ),
  td: ({ children }: { children?: ReactNode }) => (
    <td className="border border-gray-200 px-2 py-1">{children}</td>
  ),
  hr: () => <hr className="my-4 border-gray-200" />,
}

function MarkdownBlock({ content }: { content: string }) {
  if (!content.trim()) return null
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
      {content}
    </ReactMarkdown>
  )
}

function ThinkBlock({ content, defaultOpen = false }: { content: string; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="mb-3 rounded-lg border border-dashed border-purple-200 bg-purple-50/50 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 text-left text-sm text-purple-800 hover:bg-purple-50 transition-colors"
      >
        <span className="flex items-center gap-2 font-medium">
          <Brain className="w-4 h-4 shrink-0 opacity-70" />
          思考过程
          <span className="text-xs font-normal text-purple-600/80">
            {open ? '（点击收起）' : '（点击展开）'}
          </span>
        </span>
        <ChevronDown
          className={`w-4 h-4 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <div className="px-3 pb-3 pt-0 border-t border-purple-100/80 max-h-64 overflow-auto">
          <div className="text-xs text-purple-900/90">
            <MarkdownBlock content={content} />
          </div>
        </div>
      )}
    </div>
  )
}

export function AIContentRenderer({ content }: { content: string }) {
  const blocks = parseAIContent(content)

  if (blocks.length === 0) {
    return <p className="text-sm text-gray-500">无内容</p>
  }

  return (
    <div className="ai-markdown max-h-[480px] overflow-auto">
      {blocks.map((block, i) =>
        block.type === 'think' ? (
          <ThinkBlock key={`think-${i}`} content={block.content} />
        ) : (
          <div key={`md-${i}`}>
            <MarkdownBlock content={block.content} />
          </div>
        ),
      )}
    </div>
  )
}
