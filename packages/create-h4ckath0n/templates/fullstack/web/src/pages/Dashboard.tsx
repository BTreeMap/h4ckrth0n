import {
  Code,
  Users,
  Trophy,
  Calendar,
  ArrowRight,
  GitBranch,
  Star,
  Activity,
} from "lucide-react";
import { useAuth } from "../auth";
import { Button } from "../components/Button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "../components/Card";
import { Badge } from "../components/Badge";
import { Avatar, AvatarFallback, AvatarImage } from "../components/Avatar";

export function Dashboard() {
  const { user } = useAuth();

  const projects = [
    {
      id: 1,
      name: "Hackathon Starter",
      description: "A secure-by-default starter kit for hackathons.",
      status: "In Progress",
      stars: 12,
      forks: 4,
      updated: "2 hours ago",
    },
    {
      id: 2,
      name: "AI Tutor",
      description: "Personalized learning assistant using GPT-4.",
      status: "Submitted",
      stars: 45,
      forks: 8,
      updated: "1 day ago",
    },
  ];

  const upcomingEvents = [
    {
      id: 1,
      name: "Submission Deadline",
      time: "Sunday, 11:59 PM",
      type: "deadline",
    },
    {
      id: 2,
      name: "Demo Day Rehearsal",
      time: "Monday, 2:00 PM",
      type: "meeting",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-text-muted mt-1">
            Welcome back, <span className="font-semibold text-text">{user?.id}</span>.
            Here's what's happening with your projects.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Users className="w-4 h-4 mr-2" />
            Find Team
          </Button>
          <Button>
            <Code className="w-4 h-4 mr-2" />
            New Project
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Projects</CardTitle>
            <Code className="h-4 w-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2</div>
            <p className="text-xs text-text-muted">+1 from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Team Members</CardTitle>
            <Users className="h-4 w-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">4</div>
            <p className="text-xs text-text-muted">Active contributors</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Achievements</CardTitle>
            <Trophy className="h-4 w-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-text-muted">Badges earned</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activity</CardTitle>
            <Activity className="h-4 w-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">98%</div>
            <p className="text-xs text-text-muted">Commit consistency</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Projects List */}
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Recent Projects</CardTitle>
            <CardDescription>
              You have {projects.length} active projects.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className="flex items-center justify-between p-4 border rounded-xl hover:bg-surface-alt/50 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{project.name}</h3>
                      <Badge
                        variant={
                          project.status === "Submitted"
                            ? "default"
                            : "secondary"
                        }
                      >
                        {project.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-text-muted">
                      {project.description}
                    </p>
                    <div className="flex items-center gap-4 text-xs text-text-muted pt-2">
                      <span className="flex items-center gap-1">
                        <Star className="w-3 h-3" /> {project.stars}
                      </span>
                      <span className="flex items-center gap-1">
                        <GitBranch className="w-3 h-3" /> {project.forks}
                      </span>
                      <span>Updated {project.updated}</span>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon">
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
          <CardFooter>
            <Button variant="outline" className="w-full">
              View All Projects
            </Button>
          </CardFooter>
        </Card>

        {/* Sidebar / Events */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Upcoming Events</CardTitle>
            <CardDescription>Don't miss these deadlines.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {upcomingEvents.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-4 p-3 rounded-lg bg-surface-alt/50"
                >
                  <div className="p-2 bg-surface rounded-lg border shadow-sm">
                    <Calendar className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{event.name}</p>
                    <p className="text-xs text-text-muted">{event.time}</p>
                  </div>
                </div>
              ))}

              <div className="mt-6 pt-6 border-t border-border">
                <h4 className="text-sm font-medium mb-4">Team Members</h4>
                <div className="flex items-center gap-2">
                  <Avatar>
                    <AvatarImage src="https://github.com/shadcn.png" />
                    <AvatarFallback>CN</AvatarFallback>
                  </Avatar>
                  <Avatar>
                    <AvatarImage src="https://github.com/leerob.png" />
                    <AvatarFallback>LR</AvatarFallback>
                  </Avatar>
                  <Avatar>
                    <AvatarImage src="https://github.com/evilrabbit.png" />
                    <AvatarFallback>ER</AvatarFallback>
                  </Avatar>
                  <Button
                    variant="outline"
                    size="icon"
                    className="rounded-full w-10 h-10 border-dashed"
                  >
                    <Users className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
