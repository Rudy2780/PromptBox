import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import Login from "../components/Login"

global.fetch = vi.fn()

describe("Login form", () => {
  beforeEach(() => {
    fetch.mockClear()
  })

  test("displays error message on 401 response", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Invalid email or password" }),
    })

    render(<MemoryRouter><Login onAuth={vi.fn()} /></MemoryRouter>)
    fireEvent.click(screen.getByTestId("email-toggle"))

    fireEvent.click(screen.getByTestId("login-btn"))

    fireEvent.change(screen.getByPlaceholderText("Email Id"), {
      target: { value: "wrong@example.com" },
    })
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "wrongpassword" },
    })

    fireEvent.click(screen.getByTestId("login-btn"))

    await waitFor(() => {
      expect(screen.getByText("Invalid email or password")).toBeInTheDocument()
    })
  })

  test("blocks submission when password is under 8 characters", async () => {
    render(<MemoryRouter><Login onAuth={vi.fn()} /></MemoryRouter>)
    fireEvent.click(screen.getByTestId("email-toggle"))

    fireEvent.click(screen.getByTestId("login-btn"))

    fireEvent.change(screen.getByPlaceholderText("Email Id"), {
      target: { value: "test@example.com" },
    })
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "short" },
    })

    fireEvent.click(screen.getByTestId("login-btn"))

    await waitFor(() => {
      expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument()
    })
    expect(fetch).not.toHaveBeenCalled()
  })

  test("blocks submission when email field is empty", async () => {
    render(<MemoryRouter><Login onAuth={vi.fn()} /></MemoryRouter>)
    fireEvent.click(screen.getByTestId("email-toggle"))

    fireEvent.click(screen.getByTestId("login-btn"))

    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "password123" },
    })

    fireEvent.click(screen.getByTestId("login-btn"))

    await waitFor(() => {
      expect(screen.getByText("Email is required")).toBeInTheDocument()
    })
    expect(fetch).not.toHaveBeenCalled()
  })
})
