import { createRootRoute, createRoute, createRouter, Outlet, redirect } from '@tanstack/react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { z } from 'zod';
import { Toaster } from 'sonner';

import { AppShell } from '@/app/shell/AppShell';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { ProjectsListPage } from '@/features/projects/ProjectsListPage';
import { ProjectsNewPage } from '@/features/projects/ProjectsNewPage';
import { ProjectDetailPage } from '@/features/projects/ProjectDetailPage';
import { ProtocolsListPage } from '@/features/protocols/ProtocolsListPage';
import { ProtocolsNewPage } from '@/features/protocols/ProtocolsNewPage';
import { ProtocolDetailPage } from '@/features/protocols/ProtocolDetailPage';
import { StepsListPage } from '@/features/steps/StepsListPage';
import { StepDetailPage } from '@/features/steps/StepDetailPage';
import { RunsListPage } from '@/features/runs/RunsListPage';
import { RunDetailPage } from '@/features/runs/RunDetailPage';
import { OpsQueuesPage } from '@/features/ops/OpsQueuesPage';
import { OpsEventsPage } from '@/features/ops/OpsEventsPage';
import { OpsMetricsPage } from '@/features/ops/OpsMetricsPage';
import { PolicyPacksPage } from '@/features/policy/PacksPage';
import { SettingsPage } from '@/features/settings/SettingsPage';
import { NotFoundPage } from '@/features/errors/NotFoundPage';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
const DISABLE_AUTH = import.meta.env.VITE_DISABLE_AUTH === 'true';
const ROUTER_BASEPATH = import.meta.env.MODE === 'production' ? '/console' : '';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const RootRoute = createRootRoute({
  component: function Root() {
    return (
      <QueryClientProvider client={queryClient}>
        <Outlet />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    );
  },
});

const AppRoute = createRoute({
  getParentRoute: () => RootRoute,
  path: '/',
  beforeLoad: async ({ location }) => {
    if (location.pathname === '/') {
      throw redirect({ to: '/dashboard' });
    }
    if (!DISABLE_AUTH) {
      try {
        const resp = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' });
        if (resp.status === 401) {
          if (typeof window !== 'undefined') {
            const next = window.location.pathname + window.location.search;
            window.location.assign(`${API_BASE}/auth/login?next=${encodeURIComponent(next)}`);
          }
          return;
        }
      } catch {
        // Best effort: allow app to render and surface errors in UI.
      }
    }
  },
  component: function AppLayout() {
    return (
      <AppShell>
        <Outlet />
      </AppShell>
    );
  },
});

const DashboardRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/dashboard',
  component: DashboardPage,
});

const ProjectsRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/projects',
  component: ProjectsListPage,
});

const ProjectsNewRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/projects/new',
  component: ProjectsNewPage,
});

const ProjectDetailRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/projects/$projectId',
  validateSearch: z
    .object({
      tab: z.enum(['overview', 'onboarding', 'protocols', 'policy', 'clarifications', 'branches']).optional(),
    })
    .parse,
  component: ProjectDetailPage,
});

const ProtocolsRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/protocols',
  component: ProtocolsListPage,
});

const ProtocolDetailRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/protocols/$protocolId',
  validateSearch: z
    .object({
      tab: z.enum(['steps', 'events', 'runs', 'spec', 'policy', 'clarifications']).optional(),
    })
    .parse,
  component: ProtocolDetailPage,
});

const ProtocolsNewRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/protocols/new',
  validateSearch: z
    .object({
      projectId: z.string().optional(),
    })
    .parse,
  component: ProtocolsNewPage,
});

const RunsListRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/runs',
  component: RunsListPage,
});

const RunDetailRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/runs/$runId',
  component: RunDetailPage,
});

const OpsQueuesRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/ops/queues',
  component: OpsQueuesPage,
});

const OpsEventsRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/ops/events',
  component: OpsEventsPage,
});

const PolicyPacksRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/policy-packs',
  component: PolicyPacksPage,
});

const StepsRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/steps',
  component: StepsListPage,
});

const StepDetailRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/steps/$stepId',
  component: StepDetailPage,
});

const OpsMetricsRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/ops/metrics',
  component: OpsMetricsPage,
});

const SettingsRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '/settings',
  validateSearch: z
    .object({
      tab: z.enum(['profile', 'preferences', 'live_updates', 'integrations', 'shortcuts', 'advanced']).optional(),
    })
    .parse,
  component: SettingsPage,
});

const NotFoundRoute = createRoute({
  getParentRoute: () => AppRoute,
  path: '*',
  component: NotFoundPage,
});

const routeTree = RootRoute.addChildren([
  AppRoute.addChildren([
    DashboardRoute,
    ProjectsRoute,
    ProjectsNewRoute,
    ProjectDetailRoute,
    ProtocolsRoute,
    ProtocolsNewRoute,
    ProtocolDetailRoute,
    StepsRoute,
    StepDetailRoute,
    RunsListRoute,
    RunDetailRoute,
    OpsQueuesRoute,
    OpsEventsRoute,
    OpsMetricsRoute,
    PolicyPacksRoute,
    SettingsRoute,
    NotFoundRoute,
  ]),
]);

export const router = createRouter({ routeTree, basepath: ROUTER_BASEPATH });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
