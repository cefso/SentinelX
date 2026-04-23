import { z } from "zod"

export const loginSchema = z.object({
  username: z.string().min(1, "用户名不能为空"),
  password: z.string().min(1, "密码不能为空"),
})

export const registerSchema = z.object({
  username: z.string().min(3, "用户名至少3个字符").max(64, "用户名最多64个字符"),
  email: z.string().email("邮箱格式不正确"),
  password: z.string().min(8, "密码至少8个字符"),
  phone: z.string().optional(),
  tenant_id: z.number().optional(),
})

export const channelSchema = z.object({
  name: z.string().min(1, "渠道名称不能为空"),
  channel_type: z.string().min(1, "请选择渠道类型"),
  config: z.record(z.any()),
  is_active: z.boolean(),
  is_default: z.boolean(),
})

export const templateSchema = z.object({
  name: z.string().min(1, "模板名称不能为空"),
  channel_type: z.string().min(1, "请选择渠道类型"),
  content: z.string().min(1, "模板内容不能为空"),
  is_active: z.boolean(),
  is_default: z.boolean(),
})

export const changePasswordSchema = z.object({
  current_password: z.string().min(1, "请输入当前密码"),
  new_password: z.string().min(8, "新密码至少8个字符"),
  confirm_password: z.string().min(1, "请确认新密码"),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "两次输入的密码不一致",
  path: ["confirm_password"],
})

export type LoginFormData = z.infer<typeof loginSchema>
export type RegisterFormData = z.infer<typeof registerSchema>
export type ChannelFormData = z.infer<typeof channelSchema>
export type TemplateFormData = z.infer<typeof templateSchema>
export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>
