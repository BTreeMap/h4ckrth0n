import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Input } from "./Input";

describe("Input", () => {
  it("renders correctly", () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText("Enter text")).toBeInTheDocument();
  });

  it("renders with label", () => {
    render(<Input label="Username" id="username" />);
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
  });

  it("renders error message", () => {
    render(<Input error="Invalid input" />);
    expect(screen.getByText("Invalid input")).toBeInTheDocument();
  });

  it("toggles password visibility", () => {
    render(<Input type="password" placeholder="Enter password" />);

    const input = screen.getByPlaceholderText("Enter password") as HTMLInputElement;
    expect(input.type).toBe("password");

    const toggleButton = screen.getByLabelText("Show password");
    fireEvent.click(toggleButton);

    expect(input.type).toBe("text");
    expect(screen.getByLabelText("Hide password")).toBeInTheDocument();

    fireEvent.click(toggleButton);
    expect(input.type).toBe("password");
    expect(screen.getByLabelText("Show password")).toBeInTheDocument();
  });

  it("does not show toggle button for non-password inputs", () => {
    render(<Input type="text" placeholder="Enter text" />);
    expect(screen.queryByLabelText("Show password")).not.toBeInTheDocument();
  });
});
