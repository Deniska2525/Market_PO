import { watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { nextFocusIndex } from '../utils/dialogs'

const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

// Если открыто несколько окон, Esc и Tab обрабатывает только верхнее
const stack = []
let lockCount = 0

function lockScroll() {
  if (lockCount++ === 0) document.body.classList.add('modal-open')
}
function unlockScroll() {
  if (lockCount > 0 && --lockCount === 0) document.body.classList.remove('modal-open')
}

/**
 * Доступность модального окна: фокус уходит внутрь и не выходит за его пределы (Tab),
 * Esc закрывает, страница под окном не прокручивается, после закрытия фокус возвращается
 * на элемент, который открывал окно.
 *
 * panel        — ref на корневой элемент окна;
 * active       — ref: окно показывается, пока значение «истинно» (для всегда смонтированных окон);
 *                без него окно считается открытым, пока компонент смонтирован;
 * onEscape     — что делать по Esc;
 * initialFocus — функция, возвращающая элемент для первого фокуса.
 */
export function useDialogA11y({ panel, active = null, onEscape = null, initialFocus = null }) {
  const token = {}
  let attached = false
  let previous = null

  const focusables = () => (panel.value ? [...panel.value.querySelectorAll(FOCUSABLE)] : [])

  function onKeydown(event) {
    if (stack[stack.length - 1] !== token) return

    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      if (onEscape) onEscape()
      return
    }
    if (event.key !== 'Tab') return

    const items = focusables()
    if (!items.length) {
      event.preventDefault()
      if (panel.value) panel.value.focus()
      return
    }
    const index = items.indexOf(document.activeElement)
    const atEdge = event.shiftKey ? index <= 0 : index === items.length - 1
    if (index === -1 || atEdge) {
      event.preventDefault()
      items[nextFocusIndex(index, items.length, event.shiftKey)].focus()
    }
  }

  function open() {
    if (attached) return
    attached = true
    previous = document.activeElement
    stack.push(token)
    document.addEventListener('keydown', onKeydown, true)
    lockScroll()
    nextTick(() => {
      const target = (initialFocus && initialFocus()) || focusables()[0] || panel.value
      if (target && target.focus) target.focus()
    })
  }

  function close() {
    if (!attached) return
    attached = false
    const at = stack.indexOf(token)
    if (at !== -1) stack.splice(at, 1)
    document.removeEventListener('keydown', onKeydown, true)
    unlockScroll()
    if (previous && document.contains(previous) && previous.focus) previous.focus()
    previous = null
  }

  if (active) {
    // Окно могло смениться другим без паузы — тогда переоткрываем, чтобы фокус встал заново
    watch(active, value => {
      close()
      if (value) open()
    }, { immediate: true, flush: 'post' })
  } else {
    onMounted(open)
  }
  onBeforeUnmount(close)
}
