/**
 * Production-safe logger — only outputs in development mode.
 * Usage: import log from "@/utils/logger";
 *        log.error('msg', err);
 */
const isDev = import.meta.env.DEV;

const noop = () => {};

const log = {
  debug: isDev ? console.debug.bind(console) : noop,
  info: isDev ? console.log.bind(console) : noop,
  warn: isDev ? console.warn.bind(console) : noop,
  error: (...args) => console.error('[ERROR]', ...args),
};

export default log;
