import { extractErrors } from './format.js'

// Понятный текст ошибки для пользователя: ответ сервера, обрыв связи или сообщение исключения
export function describeError(error, fallback = 'Не удалось выполнить действие') {
  if (error?.response || error?.isAxiosError) return extractErrors(error).message
  if (error instanceof Error && error.message) return error.message
  return fallback
}
