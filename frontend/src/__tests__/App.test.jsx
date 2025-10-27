import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";

test("renders login page on root redirect", async () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>
  );

  const heading = await screen.findByRole("heading", { name: /login/i });
  expect(heading).toBeInTheDocument();
});
