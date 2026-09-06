import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import MatchError from "../../app/match/error";

it("calls the App Router reset function when retrying the match page", async () => {
  const reset = vi.fn();
  const user = userEvent.setup();
  render(<MatchError reset={reset} />);

  await user.click(screen.getByRole("button", { name: "重新尝试" }));

  expect(reset).toHaveBeenCalledOnce();
});
