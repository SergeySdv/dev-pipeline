"use client";

import { AlertTriangle, Bell, CheckCircle2, GitPullRequest,XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatRelativeTime } from "@/lib/format";

interface Notification {
  id: string;
  type: "success" | "warning" | "error" | "info";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actionUrl?: string;
}

const mockNotifications: Notification[] = [
  {
    id: "1",
    type: "success",
    title: "Protocol Completed",
    message: "Feature: User Authentication protocol completed successfully",
    timestamp: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
    read: false,
    actionUrl: "/protocols/1",
  },
  {
    id: "2",
    type: "warning",
    title: "Policy Violation",
    message: "Code complexity exceeds threshold in step: analyze_requirements",
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    read: false,
    actionUrl: "/steps/step-123",
  },
  {
    id: "3",
    type: "error",
    title: "Run Failed",
    message: "Code execution failed with syntax error",
    timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    read: true,
    actionUrl: "/runs/run-456",
  },
  {
    id: "4",
    type: "info",
    title: "PR Opened",
    message: "New pull request created for feature/user-auth",
    timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    read: true,
  },
];

const notificationIcons = {
  success: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
  info: GitPullRequest,
};

const notificationColors = {
  success: "text-green-500",
  warning: "text-yellow-500",
  error: "text-red-500",
  info: "text-blue-500",
};

export function NotificationsPanel() {
  const unreadCount = mockNotifications.filter((n) => !n.read).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Notifications
          {unreadCount > 0 && (
            <Badge variant="destructive" className="ml-2">
              {unreadCount}
            </Badge>
          )}
        </CardTitle>
        <CardDescription>Recent activity and alerts</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {mockNotifications.map((notification) => {
            const Icon = notificationIcons[notification.type];
            return (
              <div
                key={notification.id}
                className={`rounded-lg border p-4 ${!notification.read ? "bg-muted/50" : ""}`}
              >
                <div className="flex items-start gap-3">
                  <Icon className={`mt-0.5 h-5 w-5 ${notificationColors[notification.type]}`} />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{notification.title}</p>
                      {!notification.read && (
                        <Badge variant="secondary" className="text-xs">
                          New
                        </Badge>
                      )}
                    </div>
                    <p className="text-muted-foreground text-sm">{notification.message}</p>
                    <p className="text-muted-foreground text-xs">
                      {formatRelativeTime(notification.timestamp)}
                    </p>
                    {notification.actionUrl && (
                      <Button variant="link" size="sm" className="h-auto p-0 text-xs" asChild>
                        <a href={notification.actionUrl}>View details</a>
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        <Button variant="outline" size="sm" className="mt-4 w-full bg-transparent">
          View All Notifications
        </Button>
      </CardContent>
    </Card>
  );
}
