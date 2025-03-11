import { ReactNode } from 'react';
import {
  LayoutDashboard,
  Code2,
  Database,
  BarChart3,
  Settings,
  Users,
  Boxes,
  HelpCircle,
  GanttChart,
  Brain,
  FileJson,
} from 'lucide-react';

export interface NavigationItem {
  title: string;
  href: string;
  icon: ReactNode;
  badge?: string;
  badgeColor?: string;
  description?: string;
  requiresAdmin?: boolean;
  roles?: string[];
  children?: NavigationItem[];
}

export const navigationItems: NavigationItem[] = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: <LayoutDashboard className="h-5 w-5" />,
    description: 'Overview of your AI models, projects, and analytics',
  },
  {
    title: 'Projects',
    href: '/dashboard/projects',
    icon: <GanttChart className="h-5 w-5" />,
    description: 'Manage your AI projects and collaborations',
  },
  {
    title: 'Models',
    href: '/dashboard/models',
    icon: <Brain className="h-5 w-5" />,
    description: 'Create, train, and deploy AI models',
  },
  {
    title: 'Data Sources',
    href: '/dashboard/data-sources',
    icon: <Database className="h-5 w-5" />,
    description: 'Connect and manage data sources for your models',
    badge: 'New',
    badgeColor: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300',
  },
  {
    title: 'Analytics',
    href: '/dashboard/analytics',
    icon: <BarChart3 className="h-5 w-5" />,
    description: 'Performance metrics and insights for your AI platform',
  },
  {
    title: 'API',
    href: '/dashboard/api-docs',
    icon: <FileJson className="h-5 w-5" />,
    description: 'API documentation and references',
  },
  {
    title: 'Integrations',
    href: '/dashboard/integrations',
    icon: <Boxes className="h-5 w-5" />,
    description: 'Connect with other tools and platforms',
  },
  {
    title: 'Team',
    href: '/dashboard/team',
    icon: <Users className="h-5 w-5" />,
    description: 'Manage team members and permissions',
    requiresAdmin: true,
    roles: ['admin', 'owner'],
  },
  {
    title: 'Developer',
    href: '/dashboard/developer',
    icon: <Code2 className="h-5 w-5" />,
    description: 'Tools and resources for developers',
    children: [
      {
        title: 'API Keys',
        href: '/dashboard/developer/api-keys',
        icon: <Code2 className="h-5 w-5" />,
        description: 'Manage API keys for authentication',
      },
      {
        title: 'Webhooks',
        href: '/dashboard/developer/webhooks',
        icon: <Code2 className="h-5 w-5" />,
        description: 'Configure webhooks for event notifications',
      },
      {
        title: 'Logs',
        href: '/dashboard/developer/logs',
        icon: <Code2 className="h-5 w-5" />,
        description: 'View API logs and request history',
      },
    ],
  },
  {
    title: 'Settings',
    href: '/dashboard/settings',
    icon: <Settings className="h-5 w-5" />,
    description: 'Configure your account settings and preferences',
  },
  {
    title: 'Help & Support',
    href: '/dashboard/help',
    icon: <HelpCircle className="h-5 w-5" />,
    description: 'Get help and support for using the platform',
  },
];