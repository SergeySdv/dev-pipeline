"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Shield, Clock, CheckCircle2, GitBranch, PlayCircle } from "lucide-react"

export default function ProfilePage() {
  const activityLog = [
    { id: "1", action: "Created protocol", target: "CI/CD Pipeline Setup", time: "2 hours ago", icon: PlayCircle },
    { id: "2", action: "Completed run", target: "Code Review Step", time: "3 hours ago", icon: CheckCircle2 },
    { id: "3", action: "Opened PR", target: "Feature: User Authentication", time: "5 hours ago", icon: GitBranch },
    {
      id: "4",
      action: "Updated project",
      target: "E-commerce Web App",
      time: "1 day ago",
      icon: Shield,
    },
  ]

  return (
    <div className="container max-w-5xl py-8">
      <div className="flex items-start gap-6 mb-8">
        <Avatar className="h-24 w-24">
          <AvatarFallback className="bg-primary text-primary-foreground text-2xl">DU</AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <h1 className="text-3xl font-bold mb-2">Demo User</h1>
          <p className="text-muted-foreground mb-4">demo@tasksgodzilla.dev</p>
          <div className="flex gap-2">
            <Badge variant="secondary">
              <Shield className="h-3 w-3 mr-1" />
              Admin
            </Badge>
            <Badge variant="outline">
              <Clock className="h-3 w-3 mr-1" />
              Member since Jan 2024
            </Badge>
          </div>
        </div>
        <Button>Edit Profile</Button>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Personal Information</CardTitle>
              <CardDescription>Update your personal details and contact information.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input id="firstName" placeholder="Demo" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input id="lastName" placeholder="User" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" placeholder="demo@tasksgodzilla.dev" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="company">Company</Label>
                <Input id="company" placeholder="Your company" />
              </div>
              <Button>Save Changes</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>API Access</CardTitle>
              <CardDescription>Manage your API keys and access tokens.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium">Personal Access Token</p>
                  <p className="text-sm text-muted-foreground">Created on Jan 15, 2024</p>
                </div>
                <Button variant="outline" size="sm">
                  Regenerate
                </Button>
              </div>
              <Button variant="outline">Create New Token</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>Manage your password and authentication settings.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <h3 className="font-medium">Change Password</h3>
                <div className="space-y-2">
                  <Label htmlFor="currentPassword">Current Password</Label>
                  <Input id="currentPassword" type="password" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <Input id="newPassword" type="password" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <Input id="confirmPassword" type="password" />
                </div>
                <Button>Update Password</Button>
              </div>
              <Separator />
              <div>
                <h3 className="font-medium mb-4">Two-Factor Authentication</h3>
                <Button variant="outline">Enable 2FA</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>Choose how you want to be notified about events.</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Notification settings coming soon...</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Your recent actions and system events.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {activityLog.map((activity) => {
                  const Icon = activity.icon
                  return (
                    <div key={activity.id} className="flex items-start gap-4 rounded-lg border p-4">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
                        <Icon className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium">{activity.action}</p>
                        <p className="text-sm text-muted-foreground">{activity.target}</p>
                      </div>
                      <time className="text-sm text-muted-foreground">{activity.time}</time>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
