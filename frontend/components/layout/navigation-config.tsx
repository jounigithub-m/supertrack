import {
  LayoutDashboard,
  Brain,
  Bot,
  MessageSquare,
  Database,
  BarChart,
  Users,
  Key,
  Settings,
  RefreshCw,
  LucideIcon,
} from 'lucide-react';

interface NavigationItem {
  name: string;
  href: string;
  icon: LucideIcon;
}

interface NavigationGroup {
  title: string;
  items: NavigationItem[];
}

export const navigationItems: NavigationGroup[] = [
  {
    title: 'General',
    items: [
      {
        name: 'Dashboard',
        href: '/dashboard',
        icon: LayoutDashboard,
      },
      {
        name: 'AI Agents',
        href: '/agents',
        icon: Brain,
      },
      {
        name: 'Chat',
        href: '/chat',
        icon: MessageSquare,
      },
    ],
  },
  {
    title: 'Data',
    items: [
      {
        name: 'Data Sources',
        href: '/data-sources',
        icon: Database,
      },
      {
        name: 'Dashboards',
        href: '/dashboards',
        icon: BarChart,
      },
      {
        name: 'Sync Status',
        href: '/sync-status',
        icon: RefreshCw,
      },
    ],
  },
  {
    title: 'Management',
    items: [
      {
        name: 'Users',
        href: '/users',
        icon: Users,
      },
      {
        name: 'API Configuration',
        href: '/api-config',
        icon: Key,
      },
      {
        name: 'Settings',
        href: '/settings',
        icon: Settings,
      },
    ],
  },
];