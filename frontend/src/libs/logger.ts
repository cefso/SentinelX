/**
 * SentinelX - 统一日志模块
 * 提供分级日志输出，支持环境变量配置日志级别
 */

enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

const LOG_LEVEL_NAMES: Record<LogLevel, string> = {
  [LogLevel.DEBUG]: "DEBUG",
  [LogLevel.INFO]: "INFO",
  [LogLevel.WARN]: "WARN",
  [LogLevel.ERROR]: "ERROR",
};

// 日志级别配置，从环境变量读取
const LOG_LEVEL = (() => {
  const envLevel = import.meta.env.VITE_LOG_LEVEL as string | undefined;
  const levelMap: Record<string, LogLevel> = {
    debug: LogLevel.DEBUG,
    info: LogLevel.INFO,
    warn: LogLevel.WARN,
    error: LogLevel.ERROR,
  };
  return levelMap[envLevel?.toLowerCase() || "info"] ?? LogLevel.INFO;
})();

// 是否启用日志
const ENABLE_LOGGING = import.meta.env.VITE_ENABLE_LOGGING !== "false";

/**
 * 格式化日志消息
 */
function formatMessage(level: LogLevel, context: string, ...args: unknown[]): string {
  const timestamp = new Date().toISOString();
  const levelName = LOG_LEVEL_NAMES[level];
  return `[${timestamp}] [${levelName}] [${context}]`;
}

/**
 * 日志类
 */
class Logger {
  private context: string;

  constructor(context: string) {
    this.context = context;
  }

  /**
   * 记录调试信息
   */
  debug(...args: unknown[]): void {
    if (LOG_LEVEL <= LogLevel.DEBUG && ENABLE_LOGGING) {
      console.debug(formatMessage(LogLevel.DEBUG, this.context), ...args);
    }
  }

  /**
   * 记录一般信息
   */
  info(...args: unknown[]): void {
    if (LOG_LEVEL <= LogLevel.INFO && ENABLE_LOGGING) {
      console.info(formatMessage(LogLevel.INFO, this.context), ...args);
    }
  }

  /**
   * 记录警告信息
   */
  warn(...args: unknown[]): void {
    if (LOG_LEVEL <= LogLevel.WARN && ENABLE_LOGGING) {
      console.warn(formatMessage(LogLevel.WARN, this.context), ...args);
    }
  }

  /**
   * 记录错误信息
   */
  error(...args: unknown[]): void {
    if (LOG_LEVEL <= LogLevel.ERROR && ENABLE_LOGGING) {
      console.error(formatMessage(LogLevel.ERROR, this.context), ...args);
    }
  }

  /**
   * 记录调试信息（别名）
   */
  log(...args: unknown[]): void {
    this.debug(...args);
  }
}

/**
 * 创建日志记录器
 * @param context 上下文名称，通常使用模块名或类名
 */
export function createLogger(context: string): Logger {
  return new Logger(context);
}

/**
 * 默认日志记录器
 */
export default Logger;

// 导出日志级别供外部使用
export { LogLevel };
