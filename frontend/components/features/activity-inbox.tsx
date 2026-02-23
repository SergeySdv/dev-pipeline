"use client";

import { useState } from "react";

import { AlertCircle, Bell, Check, Clock, GitPullRequest, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface Notification {
  id: string;
  type: "protocol" | "clarification" | "job" | "pr" | "ci";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  link?: string;
}

const NOW = Date.now();

const DEFAULT_NOTIFICATIONS: Notification[] = [
  {
    id: "1",
    type: "protocol",
    title: "Protocol Completed",
    message: "Web App Onboarding completed successfully",
    timestamp: new Date(NOW - 5 * 60000).toISOString(),
    read: false,
  },
  {
    id: "2",
    type: "clarification",
    title: "Clarification Requested",
    message: "Need input on database migration strategy",
    timestamp: new Date(NOW - 15 * 60000).toISOString(),
    read: false,
  },
  {
    id: "3",
    type: "job",
    title: "Job Failed",
    message: "Code execution run failed with exit code 1",
    timestamp: new Date(NOW - 30 * 60000).toISOString(),
    read: true,
  },
  {
    id: "4",
    type: "pr",
    title: "PR Opened",
    message: "New pull request created: feat/user-auth",
    timestamp: new Date(NOW - 60 * 60000).toISOString(),
    read: true,
  },
];

export function ActivityInbox() {
  const [notifications, setNotifications] = useState<Notification[]>(DEFAULT_NOTIFICATIONS);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAsRead = (id: string) => {
    setNotifications(notifications.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const markAllAsRead = () => {
    setNotifications(notifications.map((n) => ({ ...n, read: true })));
  };

  const dismissNotification = (id: string) => {
    setNotifications(notifications.filter((n) => n.id !== id));
  };

  const getIcon = (type: Notification["type"]) => {
    switch (type) {
      case "protocol":
        return Clock;
      case "clarification":
        return AlertCircle;
      case "job":
        return AlertCircle;
      case "pr":
        return GitPullRequest;
      case "ci":
        return Check;
      default:
        return Bell;
    }
  };

  return (
    <div className="bg-background flex h-full w-96 flex-col border-l">
      <div className="flex items-center justify-between border-b p-4">
        <div className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          <h2 className="font-semibold">Notifications</h2>
          {unreadCount > 0 && (
            <Badge variant="destructive" className="h-5 px-1.5">
              {unreadCount}
            </Badge>
          )}
        </div>
        {unreadCount > 0 && (
          <Button variant="ghost" size="sm" onClick={markAllAsRead}>
            Mark all read
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1">
        <div className="divide-y">
          {notifications.map((notification) => {
            const Icon = getIcon(notification.type);
            return (
              <div
                key={notification.id}
                className={cn(
                  "hover:bg-muted/50 group p-4 transition-colors",
                  !notification.read && "bg-blue-500/5"
                )}
              >
                <div className="flex gap-3">
                  <div
                    className={cn(
                      "mt-0.5",
                      notification.type === "job" && "text-red-500",
                      notification.type === "clarification" && "text-yellow-500",
                      notification.type === "protocol" && "text-blue-500",
                      notification.type === "pr" && "text-green-500"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-start justify-between">
                      <p
                        className={cn("text-sm font-medium", !notification.read && "font-semibold")}
                      >
                        {notification.title}
                      </p>
                      <button
                        onClick={() => dismissNotification(notification.id)}
                        className="opacity-0 transition-opacity group-hover:opacity-100"
                      >
                        <X className="text-muted-foreground hover:text-foreground h-4 w-4" />
                      </button>
                    </div>
                    <p className="text-muted-foreground text-sm">{notification.message}</p>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground text-xs">
                        {new Date(notification.timestamp).toLocaleTimeString()}
                      </span>
                      {!notification.read && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 text-xs"
                          onClick={() => markAsRead(notification.id)}
                        >
                          Mark read
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
