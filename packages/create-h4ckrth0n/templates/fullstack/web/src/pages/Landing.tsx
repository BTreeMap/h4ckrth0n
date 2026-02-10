import { Link } from "react-router";

export function Landing() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-20 text-center">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
        Ship fast, safely&nbsp;🚀
      </h1>
      <p className="mt-4 text-lg text-text-muted">
        Fullstack hackathon starter with passkey auth, Postgres, and LLM tooling — ready in seconds.
      </p>
      <div className="mt-8 flex justify-center gap-4">
        <Link
          to="/register"
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-hover"
        >
          Get started
        </Link>
        <Link
          to="/login"
          className="rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-text hover:bg-surface-alt"
        >
          Sign in
        </Link>
      </div>
    </div>
  );
}
