/**
 * 安全的 HTML 渲染组件
 * 仅允许白名单内的 HTML 标签，防止 XSS 攻击
 */
import React from 'react'

// 允许的 HTML 标签（白名单）
const ALLOWED_TAGS = ['font', 'b', 'i', 'u', 'em', 'strong', 'span']

interface ParsedNode {
  type: 'text' | 'tag'
  content: string
  tag?: string
  color?: string
  children?: ParsedNode[]
}

// 解析 HTML 为节点树
function parseHtml(html: string): ParsedNode[] {
  const nodes: ParsedNode[] = []
  let remaining = html

  while (remaining.length > 0) {
    // 查找下一个 HTML 标签
    const tagRegex = /<(\/*?)(\w+)([^>]*)>/
    const tagMatch = remaining.match(tagRegex)

    if (!tagMatch || tagMatch.index === undefined) {
      // 没有更多标签，添加剩余文本
      if (remaining) {
        nodes.push({ type: 'text', content: remaining })
      }
      break
    }

    // 添加标签前的文本
    if (tagMatch.index > 0) {
      nodes.push({ type: 'text', content: remaining.substring(0, tagMatch.index) })
    }

    const [, closing, tagName, attrs] = tagMatch
    const tagLower = tagName.toLowerCase()

    // 跳过不在白名单中的标签
    if (!ALLOWED_TAGS.includes(tagLower)) {
      remaining = remaining.substring(tagMatch.index + tagMatch[0].length)
      continue
    }

    // 跳过闭合标签
    if (closing) {
      remaining = remaining.substring(tagMatch.index + tagMatch[0].length)
      continue
    }

    // 查找对应的闭合标签
    const closeTag = '</' + tagName + '>'
    const closeIndex = remaining.indexOf(closeTag, tagMatch.index + tagMatch[0].length)

    if (closeIndex === -1) {
      // 没有找到闭合标签，跳过
      remaining = remaining.substring(tagMatch.index + tagMatch[0].length)
      continue
    }

    // 提取标签内容
    const innerHtml = remaining.substring(
      tagMatch.index + tagMatch[0].length,
      closeIndex
    )

    // 解析颜色属性
    let color: string | undefined
    if (tagLower === 'font') {
      const colorMatch = attrs.match(/color=['"]([^'"]+)['"]/)
      if (colorMatch) {
        color = colorMatch[1]
      }
    }

    // 递归解析内部内容
    const children = parseHtml(innerHtml)

    nodes.push({
      type: 'tag',
      content: tagMatch[0],
      tag: tagLower,
      color,
      children,
    })

    remaining = remaining.substring(closeIndex + closeTag.length)
  }

  return nodes
}

// 渲染节点为 React 元素
function renderNodes(nodes: ParsedNode[]): React.ReactNode[] {
  return nodes.map((node, index) => {
    if (node.type === 'text') {
      return node.content
    }

    const style: React.CSSProperties = {}
    if (node.color) {
      style.color = node.color
    }

    const children = node.children ? renderNodes(node.children) : []

    return React.createElement(
      node.tag || 'span',
      { key: index, style: Object.keys(style).length > 0 ? style : undefined },
      ...children
    )
  })
}

interface SafeHtmlProps {
  html: string
  className?: string
}

export function SafeHtml({ html, className }: SafeHtmlProps) {
  const nodes = parseHtml(html)
  const elements = renderNodes(nodes)

  return <span className={className}>{elements}</span>
}
