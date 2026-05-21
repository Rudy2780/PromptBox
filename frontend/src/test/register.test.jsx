import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import Login from "../components/Login"

global.fetch = vi.fn()

describe("Registration form", () => {
  beforeEach(() => {
    fetch.mockClear()
  })

  test("shows success message on successful registration", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({}),
    })

    render(<MemoryRouter><Login /></MemoryRouter>)

    fireEvent.change(screen.getByPlaceholderText("Email Id"), {
      target: { value: "newuser@example.com" },
    })
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "validpassword" },
    })

    fireEvent.click(screen.getByTestId("signup-btn"))

    await waitFor(() => {
      expect(screen.getByText("Account created! You can now login.")).toBeInTheDocument()
    })
  })

  test("shows error on duplicate email (409)", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({ detail: "Email already registered" }),
    })

    render(<MemoryRouter><Login /></MemoryRouter>)

    fireEvent.change(screen.getByPlaceholderText("Email Id"), {
      target: { value: "existing@example.com" },
    })
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "validpassword" },
    })

    fireEvent.click(screen.getByTestId("signup-btn"))

    await waitFor(() => {
      expect(screen.getByText("Email already registered")).toBeInTheDocument()
    })
  })

  test("blocks submission when password is under 8 characters", async () => {
    render(<MemoryRouter><Login /></MemoryRouter>)

    fireEvent.change(screen.getByPlaceholderText("Email Id"), {
      target: { value: "test@example.com" },
    })
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "short" },
    })

    fireEvent.click(screen.getByTestId("signup-btn"))

    await waitFor(() => {
      expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument()
    })
  })

  test("blocks submission when email is invalid", async () => {
    render(<MemoryRouter><Login /></MemoryRouter>)

    fireEvent.change(screen.getByPlaceholderText("Email Id"), {
      target: { value: "" },
    })
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "validpassword" },
    })

    fireEvent.click(screen.getByTestId("signup-btn"))

    await waitFor(() => {
      expect(screen.getByText("Email is required")).toBeInTheDocument()
    })
  })
})
