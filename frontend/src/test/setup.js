import '@testing-library/jest-dom'
import { afterEach, beforeEach } from 'vitest'

// The workspace mirrors its non-sensitive state to sessionStorage, and jsdom
// keeps one storage area for every test in a file. Without this, a test that
// switched tabs or typed a draft would hand that state to the next test.
beforeEach(() => {
  window.sessionStorage.clear()
})

afterEach(() => {
  window.sessionStorage.clear()
})
