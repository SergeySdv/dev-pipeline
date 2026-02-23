"use client";

import { useState } from "react";

import { Bell, CheckCircle2, Globe, SettingsIcon, Shield,XCircle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiClient, useHealth } from "@/lib/api";

export default function SettingsPage() {
  const [apiBase, setApiBase] = useState(() => apiClient.getConfig().baseUrl);
  const [token, setToken] = useState(() => apiClient.getConfig().token || "");
  const { data: health, isError, refetch } = useHealth();

  const handleSave = () => {
    apiClient.configure({
      baseUrl: apiBase,
      token: token || undefined,
    });
    toast.success("Settings saved successfully");
    refetch();
  };

  return (
    <div className="container max-w-5xl py-8">
      <div className="mb-8">
        <h1 className="mb-2 text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your console configuration and preferences.</p>
      </div>

      <Tabs defaultValue="api" className="space-y-6">
        <TabsList>
          <TabsTrigger value="api">
            <Globe className="mr-2 h-4 w-4" />
            API
          </TabsTrigger>
          <TabsTrigger value="preferences">
            <SettingsIcon className="mr-2 h-4 w-4" />
            Preferences
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <Bell className="mr-2 h-4 w-4" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="security">
            <Shield className="mr-2 h-4 w-4" />
            Security
          </TabsTrigger>
        </TabsList>

        <TabsContent value="api" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>API Configuration</CardTitle>
              <CardDescription>
                Configure the connection to your DevGodzilla API server.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="apiBase">API Base URL</Label>
                <Input
                  id="apiBase"
                  placeholder="http://localhost:8011"
                  value={apiBase}
                  onChange={(e) => setApiBase(e.target.value)}
                />
                <p className="text-muted-foreground text-xs">
                  The base URL of your DevGodzilla API server
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="token">API Token (optional)</Label>
                <Input
                  id="token"
                  type="password"
                  placeholder="Enter your API token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                />
                <p className="text-muted-foreground text-xs">Bearer token for API authentication</p>
              </div>
              <Button onClick={handleSave}>Save Configuration</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Connection Status</CardTitle>
              <CardDescription>Current connection status to the API server.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3 rounded-lg border p-4">
                {health?.status === "ok" ? (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <div className="flex-1">
                      <p className="font-medium text-green-500">Connected</p>
                      <p className="text-muted-foreground text-sm">
                        API server is responding normally
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => refetch()}>
                      Test Connection
                    </Button>
                  </>
                ) : (
                  <>
                    <XCircle className="text-destructive h-5 w-5" />
                    <div className="flex-1">
                      <p className="text-destructive font-medium">Disconnected</p>
                      <p className="text-muted-foreground text-sm">
                        {isError ? "Unable to reach API server" : "Checking connection..."}
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => refetch()}>
                      Retry
                    </Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Display Preferences</CardTitle>
              <CardDescription>Customize how the console displays information.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Dark Mode</p>
                  <p className="text-muted-foreground text-sm">Always use dark theme</p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Compact View</p>
                  <p className="text-muted-foreground text-sm">
                    Show more items in tables and lists
                  </p>
                </div>
                <Switch />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Auto-refresh Data</p>
                  <p className="text-muted-foreground text-sm">
                    Automatically refresh active protocol data
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Timezone</CardTitle>
              <CardDescription>
                Set your preferred timezone for displaying dates and times.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Input id="timezone" placeholder="UTC" />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Settings</CardTitle>
              <CardDescription>Choose when and how you want to be notified.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Protocol Completion</p>
                  <p className="text-muted-foreground text-sm">
                    Notify when protocols finish executing
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Policy Violations</p>
                  <p className="text-muted-foreground text-sm">Alert on policy check failures</p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Run Failures</p>
                  <p className="text-muted-foreground text-sm">Notify when runs encounter errors</p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">System Alerts</p>
                  <p className="text-muted-foreground text-sm">Important system notifications</p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>Manage security and access control settings.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Require Authentication</p>
                  <p className="text-muted-foreground text-sm">
                    Require API token for all requests
                  </p>
                </div>
                <Switch />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Session Timeout</p>
                  <p className="text-muted-foreground text-sm">
                    Auto-logout after 30 minutes of inactivity
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Audit Logging</p>
                  <p className="text-muted-foreground text-sm">
                    Log all API requests for audit trail
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
