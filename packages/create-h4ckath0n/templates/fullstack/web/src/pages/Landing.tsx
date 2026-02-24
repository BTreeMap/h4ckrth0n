import { Link } from "react-router";
import {
  Fingerprint,
  Zap,
  Lock,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "../auth";
import { Button } from "../components/Button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from "../components/Card";
import { Badge } from "../components/Badge";

export function Landing() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="flex flex-col items-center">
      {/* Hero Section */}
      <section className="w-full max-w-5xl mx-auto pt-20 pb-32 px-4 text-center">
        <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-sm font-medium text-primary mb-8 backdrop-blur-sm">
          <span className="flex h-2 w-2 rounded-full bg-primary mr-2 animate-pulse"></span>
          Hackathon Ready Template
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-text mb-6">
          Build your next big thing
          <span className="text-primary block mt-2">in record time.</span>
        </h1>

        <p className="text-xl text-text-muted mb-10 max-w-2xl mx-auto leading-relaxed">
          A secure-by-default starter kit with passkey authentication,
          device-bound keys, and role-based access control. Focus on shipping,
          not boilerplate.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          {isAuthenticated ? (
            <Link to="/dashboard">
              <Button size="lg" className="h-12 px-8 text-lg">
                Go to Dashboard <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </Link>
          ) : (
            <>
              <Link to="/register">
                <Button
                  size="lg"
                  className="h-12 px-8 text-lg"
                  data-testid="landing-register"
                >
                  <Fingerprint className="w-5 h-5 mr-2" />
                  Start Hacking
                </Button>
              </Link>
              <Link to="/login">
                <Button
                  variant="outline"
                  size="lg"
                  className="h-12 px-8 text-lg"
                  data-testid="landing-login"
                >
                  Login
                </Button>
              </Link>
            </>
          )}
        </div>
      </section>

      {/* Features Grid */}
      <section className="w-full max-w-6xl mx-auto px-4 pb-24">
        <div className="grid md:grid-cols-3 gap-6">
          <Card className="bg-surface/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-colors">
            <CardHeader>
              <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <Fingerprint className="w-6 h-6 text-primary" />
              </div>
              <CardTitle>Passkey Auth</CardTitle>
              <CardDescription className="text-base mt-2">
                No passwords to store or leak. Register and login with device
                biometrics or security keys.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="bg-surface/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-colors">
            <CardHeader>
              <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <Lock className="w-6 h-6 text-primary" />
              </div>
              <CardTitle>Device-Bound Keys</CardTitle>
              <CardDescription className="text-base mt-2">
                Each device has a non-extractable P-256 keypair. Tokens are
                signed locally and verified server-side.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="bg-surface/50 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-colors">
            <CardHeader>
              <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <Zap className="w-6 h-6 text-primary" />
              </div>
              <CardTitle>Ship Fast</CardTitle>
              <CardDescription className="text-base mt-2">
                Built on FastAPI + React + Vite. Secure defaults so you can
                focus on building your product.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="w-full bg-surface-alt/50 py-24 border-y border-border">
        <div className="max-w-5xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-12">Powered by modern tech</h2>
          <div className="flex flex-wrap justify-center gap-4">
            {[
              "React 19",
              "Vite",
              "Tailwind CSS",
              "FastAPI",
              "SQLAlchemy",
              "WebAuthn",
              "TypeScript",
              "Python",
            ].map((tech) => (
              <Badge
                key={tech}
                variant="secondary"
                className="text-lg py-2 px-4"
              >
                {tech}
              </Badge>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
