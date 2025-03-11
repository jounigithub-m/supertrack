'use client';

import React from 'react';
import Image from 'next/image';
import { BarChart, Clock, ArrowUpRight, Users, Database, Bot, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import DashboardLayout from '@/components/layout/dashboard-layout';

const DashboardPage = () => {
  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <h1 className="text-3xl font-semibold">Dashboard</h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 flex items-center gap-4">
              <div className="bg-blue-100 dark:bg-blue-800/30 p-3 rounded-full">
                <Users className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Users</p>
                <h2 className="text-2xl font-semibold">2,543</h2>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center gap-4">
              <div className="bg-green-100 dark:bg-green-800/30 p-3 rounded-full">
                <Database className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Data Sources</p>
                <h2 className="text-2xl font-semibold">87</h2>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center gap-4">
              <div className="bg-purple-100 dark:bg-purple-800/30 p-3 rounded-full">
                <Bot className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">AI Models</p>
                <h2 className="text-2xl font-semibold">12</h2>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center gap-4">
              <div className="bg-orange-100 dark:bg-orange-800/30 p-3 rounded-full">
                <Activity className="h-6 w-6 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Active Projects</p>
                <h2 className="text-2xl font-semibold">34</h2>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Analytics Overview</CardTitle>
              <CardDescription>
                Your platform usage over the last 30 days
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80 flex items-center justify-center">
                <BarChart className="h-20 w-20 text-muted-foreground" />
                <p className="text-muted-foreground ml-4">Chart visualization will appear here</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Activities</CardTitle>
              <CardDescription>Latest actions across your projects</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-start gap-4">
                    <div className="bg-gray-100 dark:bg-gray-800 p-2 rounded-full">
                      <Clock className="h-4 w-4 text-primary" />
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-medium">
                        Data source {i} was updated
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {i * 12} minutes ago by User{i}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>Frequently used features</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  'Import New Data Source',
                  'Create AI Model',
                  'Generate Report',
                  'Manage Team Access',
                ].map((action, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted cursor-pointer"
                  >
                    <span className="font-medium text-sm">{action}</span>
                    <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Latest Platform Updates</CardTitle>
              <CardDescription>New features and improvements</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="border-l-4 border-primary pl-4 space-y-1">
                  <h3 className="text-base font-medium">New Data Processing Engine</h3>
                  <p className="text-sm text-muted-foreground">
                    We've upgraded our data processing capabilities, increasing speed by up to 40%.
                  </p>
                  <p className="text-xs text-muted-foreground">Released 3 days ago</p>
                </div>
                <div className="border-l-4 border-primary pl-4 space-y-1">
                  <h3 className="text-base font-medium">Enhanced Security Features</h3>
                  <p className="text-sm text-muted-foreground">
                    Added additional encryption layers and improved authentication mechanisms.
                  </p>
                  <p className="text-xs text-muted-foreground">Released 1 week ago</p>
                </div>
                <div className="border-l-4 border-primary pl-4 space-y-1">
                  <h3 className="text-base font-medium">User Interface Improvements</h3>
                  <p className="text-sm text-muted-foreground">
                    Redesigned dashboard and improved navigation for better usability.
                  </p>
                  <p className="text-xs text-muted-foreground">Released 2 weeks ago</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default DashboardPage;