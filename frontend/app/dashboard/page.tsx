import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Dashboard - Supertrack AI Platform',
  description: 'Your AI analytics dashboard and insights',
};

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <main className="flex-1 p-6 md:p-10">
        <div className="mx-auto max-w-7xl">
          <h1 className="mb-6 text-3xl font-bold tracking-tight">Dashboard</h1>
          
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {/* Analytics Cards will go here */}
            <div className="rounded-lg border bg-card p-6 shadow-sm">
              <h3 className="mb-4 text-xl font-medium">AI Workspaces</h3>
              <p className="text-3xl font-bold text-primary">3</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Active AI workspaces with recent activity
              </p>
            </div>
            
            <div className="rounded-lg border bg-card p-6 shadow-sm">
              <h3 className="mb-4 text-xl font-medium">Models</h3>
              <p className="text-3xl font-bold text-primary">12</p>
              <p className="mt-2 text-sm text-muted-foreground">
                AI models in your workspace
              </p>
            </div>
            
            <div className="rounded-lg border bg-card p-6 shadow-sm">
              <h3 className="mb-4 text-xl font-medium">Data Sources</h3>
              <p className="text-3xl font-bold text-primary">8</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Connected data sources
              </p>
            </div>
          </div>
          
          <div className="mt-8 grid gap-6 md:grid-cols-2">
            <div className="rounded-lg border bg-card p-6 shadow-sm">
              <h3 className="mb-4 text-xl font-medium">Recent Activities</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="h-2 w-2 rounded-full bg-green-500"></div>
                  <div>
                    <p className="font-medium">Model Training Completed</p>
                    <p className="text-sm text-muted-foreground">Yesterday at 2:30 PM</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="h-2 w-2 rounded-full bg-blue-500"></div>
                  <div>
                    <p className="font-medium">New Data Source Connected</p>
                    <p className="text-sm text-muted-foreground">2 days ago</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="h-2 w-2 rounded-full bg-amber-500"></div>
                  <div>
                    <p className="font-medium">AI Report Generated</p>
                    <p className="text-sm text-muted-foreground">3 days ago</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="rounded-lg border bg-card p-6 shadow-sm">
              <h3 className="mb-4 text-xl font-medium">Quick Actions</h3>
              <div className="grid gap-2">
                <button className="inline-flex w-full items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  Create New AI Workspace
                </button>
                <button className="inline-flex w-full items-center justify-center rounded-md bg-secondary px-4 py-2 text-sm font-medium text-secondary-foreground shadow hover:bg-secondary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  Connect Data Source
                </button>
                <button className="inline-flex w-full items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  View Reports
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}