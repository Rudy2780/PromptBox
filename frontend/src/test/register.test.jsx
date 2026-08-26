import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import Login from "../components/Login"

global.fetch = vi.fn()

describe("Registration form", () => {
  beforeEach(() => {
    fetch.mockClear()
  })

  test("shows the server's registration message", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({ status: "ok", detail: "If that email address is available, your account has been created. You can now sign in." }),
    })

    render(<MemoryRouter><Login /></MemoryRouter>)
    // Email sign-in is revealed by the "or continue with email" toggle.
    fireEvent.click(screen.getByTestId("email-toggle"))

    fireEvent.change(screen.getByPlaceholderText("Email Id"), {
      target: { value: "newuser@example.com" },
    })
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "validpassword" },
    })

    fireEvent.click(screen.getByTestId("signup-btn"))

    await waitFor(() => {
      expect(screen.getByText("If that email address is available, your account has been created. You can now sign in.")).toBeInTheDocument()
    })
  })

  test("a taken address is indistinguishable from a fresh one", async () => {
    // The server used to answer 409 "Email already registered" here, which let
    // anyone test whether an address had an account. It now returns the same
    // 201 and body as a fresh signup, so the UI cannot reveal the difference.
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({ status: "ok", detail: "If that email address is available, your account has been created. You can now sign in." }),
    })

    render(<MemoryRouter><Login /></MemoryRouter>)
    // Email sign-in is revealed by the "or continue with email" toggle.
    fireEvent.click(screen.getByTestId("email-toggle"))

    fireEvent.change(screen.getByPlaceholderText("Email Id"), {
      target: { value: "existing@example.com" },
    })
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "validpassword" },
    })

    fireEvent.click(screen.getByTestId("signup-btn"))

    await waitFor(() => {
      expect(screen.getByText("If that email address is available, your account has been created. You can now sign in.")).toBeInTheDocument()
    })
    expect(screen.queryByText(/already registered/i)).not.toBeInTheDocument()
  })

  test("blocks submission when password is under 8 characters", async () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    // Email sign-in is revealed by the "or continue with email" toggle.
    fireEvent.click(screen.getByTestId("email-toggle"))

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
    // Email sign-in is revealed by the "or continue with email" toggle.
    fireEvent.click(screen.getByTestId("email-toggle"))

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
