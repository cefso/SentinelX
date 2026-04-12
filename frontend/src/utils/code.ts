/**
 * 从名称生成 code 字符串
 * 保留 ASCII 字母和数字，其余字符替换为连字符
 * 如果结果为空（名称全是中文/特殊字符），使用随机字符串兜底
 */
export function generateCode(name: string): string {
  const code = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
  return code || Math.random().toString(36).slice(2, 10)
}
