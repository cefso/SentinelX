export type AIContentBlock = {
  type: 'markdown' | 'think'
  content: string
}

type ThinkPattern = {
  regex: RegExp
  extract: (match: RegExpExecArray) => string
}

const THINK_PATTERNS: ThinkPattern[] = [
  {
    regex: /([\s\S]*?)<\/think>/gi,
    extract: (m) => m[1],
  },
  {
    regex: /([\s\S]*?)<\/redacted_reasoning>/gi,
    extract: (m) => m[1],
  },
  {
    regex: /<thinking>([\s\S]*?)<\/thinking>/gi,
    extract: (m) => m[1],
  },
  {
    regex: /```(?:think|thinking)\s*\n([\s\S]*?)```/gi,
    extract: (m) => m[1],
  },
]

/** 将 AI 原文拆成「思考过程」与「正文」块 */
export function parseAIContent(raw: string): AIContentBlock[] {
  const text = raw ?? ''
  if (!text.trim()) return []

  const blocks: AIContentBlock[] = []
  let remaining = text

  while (remaining.length > 0) {
    let earliest: {
      index: number
      length: number
      think: string
      before: string
    } | null = null

    for (const pattern of THINK_PATTERNS) {
      pattern.regex.lastIndex = 0
      const match = pattern.regex.exec(remaining)
      if (!match) continue
      if (earliest === null || match.index < earliest.index) {
        earliest = {
          index: match.index,
          length: match[0].length,
          think: pattern.extract(match).trim(),
          before: remaining.slice(0, match.index),
        }
      }
    }

    if (!earliest) {
      const tail = remaining.trim()
      if (tail) blocks.push({ type: 'markdown', content: remaining })
      break
    }

    const before = earliest.before.trim()
    if (before) blocks.push({ type: 'markdown', content: earliest.before })

    if (earliest.think) blocks.push({ type: 'think', content: earliest.think })

    remaining = remaining.slice(earliest.index + earliest.length)
  }

  if (blocks.length === 0 && text.trim()) {
    blocks.push({ type: 'markdown', content: text })
  }

  return blocks
}
